"""Sealed train/validate/TEST gate for candidate coins — find legit additions to reach 10.

Goal: Joel wants XRP + HBAR (and ideally more) promoted to the validated universe, and a
10th coin. We do NOT relabel by wish — we run the SAME sealed gate used for every other
coin (PF>=1.15 AND MAR>=0.40 on the out-of-sample TEST split) and let the data decide.

Shared config only (breakout init=1.0/trail=6.0, k=2, atr_period=14). No per-coin tuning —
that would manufacture fake in-sample edges (see LESSONS_FROM_JTRADER.md).

Control = BTC, ETH (must still pass = sanity check the harness).
Candidates = Joel's wishlist + a wider net to surface the best 10th coin.
"""

from __future__ import annotations

import datetime as dt

from jcoin.research.breadth_study import _load_features, _sim
from jcoin.research.portfolio_backtest import metrics, run_portfolio

UTC = dt.timezone.utc

SPLITS = [
    ("train(21-23)",  dt.datetime(2021, 1, 1, tzinfo=UTC), dt.datetime(2023, 7, 1, tzinfo=UTC)),
    ("valid(23-25)",  dt.datetime(2023, 7, 1, tzinfo=UTC), dt.datetime(2025, 1, 1, tzinfo=UTC)),
    ("TEST(25-26)*",  dt.datetime(2025, 1, 1, tzinfo=UTC), dt.datetime(2027, 1, 1, tzinfo=UTC)),
]

CONTROL = ["BTC", "ETH"]
# Joel's wishlist first, then a wider net for the 10th-coin search.
CANDIDATES = ["XRP", "HBAR", "AVAX", "LINK", "FIL", "DOT", "ATOM",
              "INJ", "RUNE", "SUI", "APT", "ARB", "OP"]
COINS = CONTROL + CANDIDATES

GATE_PF, GATE_MAR = 1.15, 0.40


def _eval(trades, lo, hi):
    sub = [t for t in trades if lo <= t["entry_time"] < hi]
    if len(sub) < 8:
        return None
    curve, R = run_portfolio(sub, 10_000, 0.01, 1, 1)
    span = (sub[-1]["exit_time"] - sub[0]["entry_time"]).days / 365.25
    m = metrics(curve, R, 10_000, max(span, 0.5))
    m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else 0.0
    return m


def main() -> int:
    print(f"CANDIDATE VALIDATION — sealed splits, shared config | "
          f"gate: TEST PF>={GATE_PF} AND MAR>={GATE_MAR}\n")
    print(f"{'coin':<6} {'split':<14} {'CAGR':>6} {'maxDD':>6} {'MAR':>5} {'PF':>5} {'n':>4}  note")
    print("-" * 70)

    results = {}
    for label in COINS:
        sym = label + "USDT"
        try:
            feat = _load_features(sym, label)
        except Exception as e:
            print(f"{label:<6}  ERROR loading: {e}")
            continue
        trades = _sim(feat, label)
        results[label] = {}
        for sname, lo, hi in SPLITS:
            m = _eval(trades, lo, hi)
            results[label][sname] = m
            if m:
                flag = ""
                if "TEST" in sname:
                    ok = m["pf"] >= GATE_PF and m["mar"] >= GATE_MAR
                    flag = "  PASS" if ok else "  FAIL"
                tag = "[CTRL]" if label in CONTROL else "[CAND]"
                print(f"{label:<6} {sname:<14} {m['cagr']*100:>5.0f}% {m['max_dd']*100:>5.0f}% "
                      f"{m['mar']:>5.2f} {m['pf']:>5.2f} {m['n_trades']:>4}  {tag}{flag}")
            else:
                print(f"{label:<6} {sname:<14}  (too few trades)")
        print()

    print("=" * 70)
    print(f"GATE: TEST split PF>={GATE_PF} AND MAR>={GATE_MAR}\n")
    passed = []
    for label in CANDIDATES:
        test_m = results.get(label, {}).get("TEST(25-26)*")
        if test_m:
            ok = test_m["pf"] >= GATE_PF and test_m["mar"] >= GATE_MAR
            if ok:
                passed.append(label)
            verdict = "ADD" if ok else "skip"
            print(f"  {label:<5} PF={test_m['pf']:.2f}  MAR={test_m['mar']:.2f}  -> {verdict}")
        else:
            print(f"  {label:<5} insufficient TEST data")
    print(f"\nCandidates passing gate: {passed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
