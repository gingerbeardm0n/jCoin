"""Breakout momentum backtest with a REAL exit model + robustness checks.

Improves on thesis_breakout.py (which used a too-tight stop-at-the-level and got
whipsawed). Here:

  - Entry: trend-ALIGNED breakout only (long breakouts in uptrend regime, short in
    downtrend; skip range — that's where breakouts failed).
  - Initial stop: entry -/+ atr_init * ATR  (ATR-based, not the broken level).
  - Trailing stop: chandelier — trail atr_trail * ATR behind the best price since
    entry, so winners run and losers are cut. Effective stop = tighter of the two.
  - Exit: trailing/initial stop hit, or max_hold timeout (mark to close).
  - Costs: round-trip fee in bps subtracted from every trade.

Robustness: reports per-year and per-symbol (fixed params = honest out-of-sample-ish
consistency check), plus a small ATR sensitivity grid so we can see it's not knife-edge.

Approximations (stated honestly): intrabar fills use this timeframe's high/low; stop
assumed filled at the stop price (no gap modeling); trades evaluated independently
(overlap allowed) — a portfolio layer would serialize. Good enough for a go/no-go.

Usage:
    python -m jcoin.research.backtest_breakout --tf 4h
    python -m jcoin.research.backtest_breakout --tf 4h --grid
"""

from __future__ import annotations

import argparse

import numpy as np
import polars as pl

from jcoin.data.feed import DataFeed
from jcoin.strategy.breakout import detect_breakout
from jcoin.strategy.regime import REGIME_DOWNTREND, REGIME_UPTREND


def _atr(df: pl.DataFrame, period: int) -> np.ndarray:
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    prev_close = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum.reduce([
        high - low,
        np.abs(high - prev_close),
        np.abs(low - prev_close),
    ])
    # Wilder-style EMA of TR
    atr = np.empty_like(tr)
    atr[0] = tr[0]
    a = 1.0 / period
    for i in range(1, len(tr)):
        atr[i] = atr[i - 1] + a * (tr[i] - atr[i - 1])
    return atr


def simulate(df, signals, atr, atr_init, atr_trail, max_hold, fee_bps):
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    ts = df["ts"].to_list()
    n = len(close)
    trades = []
    for s in signals:
        # trend alignment: long only in uptrend, short only in downtrend
        if s["side"] == "long" and s["regime"] != REGIME_UPTREND:
            continue
        if s["side"] == "short" and s["regime"] != REGIME_DOWNTREND:
            continue
        i = s["idx"]
        if i + 1 >= n or atr[i] <= 0:
            continue
        long = s["side"] == "long"
        entry = close[i]
        a = atr[i]
        if long:
            stop = entry - atr_init * a
            best = high[i]
        else:
            stop = entry + atr_init * a
            best = low[i]

        exit_price = None
        for j in range(i + 1, min(i + 1 + max_hold, n)):
            if long:
                if low[j] <= stop:
                    exit_price = stop
                    break
                best = max(best, high[j])
                stop = max(stop, best - atr_trail * a)  # chandelier trail up
            else:
                if high[j] >= stop:
                    exit_price = stop
                    break
                best = min(best, low[j])
                stop = min(stop, best + atr_trail * a)  # trail down
        if exit_price is None:
            exit_price = close[min(i + max_hold, n - 1)]

        ret = (exit_price - entry) / entry if long else (entry - exit_price) / entry
        ret_bps = ret * 1e4 - fee_bps
        trades.append({"year": ts[i].year, "symbol": s.get("symbol", "?"),
                       "side": s["side"], "ret_bps": ret_bps})
    return pl.DataFrame(trades) if trades else pl.DataFrame(
        schema={"year": pl.Int64, "symbol": pl.Utf8, "side": pl.Utf8, "ret_bps": pl.Float64})


