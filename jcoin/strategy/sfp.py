"""Swing Failure Pattern (SFP) detector — the real mean-reversion trigger.

From pipeline/concepts (Mayne batch1 ITEM 2 + TradingRiot absorption):
  SFP short: candle wick pierces ABOVE a prior confirmed swing high, but the candle
             BODY closes back BELOW it (a failed breakout / stop-run above).
  SFP long:  candle wick pierces BELOW a prior confirmed swing low, but the body
             closes back ABOVE it (a failed breakdown).
  Optional displacement filter: the next candle continues in the fade direction
  (Mayne's MSS confirmation).

Lookahead-safe: the swing level used at bar i is the most recent swing CONFIRMED by
bar i (a fractal pivot at j is only known at j+k). With displacement on, entry is the
close of bar i+1 (the confirming bar), not i.

Returns the regime-labeled frame and a list of signal dicts:
  {idx, entry_idx, side, level, wick, entry, regime}
"""

from __future__ import annotations

import numpy as np
import polars as pl

from jcoin.strategy.regime import label_regime


def detect_sfp(df: pl.DataFrame, k: int = 2, require_displacement: bool = False):
    df = label_regime(df, k=k)
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    is_sh = df["swing_high"].to_numpy()
    is_sl = df["swing_low"].to_numpy()
    regime = df["regime"].to_numpy()
    n = len(close)

    # Most recent swing level CONFIRMED as of each bar (pivot at j known at j+k).
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
    for i in range(n):
        lvl_h = conf_sh[i]
        if not np.isnan(lvl_h) and high[i] > lvl_h and close[i] < lvl_h:
            if require_displacement:
                if i + 1 < n and close[i + 1] < close[i]:
                    signals.append(_sig(i, i + 1, "short", lvl_h, high[i], close[i + 1], regime))
            else:
                signals.append(_sig(i, i, "short", lvl_h, high[i], close[i], regime))

        lvl_l = conf_sl[i]
        if not np.isnan(lvl_l) and low[i] < lvl_l and close[i] > lvl_l:
            if require_displacement:
                if i + 1 < n and close[i + 1] > close[i]:
                    signals.append(_sig(i, i + 1, "long", lvl_l, low[i], close[i + 1], regime))
            else:
                signals.append(_sig(i, i, "long", lvl_l, low[i], close[i], regime))

    return df, signals


def _sig(idx, entry_idx, side, level, wick, entry, regime):
    return {
        "idx": idx,
        "entry_idx": entry_idx,
        "side": side,
        "level": float(level),
        "wick": float(wick),
        "entry": float(entry),
        "regime": str(regime[idx]),
    }
