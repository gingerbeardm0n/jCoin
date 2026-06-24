"""Breakout / Break-of-Structure detector — the momentum (continuation) trigger.

The mirror image of the SFP fade: instead of fading a wick past a swing, we trade
WITH a body close past it.

  Breakout long:  candle body CLOSES above a prior confirmed swing high (fresh cross).
  Breakout short: candle body CLOSES below a prior confirmed swing low (fresh cross).

Entry = close of the breakout candle (taker — acceptable for breakouts; the target
dwarfs the fee). Stop reference = the broken level (broken resistance should act as
support, and vice versa); risk = entry distance to that level.

Lookahead-safe: same confirmed-swing logic as the SFP detector (a fractal pivot at j
is only known at j+k). Returns signals in the SAME schema as sfp.detect_sfp, so the
thesis_sfp evaluator can score them unchanged (`wick` carries the stop reference).
"""

from __future__ import annotations

import numpy as np
import polars as pl

from jcoin.strategy.regime import label_regime


def detect_breakout(df: pl.DataFrame, k: int = 2):
    df = label_regime(df, k=k)
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    is_sh = df["swing_high"].to_numpy()
    is_sl = df["swing_low"].to_numpy()
    regime = df["regime"].to_numpy()
    n = len(close)

    sh_conf = {int(j + k): high[j] for j in np.flatnonzero(is_sh) if j + k < n}
    sl_conf = {int(j + k): low[j] for j in np.flatnonzero(is_sl) if j + k < n}
    conf_sh = np.full(n, np.nan)
    conf_sl = np.full(n, np.nan)
    cur_h = np.nan
    cur_l = np.nan
    for i in range(n):
        if i in sh_conf:
            cur_h = sh_conf[i]
        if i in sl_conf:
            cur_l = sl_conf[i]
        conf_sh[i] = cur_h
        conf_sl[i] = cur_l

    signals = []
    for i in range(1, n):
        lvl_h = conf_sh[i]
        # fresh upside break: close crosses above the confirmed swing high this bar
        if not np.isnan(lvl_h) and close[i] > lvl_h and close[i - 1] <= lvl_h:
            signals.append(_sig(i, "long", lvl_h, regime, close[i]))

        lvl_l = conf_sl[i]
        if not np.isnan(lvl_l) and close[i] < lvl_l and close[i - 1] >= lvl_l:
            signals.append(_sig(i, "short", lvl_l, regime, close[i]))

    return df, signals


def _sig(i, side, level, regime, entry):
    # `wick` = stop reference (the broken level); reused by thesis_sfp evaluator.
    return {
        "idx": i,
        "entry_idx": i,
        "side": side,
        "level": float(level),
        "wick": float(level),
        "entry": float(entry),
        "regime": str(regime[i]),
    }
