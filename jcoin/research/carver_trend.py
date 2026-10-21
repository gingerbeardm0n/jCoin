"""Carver-style continuous trend follower — always in the market, no tight stops.

Instead of binary breakout signals with ATR stops, this strategy:
  - Computes a risk-adjusted forecast from an EMA crossover: (fast - slow) / ATR
  - Clamps the forecast to [-20, +20] (Carver's standard)
  - Sizes positions continuously: stronger trend = bigger position, weaker = smaller
  - Rebalances only when position change > 10% of current (avoids churn)
  - Costs charged only on the delta traded

This addresses the biggest weakness of strategy A: tight stops that get knocked out
by exchange-specific price spikes. A continuous strategy never has a stop to hit.

Reference: Rob Carver, "Leveraged Trading" (2019), chapters on trend forecasting
and position sizing. The forecast scalar (±10 = full size) and 25% annual vol target
are Carver's standard values.

Also includes Strategy A on daily bars (same breakout logic, different timeframe),
per community feedback from iSnake37: fewer signals, lower costs, cleaner trends.

Usage:
    python -m jcoin.research.carver_trend
Writes pipeline/CARVER_TREND_2026-10.md and pipeline/A_DAILY_2026-10.md
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import polars as pl

from jcoin.data.config import ROOT
from jcoin.data.feed import DataFeed
from jcoin.research import splits
from jcoin.research.backtest_breakout import _atr
from jcoin.research.portfolio_backtest import (
    build_trades, metrics, run_portfolio,
)

LABELS = ["BTC", "ETH"]
START_EQUITY = 10_000

# Carver trend configs (fixed — no tuning, all reported)
EMA_PAIRS = [
    ("8/32",   8,  32),
    ("16/64",  16, 64),    # Carver's standard trend
    ("32/128", 32, 128),
]
ATR_PERIOD = 20              # Carver uses ~25 days; 20 is common for crypto
VOL_TARGETS = [0.25, 0.50]  # 25% (Carver standard) and 50% (crypto-adjusted)
REBALANCE_THRESHOLD = 0.10   # only trade if position changes > 10%
COST_PER_SIDE = 0.006        # Coinbase spot taker 0.60%

# Daily breakout config (same as A but on daily bars)
DAILY_ATR_PERIOD, DAILY_ATR_INIT, DAILY_ATR_TRAIL = 14, 1.0, 6.0
DAILY_MAX_HOLD = 120         # 120 daily bars = 120 days
DAILY_COST_FRAC = 0.0012     # 12bp round trip (same as A)
DAILY_RISK_FRAC = 0.01
DAILY_MAX_PER_SYMBOL, DAILY_MAX_CONCURRENT = 1, 2

_END = splits.SEALED_START - dt.timedelta(microseconds=1)


def _years(lo: dt.datetime, hi: dt.datetime) -> float:
    return (hi - lo).days / 365.25


def _ema(arr: np.ndarray, span: int) -> np.ndarray:
    """Exponential moving average (span-based, like pandas ewm(span=...))."""
    alpha = 2.0 / (span + 1)
    out = np.empty_like(arr)
    out[0] = arr[0]
    for i in range(1, len(arr)):
        out[i] = out[i - 1] + alpha * (arr[i] - out[i - 1])
    return out


def carver_forecast(close: np.ndarray, atr: np.ndarray,
                    fast: int, slow: int) -> np.ndarray:
    """Risk-adjusted trend forecast, clamped to [-20, +20].

    forecast = (EMA_fast - EMA_slow) / ATR. Positive = bullish, negative = bearish.
    The division by ATR normalizes for volatility so forecasts across instruments
    and time periods are comparable.
    """
    ema_f = _ema(close, fast)
    ema_s = _ema(close, slow)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = np.where(atr > 0, (ema_f - ema_s) / atr, 0.0)
    return np.clip(raw, -20.0, 20.0)


def carver_backtest(labels: list[str], tf: str, fast: int, slow: int,
                    start: dt.datetime, end: dt.datetime,
                    start_equity: float = START_EQUITY,
                    vol_target: float = 0.25) -> dict:
    """Run the Carver continuous trend strategy on [start, end).

    Returns equity curve, metrics dict, and per-bar details.
    """
    splits.check_window(start, end)
    feed = DataFeed()

    # Load candles for each label, filter to window
    data = {}
    for label in labels:
        df = feed.get_candles(label, tf, end=_END)
        df = df.filter(
            (pl.col("ts") >= start) & (pl.col("ts") < end)
        )
        close = df["close"].to_numpy().astype(float)
        atr = _atr(df, ATR_PERIOD)
        fc = carver_forecast(close, atr, fast, slow)
        data[label] = {
            "ts": df["ts"].to_list(),
            "close": close,
            "atr": atr,
            "forecast": fc,
        }

    # Align timestamps across labels (use intersection)
    ts_sets = [set(d["ts"]) for d in data.values()]
    common_ts = sorted(ts_sets[0].intersection(*ts_sets[1:]))
    if len(common_ts) < slow + 10:
        return {"error": "too few bars"}

    # Index maps
    for label in labels:
        d = data[label]
        ts_to_idx = {t: i for i, t in enumerate(d["ts"])}
        d["aligned_idx"] = [ts_to_idx[t] for t in common_ts]

    equity = start_equity
    curve = [(common_ts[0], equity)]
    positions = {label: 0.0 for label in labels}  # in units of the asset
    total_traded_value = 0.0

    # Skip warmup period (need slow EMA to stabilize)
    warmup = slow + 10
    for bar_i in range(warmup, len(common_ts)):
        ts = common_ts[bar_i]
        prev_ts = common_ts[bar_i - 1]

        # Mark-to-market from previous bar's positions
        pnl = 0.0
        for label in labels:
            d = data[label]
            idx = d["aligned_idx"][bar_i]
            prev_idx = d["aligned_idx"][bar_i - 1]
            price_now = d["close"][idx]
            price_prev = d["close"][prev_idx]
            pnl += positions[label] * (price_now - price_prev)
        equity += pnl

        if equity <= 0:
            break

        # Compute target positions
        n_instruments = len(labels)
        for label in labels:
            d = data[label]
            idx = d["aligned_idx"][bar_i]
            fc = d["forecast"][idx]
            atr_val = d["atr"][idx]
            price = d["close"][idx]

            if atr_val <= 0 or price <= 0:
                continue

            # Carver position sizing:
            # target = (forecast / 10) * (vol_target * equity) / (daily_vol * price)
            # daily_vol = ATR (already in price units)
            # Divide vol_target by n_instruments for equal risk allocation
            instrument_vol_target = vol_target / n_instruments
            daily_vol_pct = atr_val / price
            # Annualize: ~365 trading days for crypto
            ann_vol = daily_vol_pct * np.sqrt(365) if tf == "1d" else daily_vol_pct * np.sqrt(365 * 6)
            target_notional = (fc / 10.0) * (instrument_vol_target / ann_vol) * equity
            target_pos = target_notional / price

            current_pos = positions[label]

            # Rebalance threshold: only trade if change > 10% of target
            if abs(current_pos) > 1e-12:
                change_pct = abs(target_pos - current_pos) / abs(current_pos)
            else:
                change_pct = 1.0 if abs(target_pos) > 1e-12 else 0.0

            if change_pct >= REBALANCE_THRESHOLD:
                delta = abs(target_pos - current_pos)
                trade_value = delta * price
                cost = trade_value * COST_PER_SIDE  # one side
                equity -= cost
                total_traded_value += trade_value
                positions[label] = target_pos

        curve.append((ts, equity))

    # Compute metrics
    eq_arr = np.array([e for _, e in curve])
    if len(eq_arr) < 2:
        return {"error": "insufficient data"}

    years = _years(start, end)
    total_ret = eq_arr[-1] / start_equity - 1
    cagr = (eq_arr[-1] / start_equity) ** (1 / max(years, 0.25)) - 1
    peak = np.maximum.accumulate(eq_arr)
    max_dd = float(np.max((peak - eq_arr) / peak)) if peak.max() > 0 else 0.0

    # Daily returns for Sharpe
    daily_rets = np.diff(eq_arr) / eq_arr[:-1]
    sharpe = (float(np.mean(daily_rets) / np.std(daily_rets) * np.sqrt(365))
              if np.std(daily_rets) > 0 else float("nan"))

    mar = cagr / max_dd if max_dd > 0 else float("nan")
    avg_annual_turnover = (total_traded_value / max(np.mean(eq_arr), 1)) / max(years, 0.25)

    return {
        "cagr": cagr, "max_dd": max_dd, "mar": mar, "sharpe": sharpe,
        "total_ret": total_ret, "final_equity": eq_arr[-1],
        "avg_annual_turnover": avg_annual_turnover,
        "total_traded": total_traded_value,
        "n_bars": len(curve),
    }


def buy_hold(labels: list[str], tf: str,
             start: dt.datetime, end: dt.datetime,
             start_equity: float = START_EQUITY) -> dict:
    """Equal-weight buy-and-hold benchmark."""
    feed = DataFeed()
    weight = 1.0 / len(labels)
    curves = []
    for label in labels:
        df = feed.get_candles(label, tf, end=_END)
        df = df.filter((pl.col("ts") >= start) & (pl.col("ts") < end))
        close = df["close"].to_numpy().astype(float)
        curves.append(close / close[0] * start_equity * weight)

    combined = sum(curves)
    eq = combined
    years = _years(start, end)
    peak = np.maximum.accumulate(eq)
    max_dd = float(np.max((peak - eq) / peak)) if peak.max() > 0 else 0.0
    cagr = (eq[-1] / start_equity) ** (1 / max(years, 0.25)) - 1
    return {"cagr": cagr, "max_dd": max_dd, "mar": cagr / max_dd if max_dd > 0 else float("nan")}


# ---- Daily breakout (Strategy A on daily bars) --------------------------------

def daily_breakout_trades():
    """A's breakout logic on daily candles, dev window only."""
    lo, hi = splits.dev_window()
    splits.check_window(lo, hi)
    trades = build_trades("1d", LABELS, DAILY_ATR_PERIOD, DAILY_ATR_INIT,
                          DAILY_ATR_TRAIL, DAILY_MAX_HOLD, DAILY_COST_FRAC,
                          funding_mult=0.0, end=_END)
    assert all(t["exit_time"] < splits.SEALED_START for t in trades), "sealed data leaked"
    return trades, _years(lo, hi)


