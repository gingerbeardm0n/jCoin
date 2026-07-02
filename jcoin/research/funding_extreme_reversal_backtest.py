"""Funding-extreme reversal backtest — a fifth strategy variant, testing "predict the flip."

Documented pattern (tradingriot_crypto_guide_compressed.md, "Mean Reversion" section):
crowded longs stretched = OI spike + funding hard positive + short-liquidation flush =
"little fuel left, snap brutal." This is a real professional reversal signal, not a naive
guess -- but it has THREE legs, and two of them (OI history, liquidation history) turned out
to not exist as free/available historical data:

  - Open Interest: verified directly against Kraken Futures' API this session (both ccxt
    and raw REST) -- LIVE OI is available (ticker.openInterest), but there is NO historical
    OI endpoint at all. Confirmed 404 on every historical-OI path tried. DATA_AVAILABILITY.md
    already flagged this; this is a second, direct confirmation.
  - Liquidations: per DATA_AVAILABILITY.md, Kraken liquidation history requires paid Tardis.dev
    (~$450+/mo), no free option.

So this tests a DOWNGRADED, 1-factor version: funding-rate extremity ALONE as the reversal
trigger (the "crowd is extremely one-sided" leg), missing the OI-confirmation and
liquidation-flush-confirmation legs that make the full documented signal credible. If this
weaker version doesn't show an edge, the full version might still work -- this is not a
complete disproof of the pattern, only of its cheapest testable slice.

Mechanics:
  - Funding data: same Kraken Futures hourly funding history used in funding_carry_backtest.py
    (~370-day window), resampled to 4h to align with existing price data.
  - z = rolling z-score of the 4h-mean funding rate (window ~30 days).
  - Entry: |z| >= ENTRY_Z. z>0 (funding unusually positive = crowd paying to be long =
    overheated longs) -> SHORT, betting the crowd unwinds. z<0 (crowd paying to be short) ->
    LONG, betting a short squeeze.
  - Exit: z reverts to within EXIT_Z of 0, or MAX_HOLD bars, whichever first.
  - Same full-period + first-half/second-half consistency check as funding_carry_backtest.py
    (thin data -- not enough for a 3-way sealed split).

Usage:
    python -m jcoin.research.funding_extreme_reversal_backtest
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from jcoin.research.breadth_study import _fetch_4h
from jcoin.research.funding_carry_backtest import _fetch_funding
from jcoin.research.portfolio_backtest import metrics, run_portfolio

UTC = dt.timezone.utc
ROLL_BARS = 180       # ~30 days at 4h
ENTRY_Z = 2.0
EXIT_Z = 0.5
MAX_HOLD = 180
COST_FRAC = 0.0012     # 12bp round-trip, single leg (directional, not paired)

COINS = ["BTC", "ETH", "XRP", "HBAR", "EGLD", "SAND", "IMX", "ADA", "AVAX"]
GATE_PF, GATE_MAR = 1.15, 0.40


def _load(label: str) -> pl.DataFrame:
    funding = _fetch_funding(label)  # hourly, cached from funding_carry_backtest
    funding_4h = (
        funding.with_columns((pl.col("ts") - pl.col("ts") % (4 * 3600 * 1000)).alias("bucket"))
        .group_by("bucket").agg(pl.col("funding_rate").mean())
        .rename({"bucket": "ts"}).sort("ts")
    )
    price = _fetch_4h(f"{label}USDT", label).select(["ts", "close"])
    df = funding_4h.join(price, on="ts", how="inner").sort("ts")
    df = df.with_columns(
        pl.from_epoch(pl.col("ts"), time_unit="ms").dt.replace_time_zone("UTC").alias("ts")
    )
    df = df.with_columns([
        pl.col("funding_rate").rolling_mean(window_size=ROLL_BARS).alias("roll_mean"),
        pl.col("funding_rate").rolling_std(window_size=ROLL_BARS).alias("roll_std"),
    ])
    df = df.with_columns(
        ((pl.col("funding_rate") - pl.col("roll_mean")) / pl.col("roll_std")).alias("z")
    )
    return df


def _sim(df: pl.DataFrame, label: str) -> list[dict]:
    z = df["z"].to_numpy()
    close = df["close"].to_numpy()
    ts = df["ts"].to_list()
    n = len(z)
    trades = []
    i = 0
    while i < n:
        zi = z[i]
        if np.isnan(zi) or abs(zi) < ENTRY_Z:
            i += 1
            continue
        direction = -1 if zi > 0 else 1  # funding hot (crowd long) -> short; crowd short -> long
        entry = close[i]
        exit_i = min(i + MAX_HOLD, n - 1)
        for j in range(i + 1, min(i + 1 + MAX_HOLD, n)):
            zj = z[j]
            if not np.isnan(zj) and abs(zj) <= EXIT_Z:
                exit_i = j
                break
        exit_price = close[exit_i]
        gross = direction * (exit_price - entry) / entry
        net = gross - COST_FRAC
        trades.append({
            "symbol": label, "entry_time": ts[i], "exit_time": ts[exit_i],
            "side": "long" if direction > 0 else "short", "R": net,
        })
        i = exit_i + 1
    return trades


def _eval(trades, lo_ms, hi_ms):
    sub = [t for t in trades if lo_ms <= int(t["entry_time"].timestamp() * 1000) < hi_ms]
    if len(sub) < 8:
        return None
    curve, R = run_portfolio(sub, 10_000, 0.01, 1, 1)
    span = (sub[-1]["exit_time"] - sub[0]["entry_time"]).days / 365.25
    m = metrics(curve, R, 10_000, max(span, 0.25))
    m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else 0.0
    return m


def main() -> int:
    print(f"FUNDING-EXTREME REVERSAL | entry_z={ENTRY_Z} exit_z={EXIT_Z} roll={ROLL_BARS}bars(~30d) "
          f"cost={COST_FRAC*1e4:.0f}bp rt | gate: PF>={GATE_PF} AND MAR>={GATE_MAR}\n")
    print("CAVEAT: 1-factor downgrade of the documented 3-factor signal (funding only -- no OI\n"
          "history exists free/anywhere for Kraken; liquidation history needs paid Tardis). See\n"
          "module docstring. ~370-day funding window -> full-period + half-split check, not a\n"
          "3-way sealed gate.\n")
    print(f"{'coin':<6} {'window':<8} {'n':>4} {'CAGR':>6} {'maxDD':>6} {'MAR':>5} {'PF':>5}  note")
    print("-" * 62)

    passed = []
    for label in COINS:
        try:
            df = _load(label)
        except Exception as e:
            print(f"{label:<6} ERROR: {e}")
            continue
        trades = _sim(df, label)
        if not trades:
            print(f"{label:<6}  no signals fired")
            continue

        lo_ms = int(trades[0]["entry_time"].timestamp() * 1000)
        hi_ms = int(trades[-1]["exit_time"].timestamp() * 1000) + 1
        mid_ms = (lo_ms + hi_ms) // 2
        windows = [("full", lo_ms, hi_ms), ("1st-half", lo_ms, mid_ms), ("2nd-half", mid_ms, hi_ms)]

        results = {}
        for wname, lo, hi in windows:
            m = _eval(trades, lo, hi)
            results[wname] = m
            if m:
                flag = ""
                if wname == "full":
                    ok = m["pf"] >= GATE_PF and m["mar"] >= GATE_MAR
                    flag = "  PASS" if ok else "  FAIL"
                print(f"{label:<6} {wname:<8} {m['n_trades']:>4} {m['cagr']*100:>5.0f}% "
                      f"{m['max_dd']*100:>5.0f}% {m['mar']:>5.2f} {m['pf']:>5.2f}{flag}")
            else:
                print(f"{label:<6} {wname:<8}  (too few trades)")

        full, h1, h2 = results.get("full"), results.get("1st-half"), results.get("2nd-half")
        ok = bool(full and h1 and h2 and full["pf"] >= GATE_PF and full["mar"] >= GATE_MAR
                  and h1["mar"] > 0 and h2["mar"] > 0)
        if ok:
            passed.append(label)
        print()

    print("=" * 62)
    print(f"Coins clearing PF>={GATE_PF} MAR>={GATE_MAR} full-period AND positive both halves: {passed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