def _stats(d: pl.DataFrame) -> dict:
    if d.height == 0:
        return {"n": 0}
    rb = d["ret_bps"]
    wins = d.filter(pl.col("ret_bps") > 0)["ret_bps"]
    losses = d.filter(pl.col("ret_bps") <= 0)["ret_bps"]
    pf = (wins.sum() / abs(losses.sum())) if losses.sum() != 0 else float("inf")
    return {
        "n": d.height,
        "win_pct": (d.select((pl.col("ret_bps") > 0).mean()).item()) * 100,
        "avg_bps": rb.mean(),
        "total_bps": rb.sum(),
        "pf": pf,
    }


def _row(label, st):
    if st.get("n", 0) == 0:
        return f"{label:<10} {'(no trades)':>30}"
    return (f"{label:<10} {st['n']:>6,} {st['win_pct']:>6.1f}% {st['avg_bps']:>9.1f} "
            f"{st['total_bps']:>11,.0f} {st['pf']:>6.2f}")


def run(tf, atr_period, atr_init, atr_trail, max_hold, fee_bps, labels, verbose=True):
    feed = DataFeed()
    all_trades = []
    for label in labels:
        df = feed.get_candles(label, tf)
        df2, sigs = detect_breakout(df, k=2)
        for s in sigs:
            s["symbol"] = label
        atr = _atr(df2, atr_period)
        t = simulate(df2, sigs, atr, atr_init, atr_trail, max_hold, fee_bps)
        all_trades.append(t)
    trades = pl.concat(all_trades)

    if verbose:
        hdr = f"{'bucket':<10} {'n':>6} {'win%':>6} {'avg_bps':>9} {'total_bps':>11} {'pf':>6}"
        print(f"\n--- per year ---\n{hdr}")
        for yr in sorted(trades["year"].unique().to_list()):
            print(_row(str(yr), _stats(trades.filter(pl.col("year") == yr))))
        print(f"\n--- per symbol ---\n{hdr}")
        for sym in labels:
            print(_row(sym, _stats(trades.filter(pl.col("symbol") == sym))))
        print(f"\n--- overall ---\n{hdr}")
        print(_row("ALL", _stats(trades)))
    return trades


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Breakout backtest w/ ATR trailing stop")
    p.add_argument("--tf", default="4h")
    p.add_argument("--atr-period", type=int, default=14)
    p.add_argument("--atr-init", type=float, default=1.5)
    p.add_argument("--atr-trail", type=float, default=3.0)
    p.add_argument("--max-hold", type=int, default=120)
    p.add_argument("--fee-bps", type=float, default=9.0)
    p.add_argument("--labels", nargs="+", default=["BTC", "ETH", "SOL"])
    p.add_argument("--grid", action="store_true", help="ATR sensitivity grid")
    args = p.parse_args(argv)

    print(f"BREAKOUT backtest | tf={args.tf} atr_period={args.atr_period} "
          f"atr_init={args.atr_init} atr_trail={args.atr_trail} max_hold={args.max_hold} "
          f"fee={args.fee_bps}bp | trend-aligned only")

    if args.grid:
        print("\n=== ATR sensitivity grid (overall avg_bps net / profit factor) ===")
        corner = "init\\trail"
        print(f"{corner:>10} " + " ".join(f"{t:>14.1f}" for t in (2.0, 3.0, 4.0, 5.0)))
        for init in (1.0, 1.5, 2.0):
            cells = []
            for trail in (2.0, 3.0, 4.0, 5.0):
                tr = run(args.tf, args.atr_period, init, trail, args.max_hold,
                         args.fee_bps, args.labels, verbose=False)
                st = _stats(tr)
                cells.append(f"{st['avg_bps']:>6.1f}/{st['pf']:>4.2f}")
            print(f"{init:>10.1f} " + " ".join(f"{c:>14}" for c in cells))
        return 0

    run(args.tf, args.atr_period, args.atr_init, args.atr_trail, args.max_hold,
        args.fee_bps, args.labels)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
