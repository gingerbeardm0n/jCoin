"""Funding-rate carry backtest — a second strategy FAMILY, not a per-coin breakout variant.

Delta-neutral: long spot, short perp, collect funding when rate > 0 (perp above spot,
longs pay shorts). Edge source is funding imbalance, NOT price direction — uncorrelated
with the momentum/breakout book. See STRATEGY_SPEC.md "Strategy 3 — Funding Carry".

Data: Kraken Futures historical funding rates — free, public, no auth (ccxt
fetch_funding_rate_history). CORRECTION to pipeline/DATA_AVAILABILITY.md: that doc
claimed "full history" — verified empirically (direct REST call, 2026-06-30) the public
endpoint only retains a ~370-day rolling window (floor 2025-06-26), for BOTH PF_ and PI_
symbols. Not enough for the same 3-way sealed train/valid/TEST split used for breakout
coins. Design reflects that honestly: full-period net APR + a first-half/second-half
consistency check, not a sealed gate at the same confidence level.

Model (simplified, honest about what's NOT captured):
  - 1 unit spot + 1 unit-equivalent short perp, held continuously across the window.
  - Each hourly funding print: short side receives rate*notional when rate > 0, pays
    when rate < 0 (sum of prints = the carry return over the window).
  - Round-trip taker fees charged once (open + close), both legs.
  - NOT modeled: margin calls / liquidation risk on the short leg during a price spike,
    spot borrow cost if the spot leg is leveraged, rebalancing to keep the hedge notional-
    neutral as price moves. A pass here means "the funding stream is worth building a
    real margin-risk sim for" — not a green light to trade it directly.

Usage:
    python -m jcoin.research.funding_carry_backtest
"""

from __future__ import annotations

import datetime as dt

import ccxt
import numpy as np
import polars as pl

from jcoin.data.config import ROOT

FUNDING_DIR = ROOT / "data" / "funding" / "krakenfutures"

COINS = ["BTC", "ETH", "XRP", "HBAR", "EGLD", "SAND", "IMX", "ADA", "AVAX"]

PERP_TAKER_FEE = 0.0005   # Kraken Futures taker, one side
SPOT_TAKER_FEE = 0.0016   # Kraken spot taker, one side (rough, conservative)
ROUND_TRIP_COST = 2 * PERP_TAKER_FEE + 2 * SPOT_TAKER_FEE  # open+close, both legs

UTC = dt.timezone.utc
GATE_APR = 0.08  # net APR hurdle — must clear full-period AND both halves


def _fetch_funding(label: str) -> pl.DataFrame:
    """Pull + cache full available funding-rate history for one coin from Kraken Futures."""
    path = FUNDING_DIR / label / "funding.parquet"
    if path.exists():
        return pl.read_parquet(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    ex = ccxt.krakenfutures({"enableRateLimit": True})
    symbol = f"{label}/USD:USD"
    all_rows = []
    since = int(dt.datetime(2020, 1, 1, tzinfo=UTC).timestamp() * 1000)
    while True:
        batch = ex.fetch_funding_rate_history(symbol, since=since, limit=200)
        if not batch:
            break
        all_rows.extend(batch)
        last_ts = batch[-1]["timestamp"]
        if last_ts is None or last_ts <= since:
            break
        since = last_ts + 1
        if len(batch) < 200:
            break
    if not all_rows:
        raise RuntimeError(f"no funding history for {label}")

    df = pl.DataFrame({
        "ts": [r["timestamp"] for r in all_rows],
        "funding_rate": [r["fundingRate"] for r in all_rows],
    }).unique(subset=["ts"], keep="last").sort("ts")
    df.write_parquet(path)
    return df


def _eval(df: pl.DataFrame, lo_ms: int, hi_ms: int) -> dict | None:
    sub = df.filter((pl.col("ts") >= lo_ms) & (pl.col("ts") < hi_ms))
    if sub.height < 100:
        return None
    rates = sub["funding_rate"].to_numpy()
    n = len(rates)
    span_days = (hi_ms - lo_ms) / 1000 / 86400
    gross = float(np.sum(rates))
    net = gross - ROUND_TRIP_COST
    apr = net * (365.0 / span_days)
    sharpe = float(rates.mean() / rates.std() * np.sqrt(n * 365 / span_days)) if rates.std() > 0 else 0.0
    pct_positive = float((rates > 0).mean() * 100)
    return {"n": n, "gross": gross, "net": net, "apr": apr, "sharpe": sharpe, "pct_pos": pct_positive}


def main() -> int:
    print(f"FUNDING CARRY BACKTEST | short-perp/long-spot delta-neutral | "
          f"cost={ROUND_TRIP_COST*1e4:.0f}bp round-trip | gate: net APR>={GATE_APR:.0%} "
          f"full-period AND both halves\n")
    print("CAVEAT: Kraken public funding history is ~370 days only (verified 2026-06-30, "
          "corrects DATA_AVAILABILITY.md). This is a thin-data preliminary screen, NOT a "
          "sealed 3-way gate at the same confidence as the breakout coin validation.\n")
    print(f"{'coin':<6} {'window':<8} {'n':>5} {'%pos':>6} {'gross%':>8} {'net%':>8} {'APR':>7} {'sharpe':>7}")
    print("-" * 68)

    passed = []
    for label in COINS:
        try:
            df = _fetch_funding(label)
        except Exception as e:
            print(f"{label:<6} ERROR: {e}")
            continue

        lo_ms, hi_ms = int(df["ts"].min()), int(df["ts"].max()) + 1
        mid_ms = (lo_ms + hi_ms) // 2
        windows = [("full", lo_ms, hi_ms), ("1st-half", lo_ms, mid_ms), ("2nd-half", mid_ms, hi_ms)]

        results = {}
        for wname, lo, hi in windows:
            m = _eval(df, lo, hi)
            results[wname] = m
            if m:
                print(f"{label:<6} {wname:<8} {m['n']:>5} {m['pct_pos']:>5.1f}% "
                      f"{m['gross']*100:>7.2f}% {m['net']*100:>7.2f}% {m['apr']*100:>6.1f}% {m['sharpe']:>7.2f}")
            else:
                print(f"{label:<6} {wname:<8}  (insufficient funding history)")

        full, h1, h2 = results.get("full"), results.get("1st-half"), results.get("2nd-half")
        ok = bool(full and h1 and h2 and full["apr"] >= GATE_APR and h1["net"] > 0 and h2["net"] > 0)
        if ok:
            passed.append(label)
        print()

    print("=" * 68)
    print(f"Coins clearing net APR>={GATE_APR:.0%} full-period AND positive both halves: {passed}")
    print("\nA pass here means the funding stream itself, net of trading fees, is worth\n"
          "building a real margin-risk simulator for — NOT a green light to trade it.\n"
          "Margin/liquidation risk on the short leg is not modeled (see module docstring).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
