"""Cycle-filtered backtest — does disabling trades in bear phase improve performance?

Fetches BTC + ETH 4h from 2019-09 (Binance USDT-M futures launch) for ~2.5x more
history than our current 2021 dataset. Compares three scenarios:

  A) No filter:        trade all bars (current behaviour)
  B) Cycle filter:     disable ALL entries when cycle_phase == 'bear'
  C) Bull-only stats:  show per-phase breakdown to understand where edge lives

Cycle filter uses price-only indicators (no on-chain data):
  - 365-day SMA: close below SMA = bear
  - Pi Cycle Top: 111-day SMA > 2x 350-day SMA = top (immediate bear)

Usage:
    python -m jcoin.research.cycle_backtest
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import polars as pl

from jcoin.data.fetch_binance_vision import _BASE, _download, _month_range, _parse_zip
from jcoin.engine.features import compute_features
from jcoin.research.portfolio_backtest import metrics, run_portfolio
from jcoin.strategy.cycle import CYCLE_BEAR, CYCLE_BULL, CYCLE_UNKNOWN, add_cycle_filter

UTC = dt.timezone.utc
TF = "4h"
EXTENDED_START = "2019-09"   # Binance USDT-M futures launched Sep 2019
K, ATRP, INIT, TRAIL, HOLD = 2, 14, 1.0, 6.0, 120
COST_FRAC, RISK = 0.0012, 0.01

LABELS = ["BTC", "ETH"]
SYMBOLS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}

# Store extended data separately to avoid clobbering breadth study parquets
_EXT_DIR = Path(__file__).parent.parent.parent / "data" / "ohlcv" / "extended"


def _fetch_extended(symbol: str, label: str) -> pl.DataFrame:
    path = _EXT_DIR / label / "4h.parquet"
    if path.exists():
        print(f"  {label}: using cached {path}")
        return pl.read_parquet(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"  {label}: downloading from {EXTENDED_START}...", end="", flush=True)
    start_date = dt.datetime.strptime(EXTENDED_START, "%Y-%m").date().replace(day=1)
    today = dt.datetime.now(dt.timezone.utc).date()
    last_complete = today.replace(day=1) - dt.timedelta(days=1)
    frames = []
    for y, m in _month_range(start_date, last_complete):
        blob = _download(f"{_BASE}/monthly/klines/{symbol}/{TF}/{symbol}-{TF}-{y}-{m:02d}.zip")
        if blob:
            frames.append(_parse_zip(blob))
    if not frames:
        raise RuntimeError(f"no 4h data for {symbol}")
    df = pl.concat(frames).unique(subset=["ts"], keep="last").sort("ts")
    df.write_parquet(path)
    print(f" {len(df):,} bars saved.")
    return df


def _load_features(label: str) -> pl.DataFrame:
    df = _fetch_extended(SYMBOLS[label], label)
    df = df.with_columns(
        pl.from_epoch(pl.col("ts"), time_unit="ms").dt.replace_time_zone("UTC").alias("ts")
    ).sort("ts")
    feat = compute_features(df, k=K, atr_period=ATRP)
    return add_cycle_filter(feat)   # adds sma_365, pi_cycle_top, cycle_phase


def _sim(feat: pl.DataFrame, label: str, use_cycle_filter: bool):
    """Simulate trades. If use_cycle_filter, skip entries in bear phase."""
    high = feat["high"].to_numpy()
    low = feat["low"].to_numpy()
    close = feat["close"].to_numpy()
    atr = feat["atr"].to_numpy()
    regime = feat["regime"].to_numpy()
    bl = feat["brk_long"].to_numpy()
    bs = feat["brk_short"].to_numpy()
    cycle = feat["cycle_phase"].to_list()
    ts = feat["ts"].to_list()
    n = len(close)
    trades = []
    for i in range(n):
        if use_cycle_filter and cycle[i] == CYCLE_BEAR:
            continue
        if bl[i] and regime[i] == "uptrend":
            long = True
        elif bs[i] and regime[i] == "downtrend":
            long = False
        else:
            continue
        if i + 1 >= n or atr[i] <= 0:
            continue
        entry, a = close[i], atr[i]
        stop = entry - INIT * a if long else entry + INIT * a
        sd = abs(entry - stop) / entry
        if sd <= 0:
            continue
        best = high[i] if long else low[i]
        exit_price, exit_idx = None, min(i + HOLD, n - 1)
        for j in range(i + 1, min(i + 1 + HOLD, n)):
            if long:
                if low[j] <= stop:
                    exit_price, exit_idx = stop, j; break
                best = max(best, high[j]); stop = max(stop, best - TRAIL * a)
            else:
                if high[j] >= stop:
                    exit_price, exit_idx = stop, j; break
                best = min(best, low[j]); stop = min(stop, best + TRAIL * a)
        if exit_price is None:
            exit_price = close[exit_idx]
        gross = (exit_price - entry) / entry if long else (entry - exit_price) / entry
        trades.append({
            "symbol": label, "entry_time": ts[i], "exit_time": ts[exit_idx],
            "side": "long" if long else "short",
            "R": (gross - COST_FRAC) / sd,
            "cycle": cycle[i],
        })
    return sorted(trades, key=lambda t: t["entry_time"])


def _eval(trades, lo=None, hi=None):
    sub = trades if lo is None else [t for t in trades if lo <= t["entry_time"] < hi]
    if len(sub) < 10:
        return None
    curve, R = run_portfolio(sub, 10_000, RISK, 1, 2)
    span = (sub[-1]["exit_time"] - sub[0]["entry_time"]).days / 365.25
    m = metrics(curve, R, 10_000, max(span, 0.5))
    m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else 0.0
    return m


def _phase_summary(trades):
    """Break out trade stats by cycle phase."""
    by_phase = {}
    for t in trades:
        ph = t.get("cycle", CYCLE_UNKNOWN)
        by_phase.setdefault(ph, []).append(t)
    results = {}
    for ph, sub in by_phase.items():
        if len(sub) >= 5:
            curve, R = run_portfolio(sub, 10_000, RISK, 1, 2)
            span = (sub[-1]["exit_time"] - sub[0]["entry_time"]).days / 365.25
            m = metrics(curve, R, 10_000, max(span, 0.5))
            m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else 0.0
            m["n_raw"] = len(sub)
            results[ph] = m
    return results


def main() -> int:
    print(f"CYCLE FILTER BACKTEST | {LABELS} | 4h | 2019-09 to present\n")
    print("Downloading / loading extended history...")
    feats = {}
    for label in LABELS:
        feats[label] = _load_features(label)
        span_days = (feats[label]["ts"].max() - feats[label]["ts"].min()).days
        n_bear = (feats[label]["cycle_phase"] == CYCLE_BEAR).sum()
        n_bull = (feats[label]["cycle_phase"] == CYCLE_BULL).sum()
        print(f"  {label}: {len(feats[label]):,} bars  "
              f"bull={n_bull:,} bear={n_bear:,}  ({span_days//365:.1f} yrs)")

    print()

    # ---- A) No cycle filter (current behaviour) ----
    print("=== A) NO CYCLE FILTER (current behaviour) ===")
    trades_all = []
    for label in LABELS:
        trades_all += _sim(feats[label], label, use_cycle_filter=False)
    trades_all.sort(key=lambda t: t["entry_time"])
    m_all = _eval(trades_all)
    if m_all:
        print(f"  CAGR={m_all['cagr']*100:.0f}%  maxDD={m_all['max_dd']*100:.0f}%  "
              f"MAR={m_all['mar']:.2f}  PF={m_all['pf']:.2f}  n={m_all['n_trades']}")

    # ---- B) Cycle filter active ----
    print("\n=== B) WITH CYCLE FILTER (no entries in bear phase) ===")
    trades_filt = []
    for label in LABELS:
        trades_filt += _sim(feats[label], label, use_cycle_filter=True)
    trades_filt.sort(key=lambda t: t["entry_time"])
    m_filt = _eval(trades_filt)
    if m_filt:
        print(f"  CAGR={m_filt['cagr']*100:.0f}%  maxDD={m_filt['max_dd']*100:.0f}%  "
              f"MAR={m_filt['mar']:.2f}  PF={m_filt['pf']:.2f}  n={m_filt['n_trades']}")

    # ---- C) Per-phase breakdown ----
    print("\n=== C) PER-PHASE BREAKDOWN (no filter, split by phase) ===")
    all_by_phase = {}
    for t in trades_all:
        ph = t.get("cycle", CYCLE_UNKNOWN)
        all_by_phase.setdefault(ph, []).append(t)
    print(f"  {'phase':<10} {'CAGR':>6} {'maxDD':>6} {'MAR':>5} {'PF':>5} {'win%':>5} "
          f"{'n_taken':>8} {'n_raw':>7}")
    for ph in [CYCLE_BULL, CYCLE_BEAR, CYCLE_UNKNOWN]:
        sub = all_by_phase.get(ph, [])
        if len(sub) < 5:
            print(f"  {ph:<10}  (< 5 trades, skip)")
            continue
        curve, R = run_portfolio(sub, 10_000, RISK, 1, 2)
        span = (sub[-1]["exit_time"] - sub[0]["entry_time"]).days / 365.25
        m = metrics(curve, R, 10_000, max(span, 0.5))
        m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else 0.0
        print(f"  {ph:<10} {m['cagr']*100:>5.0f}% {m['max_dd']*100:>5.0f}% "
              f"{m['mar']:>5.2f} {m['pf']:>5.2f} {m['win_pct']:>4.0f}% "
              f"{m['n_trades']:>8} {len(sub):>7}")

    # ---- D) Per-year consistency with filter ----
    print("\n=== D) PER-YEAR (filtered) ===")
    print(f"  {'year':<6} {'CAGR':>6} {'maxDD':>6} {'MAR':>5} {'PF':>5} "
          f"{'n':>4}  phase_active")
    for yr in range(2019, 2027):
        lo = dt.datetime(yr, 1, 1, tzinfo=UTC)
        hi = dt.datetime(yr + 1, 1, 1, tzinfo=UTC)
        sub = [t for t in trades_filt if lo <= t["entry_time"] < hi]
        if len(sub) < 5:
            # count bear bars this year
            bear_bars = sum(
                1 for f in feats.values()
                for row in f.filter(
                    (pl.col("ts") >= lo) & (pl.col("ts") < hi)
                )["cycle_phase"].to_list()
                if row == CYCLE_BEAR
            )
            bull_bars = sum(
                1 for f in feats.values()
                for row in f.filter(
                    (pl.col("ts") >= lo) & (pl.col("ts") < hi)
                )["cycle_phase"].to_list()
                if row == CYCLE_BULL
            )
            print(f"  {yr:<6}  (< 5 trades — bull={bull_bars} bear={bear_bars} bars)")
            continue
        curve, R = run_portfolio(sub, 10_000, RISK, 1, 2)
        span = (sub[-1]["exit_time"] - sub[0]["entry_time"]).days / 365.25
        m = metrics(curve, R, 10_000, max(span, 0.5))
        m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else 0.0
        print(f"  {yr:<6} {m['cagr']*100:>5.0f}% {m['max_dd']*100:>5.0f}% "
              f"{m['mar']:>5.2f} {m['pf']:>5.2f} {m['n_trades']:>4}")

    # ---- Summary ----
    print("\n=== SUMMARY ===")
    if m_all and m_filt:
        dd_delta = m_all["max_dd"] - m_filt["max_dd"]
        cagr_delta = m_filt["cagr"] - m_all["cagr"]
        trades_removed = len(trades_all) - len(trades_filt)
        print(f"  Filter removes {trades_removed} trades ({trades_removed/len(trades_all)*100:.0f}%)")
        print(f"  CAGR change:   {cagr_delta*100:+.0f}%")
        print(f"  MaxDD change:  {-dd_delta*100:+.0f}% (reduction = good)")
        print(f"  MAR change:    {m_filt['mar']-m_all['mar']:+.2f}")
        print(f"  PF change:     {m_filt['pf']-m_all['pf']:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
