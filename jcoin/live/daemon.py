"""jCoin autonomous trading daemon.

Runs forever. Wakes at each 4h bar close + OFFSET_MIN, fires run_kraken (or
run_paper), sleeps until next close. No Task Scheduler needed.

Usage:
    # Demo Kraken trading (default):
    python -m jcoin.live.daemon

    # Paper simulation only:
    python -m jcoin.live.daemon --mode paper

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
import urllib.request

log = logging.getLogger("jcoin.daemon")

# GAP FOUND 2026-07-03 auditing the Render blueprint: Render Cron Jobs cannot attach to
# disks, and disks cannot be shared between services -- so the local Windows watchdog
# (jcoin/live/watchdog.py, a separate scheduled task reading the SAME state.json) has
# no equivalent on Render; a second service literally cannot see this worker's state.
# Fix: an optional dead-man's-switch ping after every successful tick. Point PING_URL at
# any uptime-monitor "ping" endpoint (healthchecks.io / cronitor / better-uptime all use
# this exact pattern: they alert YOU if the ping doesn't arrive within the expected
# window). Unset locally -> no-op, the Windows watchdog task covers that deployment.
_PING_URL = os.environ.get("JCOIN_PING_URL")


def _ping_alive() -> None:
    if not _PING_URL:
        return
    try:
        urllib.request.urlopen(_PING_URL, timeout=10)
    except Exception as e:
        log.warning("heartbeat ping failed (non-fatal): %s", e)

# On a hosted deploy (Render, etc.) the container filesystem is thrown away on every
# restart/redeploy UNLESS state lives on a mounted persistent disk. Set JCOIN_STATE_DIR
# to that disk's mount path (e.g. /var/data) and state writes there instead of the
# relative default. Unset -> unchanged local-machine behavior (paper_state/, kraken_state/
# under the working directory). See STRATEGY_SPEC.md deployment notes.
_STATE_ROOT = os.environ.get("JCOIN_STATE_DIR")

BAR_HOURS    = 4
PREFETCH_MIN = 15  # wake before bar close to prefetch historical data
OFFSET_MIN   = 5   # fire N minutes AFTER bar close (bar fully settled)


# ── timing helpers ────────────────────────────────────────────────────────────

def bar_closes() -> list[dt.datetime]:
    """Next two 4h bar close times from now (UTC)."""
    now = dt.datetime.now(dt.timezone.utc)
    bar_start_hour = (now.hour // BAR_HOURS) * BAR_HOURS
    base = now.replace(hour=bar_start_hour, minute=0, second=0, microsecond=0)
    return [base + dt.timedelta(hours=BAR_HOURS * i) for i in range(1, 3)]


def next_prefetch_utc() -> dt.datetime:
    return bar_closes()[0] - dt.timedelta(minutes=PREFETCH_MIN)


def next_fire_utc() -> dt.datetime:
    return bar_closes()[0] + dt.timedelta(minutes=OFFSET_MIN)


def sleep_until(target: dt.datetime, label: str) -> None:
    while True:
        remaining = (target - dt.datetime.now(dt.timezone.utc)).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 60))
        remaining2 = (target - dt.datetime.now(dt.timezone.utc)).total_seconds()
        if remaining2 > 0:
            log.info("%s in %dm %ds", label, int(remaining2 // 60), int(remaining2 % 60))


# ── runners ───────────────────────────────────────────────────────────────────

def run_module(module: str, extra_args: list[str] | None = None) -> int:
    cmd = [sys.executable, "-m", module] + (extra_args or [])
    return subprocess.run(cmd, capture_output=False).returncode


def prefetch(mode: str) -> None:
    """T-15: warm up data cache while bar still forming. Cuts order latency at close."""
    log.info("=== PREFETCH (bar closes in %dmin) ===", PREFETCH_MIN)
    # Import here to avoid slowing startup; errors are non-fatal
    try:
        from jcoin.data.live_source import get_recent_candles
        from jcoin.data.config import LIVE_MARKETS
        labels = [m.label for m in LIVE_MARKETS]
        for label in labels:
            get_recent_candles(label, "4h", limit=2300)
        log.info("prefetch done: %d symbols cached", len(labels))
    except Exception:
        log.warning("prefetch failed (non-fatal — full fetch will run at bar close)")


def tick(mode: str) -> None:
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    log.info("=== BAR CLOSE %s mode=%s ===", now, mode)

    if mode in ("kraken", "both"):
        args = ["--state-dir", f"{_STATE_ROOT}/kraken_state"] if _STATE_ROOT else None
        rc = run_module("jcoin.live.run_kraken", args)
        log.info("run_kraken exit=%d", rc)

    if mode in ("paper", "both"):
        args = ["--state-dir", f"{_STATE_ROOT}/paper_state"] if _STATE_ROOT else None
        rc = run_module("jcoin.live.run_paper", args)
        log.info("run_paper exit=%d", rc)


# ── main loop ─────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="jCoin autonomous 4h daemon")
    p.add_argument("--mode", choices=["kraken", "paper", "both"], default="kraken")
    p.add_argument("--run-now", action="store_true",
                   help="Fire once immediately before entering the sleep loop")
    args = p.parse_args(argv)

    import pathlib
    pathlib.Path("logs").mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/daemon.log", encoding="utf-8"),
        ],
    )

    closes = bar_closes()
    log.info("jCoin daemon started | mode=%s | bar=%dh | prefetch=T-%dmin | fire=T+%dmin",
             args.mode, BAR_HOURS, PREFETCH_MIN, OFFSET_MIN)
    log.info("upcoming bars: %s", [c.isoformat(timespec="minutes") for c in closes])

    if args.run_now:
        tick(args.mode)

    while True:
        pf  = next_prefetch_utc()
        fire = next_fire_utc()

        # Sleep until prefetch window (T-15)
        if dt.datetime.now(dt.timezone.utc) < pf:
            log.info("sleeping until prefetch %s UTC", pf.isoformat(timespec="seconds"))
            sleep_until(pf, "prefetch")
            try:
                prefetch(args.mode)
            except Exception:
                log.exception("prefetch error (non-fatal)")

        # Sleep until bar close + offset (T+5)
        log.info("sleeping until bar close %s UTC", fire.isoformat(timespec="seconds"))
        sleep_until(fire, "bar close")
        try:
            tick(args.mode)
            _ping_alive()  # proves the daemon process itself is alive + looping, every
                           # wake, independent of whether this wake had a new bar to trade
        except Exception:
            log.exception("tick failed — continuing to next bar")

        time.sleep(30)  # ensure next_fire_utc() moves past current bar


if __name__ == "__main__":
    raise SystemExit(main())
