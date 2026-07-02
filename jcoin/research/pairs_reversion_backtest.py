"""Pairs / relative-value mean-reversion backtest — a third strategy FAMILY.

Different edge source than the dead single-asset z-score fade (see THESIS_RESULTS_2026-06-20.md,
"candle-only mean-reversion thesis is DEAD"). That test faded ABSOLUTE price extremes. This
fades the RATIO of altcoin/BTC when it stretches from its own rolling mean, dollar-neutral
(long coin + short BTC, or the reverse) — isolating each coin's idiosyncratic move from its
BTC-beta. Structurally different bet: "this coin is over/under-extended RELATIVE TO BTC", not
"this price is stretched" (failed) or "this coin is trending" (the validated breakout edge).
Matches how institutional quants separate coin-specific signal from BTC's market-wide pull
("BTC-neutral residual mean reversion" — see prior web research on systematic crypto funds).

Mechanics:
  - ratio = log(coin_close / btc_close), 4h bars.
  - z = (ratio - rolling_mean) / rolling_std, window = ROLL_BARS (~30 days).
  - Entry: |z| >= ENTRY_Z. z>0 (coin rich vs BTC) -> short coin / long BTC.
                            z<0 (coin cheap vs BTC) -> long coin / short BTC.
  - Exit: z reverts to within EXIT_Z of the mean, or MAX_HOLD bars elapse, whichever first.
  - P&L = direction * (coin_return - btc_return) over the hold, dollar-neutral, minus a
    round-trip cost charged on BOTH legs (coin + BTC hedge).
  - CAVEAT (honest, not modeled): each pair trade opens its own BTC hedge leg here. A real
    implementation would NET BTC exposure across all concurrent pairs positions instead of
    paying the hedge cost per pair — this backtest is conservative (overstates cost).
  - Same sealed train/valid/TEST split + PF/MAR gate as validate_coins4.py, for direct
    comparability with the breakout coin-selection results.

Usage:
    python -m jcoin.research.pairs_reversion_backtest
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from jcoin.research.breadth_study import _fetch_4h
from jcoin.research.portfolio_backtest import metrics, run_portfolio

UTC = dt.timezone.utc
ROLL_BARS = 180       # ~30 days at 4h — the ratio's own rolling mean/std window
ENTRY_Z = 2.0
EXIT_Z = 0.5
MAX_HOLD = 180         # ~30 days cap
COST_FRAC = 0.0024     # 24bp round-trip, BOTH legs (see caveat above — conservative)

CONTROL = ["ETH"]
CANDIDATES = ["XRP", "HBAR", "AVAX", "LINK", "FIL", "DOT", "ATOM",
              "INJ", "RUNE", "SUI", "APT", "ARB", "OP"]
COINS = CONTROL + CANDIDATES

SPLITS = [
    ("train(21-23)",  dt.datetime(2021, 1, 1, tzinfo=UTC), dt.datetime(2023, 7, 1, tzinfo=UTC)),
    ("valid(23-25)",  dt.datetime(2023, 7, 1, tzinfo=UTC), dt.datetime(2025, 1, 1, tzinfo=UTC)),
    ("TEST(25-26)*",  dt.datetime(2025, 1, 1, tzinfo=UTC), dt.datetime(2027, 1, 1, tzinfo=UTC)),
]
GATE_PF, GATE_MAR = 1.15, 0.40


def _load_pair(label: str) -> pl.DataFrame:
    btc = _fetch_4h("BTCUSDT", "BTC").select(["ts", "close"]).rename({"close": "btc_close"})
    coin = _fetch_4h(f"{label}USDT", label).select(["ts", "close"]).rename({"close": "coin_close"})
    df = coin.join(btc, on="ts", how="inner").sort("ts")
    df = df.with_columns(
        pl.from_epoch(pl.col("ts"), time_unit="ms").dt.replace_time_zone("UTC").alias("ts")
    )
    df = df.with_columns((pl.col("coin_close") / pl.col("btc_close")).log().alias("log_ratio"))
    df = df.with_columns([
        pl.col("log_ratio").rolling_mean(window_size=ROLL_BARS).alias("roll_mean"),
        pl.col("log_ratio").rolling_std(window_size=ROLL_BARS).alias("roll_std"),
    ])
    df = df.with_columns(
        ((pl.col("log_ratio") - pl.col("roll_mean")) / pl.col("roll_std")).alias("z")
    )
    return df


def _sim_pair(df: pl.DataFrame, label: str) -> list[dict]:
    z = df["z"].to_numpy()
    coin_close = df["coin_close"].to_numpy()
    btc_close = df["btc_close"].to_numpy()
    ts = df["ts"].to_list()
    n = len(z)
    trades = []
    i = 0
    while i < n:
        zi = z[i]
        if np.isnan(zi) or abs(zi) < ENTRY_Z:
            i += 1
            continue
        direction = -1 if zi > 0 else 1  # rich vs BTC -> short coin/long BTC; cheap -> reverse
        entry_coin, entry_btc = coin_close[i], btc_close[i]
        exit_i = min(i + MAX_HOLD, n - 1)
        for j in range(i + 1, min(i + 1 + MAX_HOLD, n)):
            zj = z[j]
            if not np.isnan(zj) and abs(zj) <= EXIT_Z:
                exit_i = j
                break
        exit_coin, exit_btc = coin_close[exit_i], btc_close[exit_i]
        coin_ret = (exit_coin - entry_coin) / entry_coin
        btc_ret = (exit_btc - entry_btc) / entry_btc
        gross = direction * (coin_ret - btc_ret)
        net = gross - COST_FRAC
        trades.append({
            "symbol": label, "entry_time": ts[i], "exit_time": ts[exit_i],
            "side": "long" if direction > 0 else "short", "R": net,
        })
        i = exit_i + 1  # no overlapping trades per coin
    return trades


def _eval(trades, lo, hi):
    sub = [t for t in trades if lo <= t["entry_time"] < hi]
    if len(sub) < 8:
        return None
    curve, R = run_portfolio(sub, 10_000, 0.02, 1, 1)
    span = (sub[-1]["exit_time"] - sub[0]["entry_time"]).days / 365.25
    m = metrics(curve, R, 10_000, max(span, 0.5))
    m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else 0.0
    return m


def main() -> int:
    print(f"PAIRS/RELATIVE-VALUE MEAN-REVERSION vs BTC | entry_z={ENTRY_Z} exit_z={EXIT_Z} "
          f"roll={ROLL_BARS}bars(~30d) cost={COST_FRAC*1e4:.0f}bp rt (both legs) | "
          f"gate: TEST PF>={GATE_PF} AND MAR>={GATE_MAR}\n")
    print(f"{'coin':<6} {'split':<14} {'CAGR':>6} {'maxDD':>6} {'MAR':>5} {'PF':>5} {'n':>4}  note")
    print("-" * 70)

    results = {}
    for label in COINS:
        try:
            df = _load_pair(label)
        except Exception as e:
            print(f"{label:<6}  ERROR loading: {e}")
            continue
        trades = _sim_pair(df, label)
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