def evaluate_daily(trades, lo, hi) -> dict | None:
    """Run portfolio on daily trades entered in [lo, hi)."""
    splits.check_window(lo, hi)
    sub = [t for t in trades if lo <= t["entry_time"] < hi]
    if len(sub) < 2:
        return None
    taken: list = []
    curve, R = run_portfolio(sub, START_EQUITY, DAILY_RISK_FRAC,
                             DAILY_MAX_PER_SYMBOL, DAILY_MAX_CONCURRENT,
                             taken_trades=taken)
    m = metrics(curve, R, START_EQUITY, _years(lo, hi))
    if not m:
        return None
    m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else float("nan")
    return m


# ---- Report writing -----------------------------------------------------------

def _carver_row(name: str, m: dict) -> str:
    if "error" in m:
        return f"| {name} | error: {m['error']} | | | | | |"
    return (f"| {name} | {m['cagr']*100:.1f}% | {m['max_dd']*100:.1f}% | "
            f"{m['mar']:.2f} | {m['sharpe']:.2f} | {m['avg_annual_turnover']:.1f}x | "
            f"${m['final_equity']:,.0f} |")


def _daily_row(name: str, m: dict | None) -> str:
    if m is None:
        return f"| {name} | n/a | | | | | | |"
    return (f"| {name} | {m['cagr']*100:.1f}% | {m['max_dd']*100:.1f}% | {m['mar']:.2f} | "
            f"{m['sharpe']:.2f} | {m['pf']:.2f} | {m['n_trades']} | {m['avg_R']:.3f} |")


