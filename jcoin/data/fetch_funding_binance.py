"""Fetch Binance USD-M perpetual funding-rate history from data.binance.vision.

Free static monthly archives (no account, no trading API); we only READ them, like the
kline fetcher. Each monthly zip holds one CSV:

    calc_time,funding_interval_hours,last_funding_rate
    1609459200002,8,0.00022753

URL pattern (verified 2026-10-14):
    https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/
        BTCUSDT-fundingRate-2021-01.zip

Output: data/funding/binanceusdm/<COIN>/funding.parquet with columns
    ts            Int64, milliseconds since epoch (raw calc_time; carries a few ms of jitter)
    funding_rate  Float64, fraction of notional paid by longs to shorts per print
                  (positive = longs pay). Same layout as the Kraken cache read by
                  funding_carry_backtest.py.

SEALED WINDOW: this fetcher refuses to download any month at or after 2026-06 (the
sealed OOS window, VALIDATION_RULES.md section 1), so the dev funding cache can never
contain sealed data. Pass --allow-sealed only for the single logged confirmation look.

CLI:
    python -m jcoin.data.fetch_funding_binance --labels BTC ETH
"""

from __future__ import annotations

import argparse
import io
import sys
import zipfile

import numpy as np
import polars as pl

from jcoin.data.config import DATA_DIR, market_by_label
from jcoin.data.fetch_binance_vision import _download, _month_range
from jcoin.research.splits import SEALED_START

import datetime as dt

_BASE = "https://data.binance.vision/data/futures/um/monthly/fundingRate"
FUNDING_DIR = DATA_DIR / "funding" / "binanceusdm"


def _parse_zip(blob: bytes) -> pl.DataFrame:
    """Extract the single funding CSV from a monthly zip -> (ts ms, funding_rate)."""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        raw = z.read(z.namelist()[0])
    has_header = raw[:9].lower().startswith(b"calc_time")
    df = pl.read_csv(
        raw,
        has_header=has_header,
        new_columns=None if has_header else ["calc_time", "funding_interval_hours",
                                              "last_funding_rate"],
        infer_schema_length=0,  # read everything as str, cast explicitly
    )
    df = df.select(
        pl.col("calc_time").cast(pl.Int64).alias("ts"),
        pl.col("last_funding_rate").cast(pl.Float64).alias("funding_rate"),
    )
    # Defensive: normalize microsecond timestamps to ms (same quirk as the kline dumps).
    return df.with_columns(
        pl.when(pl.col("ts") >= 1_000_000_000_000_000)
        .then(pl.col("ts") // 1000)
        .otherwise(pl.col("ts"))
        .alias("ts")
    )


def fetch_label(label: str, start: str = "2021-01", end: str = "2026-05",
                allow_sealed: bool = False, verbose: bool = True) -> pl.DataFrame:
    """Download monthly funding files for one coin, merge, write parquet."""
    sym = market_by_label(label).symbol
    start_d = dt.datetime.strptime(start, "%Y-%m").date()
    end_d = dt.datetime.strptime(end, "%Y-%m").date()
    sealed_d = SEALED_START.date()
    if not allow_sealed and (end_d.year, end_d.month) >= (sealed_d.year, sealed_d.month):
        raise ValueError(f"end month {end} is in the sealed window (>= {sealed_d:%Y-%m}); "
                         f"dev funding stops at 2026-05")

    frames: list[pl.DataFrame] = []
    for y, m in _month_range(start_d, end_d):
        url = f"{_BASE}/{sym}/{sym}-fundingRate-{y}-{m:02d}.zip"
        blob = _download(url)
        if blob is None:
            print(f"  {label} {y}-{m:02d}: no file (skip)")
            continue
        df = _parse_zip(blob)
        frames.append(df)
        if verbose:
            print(f"  {label} {y}-{m:02d}: {df.height} prints", flush=True)
    if not frames:
        raise RuntimeError(f"no funding files downloaded for {label}")

    out = pl.concat(frames).unique(subset=["ts"], keep="last").sort("ts")
    path = FUNDING_DIR / label / "funding.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    out.write_parquet(path)
    return out


def describe(label: str, df: pl.DataFrame) -> str:
    r = df["funding_rate"].to_numpy()
    lo = dt.datetime.fromtimestamp(int(df["ts"].min()) / 1000, dt.timezone.utc)
    hi = dt.datetime.fromtimestamp(int(df["ts"].max()) / 1000, dt.timezone.utc)
    return (f"{label}: rows={df.height} | {lo:%Y-%m-%d %H:%M} -> {hi:%Y-%m-%d %H:%M} UTC | "
            f"mean={r.mean():.6f} median={float(np.median(r)):.6f} max={r.max():.6f} "
            f"min={r.min():.6f} | frac_positive={float((r > 0).mean()):.3f}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fetch Binance-vision funding rates -> parquet")
    p.add_argument("--labels", nargs="+", default=["BTC", "ETH"])
    p.add_argument("--start", default="2021-01", help="first month YYYY-MM")
    p.add_argument("--end", default="2026-05", help="last month YYYY-MM (dev ends 2026-05)")
    p.add_argument("--allow-sealed", action="store_true",
                   help="permit months >= 2026-06 (single logged confirmation look only)")
    args = p.parse_args(argv)
    for label in args.labels:
        print(f"Fetching {label} funding {args.start} -> {args.end} ...")
        df = fetch_label(label, args.start, args.end, allow_sealed=args.allow_sealed)
        print(describe(label, df))
    return 0


if __name__ == "__main__":
    sys.exit(main())
