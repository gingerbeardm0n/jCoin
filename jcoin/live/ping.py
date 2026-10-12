"""Shared dead-man's-switch ping helper (audit 2026-09-18).

Some deploy/scheduling setups want a positive "I'm alive" HTTP signal in addition to
the local Windows watchdog (jcoin/live/watchdog.py) and the ERROR_HALT latch
(error_breaker.py). Point JCOIN_PING_URL at any uptime-monitor "ping" endpoint
(healthchecks.io / cronitor / better-uptime all use this exact GET-to-confirm
pattern: they alert YOU if the ping doesn't arrive within the expected window).

Unset (the default -- Joel does not need to configure this) -> every call here is a
silent no-op. A ping failure is always logged, never raised -- monitoring must never
be the reason a trading tick fails.

Originally lived only in daemon.py as `_ping_alive`; moved here so run_paper.py and
watchdog.py can share it instead of duplicating the urllib call.
"""

from __future__ import annotations

import logging
import os
import urllib.request

log = logging.getLogger(__name__)

PING_URL = os.environ.get("JCOIN_PING_URL")


def ping(url: str | None = None, suffix: str = "", timeout: float = 5.0) -> None:
    """Best-effort GET to the ping URL (+ optional path suffix, e.g. '/fail').

    `url` defaults to the JCOIN_PING_URL env var (read once at import time). Does
    nothing if no URL is configured either way.
    """
    target = url if url is not None else PING_URL
    if not target:
        return
    try:
        urllib.request.urlopen(target + suffix, timeout=timeout)
    except Exception as e:
        log.warning("ping failed (non-fatal) %s: %s", target + suffix, e)