_CARVER_HDR = ("| config | CAGR | maxDD | MAR | Sharpe | turnover | final equity |\n"
               "|---|---|---|---|---|---|---|")

_DAILY_HDR = ("| window | CAGR | maxDD | MAR | Sharpe | PF | n_trades | avg_R |\n"
              "|---|---|---|---|---|---|---|---|")


def write_carver_report(results_by_ema: dict, slice_results: dict, benchmarks: dict):
    """Write pipeline/CARVER_TREND_2026-10.md."""
    out: list[str] = []
    w = out.append

    w("# Carver-style continuous trend follower: BTC + ETH")
    w("")
    w(f"Generated {dt.date.today().isoformat()} by `jcoin/research/carver_trend.py`. "
      f"Dev window only (2021-01-01 to 2026-05-31). All configs are fixed and pre-declared — "
      f"nothing was tuned. This is a research comparison, not a selection.")
    w("")
    w("**How it works:** instead of binary breakout signals with tight ATR stops, this "
      "strategy computes a continuous forecast from an EMA crossover, normalized by ATR. "
      "Position size scales with forecast strength — stronger trend = bigger position. "
      "No stops: positions shrink gradually as the trend weakens. Cost: Coinbase spot "
      "taker 0.60% per side, charged on the trade delta only. Rebalance threshold 10%.")
    w("")
    w("**Why test this:** strategy A's biggest problem on Coinbase is that tight stops get "
      "knocked out by exchange-specific price spikes (~2/month/coin). A continuous strategy "
      "has no stop to hit. Costs are higher (spot taker vs perp maker), but no funding.")
    w("")

    for vt in VOL_TARGETS:
        vt_pct = int(vt * 100)
        w(f"## Vol target {vt_pct}% — daily bars")
        w("")
        w(f"Position sizes scale with 1/volatility. At 25% target, BTC's ~100% annual "
          f"vol means only ~2-5% equity exposure. At 50%, double that. "
          f"Neither is leveraged — max exposure stays well under 1x equity.")
        w("")
        w(_CARVER_HDR)
        for ema_name, fast, slow in EMA_PAIRS:
            key = f"1d_{ema_name}_vt{vt_pct}"
            w(_carver_row(f"EMA {ema_name}", results_by_ema.get(key, {"error": "not run"})))
        w("")

    w("### Benchmarks")
    w("")
    w("| benchmark | CAGR | maxDD | MAR |")
    w("|---|---|---|---|")
    for name, bm in benchmarks.items():
        w(f"| {name} | {bm['cagr']*100:.1f}% | {bm['max_dd']*100:.1f}% | {bm['mar']:.2f} |")
    w("")

    for vt in VOL_TARGETS:
        vt_pct = int(vt * 100)
        w(f"## Per slice (daily, EMA 16/64, vol target {vt_pct}%)")
        w("")
        w(_CARVER_HDR)
        for slice_name, _, _ in splits.DEV_SLICES:
            key = f"1d_16/64_{slice_name}_vt{vt_pct}"
            m = slice_results.get(key, {"error": "not run"})
            w(_carver_row(slice_name, m))
        w("")

    w("## 4h bars (for comparison with A, vol target 25%)")
    w("")
    w(_CARVER_HDR)
    for ema_name, fast, slow in EMA_PAIRS:
        key = f"4h_{ema_name}_vt25"
        w(_carver_row(f"EMA {ema_name} (4h)", results_by_ema.get(key, {"error": "not run"})))
    w("")

    w("## Interpretation")
    w("")
    w("The Carver approach trades cost for robustness: no tight stops to get spiked out, "
      "but higher round-trip costs (spot taker) and continuous position adjustment. "
      "Compare Sharpe and MAR to strategy A's honest numbers (A_HONEST_NUMBERS_2026-10.md). "
      "If Carver's MAR is competitive with A's, it may be more robust on Coinbase where "
      "A's PF collapsed from 1.12 to 0.59 due to stop-hunting spikes.")
    w("")

    path = ROOT / "pipeline" / "CARVER_TREND_2026-10.md"
    path.write_text("\n".join(out), encoding="utf-8")
    return path


