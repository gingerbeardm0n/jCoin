"""Fetch historical OHLCV from any ccxt exchange and store as parquet.

Design goals (from LESSONS_FROM_JTRADER.md):
- Incremental + idempotent: re-running only fetches bars you don't already have.
- Single source of truth: store the BASE timeframe (1m) only; higher timeframes
  are derived on read in DataFeed, so they can never drift from the base.
- Fail loudly: an unknown symbol raises with close matches, never silently no-ops.

CLI:
    python -m jcoin.data.fetch --label BTC --days 365
    python -m jcoin.data.fetch --all --days 730
"""

from __future__ import annotations

import argparse
import sys
import time

import ccxt
import polars as pl

from jcoin.data.config import (
    BASE_TIMEFRAME,
    DEFAULT_MARKETS,
    OHLCV_COLUMNS,
    Market,
    market_by_label,
    partition_path,
)

# ccxt timeframe -> milliseconds (only base timeframe needed for fetch loop)
_TF_MS = {"1m": 60_000}

_PAGE_LIMIT = 1000  # bars per request; most exchanges cap near here


def _make_exchange(exchange_id: str) -> ccxt.Exchange:
    try:
        klass = getattr(ccxt, exchange_id)
    except AttributeError as e:
        raise ValueError(f"Unknown ccxt exchange id {exchange_id!r}") from e
    return klass({"enableRateLimit": True})


def _verify_symbol(exchange: ccxt.Exchange, symbol: str) -> None:
    """Confirm the symbol exists on the exchange, else raise with suggestions."""
    markets = exchange.load_markets()
    if symbol in markets:
        return
    base = symbol.split("/")[0]
    matches = [s for s in markets if s.startswith(base + "/")][:15]
    raise ValueError(
        f"Symbol {symbol!r} not found on {exchange.id}. "
        f"Close matches: {matches or 'none'}"
    )


def _read_existing(path) -> pl.DataFrame | None:
    if path.exists():
        return pl.read_parquet(path)
    return None


def fetch_market(
    market: Market,
    timeframe: str = BASE_TIMEFRAME,
    days: int = 365,
    verbose: bool = True,
) -> pl.DataFrame:
    """Fetch (incrementally) and persist OHLCV for one market. Returns full table."""
    if timeframe not in _TF_MS:
        raise ValueError(
            f"fetch only supports base timeframe(s) {list(_TF_MS)}; "
            f"higher timeframes are derived in DataFeed, got {timeframe!r}"
        )
    tf_ms = _TF_MS[timeframe]
    path = partition_path(market.exchange, market.label, timeframe)
    path.parent.mkdir(parents=True, exist_ok=True)

    exchange = _make_exchange(market.exchange)
    _verify_symbol(exchange, market.symbol)

    now_ms = exchange.milliseconds()
    existing = _read_existing(path)
    if existing is not None and existing.height > 0:
        since = int(existing["ts"].max()) + tf_ms  # resume just after last bar
    else:
        since = now_ms - days * 86_400_000

    new_rows: list[list] = []
    cursor = since
    stall_guard = 0
    while cursor < now_ms:
        batch = exchange.fetch_ohlcv(market.symbol, timeframe, since=cursor, limit=_PAGE_LIMIT)
        if not batch:
            break
        # keep only bars at/after cursor (some venues return a window around `since`)
        batch = [b for b in batch if b[0] >= cursor]
        if not batch:
            stall_guard += 1
            if stall_guard >= 3:
                break
            cursor += tf_ms * _PAGE_LIMIT  # nudge forward past a sparse region
            continue
        stall_guard = 0
        new_rows.extend(batch)
        last_ts = batch[-1][0]
        cursor = last_ts + tf_ms  # advance past the last bar we got
        if verbose:
            done = pl.from_epoch(pl.Series([last_ts]), time_unit="ms")[0]
            print(f"  {market.label} {timeframe}: {len(new_rows)} new bars (...{done})", flush=True)

    if not new_rows:
        if verbose:
            print(f"  {market.label} {timeframe}: up to date, no new bars")
        return existing if existing is not None else pl.DataFrame(schema={c: pl.Float64 for c in OHLCV_COLUMNS})

    fresh = pl.DataFrame(new_rows, schema=OHLCV_COLUMNS, orient="row").with_columns(
        pl.col("ts").cast(pl.Int64)
    )
    combined = fresh if existing is None else pl.concat([existing, fresh])
    combined = combined.unique(subset=["ts"], keep="last").sort("ts")
    combined.write_parquet(path)
    if verbose:
        print(f"  {market.label} {timeframe}: wrote {combined.height} total bars -> {path}")
    return combined


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Fetch OHLCV -> parquet")
    p.add_argument("--label", help="market label (e.g. BTC)")
    p.add_argument("--all", action="store_true", help="fetch all DEFAULT_MARKETS")
    p.add_argument("--days", type=int, default=365, help="lookback days for a cold fetch")
    args = p.parse_args(argv)

    if args.all:
        targets = DEFAULT_MARKETS
    elif args.label:
        targets = [market_by_label(args.label)]
    else:
        p.error("pass --label LABEL or --all")
        return 2

    for m in targets:
        print(f"Fetching {m.label} from {m.exchange} ({m.symbol}) ...")
        fetch_market(m, days=args.days)
    return 0


if __name__ == "__main__":
    sys.exit(main())
