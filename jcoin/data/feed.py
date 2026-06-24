"""DataFeed — the single read interface for candle data (the parity layer).

ALL strategy/backtest/sim/live code reads candles through DataFeed.get_candles().
Today it is backed by parquet on disk. Later, a live implementation with the SAME
signature is swapped in for real-time trading. Because every consumer goes through
this one interface, backtest and live see an identical data shape -> no parity drift.
(LESSONS_FROM_JTRADER.md #1: one data path, two adapters.)

Stored data is the base timeframe (1m) only. Higher timeframes are derived here by
resampling, so they cannot disagree with the base.
"""

from __future__ import annotations

from datetime import datetime

import polars as pl

from jcoin.data.config import (
    ALLOWED_TIMEFRAMES,
    BASE_TIMEFRAME,
    Market,
    market_by_label,
    partition_path,
)

# our timeframe label -> polars duration string for group_by_dynamic
_TF_EVERY = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}


class DataFeed:
    """Read candles from the parquet store, resampling to the requested timeframe."""

    def __init__(self, base_timeframe: str = BASE_TIMEFRAME):
        self.base_timeframe = base_timeframe

    # -- public API ----------------------------------------------------------
    def get_candles(
        self,
        label: str,
        timeframe: str,
        start: datetime | None = None,
        end: datetime | None = None,
        market: Market | None = None,
    ) -> pl.DataFrame:
        """Return OHLCV for `label` at `timeframe`.

        Columns: ts (Datetime UTC, candle open), open, high, low, close, volume.
        `start`/`end` are inclusive bounds on candle open time (UTC).
        """
        if timeframe not in ALLOWED_TIMEFRAMES:
            raise ValueError(f"timeframe {timeframe!r} not in {ALLOWED_TIMEFRAMES}")

        market = market or market_by_label(label)
        path = partition_path(market.exchange, market.label, self.base_timeframe)
        tf_path = partition_path(market.exchange, market.label, timeframe)

        if path.exists():
            df = pl.read_parquet(path)
            df = df.with_columns(
                pl.from_epoch(pl.col("ts"), time_unit="ms").dt.replace_time_zone("UTC").alias("ts")
            ).sort("ts")
            if timeframe != self.base_timeframe:
                df = self._resample(df, timeframe)
        elif tf_path.exists():
            # Fallback: pre-built timeframe parquet (e.g. 4h from breadth study download).
            # No resampling needed — already at the requested timeframe.
            df = pl.read_parquet(tf_path)
            df = df.with_columns(
                pl.from_epoch(pl.col("ts"), time_unit="ms").dt.replace_time_zone("UTC").alias("ts")
            ).sort("ts")
        else:
            raise FileNotFoundError(
                f"No stored data for {label} at {path} or {tf_path}. "
                f"Run: python -m jcoin.data.fetch --label {label}"
            )

        if start is not None:
            df = df.filter(pl.col("ts") >= _as_utc(start))
        if end is not None:
            df = df.filter(pl.col("ts") <= _as_utc(end))

        return df

    def coverage(self, label: str, market: Market | None = None) -> dict:
        """Quick summary of what's stored for a label (rows, first/last bar)."""
        market = market or market_by_label(label)
        path = partition_path(market.exchange, market.label, self.base_timeframe)
        if not path.exists():
            return {"label": label, "rows": 0, "first": None, "last": None}
        df = pl.read_parquet(path)
        return {
            "label": label,
            "rows": df.height,
            "first": pl.from_epoch(pl.Series([int(df["ts"].min())]), time_unit="ms")[0],
            "last": pl.from_epoch(pl.Series([int(df["ts"].max())]), time_unit="ms")[0],
        }

    # -- internals -----------------------------------------------------------
    @staticmethod
    def _resample(df: pl.DataFrame, timeframe: str) -> pl.DataFrame:
        every = _TF_EVERY[timeframe]
        return (
            df.group_by_dynamic("ts", every=every, closed="left", label="left")
            .agg(
                pl.col("open").first(),
                pl.col("high").max(),
                pl.col("low").min(),
                pl.col("close").last(),
                pl.col("volume").sum(),
            )
            .sort("ts")
        )


def _as_utc(dt: datetime) -> datetime:
    """Ensure a datetime is tz-aware UTC for comparison against the ts column."""
    if dt.tzinfo is None:
        from datetime import timezone

        return dt.replace(tzinfo=timezone.utc)
    return dt
