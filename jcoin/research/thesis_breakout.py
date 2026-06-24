"""Momentum test: does a breakout (Break-of-Structure) entry have an edge?

Mirror of thesis_sfp.py, reusing its evaluator (R-sim + horizon + fees, by regime).
Trades WITH a body close past a prior swing instead of fading the wick.

Usage:
    python -m jcoin.research.thesis_breakout
    python -m jcoin.research.thesis_breakout --tf 1h --R 2 --max-hold 48
"""

from __future__ import annotations

import argparse

import polars as pl

from jcoin.data.feed import DataFeed
from jcoin.research.thesis_sfp import _print, eval_signals, summarize
from jcoin.strategy.breakout import detect_breakout


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Breakout/momentum expectancy test")
    p.add_argument("--tf", default="1h")
    p.add_argument("--k", type=int, default=2)
    p.add_argument("--horizon", type=int, default=8)
    p.add_argument("--R", type=float, default=2.0)
    p.add_argument("--max-hold", type=int, default=48)
    p.add_argument("--fee-bps", type=float, default=9.0)
    p.add_argument("--buffer-bps", type=float, default=2.0)
    p.add_argument("--labels", nargs="+", default=["BTC", "ETH", "SOL"])
    args = p.parse_args(argv)

    feed = DataFeed()
    print(
        f"BREAKOUT test | tf={args.tf} k={args.k} horizon={args.horizon} R={args.R} "
        f"max_hold={args.max_hold} fee={args.fee_bps}bp"
    )
    pooled = []
    for label in args.labels:
        df = feed.get_candles(label, args.tf)
        df2, sigs = detect_breakout(df, k=args.k)
        res = eval_signals(df2, sigs, args.horizon, args.R, args.max_hold, args.fee_bps, args.buffer_bps)
        _print(f"{label} ({len(sigs):,} breakout signals)", summarize(res, args.fee_bps))
        pooled.append(res)

    allres = pl.concat(pooled)
    _print(f"POOLED ({allres.height:,} signals)", summarize(allres, args.fee_bps))
    print("\nEDGE if: net_bps > 0 and avg_R > 0, ideally strongest in trend regimes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
