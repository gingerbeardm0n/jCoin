"""A_LO: strategy A, long trades only, spot costs (VALIDATION_RULES.md §6).

Same signals/config as A (phase1_honest_a.py). Shorts are dropped (flat instead), no
funding, 1.00% round-trip cost (Kraken spot taker 0.40% + 0.10% slippage per side).
Report-only cost variants: 0.50% and 2.60% round trip. Dev window only.

Usage:
    python -m jcoin.research.spot_long_only
Writes pipeline/A_LO_SPOT_2026-10.md
"""

from __future__ import annotations

from jcoin.data.config import ROOT
from jcoin.research import splits
from jcoin.research.phase1_honest_a import (
    ATR_INIT, ATR_PERIOD, ATR_TRAIL, LABELS, MAX_HOLD, TF, _END, evaluate,
)
from jcoin.research.portfolio_backtest import build_trades

DECISION_COST = 0.0100
REPORT_COSTS = (0.0050, 0.0260)
BTC_BH_MAR = 0.24            # §5, BTC buy-and-hold over the dev period
REPORT_PATH = ROOT / "pipeline" / "A_LO_SPOT_2026-10.md"


def long_trades(cost_frac: float):
    lo, hi = splits.dev_window()
    splits.check_window(lo, hi)
    trades = build_trades(TF, LABELS, ATR_PERIOD, ATR_INIT, ATR_TRAIL, MAX_HOLD, cost_frac,
                          funding_mult=0.0, end=_END)
    assert all(t["exit_time"] < splits.SEALED_START for t in trades), "sealed data leaked"
    return [t for t in trades if t["side"] == "long"]


def _row(name, m):
    if not m:
        return f"| {name} | — | — | — | — | — | — | — |"
    return (f"| {name} | {m['cagr']:.1%} | {m['max_dd']:.1%} | {m['mar']:.2f} | {m['sharpe']:.2f} | "
            f"{m['pf']:.2f} | {m['n_trades']} | {m['avg_R']:+.3f} |")


def main() -> None:
    import sys
    sys.stdout.reconfigure(encoding="utf-8")  # report uses arrows/≥ (Windows console is cp1252)
    lo, hi = splits.dev_window()
    out = ["# A_LO: spot long-only (VALIDATION_RULES.md §6)", "",
           "Strategy A signals, long trades only, no funding, dev window 2021-01-01 → 2026-05-31.", "",
           "## Full dev period", "",
           "| Cost (round trip) | CAGR | Max DD | MAR | Sharpe | PF | Trades | avg R |",
           "|---|---|---|---|---|---|---|---|"]
    results = {}
    for cost in (DECISION_COST,) + REPORT_COSTS:
        tr = long_trades(cost)
        full = evaluate(tr, lo, hi)
        slices = {name: evaluate(tr, a, b) for name, a, b in splits.DEV_SLICES}
        results[cost] = (full, slices)
        tag = " **(decision)**" if cost == DECISION_COST else " (report only)"
        out.append(_row(f"{cost:.2%}{tag}", full))

    full, slices = results[DECISION_COST]
    out += ["", "## By slice at 1.00% cost", "",
            "| Slice | Return | Max DD | MAR | Trades | avg R |", "|---|---|---|---|---|---|"]
    positive = 0
    for name, m in slices.items():
        if m:
            ret = m["final_equity"] / 10_000 - 1
            positive += ret > 0
            out.append(f"| {name} | {ret:+.1%} | {m['max_dd']:.1%} | {m['mar']:.2f} | {m['n_trades']} | {m['avg_R']:+.3f} |")
        else:
            out.append(f"| {name} | (too few trades) | | | | |")

    c1 = full["pf"] >= 1.20
    c2 = full["mar"] > max(BTC_BH_MAR, 0)
    c3 = positive >= 4
    verdict = "PASS" if (c1 and c2 and c3) else "FAIL"
    out += ["", "## Pass rule (§6, all three required)", "",
            f"1. PF ≥ 1.20: **{full['pf']:.2f}** → {'yes' if c1 else 'no'}",
            f"2. MAR > BTC buy-and-hold ({BTC_BH_MAR}) and > 0: **{full['mar']:.2f}** → {'yes' if c2 else 'no'}",
            f"3. Positive in ≥ 4 of 6 slices: **{positive} of 6** → {'yes' if c3 else 'no'}",
            "", f"**Verdict: {verdict}**"]
    worst = max((m["max_dd"] for m in slices.values() if m), default=float("nan"))
    out += ["", f"Worst dev-slice max drawdown (sealed-look threshold): {worst:.1%}"]
    REPORT_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
