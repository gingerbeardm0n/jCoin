"""Consecutive-error circuit breaker (STRATEGY_SPEC.md mandatory safety item #6).

A runner that fails once is a blip; one that fails every run for a day is a broken
system placing (or failing to place) real orders blind. Track consecutive failures in
a small state file; after `max_streak` failures, latch a halt that blocks further runs
until a human deletes the latch file (explicit acknowledgment, same philosophy as the
kill-switch hard halt).

Usage (wrapping a runner's main step):
    from jcoin.live.error_breaker import ErrorBreaker
    breaker = ErrorBreaker("paper_state")
    if breaker.halted():
        sys.exit(2)      # loud non-zero exit; scheduler log shows the latch reason
    try:
        ... run ...
        breaker.record_success()
    except Exception:
        breaker.record_failure()
        raise
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_MAX_STREAK = 6  # at hourly scheduling = 6h of consecutive failures -> latch


class ErrorBreaker:
    def __init__(self, state_dir: str, max_streak: int = DEFAULT_MAX_STREAK):
        d = Path(state_dir)
        d.mkdir(parents=True, exist_ok=True)
        self.streak_path = d / "error_streak.json"
        self.latch_path = d / "ERROR_HALT.latch"
        self.max_streak = max_streak

    def halted(self) -> bool:
        if self.latch_path.exists():
            log.error("ERROR BREAKER LATCHED: %s — delete this file after fixing the "
                      "root cause to resume", self.latch_path)
            return True
        return False

    def record_success(self) -> None:
        if self.streak_path.exists():
            self.streak_path.unlink()

    def record_failure(self, reason: str = "") -> None:
        streak = 0
        if self.streak_path.exists():
            try:
                streak = json.loads(self.streak_path.read_text()).get("streak", 0)
            except Exception:
                streak = 0
        streak += 1
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        self.streak_path.write_text(json.dumps({"streak": streak, "last": now,
                                                "reason": reason}))
        log.warning("error streak: %d/%d consecutive failures", streak, self.max_streak)
        if streak >= self.max_streak:
            self.latch_path.write_text(
                f"LATCHED {now}\nstreak={streak}\nlast reason: {reason}\n"
                f"Runner is HALTED. Fix the root cause, then delete this file to resume.\n")
            log.error("ERROR BREAKER: %d consecutive failures -> HALT LATCHED at %s",
                      streak, self.latch_path)
