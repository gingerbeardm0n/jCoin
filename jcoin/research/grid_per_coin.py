"""Per-coin param grid scan — find plateaus, not peaks.

Philosophy: a coin with a REAL edge will show positive PF across a BROAD range of
trail/init values. A coin that only works at one exact setting is curve-fit noise.
We fix k=2 and atr_period=14 (already validated cross-coin) and grid init x trail.

Usage:
    python -m jcoin.research.grid_per_coin
"""

from __future__ import annotations

import datetime as dt

import polars as pl

from jcoin.data.config import partition_path
from jcoin.data.fetch_binance_vision import _BASE, _download, _month_range, _parse_zip
from jcoin.engine.features import compute_features
from jcoin.research.portfolio_backtest import metrics, run_portfolio

UTC = dt.timezone.utc
TF = "4h"
START = "2021-01"
K, ATRP = 2, 14
COST_FRAC, RISK = 0.0012, 0.01

COINS = ["EGLDUSDT", "SANDUSDT", "IMXUSDT", "ENJUSDT"]

# Grid axes — look for plateaus
INIT_VALUES  = [0.5, 1.0, 1.5, 2.0]
TRAIL_VALUES = [3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0]
HOLD = 120  # fix hold


def _fetch_4h(symbol: str, label: str) -> pl.DataFrame:
    path = partition_path("binanceusdm", label, TF)
    if path.exists():
        return pl.read_parquet(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    start_date = dt.datetime.strptime(START, "%Y-%m").date().replace(day=1)
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
    return df


def _load(symbol: str, label: str) -> pl.DataFrame:
    df = _fetch_4h(symbol, label)
    df = df.with_columns(
        pl.from_epoch(pl.col("ts"), time_unit="ms").dt.replace_time_zone("UTC").alias("ts")
    ).sort("ts")
    return compute_features(df, k=K, atr_period=ATRP)


def _sim(feat: pl.DataFrame, label: str, init: float, trail: float):
    high = feat["high"].to_numpy(); low = feat["low"].to_numpy()
    close = feat["close"].to_numpy(); atr = feat["atr"].to_numpy()
    regime = feat["regime"].to_numpy()
    bl = feat["brk_long"].to_numpy(); bs = feat["brk_short"].to_numpy()
    ts = feat["ts"].to_list()
    n = len(close); trades = []
    for i in range(n):
        if bl[i] and regime[i] == "uptrend":
            long = True
        elif bs[i] and regime[i] == "downtrend":
            long = False
        else:
            continue
        if i + 1 >= n or atr[i] <= 0:
            continue
        entry, a = close[i], atr[i]
        stop = entry - init * a if long else entry + init * a
        sd = abs(entry - stop) / entry
        if sd <= 0:
            continue
        best = high[i] if long else low[i]
        exit_price, exit_idx = None, min(i + HOLD, n - 1)
        for j in range(i + 1, min(i + 1 + HOLD, n)):
            if long:
                if low[j] <= stop:
                    exit_price, exit_idx = stop, j; break
                best = max(best, high[j]); stop = max(stop, best - trail * a)
            else:
                if high[j] >= stop:
                    exit_price, exit_idx = stop, j; break
                best = min(best, low[j]); stop = min(stop, best + trail * a)
        if exit_price is None:
            exit_price = close[exit_idx]
        gross = (exit_price - entry) / entry if long else (entry - exit_price) / entry
        trades.append({"symbol": label, "entry_time": ts[i], "exit_time": ts[exit_idx],
                       "side": "long" if long else "short", "R": (gross - COST_FRAC) / sd})
    return sorted(trades, key=lambda t: t["entry_time"])


def _eval(trades):
    if len(trades) < 15:
        return None
    curve, R = run_portfolio(trades, 10_000, RISK, 1, 1)
    span = (trades[-1]["exit_time"] - trades[0]["entry_time"]).days / 365.25
    m = metrics(curve, R, 10_000, max(span, 0.5))
    m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else 0.0
    return m


def _plateau_score(grid: dict) -> int:
    """Count param combos with PF >= 1.2 — wider = more plateau-like."""
    return sum(1 for m in grid.values() if m and m["pf"] >= 1.2)


def main() -> int:
    print(f"PER-COIN PARAM GRID | k={K} atrp={ATRP} hold={HOLD} | "
          f"init x trail | cost={COST_FRAC*1e4:.0f}bp\n")
    print("Plateau = same coin works across WIDE range of params.")
    print("Peak    = only works at 1-2 combos = curve fit, ignore.\n")

    for sym in COINS:
        label = sym.replace("USDT", "")
        print(f"{'='*60}")
        print(f"  {label}")
        print(f"{'='*60}")
        try:
            feat = _load(sym, label)
        except Exception as e:
            print(f"  ERROR: {e}\n")
            continue

        # Run full grid
        grid = {}
        best_m, best_key = None, None
        for init in INIT_VALUES:
            for trail in TRAIL_VALUES:
                trades = _sim(feat, label, init, trail)
                m = _eval(trades)
                grid[(init, trail)] = m

        # Print PF heatmap
        trail_hdr = "  ".join(f"t={t:<4.0f}" for t in TRAIL_VALUES)
        print(f"\n  PF grid (rows=init, cols=trail) — looking for broad green zone:")
        print(f"  {'init':>6}  {trail_hdr}")
        for init in INIT_VALUES:
            row = ""
            for trail in TRAIL_VALUES:
                m = grid[(init, trail)]
                pf = m["pf"] if m else 0.0
                mark = f"{pf:5.2f}"
                row += f"  {mark}"
            print(f"  i={init:<4.1f}  {row}")

        # Print MAR heatmap
        print(f"\n  MAR grid:")
        print(f"  {'init':>6}  {trail_hdr}")
        for init in INIT_VALUES:
            row = ""
            for trail in TRAIL_VALUES:
                m = grid[(init, trail)]
                mar = m["mar"] if m else 0.0
                row += f"  {mar:5.2f}"
            print(f"  i={init:<4.1f}  {row}")

        # Best single config
        best_m = max((m for m in grid.values() if m), key=lambda x: x["mar"], default=None)
        best_key = max((k for k,m in grid.items() if m), key=lambda k: grid[k]["mar"] if grid[k] else -99, default=None)

        plateau = _plateau_score(grid)
        total = len(grid)
        print(f"\n  Plateau: {plateau}/{total} combos with PF>=1.2")
        if best_m and best_key:
            print(f"  Best:    init={best_key[0]} trail={best_key[1]}  "
                  f"CAGR={best_m['cagr']*100:.0f}%  MAR={best_m['mar']:.2f}  PF={best_m['pf']:.2f}")

        # Verdict
        if plateau >= 16:
            verdict = "STRONG PLATEAU — real edge, try with best config"
        elif plateau >= 8:
            verdict = "MODERATE PLATEAU — edge exists, needs validation"
        elif plateau >= 3:
            verdict = "WEAK / NARROW — likely noise, caution"
        else:
            verdict = "NO PLATEAU — no real edge for this strategy"
        print(f"  Verdict: {verdict}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
