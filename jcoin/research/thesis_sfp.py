"""Decisive test: does the SFP sweep-and-reclaim entry have an edge?

The naive z-score fade failed (THESIS_RESULTS_2026-06-20.md). This tests the
strategy's ACTUAL trigger. Two evaluations per signal, split by regime:

  1. HORIZON return: fade direction, held `horizon` bars (apples-to-apples with the
     naive test).
  2. STOP/TARGET R-sim: stop just beyond the sweep wick; target = entry +/- R*risk in
     fade direction; walk forward up to `max_hold` bars using each bar's high/low
     (stop assumed to win ties). Outcome in R-multiples.

Reports per regime: n, win%, avg R, expectancy (R), gross bps, net bps (after fee).

Usage:
    python -m jcoin.research.thesis_sfp
    python -m jcoin.research.thesis_sfp --tf 1h --R 2 --max-hold 48 --displacement
"""

from __future__ import annotations

import argparse

import numpy as np
import polars as pl

from jcoin.data.feed import DataFeed
from jcoin.strategy.regime import REGIME_DOWNTREND, REGIME_RANGE, REGIME_UPTREND
from jcoin.strategy.sfp import detect_sfp

REGIMES = [REGIME_RANGE, REGIME_UPTREND, REGIME_DOWNTREND]


def eval_signals(df, signals, horizon, R, max_hold, fee_bps, buffer_bps):
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    n = len(close)
    rows = []
    for s in signals:
        ei = s["entry_idx"]
        if ei + 1 >= n:
            continue
        entry = s["entry"]
        side = s["side"]
        long = side == "long"

        # --- horizon return (gross) ---
        h_idx = min(ei + horizon, n - 1)
        exit_h = close[h_idx]
        hz = (exit_h - entry) / entry if long else (entry - exit_h) / entry

        # --- stop/target R-sim ---
        buf = entry * buffer_bps / 1e4
        if long:
            stop = s["wick"] - buf
            risk = entry - stop
            target = entry + R * risk
        else:
            stop = s["wick"] + buf
            risk = stop - entry
            target = entry - R * risk
        if risk <= 0:
            continue
        outcome_R = None
        for j in range(ei + 1, min(ei + 1 + max_hold, n)):
            hit_stop = (low[j] <= stop) if long else (high[j] >= stop)
            hit_tgt = (high[j] >= target) if long else (low[j] <= target)
            if hit_stop:  # ties -> stop (conservative)
                outcome_R = -1.0
                break
            if hit_tgt:
                outcome_R = float(R)
                break
        if outcome_R is None:  # timeout: mark to close
            last = close[min(ei + max_hold, n - 1)]
            mtm = (last - entry) if long else (entry - last)
            outcome_R = mtm / risk
        rows.append({"regime": s["regime"], "hz": hz, "R": outcome_R})

    if not rows:
        return pl.DataFrame(schema={"regime": pl.Utf8, "hz": pl.Float64, "R": pl.Float64})
    return pl.DataFrame(rows)


def summarize(res: pl.DataFrame, fee_bps: float) -> dict:
    out = {}
    for reg in REGIMES:
        sub = res.filter(pl.col("regime") == reg)
        n = sub.height
        if n < 20:
            out[reg] = {"n": n}
            continue
        gross_bps = sub.select(pl.col("hz").mean()).item() * 1e4
        out[reg] = {
            "n": n,
            "win_pct": sub.select((pl.col("R") > 0).mean()).item() * 100,
            "avg_R": sub.select(pl.col("R").mean()).item(),
            "gross_bps": gross_bps,
            "net_bps": gross_bps - fee_bps,
        }
    return out


def _print(title, res):
    print(f"\n=== {title} ===")
    print(f"{'regime':<10} {'n':>7} {'win%':>6} {'avg_R':>7} {'gross_bps':>10} {'net_bps':>8}")
    for reg in REGIMES:
        r = res.get(reg, {"n": 0})
        if r.get("n", 0) < 20:
            print(f"{reg:<10} {r.get('n',0):>7} {'(insufficient)':>34}")
            continue
        print(
            f"{reg:<10} {r['n']:>7,} {r['win_pct']:>5.1f}% {r['avg_R']:>7.3f} "
            f"{r['gross_bps']:>10.1f} {r['net_bps']:>8.1f}"
        )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="SFP trigger expectancy test")
    p.add_argument("--tf", default="1h")
    p.add_argument("--k", type=int, default=2, help="fractal swing half-width")
    p.add_argument("--horizon", type=int, default=8)
    p.add_argument("--R", type=float, default=2.0, help="reward:risk target multiple")
    p.add_argument("--max-hold", type=int, default=48, help="bars before timeout exit")
    p.add_argument("--fee-bps", type=float, default=9.0, help="round-trip fee (taker~9, maker~3)")
    p.add_argument("--buffer-bps", type=float, default=2.0, help="stop buffer beyond wick")
    p.add_argument("--displacement", action="store_true", help="require MSS confirmation bar")
    p.add_argument("--labels", nargs="+", default=["BTC", "ETH", "SOL"])
    args = p.parse_args(argv)

    feed = DataFeed()
    print(
        f"SFP test | tf={args.tf} k={args.k} horizon={args.horizon} R={args.R} "
        f"max_hold={args.max_hold} fee={args.fee_bps}bp displacement={args.displacement}"
    )
    pooled = []
    for label in args.labels:
        df = feed.get_candles(label, args.tf)
        df2, sigs = detect_sfp(df, k=args.k, require_displacement=args.displacement)
        res = eval_signals(df2, sigs, args.horizon, args.R, args.max_hold, args.fee_bps, args.buffer_bps)
        _print(f"{label} ({len(sigs):,} SFP signals)", summarize(res, args.fee_bps))
        pooled.append(res)

    allres = pl.concat(pooled)
    _print(f"POOLED ({allres.height:,} signals)", summarize(allres, args.fee_bps))
    print("\nEDGE if: RANGE net_bps > 0 and avg_R > 0 (and ideally > naive fade, which was <=0).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
