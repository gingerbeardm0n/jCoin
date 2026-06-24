"""Kill-switch stack — the non-negotiable safety layer before live capital (§4).

Pure decision logic (no IO) so it is unit-testable and identical in backtest/paper/live.
The engine (or live runner) calls `evaluate()` each bar; if it returns a halt, the runner
stops opening new positions and (for hard halts) flattens everything.

Switches:
  - daily loss limit:      equity down >= daily_loss_pct since the day's start -> halt to next day
  - max account drawdown:  equity down >= max_dd_pct from all-time peak -> hard halt (manual review)
  - consecutive losses:    N losing trades in a row -> cool-down halt
  - equity floor:          equity below an absolute floor -> hard halt

This module decides; wiring into the live runner (flatten-all, disable, alert) is the
runner's job. Kept OUT of the backtest parity path by default (attach explicitly).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import Enum


class HaltLevel(str, Enum):
    NONE = "none"
    SOFT = "soft"   # pause new entries; resumes automatically (e.g. next day / cooldown)
    HARD = "hard"   # flatten + disable; requires manual re-enable


@dataclass(frozen=True)
class KillSwitchConfig:
    daily_loss_pct: float = 0.03        # 3% intraday loss -> soft halt to next day
    max_dd_pct: float = 0.25            # 25% drawdown from peak -> hard halt
    consecutive_losses: int = 0         # DISABLED 2026-06-22: counterproductive for trend-
                                        # following (pauses right before breakouts; cost ~12%
                                        # of return over 5.5y). 0 = off. Set >0 to re-enable.
    cooldown_bars: int = 12             # bars to pause after a consecutive-loss trip (if on)
    equity_floor: float = 0.0           # absolute $ floor -> hard halt (0 disables)


@dataclass
class KillSwitchState:
    peak_equity: float
    day: dt.date | None = None
    day_start_equity: float = 0.0
    loss_streak: int = 0
    cooldown_left: int = 0
    halted_until_day: dt.date | None = None
    hard_halted: bool = False


@dataclass(frozen=True)
class HaltDecision:
    level: HaltLevel
    reason: str = ""


_OK = HaltDecision(HaltLevel.NONE)


class KillSwitch:
    def __init__(self, cfg: KillSwitchConfig, start_equity: float):
        self.cfg = cfg
        self.state = KillSwitchState(peak_equity=start_equity, day_start_equity=start_equity)

    def reset(self, start_equity: float) -> None:
        self.state = KillSwitchState(peak_equity=start_equity, day_start_equity=start_equity)

    def on_trade_closed(self, pnl: float) -> None:
        self.state.loss_streak = self.state.loss_streak + 1 if pnl <= 0 else 0

    def evaluate(self, ts: dt.datetime, equity: float) -> HaltDecision:
        st = self.state
        # roll the trading day
        d = ts.date()
        if st.day != d:
            st.day = d
            st.day_start_equity = equity
        st.peak_equity = max(st.peak_equity, equity)

        if st.hard_halted:
            return HaltDecision(HaltLevel.HARD, "hard halt latched")

        # hard switches
        if self.cfg.equity_floor > 0 and equity <= self.cfg.equity_floor:
            st.hard_halted = True
            return HaltDecision(HaltLevel.HARD, f"equity floor {self.cfg.equity_floor} breached")
        dd = (st.peak_equity - equity) / st.peak_equity if st.peak_equity > 0 else 0.0
        if dd >= self.cfg.max_dd_pct:
            st.hard_halted = True
            return HaltDecision(HaltLevel.HARD, f"max drawdown {dd:.1%} >= {self.cfg.max_dd_pct:.0%}")

        # soft switches
        if st.halted_until_day is not None and d <= st.halted_until_day:
            return HaltDecision(HaltLevel.SOFT, "daily loss halt active")
        day_loss = (st.day_start_equity - equity) / st.day_start_equity if st.day_start_equity > 0 else 0.0
        if day_loss >= self.cfg.daily_loss_pct:
            st.halted_until_day = d
            return HaltDecision(HaltLevel.SOFT, f"daily loss {day_loss:.1%} >= {self.cfg.daily_loss_pct:.0%}")
        # consecutive-loss COOLDOWN: pause N bars, then auto-resume (reset streak on trip
        # so we don't deadlock — paused entries can't produce the win that would reset it)
        if st.cooldown_left > 0:
            st.cooldown_left -= 1
            return HaltDecision(HaltLevel.SOFT, f"cooldown {st.cooldown_left} bars left")
        if self.cfg.consecutive_losses and st.loss_streak >= self.cfg.consecutive_losses:
            st.cooldown_left = self.cfg.cooldown_bars
            st.loss_streak = 0
            return HaltDecision(HaltLevel.SOFT, f"{self.cfg.consecutive_losses} consecutive losses -> cooldown {self.cfg.cooldown_bars} bars")

        return _OK
