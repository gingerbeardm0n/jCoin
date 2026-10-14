"""Fetch DAILY klines for every Binance USD-M USDT symbol (incl. delisted) from data.binance.vision.

Used by the strategy-B basket backtest (VALIDATION_RULES.md §5). Survivorship matters, so the
symbol list comes from the bucket listing (which keeps delisted contracts), not from today's
exchange info. Public static files only, no account, no trading API.

NOTE: these are PERP prices used as a spot proxy.

SEALED WINDOW: months after --end (default 2026-05) are never downloaded
(jcoin.research.splits.SEALED_START = 2026-06-01).

Layout: data/ohlcv/binance_daily/<SYM>/1d.parquet with
    ts (UTC datetime), open, high, low, close, volume, quote_volume.
Resume-safe: a symbol whose parquet already exists is skipped (use --force to refetch).

CLI:
    python -m jcoin.data.fetch_binance_daily --start 2020-01 --end 2026-05 --workers 16
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import polars as pl

_BASE = "https://data.binance.vision/data/futures/um/monthly/klines"
_LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
_PREFIX = "data/futures/um/monthly/klines/"
_NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
_USDT_RE = re.compile(r"^[A-Z0-9]+USDT$")   # excludes dated contracts (BTCUSDT_210625) and USDC pairs

ROOT = Path(__file__).resolve().parents[2] / "data" / "ohlcv" / "binance_daily"

_KLINE_COLS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "count",
    "taker_buy_volume", "taker_buy_quote_volume", "ignore",
]


def _get(url: str, retries: int = 4, timeout: int = 60) -> bytes | None:
    """GET with retries. Returns None on 404; raises after exhausting retries on other errors."""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = e
        except Exception as e:  # noqa: BLE001 - network flakiness
            last = e
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed after {retries} tries: {url}: {last}")


def _list_keys(prefix: str, delimiter: str = "/") -> tuple[list[str], list[str]]:
    """Paginated S3 listing -> (common_prefixes, keys)."""
    prefixes: list[str] = []
    keys: list[str] = []
    marker = ""
    while True:
        q = {"delimiter": delimiter, "prefix": prefix}
        if marker:
            q["marker"] = marker
        body = _get(_LIST + "?" + urllib.parse.urlencode(q))
        root = ET.fromstring(body)
        for cp in root.findall(f"{_NS}CommonPrefixes/{_NS}Prefix"):
            prefixes.append(cp.text)
        for c in root.findall(f"{_NS}Contents/{_NS}Key"):
            keys.append(c.text)
        if root.findtext(f"{_NS}IsTruncated") == "true":
            nm = root.findtext(f"{_NS}NextMarker")
            if nm:
                marker = nm
            else:
                marker = (keys[-1] if keys else prefixes[-1])
        else:
            break
    return prefixes, keys


def list_usdt_symbols() -> list[str]:
    """All USDT-quoted USD-M perpetual symbols ever listed (delisted included)."""
    prefixes, _ = _list_keys(_PREFIX)
    syms = [p[len(_PREFIX):].strip("/") for p in prefixes]
    return sorted(s for s in syms if _USDT_RE.match(s))


def list_months(sym: str, start: str, end: str) -> list[str]:
    """Months 'YYYY-MM' available for sym's 1d klines within [start, end]."""
    _, keys = _list_keys(f"{_PREFIX}{sym}/1d/")
    out = []
    for k in keys:
        m = re.search(rf"{re.escape(sym)}-1d-(\d{{4}}-\d{{2}})\.zip$", k)
        if m and start <= m.group(1) <= end:
            out.append(m.group(1))
    return sorted(out)


def _parse_zip(blob: bytes) -> pl.DataFrame:
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        raw = z.read(z.namelist()[0])
    has_header = raw[:9].lower().startswith(b"open_time")
    df = pl.read_csv(raw, has_header=has_header,
                     new_columns=None if has_header else _KLINE_COLS,
                     infer_schema_length=0)
    df = df.select(
        pl.col("open_time").cast(pl.Int64).alias("ts"),
        pl.col("open").cast(pl.Float64), pl.col("high").cast(pl.Float64),
        pl.col("low").cast(pl.Float64), pl.col("close").cast(pl.Float64),
        pl.col("volume").cast(pl.Float64), pl.col("quote_volume").cast(pl.Float64),
    )
    # some newer files use microseconds
    df = df.with_columns(
        pl.when(pl.col("ts") >= 1_000_000_000_000_000).then(pl.col("ts") // 1000)
        .otherwise(pl.col("ts")).alias("ts"))
    return df.with_columns(pl.from_epoch(pl.col("ts"), time_unit="ms").dt.replace_time_zone("UTC").alias("ts"))


def fetch_symbol(sym: str, start: str, end: str, force: bool = False) -> tuple[str, str, int]:
    """Fetch one symbol. Returns (sym, status, n_bars); status in ok/skipped/nodata/error."""
    path = ROOT / sym / "1d.parquet"
    if path.exists() and not force:
        return sym, "skipped", -1
    try:
        months = list_months(sym, start, end)
        if not months:
            return sym, "nodata", 0
        frames = []
        for ym in months:
            blob = _get(f"{_BASE}/{sym}/1d/{sym}-1d-{ym}.zip")
            if blob is None:
                continue
            frames.append(_parse_zip(blob))
        if not frames:
            return sym, "nodata", 0
        df = pl.concat(frames).unique(subset=["ts"], keep="last").sort("ts")
        path.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(path)
        return sym, "ok", df.height
    except Exception as e:  # noqa: BLE001
        return sym, f"error: {e}", 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fetch Binance-vision USD-M daily klines (all USDT symbols)")
    p.add_argument("--start", default="2020-01")
    p.add_argument("--end", default="2026-05", help="last month INCLUDED; sealed window starts 2026-06")
    p.add_argument("--workers", type=int, default=16)
    p.add_argument("--force", action="store_true")
    p.add_argument("--limit", type=int, default=0, help="debug: only first N symbols")
    args = p.parse_args(argv)
    if args.end >= "2026-06":
        p.error("--end must be <= 2026-05 (sealed window; see jcoin/research/splits.py)")

    t0 = time.time()
    syms = list_usdt_symbols()
    if args.limit:
        syms = syms[: args.limit]
    print(f"{len(syms)} USDT symbols in bucket listing", flush=True)
    counts: dict[str, int] = {}
    errors = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(fetch_symbol, s, args.start, args.end, args.force) for s in syms]
        for i, f in enumerate(as_completed(futs), 1):
            sym, status, n = f.result()
            key = status.split(":")[0]
            counts[key] = counts.get(key, 0) + 1
            if key == "error":
                errors.append((sym, status))
            if i % 50 == 0 or i == len(syms):
                print(f"  {i}/{len(syms)} {counts}", flush=True)
    print(f"done in {time.time() - t0:.0f}s: {counts}")
    for s, e in errors:
        print("  ERR", s, e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
