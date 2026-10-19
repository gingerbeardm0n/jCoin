"""Noise robustness of strategy A (diagnostic, dev window only — not a selection step).

Motivation: Coinbase and Binance 4h prices differ by only ~0.06-0.08% (std of close
ratio ~0.075%), yet A's results over Aug 2025-May 2026 were PF 1.12 on Binance vs 0.59
on Coinbase (pipeline/COINBASE_PARITY_2026-10.md). Wicks are not systematically larger
on Coinbase. Question: is A's result fragile to venue-sized price noise in general?

Method: perturb every Binance OHLC price by independent multiplicative noise
N(0, sigma) (sigma = 0.075%, the measured cross-venue std), re-impose high>=max(o,c),
low<=min(o,c), rerun A (fixed config, 12bp, funding 0) on the full dev window.
Repeat N times; report the distribution vs the unperturbed baseline.

Usage:
    python -m jcoin.research.noise_robustness [--runs 100] [--sigma 0.00075]
Writes pipeline/NOISE_ROBUSTNESS_2026-10.md
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import polars as pl

from jcoin.data.config import ROOT
from jcoin.data.feed import DataFeed
from jcoin.research import splits
from jcoin.research.phase1_honest_a import (
    ATR_INIT, ATR_PERIOD, ATR_TRAIL, COST_FRAC, LABELS, MAX_HOLD, TF, _END, evaluate,
)
from jcoin.research.portfolio_backtest import build_trades

REPORT_PATH = ROOT / "pipeline" / "NOISE_ROBUSTNESS_2026-10.md"


def _noisy(df: pl.DataFrame, rng: np.random.Generator, sigma: float) -> pl.DataFrame:
    n = df.height
    o, h, l, c = (df[x].to_numpy() * (1 + rng.normal(0, sigma, n)) for x in ("open", "high", "low", "close"))
    h = np.maximum.reduce([h, o, c])
    l = np.minimum.reduce([l, o, c])
    return df.with_columns(pl.Series("open", o), pl.Series("high", h), pl.Series("low", l), pl.Series("close", c))


def run(runs: int, sigma: float, seed: int = 20261019) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    lo, hi = splits.dev_window()
    splits.check_window(lo, hi)
    feed = DataFeed()
    base = {lab: feed.get_candles(lab, TF, end=_END) for lab in LABELS}
    orig = DataFeed.get_candles
    rng = np.random.default_rng(seed)

    def one(frames):
        DataFeed.get_candles = lambda self, label, tf, start=None, end=None, **kw: frames[label]
        try:
            tr = build_trades(TF, LABELS, ATR_PERIOD, ATR_INIT, ATR_TRAIL, MAX_HOLD, COST_FRAC, end=_END)
        finally:
            DataFeed.get_candles = orig
        return evaluate(tr, lo, hi)

    baseline = one(base)
    res = []
    for i in range(runs):
        m = one({lab: _noisy(df, rng, sigma) for lab, df in base.items()})
        res.append(m)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{runs}", flush=True)

    def dist(key):
        v = np.array([m[key] for m in res if m])
        return v, np.percentile(v, [5, 25, 50, 75, 95])

    lines = ["# Noise robustness of strategy A (diagnostic)", "",
             f"Dev window 2021-01-01 → 2026-05-31, Binance 4h, fixed A config, 12bp, no funding.",
             f"Noise: independent multiplicative N(0, {sigma:.3%}) on every O/H/L/C; {runs} runs, seed {seed}.", "",
             "| Metric | Baseline | p5 | p25 | median | p75 | p95 |", "|---|---|---|---|---|---|---|"]
    for key, fmt in (("cagr", "{:.1%}"), ("max_dd", "{:.1%}"), ("mar", "{:.2f}"), ("pf", "{:.2f}"),
                     ("sharpe", "{:.2f}"), ("avg_R", "{:+.3f}"), ("n_trades", "{:.0f}")):
        v, p = dist(key)
        lines.append(f"| {key} | {fmt.format(baseline[key])} | " + " | ".join(fmt.format(x) for x in p) + " |")
    pf, _ = dist("pf")
    cagr, _ = dist("cagr")
    lines += ["", f"- Runs with PF < 1.0 (losing): {np.mean(pf < 1.0):.0%}",
              f"- Runs with PF < 1.15: {np.mean(pf < 1.15):.0%}",
              f"- Runs with CAGR < 0: {np.mean(cagr < 0):.0%}"]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=100)
    ap.add_argument("--sigma", type=float, default=0.00075)
    a = ap.parse_args()
    run(a.runs, a.sigma)
