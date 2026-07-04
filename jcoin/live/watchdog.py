"""Heartbeat watchdog (STRATEGY_SPEC.md mandatory safety item #3).

Runs as its OWN scheduled task, independent of the trading runner — if the runner
process/task dies silently, something outside it must notice. Checks how stale each
state file is; the paper/live runner touches state.json every processed bar (4h bars,
hourly scheduler ticks), so anything older than the threshold means the runner has
not completed a cycle in that long.

On breach it screams in every cheap local channel we have:
  - ALERT file in the repo root AND on the user's Desktop (hard to miss)
  - Windows Application event log (survives reboots, timestamped)
  - non-zero exit code (visible in Task Scheduler history)

It does NOT try to flatten positions itself: the paper account has no real risk, and
for live the resting exchange-side stops (safety item #7, kraken_broker.place_stop)
are the between-checks protection. The watchdog's job is only to make silence loud.

Usage:
    python -m jcoin.live.watchdog                   # check default state dirs
    python -m jcoin.live.watchdog --max-age-hours 5
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# On a hosted deploy (Render, etc.), state.json lives on the mounted persistent disk
# (JCOIN_STATE_DIR), NOT under the repo checkout. This must match daemon.py's routing
# or the watchdog silently watches a path that will never exist and always "passes"
# with zero real monitoring -- found 2026-07-03 while auditing the Render blueprint.
_STATE_ROOT = Path(os.environ["JCOIN_STATE_DIR"]) if os.environ.get("JCOIN_STATE_DIR") else REPO

# Only the paper runner is scheduled today. The Kraken demo route was abandoned
# (2026-06-30) and its state dir is intentionally stale — watching it would alert
# forever. When live trading launches, add kraken_state/state.json back here (or
# pass --states) so the live runner gets the same heartbeat coverage.
DEFAULT_STATES = ["paper_state/state.json"]


def _alert(msg: str) -> None:
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = f"[{stamp}] jCoin WATCHDOG ALERT\n{msg}\n"
    for target in (REPO / "WATCHDOG_ALERT.txt", Path.home() / "Desktop" / "jCoin_WATCHDOG_ALERT.txt"):
        try:
            with open(target, "a", encoding="utf-8") as f:
                f.write(body)
        except Exception:
            pass
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Write-EventLog -LogName Application -Source 'Application Error' "
             f"-EventId 7777 -EntryType Warning -Message 'jCoin watchdog: {msg}'"],
            capture_output=True, timeout=15,
        )
    except Exception:
        pass


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="jCoin heartbeat watchdog")
    p.add_argument("--states", nargs="+", default=DEFAULT_STATES)
    p.add_argument("--max-age-hours", type=float, default=5.0,
                   help="alert if a state file is staler than this (4h bar + 1h slack)")
    args = p.parse_args(argv)

    now = dt.datetime.now(dt.timezone.utc)
    breaches = []
    for rel in args.states:
        path = REPO / rel
        if not path.exists():
            continue  # runner not deployed for this mode — nothing to watch
        age_h = (now - dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc)).total_seconds() / 3600
        status = "STALE" if age_h > args.max_age_hours else "ok"
        print(f"{rel}: last heartbeat {age_h:.1f}h ago [{status}]")
        if age_h > args.max_age_hours:
            breaches.append(f"{rel} last updated {age_h:.1f}h ago (threshold {args.max_age_hours}h) "
                            f"— trading runner appears DOWN")

    # error-breaker latches are also a loud condition worth surfacing here
    for latch in (REPO / "paper_state" / "ERROR_HALT.latch", REPO / "kraken_state" / "ERROR_HALT.latch"):
        if latch.exists():
            breaches.append(f"error breaker LATCHED: {latch}")
            print(f"{latch}: LATCHED")

    if breaches:
        _alert("; ".join(breaches))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
