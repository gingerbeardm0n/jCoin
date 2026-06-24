"""Live candle source — fetch recent CLOSED bars from a venue via ccxt.

Used by the live paper/real runner. Returns the same schema as DataFeed (ts = UTC
datetime, ohlcv) so compute_features and the engine treat it identically to backtest
data (parity). The still-forming current bar is dropped — we only ever act on closed
bars.
"""

from __future__ import annotations

import polars as pl

from jcoin.data.config import Market
from jcoin.data.fetch import _make_exchange, _verify_symbol


def get_recent_candles(market: Market, timeframe: str, limit: int = 300) -> pl.DataFrame:
    ex = _make_exchange(market.exchange)
    _verify_symbol(ex, market.symbol)
    raw = ex.fetch_ohlcv(market.symbol, timeframe, limit=limit)
    if not raw:
        return pl.DataFrame(schema={c: pl.Float64 for c in
                                    ["ts", "open", "high", "low", "close", "volume"]})
    df = pl.DataFrame(raw, schema=["ts", "open", "high", "low", "close", "volume"], orient="row")
    df = df.with_columns(pl.col("ts").cast(pl.Int64)).sort("ts")
    # drop the last row: it is the still-forming current bar
    if df.height > 1:
        df = df.head(df.height - 1)
    return df.with_columns(
        pl.from_epoch(pl.col("ts"), time_unit="ms").dt.replace_time_zone("UTC").alias("ts")
    )
