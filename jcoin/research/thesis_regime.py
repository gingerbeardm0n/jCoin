"""Thesis test: does range-labeled time mean-revert, and trend-labeled time NOT?

This is the make-or-break check for the entire candle-only mean-reversion plan
(STRATEGY_SPEC.md v1). If fading extremes does not have positive expectancy in
range regimes — and lose in trend regimes — the strategy is dead and we learn it
here, on free history, before building any execution code.

Two measures, per regime (uptrend / downtrend / range), per symbol and pooled:

  1. REVERSION CORRELATION: corr(z, fwd_ret) where z = how stretched price is vs a
     rolling mean, fwd_ret = forward return over the horizon.
       negative  -> mean-reverting (stretched -> snaps back) = fade works
       positive  -> trending (stretched -> keeps going)      = fade loses

  2. RAW FADE EXPECTANCY: take a fade whenever |z| >= entry (short if high, long if
     low), hold `horizon` bars, no stop. trade_ret = -sign(z) * fwd_ret.
     Reports avg bps/trade, win rate, n. Compare against round-trip fee (~9 bps
     taker / ~3 bps maker) to judge if the edge survives costs.

Usage:
    python -m jcoin.research.thesis_regime
    python -m jcoin.research.thesis_regime --tf 4h --window 20 --horizon 8 --entry 2.0
"""

from __future__ import annotations

import argparse

import polars as pl

from jcoin.data.feed import DataFeed
from jcoin.strategy.regime import (
    REGIME_DOWNTREND,
    REGIME_RANGE,
    REGIME_UPTREND,
    label_regime,
)

REGIMES = [REGIME_RANGE, REGIME_UPTREND, REGIME_DOWNTREND]


def prepare(df: pl.DataFrame, window: int, horizon: int, k: int) -> pl.DataFrame:
    df = label_regime(df, k=k)
    df = df.with_columns(
        pl.col("close").rolling_mean(window).alias("_mean"),
        pl.col("close").rolling_std(window).alias("_std"),
    ).with_columns(
        ((pl.col("close") - pl.col("_mean")) / pl.col("_std")).alias("z"),
        ((pl.col("close").shift(-horizon) - pl.col("close")) / pl.col("close")).alias("fwd_ret"),
    )
    return df.drop_nulls(["z", "fwd_ret", "_std"]).filter(pl.col("_std") > 0)


def analyze(df: pl.DataFrame, entry: float) -> dict:
    out = {}
    for reg in REGIMES:
        sub = df.filter(pl.col("regime") == reg)
        if sub.height < 50:
            out[reg] = None
            continue
        corr = sub.select(pl.corr("z", "fwd_ret")).item()
        # fade trades: |z| >= entry; trade_ret = -sign(z)*fwd_ret
        fades = sub.filter(pl.col("z").abs() >= entry).with_columns(
            (-pl.col("z").sign() * pl.col("fwd_ret")).alias("trade_ret")
        )
        n = fades.height
        if n >= 20:
            avg_bps = fades.select(pl.col("trade_ret").mean()).item() * 1e4
            win = fades.select((pl.col("trade_ret") > 0).mean()).item() * 100
        else:
            avg_bps = win = float("nan")
        out[reg] = {
            "bars": sub.height,
            "corr": corr,
            "n_fades": n,
            "avg_bps": avg_bps,
            "win_pct": win,
        }
    return out


def _print_table(title: str, res: dict):
    print(f"\n=== {title} ===")
    print(f"{'regime':<10} {'bars':>9} {'corr(z,fwd)':>12} {'n_fades':>8} {'avg_bps':>9} {'win%':>7}")
    for reg in REGIMES:
        r = res.get(reg)
        if not r:
            print(f"{reg:<10} {'(insufficient)':>40}")
            continue
        print(
            f"{reg:<10} {r['bars']:>9,} {r['corr']:>12.4f} {r['n_fades']:>8,} "
            f"{r['avg_bps']:>9.2f} {r['win_pct']:>6.1f}%"
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Regime mean-reversion thesis test")
    p.add_argument("--tf", default="1h", help="timeframe (default 1h)")
    p.add_argument("--window", type=int, default=20, help="rolling window for z-score")
    p.add_argument("--horizon", type=int, default=8, help="forward-return horizon (bars)")
    p.add_argument("--entry", type=float, default=2.0, help="|z| fade entry threshold")
    p.add_argument("--k", type=int, default=2, help="fractal swing half-width")
    p.add_argument("--labels", nargs="+", default=["BTC", "ETH", "SOL"])
    args = p.parse_args(argv)

    feed = DataFeed()
    print(
        f"Thesis test | tf={args.tf} window={args.window} horizon={args.horizon} "
        f"entry|z|>={args.entry} swing_k={args.k}"
    )
    print("Interpretation: corr<0 = mean-reverting (fade works); avg_bps vs ~9bp taker / ~3bp maker fee")

    pooled = []
    for label in args.labels:
        df = feed.get_candles(label, args.tf)
        prepped = prepare(df, args.window, args.horizon, args.k)
        res = analyze(prepped, args.entry)
        _print_table(f"{label} ({args.tf}, {prepped.height:,} usable bars)", res)
        pooled.append(prepped.with_columns(pl.lit(label).alias("symbol")))

    alldf = pl.concat(pooled)
    _print_table(f"POOLED ({alldf.height:,} bars)", analyze(alldf, args.entry))

    print("\nVERDICT GUIDE:")
    print("  THESIS HOLDS if: range corr clearly < 0 AND range avg_bps > fee,")
    print("                   while trend corr >= 0 (fading trends would lose).")
    print("  THESIS WEAK/DEAD if: range corr ~0 or positive, or range avg_bps < fee.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
