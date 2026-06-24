"""Sealed train/validate/test for candidate coins (ADA, NEAR) before adding to live universe.

Gate: same config, same splits as the config validation (validate_best.py).
Control: BTC + ETH must still pass (sanity check).

Reads 4h parquets already downloaded by breadth_study. If a coin is missing, downloads it.
"""

from __future__ import annotations

import datetime as dt

from jcoin.engine.features import compute_features
from jcoin.research.breadth_study import _fetch_4h, _sim, INIT, TRAIL, K, ATRP, COST_FRAC, RISK
from jcoin.research.portfolio_backtest import metrics, run_portfolio

UTC = dt.timezone.utc

SPLITS = [
    ("train(21-23)",  dt.datetime(2021, 1, 1, tzinfo=UTC), dt.datetime(2023, 7, 1, tzinfo=UTC)),
    ("valid(23-25)",  dt.datetime(2023, 7, 1, tzinfo=UTC), dt.datetime(2025, 1, 1, tzinfo=UTC)),
    ("TEST(25-26)*",  dt.datetime(2025, 1, 1, tzinfo=UTC), dt.datetime(2027, 1, 1, tzinfo=UTC)),
]

# Control = already validated. Candidates = need to pass gate.
CONTROL = ["BTC", "ETH"]
CANDIDATES = ["ADA", "NEAR"]
COINS = CONTROL + CANDIDATES

# Gate thresholds (TEST split must clear both)
GATE_PF   = 1.15
GATE_MAR  = 0.40


def _load(label: str):
    sym = label + "USDT"
    df = _fetch_4h(sym, label)
    import polars as pl
    df = df.with_columns(
        pl.from_epoch(pl.col("ts"), time_unit="ms").dt.replace_time_zone("UTC").alias("ts")
    ).sort("ts")
    return compute_features(df, k=K, atr_period=ATRP)


def _eval(trades, lo, hi):
    sub = [t for t in trades if lo <= t["entry_time"] < hi]
    if len(sub) < 8:
        return None
    curve, R = run_portfolio(sub, 10_000, RISK, 1, 1)
    span = (sub[-1]["exit_time"] - sub[0]["entry_time"]).days / 365.25
    m = metrics(curve, R, 10_000, max(span, 0.5))
    m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else 0.0
    return m


def main() -> int:
    print(f"COIN VALIDATION — sealed splits | config init={INIT}/trail={TRAIL} "
          f"k={K} atrp={ATRP} | cost={COST_FRAC*1e4:.0f}bp\n")
    print(f"{'coin':<6} {'split':<14} {'CAGR':>6} {'maxDD':>6} {'MAR':>5} {'PF':>5} "
          f"{'n':>4}  note")
    print("-" * 66)

    results = {}
    for label in COINS:
        prefix = "[CONTROL]" if label in CONTROL else "[CAND]  "
        try:
            feat = _load(label)
        except Exception as e:
            print(f"{label:<6}  ERROR loading: {e}")
            continue
        trades = _sim(feat, label)
        results[label] = {}
        for sname, lo, hi in SPLITS:
            m = _eval(trades, lo, hi)
            results[label][sname] = m
            if m:
                is_test = "TEST" in sname
                gate_ok = m["pf"] >= GATE_PF and m["mar"] >= GATE_MAR
                flag = ""
                if is_test:
                    flag = "  PASS" if gate_ok else "  FAIL"
                print(f"{label:<6} {sname:<14} {m['cagr']*100:>5.0f}% {m['max_dd']*100:>5.0f}% "
                      f"{m['mar']:>5.2f} {m['pf']:>5.2f} {m['n_trades']:>4}  {prefix}{flag}")
            else:
                print(f"{label:<6} {sname:<14}  (too few trades)")
        print()

    # Summary verdict
    print("=" * 66)
    print(f"GATE: TEST split PF>={GATE_PF} AND MAR>={GATE_MAR}\n")
    for label in CANDIDATES:
        r = results.get(label, {})
        test_m = None
        for sname, _, _ in SPLITS:
            if "TEST" in sname:
                test_m = r.get(sname)
        if test_m:
            ok = test_m["pf"] >= GATE_PF and test_m["mar"] >= GATE_MAR
            verdict = "ADD TO LIVE UNIVERSE" if ok else "DO NOT ADD — failed gate"
            print(f"  {label}: PF={test_m['pf']:.2f}  MAR={test_m['mar']:.2f}  -> {verdict}")
        else:
            print(f"  {label}: insufficient TEST data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
