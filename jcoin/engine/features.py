"""Feature pipeline — deterministic, causal (no lookahead).

Computes everything the strategy reads, into DataFrame columns:
  regime, atr, conf_sh, conf_sl, brk_long, brk_short

Used identically in both modes:
  - backtest: run once over full history; engine iterates rows.
  - live: run on the trailing window each time a bar closes; read the last row.
Same function -> same features -> parity. All inputs are past-only (the regime
classifier uses confirmed swings, ATR is causal, breakout uses bars i-1 and i).
"""

from __future__ import annotations

import numpy as np
import polars as pl

from jcoin.strategy.regime import label_regime


def _atr(high, low, close, period: int) -> np.ndarray:
    prev_close = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum.reduce([high - low, np.abs(high - prev_close), np.abs(low - prev_close)])
    atr = np.empty_like(tr)
    atr[0] = tr[0]
    a = 1.0 / period
    for i in range(1, len(tr)):
        atr[i] = atr[i - 1] + a * (tr[i] - atr[i - 1])
    return atr


def compute_features(df: pl.DataFrame, k: int = 2, atr_period: int = 14) -> pl.DataFrame:
    df = label_regime(df, k=k)
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    is_sh = df["swing_high"].to_numpy()
    is_sl = df["swing_low"].to_numpy()
    n = len(close)

    atr = _atr(high, low, close, atr_period)

    # most recent CONFIRMED swing level as of each bar (pivot at j known at j+k)
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

    # fresh-cross breakout flags
    brk_long = np.zeros(n, dtype=bool)
    brk_short = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if not np.isnan(conf_sh[i]) and close[i] > conf_sh[i] and close[i - 1] <= conf_sh[i]:
            brk_long[i] = True
        if not np.isnan(conf_sl[i]) and close[i] < conf_sl[i] and close[i - 1] >= conf_sl[i]:
            brk_short[i] = True

    return df.with_columns(
        pl.Series("atr", atr),
        pl.Series("conf_sh", conf_sh),
        pl.Series("conf_sl", conf_sl),
        pl.Series("brk_long", brk_long),
        pl.Series("brk_short", brk_short),
    )
