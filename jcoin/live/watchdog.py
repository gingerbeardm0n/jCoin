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

from jcoin.live.ping import ping

REPO = Path(__file__).resolve().parents[2]
# On a hosted deploy (Render, etc.), state.json lives on the mounted persistent disk
# (JCOIN_STATE_DIR), NOT under the repo checkout. This must match daemon.py's routing
# or the watchdog silently watches a path that will never exist and always "passes"
# with zero real monitoring -- found 2026-07-03 while auditing the Render blueprint.
_STATE_ROOT = Path(os.environ["JCOIN_STATE_DIR"]) if os.environ.get("JCOIN_STATE_DIR") else REPO

# The paper runner is always monitored. kraken_state/state.json is added ONLY if that
# file's mtime is within the last 24h (audit 2026-09-18, item #4c) -- the Kraken demo
# route was abandoned 2026-06-30 and its state dir is permanently stale, so watching it
# unconditionally would alert forever with zero signal. If live trading resumes on
# Kraken, its state.json will start getting touched again and this picks it up
# automatically; no code change needed.
DEFAULT_STATES = ["paper_state/state.json"]

ALERT_FILE = REPO / "WATCHDOG_ALERT.txt"
ALERT_FILE_OLD = REPO / "WATCHDOG_ALERT.old.txt"
ALERT_MAX_LINES = 200
_DOWN_MARKER = REPO / "paper_state" / "WATCHDOG_DOWN.marker"


def _active_default_states() -> list[str]:
    states = ["paper_state/state.json"]
    kraken_path = REPO / "kraken_state" / "state.json"
    if kraken_path.exists():
        age_h = (dt.datetime.now(dt.timezone.utc)
                 - dt.datetime.fromtimestamp(kraken_path.stat().st_mtime, tz=dt.timezone.utc)
                 ).total_seconds() / 3600
        if age_h <= 24.0:
            states.append("kraken_state/state.json")
    return states


def _rotate_alert_file() -> None:
    """Keep WATCHDOG_ALERT.txt from growing forever: once it passes ALERT_MAX_LINES,
    move it to WATCHDOG_ALERT.old.txt and start a fresh one (audit 2026-09-18, item #4b)."""
    if not ALERT_FILE.exists():
        return
    try:
        n_lines = sum(1 for _ in open(ALERT_FILE, encoding="utf-8", errors="replace"))
        if n_lines > ALERT_MAX_LINES:
            ALERT_FILE.replace(ALERT_FILE_OLD)
    except Exception:
        pass


def _alert(msg: str) -> None:
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = f"[{stamp}] jCoin WATCHDOG ALERT\n{msg}\n"
    for target in (ALERT_FILE, Path.home() / "Desktop" / "jCoin_WATCHDOG_ALERT.txt"):
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


def _record_recovery() -> None:
    """Write a RECOVERED line so the alert file shows the outage actually ended,
    instead of trailing off with the last DOWN line and leaving it ambiguous whether
    it was ever fixed (audit 2026-09-18, item #4b)."""
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = f"[{stamp}] jCoin WATCHDOG: RECOVERED\n"
    for target in (ALERT_FILE, Path.home() / "Desktop" / "jCoin_WATCHDOG_ALERT.txt"):
        try:
            with open(target, "a", encoding="utf-8") as f:
                f.write(body)
        except Exception:
            pass


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="jCoin heartbeat watchdog")
    p.add_argument("--states", nargs="+", default=None,
                   help="default: paper_state always, kraken_state only if touched in last 24h")
    p.add_argument("--max-age-hours", type=float, default=5.0,
                   help="alert if a state file is staler than this (4h bar + 1h slack)")
    args = p.parse_args(argv)

    _rotate_alert_file()

    states = args.states if args.states is not None else _active_default_states()
    print(f"monitoring: {states}")

    now = dt.datetime.now(dt.timezone.utc)
    breaches = []
    for rel in states:
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
        try:
            _DOWN_MARKER.parent.mkdir(parents=True, exist_ok=True)
            _DOWN_MARKER.touch()
        except Exception:
            pass
        ping(suffix="/fail")  # no-op unless JCOIN_PING_URL is set
        return 1

    # Healthy now -- if we were previously down, log the recovery and clear the marker
    # so the next breach starts a fresh RECOVERED/DOWN cycle instead of looking
    # continuous (audit 2026-09-18, item #4b).
    if _DOWN_MARKER.exists():
        _record_recovery()
        try:
            _DOWN_MARKER.unlink()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
