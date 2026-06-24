"""Macro cycle regime filter — bull vs bear from price alone (no on-chain data).

Two complementary indicators, both computed from 4h OHLC:

  1. 365-day SMA cross: close below 365-day SMA = bear. Confirmed every major bear
     (2014, 2018, 2022) and recovery. Straightforward trend anchor.

  2. Pi Cycle Top: 111-day SMA crosses above 2x 350-day SMA = top signal. Called
     every cycle top within days in 2013, 2017, 2021. Once triggered, overrides the
     365-SMA until price drops below the 365-SMA anyway.

Bear = below_365 OR pi_cycle_top.

On 4h bars: 1 day = 6 bars
  365-day SMA = 2190 bars (warmup ~365 days of data)
  111-day SMA =  666 bars
  350-day SMA = 2100 bars
"""

from __future__ import annotations

import polars as pl

BARS_PER_DAY = 6  # 4h timeframe

_P365 = 365 * BARS_PER_DAY   # 2190
_P111 = 111 * BARS_PER_DAY   # 666
_P350 = 350 * BARS_PER_DAY   # 2100

CYCLE_BULL = "bull"
CYCLE_BEAR = "bear"
CYCLE_UNKNOWN = "unknown"  # not enough warmup data


def add_cycle_filter(df: pl.DataFrame) -> pl.DataFrame:
    """Add cycle indicator columns to a 4h OHLC DataFrame.

    Added columns:
      sma_365      - 365-day simple moving average of close
      sma_111      - 111-day SMA (Pi Cycle numerator)
      sma_350      - 350-day SMA (Pi Cycle denominator)
      pi_cycle_top - True when 111-SMA > 2x 350-SMA (top signal)
      cycle_phase  - 'bull' | 'bear' | 'unknown' (unknown = warmup period)
    """
    close = pl.col("close")

    sma_365 = close.rolling_mean(_P365)
    sma_111 = close.rolling_mean(_P111)
    sma_350 = close.rolling_mean(_P350)

    below_365 = close < sma_365
    pi_top = sma_111 > 2.0 * sma_350
    bear = below_365 | pi_top

    # Unknown until we have enough warmup for the longest SMA (365-day)
    has_data = pl.col("close").rolling_min(_P365).is_not_null()

    phase = (
        pl.when(~has_data).then(pl.lit(CYCLE_UNKNOWN))
        .when(bear).then(pl.lit(CYCLE_BEAR))
        .otherwise(pl.lit(CYCLE_BULL))
    )

    return df.with_columns([
        sma_365.alias("sma_365"),
        sma_111.alias("sma_111"),
        sma_350.alias("sma_350"),
        pi_top.alias("pi_cycle_top"),
        phase.alias("cycle_phase"),
    ])


def current_phase(df: pl.DataFrame) -> str:
    """Return the cycle phase of the most recent bar in df.

    df must have a 'close' column and enough rows for warmup (~2190).
    Returns CYCLE_UNKNOWN if insufficient data.
    """
    augmented = add_cycle_filter(df.sort("ts") if "ts" in df.columns else df)
    phase_col = augmented["cycle_phase"]
    if phase_col.is_empty():
        return CYCLE_UNKNOWN
    return phase_col[-1]
