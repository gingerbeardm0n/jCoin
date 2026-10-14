"""Phase 1: honest numbers for strategy A (the current bot), with perp funding.

Strategy A is FIXED (no tuning): BTC+ETH, 4h trend-aligned breakout (k=2), ATR period 14,
ATR init stop 1.0, trail 6.0, max hold 120 bars, 1% risk, max 1 per symbol, max 2
concurrent, 12bp round-trip cost. Funding comes from Binance USD-M history
(data/funding/binanceusdm), added at 0x / 1x / 2x.

Dev window only (2021-01-01 -> 2026-05-31, via splits.py). Every evaluation calls
check_window; candles are bounded at SEALED_START so no sealed bar is ever used.

Conventions (identical for every row, so the later head-to-head is apples to apples):
  - A window's trades are those whose ENTRY falls in [start, end).
  - CAGR / Sharpe use the calendar length of the window as `years`.
  - Equity starts at 10,000 in every window (slices are independent).
  - win% / PF / avg_R / Sharpe come from portfolio_backtest.metrics (per taken trade).

Usage:
    python -m jcoin.research.phase1_honest_a
Writes pipeline/A_HONEST_NUMBERS_2026-10.md
"""

from __future__ import annotations

import datetime as dt

import numpy as np

from jcoin.data.config import ROOT
from jcoin.research import montecarlo, splits
from jcoin.research.portfolio_backtest import build_trades, metrics, run_portfolio

TF = "4h"
LABELS = ["BTC", "ETH"]
ATR_PERIOD, ATR_INIT, ATR_TRAIL, MAX_HOLD = 14, 1.0, 6.0, 120
COST_FRAC = 0.0012            # 12bp round trip
RISK_FRAC, MAX_PER_SYMBOL, MAX_CONCURRENT = 0.01, 1, 2
START_EQUITY = 10_000
FUNDING_MULTS = (0.0, 1.0, 2.0)

REPORT_PATH = ROOT / "pipeline" / "A_HONEST_NUMBERS_2026-10.md"

# Pinned from the UNCHANGED harness (portfolio_backtest.py as of git HEAD, before the
# funding option was added), A config above, full dev window, calendar years. A run with
# funding_mult=0 must reproduce these exactly.
REGRESSION_BASELINE = {
    "cagr": 0.3557181366348321, "max_dd": 0.2595839414218871, "pf": 1.6506706122497947,
    "sharpe": 1.0014039877260577, "n_trades": 396, "avg_R": 0.5623097715430554,
    "final_equity": 51927.50330915668,
}

_END = splits.SEALED_START - dt.timedelta(microseconds=1)  # last allowed candle-open instant


def _years(lo, hi) -> float:
    return (hi - lo).days / 365.25


def dev_trades_A(funding_mult: float, **kw):
    """All of A's candidate trades over the dev window, plus the dev length in years."""
    lo, hi = splits.dev_window()
    splits.check_window(lo, hi)
    trades = build_trades(TF, LABELS, ATR_PERIOD, ATR_INIT, ATR_TRAIL, MAX_HOLD, COST_FRAC,
                          funding_mult=funding_mult, end=_END, **kw)
    assert all(t["exit_time"] < splits.SEALED_START for t in trades), "sealed data leaked"
    return trades, _years(lo, hi)


def evaluate(trades, lo, hi) -> dict | None:
    """Run the portfolio on trades entered in [lo, hi); return metrics + funding stats."""
    splits.check_window(lo, hi)
    sub = [t for t in trades if lo <= t["entry_time"] < hi]
    if len(sub) < 2:
        return None
    taken: list = []
    curve, R = run_portfolio(sub, START_EQUITY, RISK_FRAC, MAX_PER_SYMBOL, MAX_CONCURRENT,
                             taken_trades=taken)
    m = metrics(curve, R, START_EQUITY, _years(lo, hi))
    if not m:
        return None
    m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else float("nan")
    Rarr = np.array(R)
    fund = np.array([t["funding_R"] for t in taken])
    gross_profit = float(Rarr[Rarr > 0].sum())
    m["funding_R_total"] = float(fund.sum())            # + = net received
    m["funding_R_avg"] = float(fund.mean())
    m["funding_paid_share"] = ((float(-fund.sum()) + 0.0) / gross_profit) if gross_profit > 0 else float("nan")
    m["funding_long_R"] = float(sum(t["funding_R"] for t in taken if t["side"] == "long"))
    m["funding_short_R"] = float(sum(t["funding_R"] for t in taken if t["side"] == "short"))
    m["n_long"] = sum(1 for t in taken if t["side"] == "long")
    m["n_short"] = len(taken) - m["n_long"]
    return m


