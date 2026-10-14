"""jCoin autonomous trading daemon.

Runs forever. Wakes hourly at HH:05 UTC and fires run_paper (or run_kraken).
Meant for an always-on server (systemd on the GCP VM). No Task Scheduler needed.

Usage:
    # Paper simulation (default):
    python -m jcoin.live.daemon

    # One pass then exit (smoke test):
    python -m jcoin.live.daemon --once

    # Both simultaneously:
    python -m jcoin.live.daemon --mode both

Keep this window open (or run via: pythonw -m jcoin.live.daemon to hide it).
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import subprocess
import sys
import time
from logging.handlers import RotatingFileHandler


log = logging.getLogger("jcoin.daemon")

# GAP FOUND 2026-07-03 auditing the Render blueprint: Render Cron Jobs cannot attach to
# disks, and disks cannot be shared between services -- so the local Windows watchdog
# (jcoin/live/watchdog.py, a separate scheduled task reading the SAME state.json) has
# no equivalent on Render; a second service literally cannot see this worker's state.
# Fix: an optional dead-man's-switch ping after every successful tick. Point JCOIN_PING_URL
# at any uptime-monitor "ping" endpoint (healthchecks.io / cronitor / better-uptime all use
# this exact pattern: they alert YOU if the ping doesn't arrive within the expected
# window). Unset locally -> no-op, the Windows watchdog task covers that deployment.
# (audit 2026-09-18: the ping call itself now lives in jcoin/live/ping.py, shared with
# run_paper.py and watchdog.py instead of being duplicated here.)

# On a hosted deploy (Render, etc.) the container filesystem is thrown away on every
# restart/redeploy UNLESS state lives on a mounted persistent disk. Set JCOIN_STATE_DIR
# to that disk's mount path (e.g. /var/data) and state writes there instead of the
# relative default. Unset -> unchanged local-machine behavior (paper_state/, kraken_state/
# under the working directory). See STRATEGY_SPEC.md deployment notes.
_STATE_ROOT = os.environ.get("JCOIN_STATE_DIR")

# Hourly, a few minutes past the hour (UTC). Same cadence as the Windows scheduled
# task: run_paper/run_kraken are idempotent and catch up every missed 4h bar, so
# extra wakes are harmless and act as a built-in retry if a bar shows up late.
# (2026-10-12: replaced the old once-per-4h schedule + T-15 prefetch. The prefetch
# passed a label string where a Market was required, so it always failed silently,
# and the disk candle cache made it pointless anyway.)
OFFSET_MIN = 5


def next_fire_utc(now: dt.datetime | None = None) -> dt.datetime:
    """Next HH:OFFSET_MIN (UTC) strictly after `now`."""
    now = now or dt.datetime.now(dt.timezone.utc)
    fire = now.replace(minute=OFFSET_MIN, second=0, microsecond=0)
    if fire <= now:
        fire += dt.timedelta(hours=1)
    return fire


def sleep_until(target: dt.datetime) -> None:
    while True:
        remaining = (target - dt.datetime.now(dt.timezone.utc)).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 60))


def run_module(module: str, extra_args: list[str] | None = None) -> int:
    cmd = [sys.executable, "-m", module] + (extra_args or [])
    return subprocess.run(cmd, capture_output=False).returncode


def tick(mode: str) -> dict[str, int]:
    """Run one pass of each enabled runner; return their exit codes.

    The heartbeat ping is sent by run_paper/run_kraken themselves, and only when the
    run actually worked. The daemon does NOT ping on its own any more: it used to
    ping after every wake even when the runner had failed or was halted, which made
    an uptime monitor report "alive" while trading was broken (audit 2026-09-18).
    """
    log.info("=== TICK %s mode=%s ===",
             dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), mode)
    codes: dict[str, int] = {}
    for name, module, sub in (("kraken", "jcoin.live.run_kraken", "kraken_state"),
                              ("paper", "jcoin.live.run_paper", "paper_state")):
        if mode not in (name, "both"):
            continue
        args = ["--state-dir", f"{_STATE_ROOT}/{sub}"] if _STATE_ROOT else None
        rc = run_module(module, args)
        codes[name] = rc
        if rc == 0:
            log.info("%s exit=0", module)
        else:
            log.warning("%s exit=%d (2=error halt, 3=flatten latch, 4=market data failed, 5=kill-switch latch)",
                        module, rc)
    return codes


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="jCoin autonomous daemon (hourly)")
    # Default is PAPER. Real-money mode must always be an explicit choice.
    p.add_argument("--mode", choices=["paper", "kraken", "both"], default="paper")
    p.add_argument("--run-now", action="store_true",
                   help="Fire once immediately before entering the sleep loop")
    p.add_argument("--once", action="store_true",
                   help="Fire once and exit (smoke test)")
    args = p.parse_args(argv)

    import pathlib
    pathlib.Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler("logs/daemon.log", maxBytes=5_000_000, backupCount=3,
                                encoding="utf-8"),
        ],
    )

    log.info("jCoin daemon started | mode=%s | fires hourly at HH:%02d UTC",
             args.mode, OFFSET_MIN)

    if args.once:
        codes = tick(args.mode)
        return max(codes.values(), default=0)

    if args.run_now:
        tick(args.mode)

    while True:
        fire = next_fire_utc()
        log.info("sleeping until %s UTC", fire.isoformat(timespec="minutes"))
        sleep_until(fire)
        try:
            tick(args.mode)
        except Exception:
            log.exception("tick failed — continuing to next hour")


if __name__ == "__main__":
    raise SystemExit(main())
