"""Live candle source — fetch recent CLOSED bars from a venue via ccxt.

Used by the live paper/real runner. Returns the same schema as DataFeed (ts = UTC
datetime, ohlcv) so compute_features and the engine treat it identically to backtest
data (parity). The still-forming current bar is dropped — we only ever act on closed
bars.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import polars as pl

from jcoin.data.config import Market
from jcoin.data.fetch import _make_exchange, _verify_symbol

log = logging.getLogger(__name__)

_TF_UNIT_MS = {"m": 60_000, "h": 3_600_000, "d": 86_400_000}


def _timeframe_to_ms(timeframe: str) -> int:
    """Parse a ccxt-style timeframe string (e.g. "4h", "15m", "1d") into milliseconds."""
    unit = timeframe[-1]
    if unit not in _TF_UNIT_MS or not timeframe[:-1].isdigit():
        raise ValueError(f"Unsupported timeframe string {timeframe!r}")
    return int(timeframe[:-1]) * _TF_UNIT_MS[unit]


def get_recent_candles(market: Market, timeframe: str, limit: int = 300,
                        since_ms: int | None = None) -> pl.DataFrame:
    """Fetch the most recent `limit` closed bars, paginating past the exchange's
    per-call cap if the request exceeds it.

    BUG FOUND 2026-07-03: Kraken Futures silently caps a single fetch_ohlcv call at
    2000 bars regardless of the requested `limit` (confirmed empirically: requesting
    2300 or 5000 both returned exactly 2000). The cycle filter needs 2190 bars for its
    365-day SMA, so every live/paper call has been getting 1999-2000 bars, silently
    falling back to cycle_phase=CYCLE_UNKNOWN (treated as bull) on every single tick
    since the strategy was built -- the bear-market 75% risk-scaling has never actually
    engaged in live/paper trading. Classic silent-no-op (LESSONS_FROM_JTRADER.md #1: "a
    fallback should scream, not whisper"). This paginates backward via `since` so a
    request for >2000 bars actually gets them.

    `since_ms`: fetch starting from this epoch-ms timestamp instead of computing one
    from `limit` bars back from now. Used by get_recent_candles_cached() to fetch only
    the bars newer than what is already cached (audit 2026-09-18, item #3).
    """
    ex = _make_exchange(market.exchange)
    _verify_symbol(ex, market.symbol)
    tf_ms = _timeframe_to_ms(timeframe)
    since = since_ms if since_ms is not None else int(time.time() * 1000) - limit * tf_ms
    rows: list = []
    while len(rows) < limit:
        batch = ex.fetch_ohlcv(market.symbol, timeframe, since=since, limit=limit - len(rows))
        if not batch:
            break
        batch = [b for b in batch if not rows or b[0] > rows[-1][0]]  # drop pagination overlap
        if not batch:
            break
        rows.extend(batch)
        since = batch[-1][0] + 1
        if len(batch) < 2:  # exchange returning almost nothing new -> history exhausted
            break
    if not rows:
        return pl.DataFrame(schema={c: pl.Float64 for c in
                                    ["ts", "open", "high", "low", "close", "volume"]})
    df = pl.DataFrame(rows, schema=["ts", "open", "high", "low", "close", "volume"], orient="row")
    df = df.with_columns(pl.col("ts").cast(pl.Int64)).unique(subset=["ts"], keep="last").sort("ts")
    # Drop the last row ONLY if it is still forming (bar has not closed yet).
    # BUG FOUND 2026-09-18: this used to drop the last row unconditionally, on the
    # assumption the exchange always returns one forming bar. With the incremental
    # since-based fetch used by get_recent_candles_cached(), the exchange sometimes
    # returns rows ending at the latest CLOSED bar (no forming row attached) -- the
    # unconditional drop discarded that closed bar, making the runner think the feed
    # was hours stale when it wasn't.
    if df.height > 0:
        now_ms = int(time.time() * 1000)
        last_open_ms = int(df["ts"][-1])
        if last_open_ms + tf_ms > now_ms:
            df = df.head(df.height - 1)
    return df.with_columns(
        pl.from_epoch(pl.col("ts"), time_unit="ms").dt.replace_time_zone("UTC").alias("ts")
    )


def get_recent_candles_cached(market: Market, timeframe: str, cache_dir: str | Path,
                               limit: int = 300, catchup_limit: int = 1000,
                               retry_waits_s: tuple[int, ...] = (20, 40)) -> pl.DataFrame:
    """Like get_recent_candles(), but caches candles on disk per (market.label,
    timeframe) so a scheduled run only fetches bars newer than what is already
    cached instead of re-paginating the full `limit`-bar history every tick.

    Audit 2026-09-18, item #3: the cycle filter's ~2300-bar paginated fetch (needed
    for the 365-day SMA) was slow enough to blow the scheduled task's 10-minute
    execution-time limit. Caching turns that into a small incremental fetch after the
    first run.

    Falls back to a full get_recent_candles() fetch if the cache file is missing,
    empty, or unreadable (corrupt parquet, schema mismatch, etc.) -- caching is purely
    a performance optimization and must never be the reason a tick fails.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{market.label}_{timeframe}.parquet"

    cached = None
    if path.exists():
        try:
            c = pl.read_parquet(path)
            if c.height > 0 and "ts" in c.columns:
                cached = c.sort("ts")
        except Exception as e:
            log.warning("candle cache unreadable for %s (%s), falling back to full fetch: %s",
                       market.label, path, e)
            cached = None

    if cached is None:
        df = get_recent_candles(market, timeframe, limit=limit)
        if df.height:
            _write_cache(path, df)
        return df

    last_ts = cached["ts"].max()
    since_ms = int(last_ts.timestamp() * 1000) + 1  # strictly after the last cached bar
    # BUG FOUND 2026-10-12: a run right after the laptop woke from sleep hit the
    # network before it was back up; the fetch failed, this function quietly served
    # the stale cache, and the runner logged an innocent "no new closed bar". Now:
    # retry with backoff (covers the wake-up race), and if it still fails, RAISE so
    # the runner records a real fetch failure instead of pretending all is well.
    fresh = None
    for attempt, wait_s in enumerate(retry_waits_s + (None,), start=1):
        try:
            fresh = get_recent_candles(market, timeframe, limit=catchup_limit, since_ms=since_ms)
            break
        except Exception as e:
            if wait_s is None:
                raise RuntimeError(f"incremental fetch failed for {market.label} after "
                                   f"{attempt} attempt(s): {e}") from e
            log.warning("incremental fetch failed for %s (attempt %d), retrying in %ds: %s",
                        market.label, attempt, wait_s, e)
            time.sleep(wait_s)

    combined = cached
    if fresh is not None and fresh.height:
        combined = pl.concat([cached, fresh]).unique(subset=["ts"], keep="last").sort("ts")

    # Defensive: never persist a still-forming bar to the cache. get_recent_candles()
    # already applies this rule to `fresh`, but a cache file written before this fix
    # could still have a forming bar baked in from a previous run -- this makes sure
    # it gets dropped/overwritten here too instead of sticking around forever.
    if combined.height:
        tf_ms = _timeframe_to_ms(timeframe)
        now_ms = int(time.time() * 1000)
        last_open_ms = int(combined["ts"][-1].timestamp() * 1000)
        if last_open_ms + tf_ms > now_ms:
            combined = combined.head(combined.height - 1)

    _write_cache(path, combined)
    return combined.tail(limit) if combined.height > limit else combined


def _write_cache(path: Path, df: pl.DataFrame) -> None:
    """Write the candle cache atomically so a crash mid-write never leaves a
    truncated/corrupt parquet file for the next run to trip over."""
    try:
        tmp = path.with_suffix(".tmp")
        df.write_parquet(tmp)
        tmp.replace(path)
    except Exception as e:
        log.warning("failed to write candle cache %s (non-fatal): %s", path, e)
