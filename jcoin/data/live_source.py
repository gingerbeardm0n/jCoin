"""Live candle source — fetch recent CLOSED bars from a venue via ccxt.

Used by the live paper/real runner. Returns the same schema as DataFeed (ts = UTC
datetime, ohlcv) so compute_features and the engine treat it identically to backtest
data (parity). The still-forming current bar is dropped — we only ever act on closed
bars.
"""

from __future__ import annotations

import time

import polars as pl

from jcoin.data.config import Market
from jcoin.data.fetch import _make_exchange, _verify_symbol


def get_recent_candles(market: Market, timeframe: str, limit: int = 300) -> pl.DataFrame:
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
    """
    ex = _make_exchange(market.exchange)
    _verify_symbol(ex, market.symbol)
    tf_ms = ex.parse_timeframe(timeframe) * 1000
    since = int(time.time() * 1000) - limit * tf_ms
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
    # drop the last row: it is the still-forming current bar
    if df.height > 1:
        df = df.head(df.height - 1)
    return df.with_columns(
        pl.from_epoch(pl.col("ts"), time_unit="ms").dt.replace_time_zone("UTC").alias("ts")
    )
