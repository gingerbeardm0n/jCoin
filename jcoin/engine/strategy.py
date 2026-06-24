"""Strategy logic — pure decisions, no IO. Identical in backtest and live.

jCoin v1: trend-aligned breakout with ATR trailing stop (validated 2026-06-20,
see pipeline/THESIS_RESULTS_2026-06-20.md).

Two responsibilities, both pure functions of the current feature row + position:
  - entry_signal(row): open a position on a trend-aligned break of structure.
  - manage_position(pos, row): update the trailing stop and decide exits.

The exit/trail ordering (check stop with the prior bar's level, THEN tighten) mirrors
the validated backtest (research/backtest_breakout.py) exactly, so the engine reproduces
those results.
"""

from __future__ import annotations

from dataclasses import dataclass

from jcoin.engine.types import EnterIntent, Position, Side
from jcoin.strategy.regime import REGIME_DOWNTREND, REGIME_UPTREND


@dataclass(frozen=True)
class StrategyConfig:
    atr_init: float = 1.0       # initial stop distance in ATRs
    atr_trail: float = 6.0      # chandelier trail distance in ATRs (4.0->6.0 2026-06-22:
                                # OOS-validated improvement, see OPTIMIZATION_STUDY doc)
    max_hold: int = 120         # bars before timeout exit


@dataclass(frozen=True)
class ExitDecision:
    exit: bool
    price: float = 0.0
    reason: str = ""


_NO_EXIT = ExitDecision(exit=False)


class BreakoutStrategy:
    def __init__(self, config: StrategyConfig | None = None):
        self.cfg = config or StrategyConfig()

    def entry_signal(self, row) -> EnterIntent | None:
        """row: dict with symbol, regime, brk_long, brk_short, atr, close."""
        atr = row["atr"]
        if atr is None or atr <= 0:
            return None
        close = row["close"]
        # long breakout only in uptrend; short breakout only in downtrend
        if row["brk_long"] and row["regime"] == REGIME_UPTREND:
            return EnterIntent(row["symbol"], Side.LONG, close - self.cfg.atr_init * atr,
                               atr, "breakout-long-uptrend")
        if row["brk_short"] and row["regime"] == REGIME_DOWNTREND:
            return EnterIntent(row["symbol"], Side.SHORT, close + self.cfg.atr_init * atr,
                               atr, "breakout-short-downtrend")
        return None

    def manage_position(self, pos: Position, row, bars_held: int) -> ExitDecision:
        """Check stop (prior-bar level), then tighten the chandelier trail. Mirror of
        the validated simulate() loop."""
        high, low, close = row["high"], row["low"], row["close"]
        if pos.side is Side.LONG:
            if low <= pos.trail_stop:
                return ExitDecision(True, pos.trail_stop, "stop")
            pos.extreme = max(pos.extreme, high)
            pos.trail_stop = max(pos.trail_stop, pos.extreme - self.cfg.atr_trail * pos.atr)
        else:
            if high >= pos.trail_stop:
                return ExitDecision(True, pos.trail_stop, "stop")
            pos.extreme = min(pos.extreme, low)
            pos.trail_stop = min(pos.trail_stop, pos.extreme + self.cfg.atr_trail * pos.atr)

        if bars_held >= self.cfg.max_hold:
            return ExitDecision(True, close, "timeout")
        return _NO_EXIT
