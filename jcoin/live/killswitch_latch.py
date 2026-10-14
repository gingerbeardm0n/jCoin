"""Human-reset latch for kill-switch HARD halts (KILL_RULE.md).

The KillSwitch's hard_halted flag is persisted in state.json and survives restarts, but a
flag in a state file is too easy to clear by accident (reset_equity() clears it, so does
deleting state.json). So every hard halt also writes KILLSWITCH_HALT.latch into the state
dir. run_paper / run_kraken refuse to start while it exists (exit 5), and reset_equity()
refuses too. Same explicit-human-action convention as ERROR_HALT.latch / FLATTEN_HALT.latch.

To restart (a written, dated decision, never a flag flip): review the trade log, data and
code; delete the latch file; then run once with --reset-equity to start a new clock
(deleting the latch alone is not enough: the persisted hard_halted flag re-latches on the
next bar).
"""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

log = logging.getLogger(__name__)

LATCH_NAME = "KILLSWITCH_HALT.latch"


def latch_path(state_dir) -> Path:
    return Path(state_dir) / LATCH_NAME


def is_latched(state_dir) -> bool:
    p = latch_path(state_dir)
    if p.exists():
        log.error("KILL-SWITCH HARD HALT LATCHED (%s) — human review required. See KILL_RULE.md "
                  "for the restart procedure.", p)
        return True
    return False


def write_latch(state_dir, reason: str) -> bool:
    """Create the latch (idempotent). Returns True if it was newly created."""
    p = latch_path(state_dir)
    if p.exists():
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        f"KILL-SWITCH HARD HALT {dt.datetime.now(dt.timezone.utc).isoformat()}\n"
        f"reason: {reason}\n"
        f"All positions were flattened. The runner refuses to start while this file exists.\n"
        f"Review the trade log, data feed and code (KILL_RULE.md), delete this file, then run\n"
        f"once with --reset-equity to start a new clock. Deleting the file alone is not enough.\n"
    )
    return True
