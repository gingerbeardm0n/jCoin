"""Price/signal parity: Coinbase US nano perps vs the Binance data A was backtested on.

Fetches Coinbase public 4h candles (no auth) for BIP-20DEC30-CDE (BTC) and
ETP-20DEC30-CDE (ETH), overlaps them with data/ohlcv/binanceusdm/<coin>/4h.parquet,
and compares closes plus A's features (regime, breakout flags). Dev window only
(overlap ends 2026-05-31) -- a signal comparison, not a selection step.

Usage:
    python -m jcoin.research.coinbase_parity
Writes pipeline/COINBASE_PARITY_2026-10.md
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.request

import polars as pl

from jcoin.data.config import ROOT
from jcoin.data.feed import DataFeed
from jcoin.engine.features import compute_features
from jcoin.research import splits
from jcoin.strategy.regime import REGIME_DOWNTREND, REGIME_UPTREND

UTC = dt.timezone.utc
PRODUCTS = {"BTC": "BIP-20DEC30-CDE", "ETH": "ETP-20DEC30-CDE"}
URL = "https://api.coinbase.com/api/v3/brokerage/market/products/{pid}/candles?granularity=FOUR_HOUR&start={s}&end={e}"
BAR_S = 4 * 3600
REPORT_PATH = ROOT / "pipeline" / "COINBASE_PARITY_2026-10.md"


def fetch_coinbase_4h(pid: str, start: dt.datetime, end: dt.datetime) -> pl.DataFrame:
    rows, s = [], int(start.timestamp())
    stop = int(end.timestamp())
    while s < stop:
        e = min(s + 300 * BAR_S, stop)
        req = urllib.request.Request(URL.format(pid=pid, s=s, e=e), headers={"User-Agent": "jcoin-parity"})
        with urllib.request.urlopen(req, timeout=30) as r:
            for c in json.loads(r.read())["candles"]:
                rows.append((int(c["start"]), float(c["open"]), float(c["high"]),
                             float(c["low"]), float(c["close"]), float(c["volume"])))
        s = e
        time.sleep(0.3)
    df = pl.DataFrame(rows, schema=["ts", "open", "high", "low", "close", "volume"], orient="row")
    return (df.unique("ts").sort("ts")
              .with_columns(pl.from_epoch("ts", time_unit="s").dt.replace_time_zone("UTC").alias("ts")))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    end = splits.SEALED_START - dt.timedelta(seconds=1)
    splits.check_window(dt.datetime(2025, 7, 1, tzinfo=UTC), splits.SEALED_START)
    feed = DataFeed()
    out = ["# Coinbase nano perps vs Binance (backtest data) — price & signal parity", "",
           f"Run {dt.date.today()}. Overlap ends 2026-05-31 (dev window only).", ""]
    for coin, pid in PRODUCTS.items():
        cb = fetch_coinbase_4h(pid, dt.datetime(2025, 6, 1, tzinfo=UTC), end)
        first = cb["ts"].min()
        bn = feed.get_candles(coin, "4h", end=end)
        # Features need warm-up: compute on each full series, then compare on the overlap.
        fcb = compute_features(cb, k=2, atr_period=14)
        fbn = compute_features(bn.filter(pl.col("ts") >= first - dt.timedelta(days=60)), k=2, atr_period=14)
        warm = first + dt.timedelta(days=21)   # let Coinbase-side swings/ATR settle
        j = (fcb.select("ts", "close", "regime", "brk_long", "brk_short", "atr")
                .join(fbn.select("ts", "close", "regime", "brk_long", "brk_short", "atr"),
                      on="ts", suffix="_bn")
                .filter(pl.col("ts") >= warm))
        n = j.height
        diff = ((j["close"] / j["close_bn"] - 1).abs())
        basis = (j["close"] / j["close_bn"] - 1)
        reg = (j["regime"] == j["regime_bn"]).mean()
        sig_cb = (j["brk_long"] | j["brk_short"])
        sig_bn = (j["brk_long_bn"] | j["brk_short_bn"])
        both = int((sig_cb & sig_bn).sum())
        only_cb = int((sig_cb & ~sig_bn).sum())
        only_bn = int((~sig_cb & sig_bn).sum())
        # A only trades breakouts aligned with the regime -- compare those entries.
        ent = lambda d, s: ((d[f"brk_long{s}"] & (d[f"regime{s}"] == REGIME_UPTREND)) | (d[f"brk_short{s}"] & (d[f"regime{s}"] == REGIME_DOWNTREND)))
        e_cb, e_bn = ent(j, ""), ent(j, "_bn")
        ent_both = int((e_cb & e_bn).sum())
        ent_cb_only = int((e_cb & ~e_bn).sum())
        ent_bn_only = int((~e_cb & e_bn).sum())
        atr_ratio = (j["atr"] / j["atr_bn"]).median()
        out += [f"## {coin} ({pid})", "",
                f"- Coinbase history starts {first:%Y-%m-%d %H:%M} UTC; compared {n} overlapping 4h bars from {warm:%Y-%m-%d}.",
                f"- Close difference: median {diff.median():.3%}, 95th pct {diff.quantile(0.95):.3%}, max {diff.max():.3%}.",
                f"- Basis (Coinbase vs Binance): mean {basis.mean():+.3%}, median {basis.median():+.3%}.",
                f"- ATR ratio (Coinbase / Binance), median: {atr_ratio:.3f}.",
                f"- Regime label agreement: {reg:.1%}.",
                f"- Any breakout flag: both {both}, Coinbase only {only_cb}, Binance only {only_bn}.",
                f"- **A's trade-able entries (breakout aligned with regime): both {ent_both}, Coinbase only {ent_cb_only}, Binance only {ent_bn_only}.**",
                ""]
    REPORT_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