def taken_dev_R(trades) -> list[float]:
    """Per-trade R of the trades the portfolio actually takes over the full dev window."""
    lo, hi = splits.dev_window()
    sub = [t for t in trades if lo <= t["entry_time"] < hi]
    _, R = run_portfolio(sub, START_EQUITY, RISK_FRAC, MAX_PER_SYMBOL, MAX_CONCURRENT)
    return R


# --------------------------------------------------------------------------- report
def _row(name, m) -> str:
    if m is None:
        return f"| {name} | n/a | | | | | | | |"
    return (f"| {name} | {m['cagr']*100:.1f}% | {m['max_dd']*100:.1f}% | {m['mar']:.2f} | "
            f"{m['sharpe']:.2f} | {m['pf']:.2f} | {m['n_trades']} | {m['avg_R']:.3f} | "
            f"{m['win_pct']:.1f}% |")


_HDR = ("| window | CAGR | maxDD | MAR | Sharpe | PF | n_trades | avg_R | win% |\n"
        "|---|---|---|---|---|---|---|---|---|")


def main(argv=None) -> int:
    lo, hi = splits.dev_window()
    splits.check_window(lo, hi)
    out: list[str] = []
    w = out.append

    trades_by_mult = {}
    for mult in FUNDING_MULTS:
        trades_by_mult[mult], _ = dev_trades_A(mult)
    years = _years(lo, hi)

    # ---- regression ------------------------------------------------------------
    default_call = build_trades(TF, LABELS, ATR_PERIOD, ATR_INIT, ATR_TRAIL, MAX_HOLD,
                                COST_FRAC, end=_END)           # no funding args at all
    zero = trades_by_mult[0.0]
    same_trades = (len(default_call) == len(zero) and
                   all(a["R"] == b["R"] and a["entry_time"] == b["entry_time"] and
                       a["exit_time"] == b["exit_time"] for a, b in zip(default_call, zero)))
    m0 = evaluate(zero, lo, hi)
    reg_rows = []
    all_ok = same_trades
    for k, want in REGRESSION_BASELINE.items():
        got = m0[k]
        got = int(got) if k == "n_trades" else float(got)
        ok = (got == want)
        all_ok &= ok
        reg_rows.append(f"| {k} | {want!r} | {got!r} | {'OK' if ok else 'MISMATCH'} |")

    w("# Strategy A: honest numbers (with Binance perp funding)")
    w("")
    w(f"Generated {dt.date.today().isoformat()} by `jcoin/research/phase1_honest_a.py`. "
      f"Dev window only: {lo.date()} to {(hi - dt.timedelta(days=1)).date()} "
      f"(sealed window untouched). Config is fixed, nothing was tuned.")
    w("")
    w("**A config:** BTC+ETH, 4h trend-aligned breakout (k=2), ATR period 14, init stop 1.0 ATR, "
      "chandelier trail 6.0 ATR, max hold 120 bars, 1% risk per trade, max 1 per symbol / 2 "
      "concurrent, 12bp round-trip cost. Funding: Binance USD-M history, long pays / short "
      "receives when the rate is positive, charged on entry notional for prints in "
      "(entry bar open, exit bar open], converted to R by dividing by the stop distance "
      "(same conversion as cost). Multiplier 1x = historical, 2x = double.")
    w("")
    w("Conventions: a window's trades are those entered in it; CAGR and Sharpe use the "
      "calendar length of the window; each window starts at 10,000 equity; trades that "
      "start but do not finish a slice are kept whole (sequential, risk-sized). The 2026H1 "
      "slice is only 5 months, so its CAGR is an annualized short sample.")
    w("")
    w("## 1. Regression check (funding_mult = 0 must equal the unchanged harness)")
    w("")
    w(f"Trade list from a call with no funding arguments vs `funding_mult=0`: "
      f"{'IDENTICAL' if same_trades else 'DIFFERENT'} ({len(zero)} candidate trades).")
    w("")
    w("| metric | baseline (pre-change harness) | funding_mult=0 | match |")
    w("|---|---|---|---|")
    for r in reg_rows:
        w(r)
    w("")
    w(f"**Regression result: {'PASS (exact)' if all_ok else 'FAIL'}**")
    w("")

    # ---- full dev table --------------------------------------------------------
    w("## 2. Full dev period")
    w("")
    w(_HDR)
    full = {}
    for mult in FUNDING_MULTS:
        full[mult] = evaluate(trades_by_mult[mult], lo, hi)
        w(_row(f"funding {mult:g}x", full[mult]))
    w("")
    w("### Funding paid vs gross profit (taken trades, R units)")
    w("")
    w("Gross profit = sum of R over winning taken trades (after costs and funding, the PF "
      "numerator). Funding paid = minus the sum of per-trade funding R (negative share = "
      "net funding received).")
    w("")
    w("| funding | total funding R | avg funding R/trade | funding paid / gross profit | "
      "long funding R | short funding R | n long / short |")
    w("|---|---|---|---|---|---|---|")
    for mult in FUNDING_MULTS:
        m = full[mult]
        w(f"| {mult:g}x | {m['funding_R_total']:+.2f} | {m['funding_R_avg']:+.4f} | "
          f"{m['funding_paid_share']*100:.1f}% | {m['funding_long_R']:+.2f} | "
          f"{m['funding_short_R']:+.2f} | {m['n_long']} / {m['n_short']} |")
    w("")

    # ---- per slice -------------------------------------------------------------
    w("## 3. Per slice (DEV_SLICES)")
    slice_res = {}
    for mult in FUNDING_MULTS:
        w("")
        w(f"### funding {mult:g}x")
        w("")
        w(_HDR)
        for name, s, e in splits.DEV_SLICES:
            m = evaluate(trades_by_mult[mult], s, e)
            slice_res[(mult, name)] = m
            w(_row(name, m))
    w("")
    w("Funding paid / gross profit by slice (funding 1x):")
    w("")
    w("| slice | " + " | ".join(n for n, _, _ in splits.DEV_SLICES) + " |")
    w("|---|" + "---|" * len(splits.DEV_SLICES))
    cells = []
    for name, _, _ in splits.DEV_SLICES:
        m = slice_res[(1.0, name)]
        cells.append("n/a" if m is None else f"{m['funding_paid_share']*100:.1f}%")
    w("| funding / gross profit | " + " | ".join(cells) + " |")
    w("")

    # ---- Monte Carlo -----------------------------------------------------------
    R1 = taken_dev_R(trades_by_mult[1.0])
    per_year = int(round(len(R1) / years))
    mc = montecarlo.summarize(R1, trades_per_path=per_year)
    w("## 4. Monte Carlo (funding 1x)")
    w("")
    w(f"Bootstrap with replacement of A's {len(R1)} dev-period per-trade R values (funding "
      f"1x) into {mc['n_paths']:,} one-year paths of {per_year} trades each (the dev "
      f"average per year), compounded at {mc['risk_frac']:.0%} risk per trade from 1.0 "
      f"equity. Seed {mc['seed']}. Trades are resampled independently, so real-life "
      f"clustering of losses (chop regimes) is NOT captured: treat these as a floor on "
      f"how bad ordinary bad luck looks, not a ceiling.")
    w("")
    w("| percentile | max drawdown | longest losing streak (trades) |")
    w("|---|---|---|")
    for p in montecarlo.PCTS:
        w(f"| p{p} | {mc['max_dd'][p]*100:.1f}% | {mc['streak'][p]} |")
    w("")
    w("A losing trade is R <= 0 (same definition as the profit-factor split). Streak "
      "percentiles are rounded up to a whole trade.")
    w("")
    w("These p99 values feed `KILL_RULE.md`.")
    w("")

    REPORT_PATH.write_text("\n".join(out), encoding="utf-8")

    # console summary
    print("regression:", "PASS" if all_ok else "FAIL")
    print(_HDR)
    for mult in FUNDING_MULTS:
        print(_row(f"funding {mult:g}x", full[mult]))
    print("MAR by slice @1x:", {n: (None if slice_res[(1.0, n)] is None else round(slice_res[(1.0, n)]['mar'], 2))
                                 for n, _, _ in splits.DEV_SLICES})
    print("MC:", mc["max_dd"], mc["streak"], "per_year", per_year)
    print("wrote", REPORT_PATH)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