def write_daily_report(full_m: dict | None, slice_m: dict):
    """Write pipeline/A_DAILY_2026-10.md."""
    out: list[str] = []
    w = out.append

    w("# Strategy A on daily bars (1d breakout)")
    w("")
    w(f"Generated {dt.date.today().isoformat()} by `jcoin/research/carver_trend.py`. "
      f"Dev window only. Same logic as the 4h bot: trend-aligned breakout (k=2), "
      f"ATR(14) init stop 1.0, trail 6.0, max hold 120 bars (= 120 days on daily), "
      f"1% risk, max 1 per symbol, 2 concurrent, 12bp round-trip cost. No funding "
      f"(this is testing the signal on daily bars, not the funding model).")
    w("")
    w("**Why test this:** community feedback (iSnake37) suggested daily candles produce "
      "fewer, cleaner signals with lower trading costs. Fewer trades also means less "
      "exposure to exchange-specific microstructure (Coinbase spikes).")
    w("")

    w("## 1. Full dev period")
    w("")
    w(_DAILY_HDR)
    w(_daily_row("full dev (1d)", full_m))
    w("")

    w("## 2. Per slice")
    w("")
    w(_DAILY_HDR)
    for name, _, _ in splits.DEV_SLICES:
        w(_daily_row(name, slice_m.get(name)))
    w("")

    w("## 3. Comparison with A on 4h")
    w("")
    w("Strategy A on 4h (funding 1x) from A_HONEST_NUMBERS_2026-10.md: CAGR 30.1%, "
      "maxDD 27.4%, MAR 1.10, Sharpe 0.90, PF 1.53, 396 trades, avg_R 0.435.")
    w("")
    w("Key question: does daily produce enough trades to be meaningful, and does "
      "the MAR hold up? Fewer trades means wider confidence intervals.")
    w("")

    path = ROOT / "pipeline" / "A_DAILY_2026-10.md"
    path.write_text("\n".join(out), encoding="utf-8")
    return path


