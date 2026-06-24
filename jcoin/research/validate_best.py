"""Validate the full-range 'BEST' config two ways before trusting it:
  1. SEALED train/validate/test split (does it generalize, or did no-holdout hide overfit?)
  2. SLIPPAGE STRESS (tight 0.5-ATR stops = many stop-outs = most exposed to fill costs)
Compared head-to-head against the current DEFAULT on both.
"""

from __future__ import annotations

import datetime as dt

from jcoin.research.portfolio_backtest import build_trades, metrics, run_portfolio

UTC = dt.timezone.utc
TF, LABELS = "4h", ["BTC", "ETH"]

# (atr_period, atr_init, atr_trail, max_hold)  [k is 2 in build_trades]
CONFIGS = {"BEST(0.5/6.0,ap10,h160)": (10, 0.5, 6.0, 160),
           "MIDDLE(1.0/6.0,ap14,h120)": (14, 1.0, 6.0, 120),
           "DEFAULT(1.0/4.0,ap14,h120)": (14, 1.0, 4.0, 120)}

SPLITS = {"train(21-23)": (dt.datetime(2021, 1, 1, tzinfo=UTC), dt.datetime(2023, 7, 1, tzinfo=UTC)),
          "valid(23-25)": (dt.datetime(2023, 7, 1, tzinfo=UTC), dt.datetime(2025, 1, 1, tzinfo=UTC)),
          "TEST(25-26)*": (dt.datetime(2025, 1, 1, tzinfo=UTC), dt.datetime(2027, 1, 1, tzinfo=UTC))}


def ev(trades, lo=None, hi=None):
    sub = trades if lo is None else [t for t in trades if lo <= t["entry_time"] < hi]
    if len(sub) < 12:
        return None
    c, R = run_portfolio(sub, 10_000, 0.01, 1, 2)
    span = (sub[-1]["exit_time"] - sub[0]["entry_time"]).days / 365.25
    m = metrics(c, R, 10_000, max(span, 0.5))
    m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else 0.0
    return m


def main() -> int:
    # ---------- 1) SEALED SPLIT ----------
    print("=== VALIDATION 1: sealed train/validate/TEST (12bp cost) ===")
    print(f"{'config':<26} {'split':<14} {'CAGR':>6} {'maxDD':>6} {'MAR':>5} {'PF':>5} {'n':>4}")
    for name, (ap, ii, tr, h) in CONFIGS.items():
        trades = build_trades(TF, LABELS, ap, ii, tr, h, 0.0012)
        for sname, (lo, hi) in SPLITS.items():
            m = ev(trades, lo, hi)
            if m:
                print(f"{name:<26} {sname:<14} {m['cagr']*100:>5.0f}% {m['max_dd']*100:>5.0f}% "
                      f"{m['mar']:>5.2f} {m['pf']:>5.2f} {m['n_trades']:>4}")
            else:
                print(f"{name:<26} {sname:<14} (insufficient)")
        print()

    # ---------- 2) SLIPPAGE STRESS (full range) ----------
    print("=== VALIDATION 2: slippage stress, full range (fee 6bp + slippage) ===")
    print(f"{'config':<26} {'rt cost':>7} {'CAGR':>6} {'maxDD':>6} {'MAR':>5} {'PF':>5}")
    for name, (ap, ii, tr, h) in CONFIGS.items():
        for slip in (6, 18, 30):
            cf = (6 + slip) / 1e4
            trades = build_trades(TF, LABELS, ap, ii, tr, h, cf)
            m = ev(trades)
            print(f"{name:<26} {6+slip:>5}bp {m['cagr']*100:>5.0f}% {m['max_dd']*100:>5.0f}% "
                  f"{m['mar']:>5.2f} {m['pf']:>5.2f}")
        print()
    print("READ: BEST must (a) stay strongly positive on the SEALED TEST, and (b) degrade\n"
          "gracefully under slippage like DEFAULT does. Tight 0.5-ATR stops are the risk.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
