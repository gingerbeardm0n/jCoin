"""§7 test: A vs A_CS (close-based stops + 2 ATR disaster stop). VALIDATION_RULES.md §7.

Usage:
    python -m jcoin.research.close_stop_test
Writes pipeline/CLOSE_STOP_TEST_2026-10.md
"""

from __future__ import annotations

import datetime as dt
import sys

import polars as pl

from jcoin.data.config import ROOT
from jcoin.data.feed import DataFeed
from jcoin.research import splits
from jcoin.research.coinbase_parity import PRODUCTS, fetch_coinbase_4h
from jcoin.research.phase1_honest_a import (
    ATR_INIT, ATR_PERIOD, ATR_TRAIL, COST_FRAC, LABELS, MAX_HOLD, TF, _END, evaluate,
)
from jcoin.research.portfolio_backtest import build_trades

UTC = dt.timezone.utc
CB_LO, CB_HI = dt.datetime(2025, 8, 8, tzinfo=UTC), splits.SEALED_START
REPORT_PATH = ROOT / "pipeline" / "CLOSE_STOP_TEST_2026-10.md"


def trades(mode: str, funding: float, frames=None):
    orig = DataFeed.get_candles
    if frames is not None:
        DataFeed.get_candles = lambda self, label, tf, start=None, end=None, **kw: frames[label]
    try:
        return build_trades(TF, LABELS, ATR_PERIOD, ATR_INIT, ATR_TRAIL, MAX_HOLD, COST_FRAC,
                            funding_mult=funding, end=_END, stop_mode=mode)
    finally:
        DataFeed.get_candles = orig


def row(name, m):
    return (f"| {name} | {m['cagr']:.1%} | {m['max_dd']:.1%} | {m['mar']:.2f} | {m['sharpe']:.2f} | "
            f"{m['pf']:.2f} | {m['n_trades']} | {m['avg_R']:+.3f} | {m['final_equity']/10_000-1:+.1%} |")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    lo, hi = splits.dev_window()
    splits.check_window(lo, hi)
    splits.check_window(CB_LO, CB_HI)
    hdr = ["| Run | CAGR | Max DD | MAR | Sharpe | PF | Trades | avg R | Return |", "|---|---|---|---|---|---|---|---|---|"]

    dev = {m: evaluate(trades(m, 1.0), lo, hi) for m in ("intrabar", "close")}
    cb = {c: fetch_coinbase_4h(p, dt.datetime(2025, 6, 1, tzinfo=UTC), _END) for c, p in PRODUCTS.items()}
    cbw = {m: evaluate(trades(m, 0.0, cb), CB_LO, CB_HI) for m in ("intrabar", "close")}
    bnw = {m: evaluate(trades(m, 0.0), CB_LO, CB_HI) for m in ("intrabar", "close")}
    slices = {m: {n: evaluate(trades(m, 1.0), a, b) for n, a, b in splits.DEV_SLICES} for m in ("intrabar", "close")}

    a, c = dev["intrabar"], dev["close"]
    c1 = c["sharpe"] >= 0.90 * a["sharpe"] and c["mar"] >= 0.90 * a["mar"]
    c2 = cbw["close"]["pf"] > cbw["intrabar"]["pf"]
    out = ["# §7: A vs A_CS (close-based stops + 2 ATR disaster stop)", "",
           "## 1. Binance, full dev period (12bp + 1x funding)", ""] + hdr + [row("A (intrabar stops)", a), row("A_CS (close stops)", c)]
    out += ["", "MAR by slice (1x funding):", "", "| Slice | " + " | ".join(n for n, _, _ in splits.DEV_SLICES) + " |",
            "|---|" + "---|" * len(splits.DEV_SLICES)]
    for m, nm in (("intrabar", "A"), ("close", "A_CS")):
        out.append(f"| {nm} | " + " | ".join(f"{v['mar']:.2f}" if v else "—" for v in slices[m].values()) + " |")
    out += ["", "## 2. Coinbase prices, 2025-08-08 → 2026-05-31 (12bp, no funding)", ""] + hdr + \
           [row("A on Coinbase", cbw["intrabar"]), row("A_CS on Coinbase", cbw["close"])]
    out += ["", "Report only — same window on Binance prices:", ""] + hdr + \
           [row("A on Binance", bnw["intrabar"]), row("A_CS on Binance", bnw["close"])]
    out += ["", "## Decision (§7, both required)", "",
            f"1. Dev Sharpe {c['sharpe']:.2f} ≥ 0.90×{a['sharpe']:.2f}={0.9*a['sharpe']:.2f} and MAR {c['mar']:.2f} ≥ 0.90×{a['mar']:.2f}={0.9*a['mar']:.2f} → {'yes' if c1 else 'no'}",
            f"2. Coinbase PF {cbw['close']['pf']:.2f} > {cbw['intrabar']['pf']:.2f} → {'yes' if c2 else 'no'}",
            "", f"**Verdict: {'ADOPT A_CS' if (c1 and c2) else 'KEEP A (intrabar stops)'}**"]
    REPORT_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