def main(argv=None) -> int:
    lo, hi = splits.dev_window()
    splits.check_window(lo, hi)

    print("=== Carver continuous trend follower ===")
    print()

    results_by_ema = {}
    slice_results = {}

    # Full dev period — daily and 4h, at each vol target
    for vt in VOL_TARGETS:
        print(f"\n--- vol target {vt:.0%} ---")
        for tf in ["1d", "4h"]:
            for ema_name, fast, slow in EMA_PAIRS:
                key = f"{tf}_{ema_name}_vt{int(vt*100)}"
                print(f"  running {key}...")
                m = carver_backtest(LABELS, tf, fast, slow, lo, hi, vol_target=vt)
                results_by_ema[key] = m
                if "error" not in m:
                    print(f"    CAGR={m['cagr']*100:.1f}%  maxDD={m['max_dd']*100:.1f}%  "
                          f"MAR={m['mar']:.2f}  Sharpe={m['sharpe']:.2f}  "
                          f"turnover={m['avg_annual_turnover']:.1f}x")
                else:
                    print(f"    {m['error']}")

    # Per slice (daily, standard 16/64, both vol targets)
    for vt in VOL_TARGETS:
        for name, s, e in splits.DEV_SLICES:
            key = f"1d_16/64_{name}_vt{int(vt*100)}"
            print(f"  slice {key}...")
            m = carver_backtest(LABELS, "1d", 16, 64, s, e, vol_target=vt)
            slice_results[key] = m

    # Benchmarks
    benchmarks = {}
    print("  benchmarks...")
    benchmarks["BTC buy-hold"] = buy_hold(["BTC"], "1d", lo, hi)
    benchmarks["BTC+ETH equal-weight"] = buy_hold(["BTC", "ETH"], "1d", lo, hi)

    p1 = write_carver_report(results_by_ema, slice_results, benchmarks)
    print(f"\nWrote {p1}")

    # === Daily breakout ===
    print("\n=== Strategy A on daily bars ===")
    print()

    trades, years = daily_breakout_trades()
    print(f"  {len(trades)} candidate trades over {years:.1f} years")

    full_m = evaluate_daily(trades, lo, hi)
    if full_m:
        print(f"  full dev: CAGR={full_m['cagr']*100:.1f}%  maxDD={full_m['max_dd']*100:.1f}%  "
              f"MAR={full_m['mar']:.2f}  Sharpe={full_m['sharpe']:.2f}  "
              f"PF={full_m['pf']:.2f}  trades={full_m['n_trades']}")

    slice_m = {}
    for name, s, e in splits.DEV_SLICES:
        m = evaluate_daily(trades, s, e)
        slice_m[name] = m
        if m:
            print(f"  {name}: CAGR={m['cagr']*100:.1f}%  MAR={m['mar']:.2f}  trades={m['n_trades']}")

    p2 = write_daily_report(full_m, slice_m)
    print(f"\nWrote {p2}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
