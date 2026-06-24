"""Fetch deep 1m history from Binance public data dumps (data.binance.vision).

These are free static CSV archives (no account, no trading API) of USDT-margined
perpetual klines. We READ this data for thesis backtesting only — we never trade
Binance. Output is written to the same canonical parquet store as ccxt fetches, so
the DataFeed reads it identically (parity at the interface).

Strategy: download monthly zips (fast, one file = one month) back to a start date,
plus daily zips for the current partial month (monthly file doesn't exist until the
month closes). Idempotent: skips months already covered in the parquet.

CLI:
    python -m jcoin.data.fetch_binance_vision --label BTC --start 2021-01
    python -m jcoin.data.fetch_binance_vision --all --start 2021-01
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import sys
import urllib.request
import zipfile

import polars as pl

from jcoin.data.config import (
    DEFAULT_MARKETS,
    OHLCV_COLUMNS,
    Market,
    market_by_label,
    partition_path,
)

_BASE = "https://data.binance.vision/data/futures/um"
_TF = "1m"

# Binance kline CSV columns (no header in older files; header in newer ones).
_KLINE_COLS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "count",
    "taker_buy_volume", "taker_buy_quote_volume", "ignore",
]


def _month_range(start: dt.date, end: dt.date):
    """Yield (year, month) from start to end inclusive (by month)."""
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def _download(url: str) -> bytes | None:
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return r.read()
    except Exception:
        return None


def _parse_zip(blob: bytes) -> pl.DataFrame | None:
    """Extract the single CSV from a kline zip -> canonical OHLCV DataFrame."""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        name = z.namelist()[0]
        raw = z.read(name)
    # Detect header: newer dumps start with the literal column name "open_time".
    has_header = raw[:9].lower().startswith(b"open_time")
    df = pl.read_csv(
        raw,
        has_header=has_header,
        new_columns=None if has_header else _KLINE_COLS,
        infer_schema_length=0,  # read all as str, cast explicitly below
    )
    # Some files name the col "open_time", keep only what we need.
    df = df.select(
        pl.col("open_time").alias("ts"),
        pl.col("open"), pl.col("high"), pl.col("low"), pl.col("close"), pl.col("volume"),
    ).with_columns(
        pl.col("ts").cast(pl.Int64),
        pl.col("open").cast(pl.Float64),
        pl.col("high").cast(pl.Float64),
        pl.col("low").cast(pl.Float64),
        pl.col("close").cast(pl.Float64),
        pl.col("volume").cast(pl.Float64),
    )
    # Normalize ts to milliseconds: Binance switched some 2025+ files to microseconds.
    # ms ~ 1.7e12, microseconds ~ 1.7e15. Anything >= 1e15 -> divide by 1000.
    df = df.with_columns(
        pl.when(pl.col("ts") >= 1_000_000_000_000_000)
        .then(pl.col("ts") // 1000)
        .otherwise(pl.col("ts"))
        .alias("ts")
    )
    return df.select(OHLCV_COLUMNS)


def fetch_market(market: Market, start: str, verbose: bool = True) -> pl.DataFrame:
    """Download monthly+daily 1m klines from `start` (YYYY-MM) to now -> parquet."""
    sym = market.symbol
    start_date = dt.datetime.strptime(start, "%Y-%m").date().replace(day=1)
    today = dt.datetime.now(dt.timezone.utc).date()

    path = partition_path(market.exchange, market.label, _TF)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = pl.read_parquet(path) if path.exists() else None
    have = existing is not None and existing.height > 0
    have_min = int(existing["ts"].min()) if have else 0
    have_max = int(existing["ts"].max()) if have else 0

    frames: list[pl.DataFrame] = []

    # --- monthly files (all complete months up to last month) ---
    last_complete = (today.replace(day=1) - dt.timedelta(days=1))
    for y, m in _month_range(start_date, last_complete):
        # skip a month only if it is FULLY covered by existing data (handles
        # both forward-append and backfill-older without skipping gaps)
        month_start_ms = int(dt.datetime(y, m, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
        month_end_ms = int(dt.datetime(y, m, 28, tzinfo=dt.timezone.utc).timestamp() * 1000)
        if have and have_min <= month_start_ms and month_end_ms <= have_max:
            continue
        url = f"{_BASE}/monthly/klines/{sym}/{_TF}/{sym}-{_TF}-{y}-{m:02d}.zip"
        blob = _download(url)
        if blob is None:
            if verbose:
                print(f"  {market.label} {y}-{m:02d}: no monthly file (skip)")
            continue
        df = _parse_zip(blob)
        frames.append(df)
        if verbose:
            print(f"  {market.label} {y}-{m:02d}: {df.height} bars", flush=True)

    # --- daily files for the current (incomplete) month ---
    first_of_month = today.replace(day=1)
    d = first_of_month
    while d < today:
        url = f"{_BASE}/daily/klines/{sym}/{_TF}/{sym}-{_TF}-{d.isoformat()}.zip"
        blob = _download(url)
        if blob is not None:
            frames.append(_parse_zip(blob))
            if verbose:
                print(f"  {market.label} {d.isoformat()}: daily ok", flush=True)
        d += dt.timedelta(days=1)

    if not frames and existing is None:
        raise RuntimeError(f"No data downloaded for {market.label} from {start}")

    parts = ([existing] if existing is not None else []) + frames
    combined = pl.concat(parts).unique(subset=["ts"], keep="last").sort("ts")
    combined.write_parquet(path)
    if verbose:
        span_lo = pl.from_epoch(pl.Series([int(combined["ts"].min())]), time_unit="ms")[0]
        span_hi = pl.from_epoch(pl.Series([int(combined["ts"].max())]), time_unit="ms")[0]
        print(f"  {market.label}: {combined.height} total bars {span_lo} -> {span_hi}")
    return combined


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fetch Binance-vision 1m klines -> parquet")
    p.add_argument("--label", help="market label (e.g. BTC)")
    p.add_argument("--all", action="store_true", help="all DEFAULT_MARKETS")
    p.add_argument("--start", default="2021-01", help="start month YYYY-MM")
    args = p.parse_args(argv)

    if args.all:
        targets = DEFAULT_MARKETS
    elif args.label:
        targets = [market_by_label(args.label)]
    else:
        p.error("pass --label LABEL or --all")
        return 2

    for m in targets:
        print(f"Fetching {m.label} ({m.symbol}) from Binance-vision since {args.start} ...")
        fetch_market(m, start=args.start)
    return 0


if __name__ == "__main__":
    sys.exit(main())
