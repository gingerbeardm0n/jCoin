"""Market regime filter — trend (HH/HL or LL/LH) vs range.

Faithful to pipeline/concepts/concept_regime_filter.md. This is the mean-reversion
bot's master on/off switch: fade ONLY when regime == range.

Pipeline:
  1. Detect fractal swing highs/lows (strict local extremum over +/- k bars).
  2. Each swing CONFIRMS k bars later (you can't know bar i is a pivot until i+k
     bars have printed). We attach the regime change at the confirmation bar, never
     at the pivot bar — this prevents lookahead bias in any backtest that reads it.
  3. Classify from the last two swing highs + last two swing lows:
       HH and HL -> uptrend ; LL and LH -> downtrend ; otherwise range.

Returns the input frame with added columns:
  swing_high (bool), swing_low (bool), regime (str: uptrend|downtrend|range|undefined)

`regime` is the label IN FORCE at each bar (forward-filled from confirmations).
"""

from __future__ import annotations

import numpy as np
import polars as pl

REGIME_UPTREND = "uptrend"
REGIME_DOWNTREND = "downtrend"
REGIME_RANGE = "range"
REGIME_UNDEFINED = "undefined"


def _detect_fractal_swings(high: np.ndarray, low: np.ndarray, k: int):
    """Boolean arrays marking strict fractal swing highs / lows.

    Swing high at i: high[i] strictly greater than the k bars on each side.
    (k=1 == the 3-candle definition in the concept doc; k=2 is a bit more robust.)
    """
    n = high.size
    is_sh = np.zeros(n, dtype=bool)
    is_sl = np.zeros(n, dtype=bool)
    for i in range(k, n - k):
        hi = high[i]
        lo = low[i]
        is_high = True
        is_low = True
        for j in range(1, k + 1):
            if not (hi > high[i - j] and hi > high[i + j]):
                is_high = False
            if not (lo < low[i - j] and lo < low[i + j]):
                is_low = False
            if not is_high and not is_low:
                break
        is_sh[i] = is_high
        is_sl[i] = is_low
    return is_sh, is_sl


def label_regime(df: pl.DataFrame, k: int = 2) -> pl.DataFrame:
    """Add swing_high, swing_low, and regime columns to an OHLC frame.

    df must be sorted ascending by ts and contain high/low/close columns.
    """
    n = df.height
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()

    is_sh, is_sl = _detect_fractal_swings(high, low, k)

    # Build confirmation events: a pivot at i is known only at i+k.
    # event = (confirm_index, kind, price)
    events = []
    for i in np.flatnonzero(is_sh):
        events.append((i + k, "H", high[i]))
    for i in np.flatnonzero(is_sl):
        events.append((i + k, "L", low[i]))
    events.sort(key=lambda e: e[0])

    regime = np.array([REGIME_UNDEFINED] * n, dtype=object)

    prev_sh = last_sh = None
    prev_sl = last_sl = None
    cur = REGIME_UNDEFINED
    ev_idx = 0
    n_events = len(events)

    # Walk bars; apply each event at its confirmation bar, then forward-fill.
    for bar in range(n):
        while ev_idx < n_events and events[ev_idx][0] == bar:
            _, kind, price = events[ev_idx]
            if kind == "H":
                prev_sh, last_sh = last_sh, price
            else:
                prev_sl, last_sl = last_sl, price
            if None not in (prev_sh, last_sh, prev_sl, last_sl):
                hh = last_sh > prev_sh
                hl = last_sl > prev_sl
                ll = last_sl < prev_sl
                lh = last_sh < prev_sh
                if hh and hl:
                    cur = REGIME_UPTREND
                elif ll and lh:
                    cur = REGIME_DOWNTREND
                else:
                    cur = REGIME_RANGE
            ev_idx += 1
        regime[bar] = cur

    return df.with_columns(
        pl.Series("swing_high", is_sh),
        pl.Series("swing_low", is_sl),
        pl.Series("regime", regime, dtype=pl.Utf8),
    )
