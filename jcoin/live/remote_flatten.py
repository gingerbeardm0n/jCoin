"""Remote flatten-all switch (STRATEGY_SPEC.md mandatory safety item #9: "manual
flatten-all + disable reachable from phone").

Mechanism: check a raw GitHub URL for a trigger file each tick. To flatten everything
from your phone: open the GitHub app/browser, create a file named `FLATTEN.request`
in the repo root on `main` (any content), commit. The next tick (within the hourly
scheduler cadence, no redeploy needed -- this is a live HTTP fetch, not a git pull)
sees it, flattens every open position at the current price, and LATCHES a local halt
so the bot stays benched until you delete `FLATTEN_HALT.latch` from the state dir
yourself (same explicit-human-reset philosophy as the error breaker / kill-switch
hard halt). Delete `FLATTEN.request` from the repo once you're ready to resume, or
the very next tick after you clear the latch will just flatten again.

Deliberately does NOT use git (no repo pull needed on the runner) -- a plain
raw.githubusercontent.com fetch works identically whether the bot runs on a laptop
or on Render, and needs no local git state.
"""

from __future__ import annotations

import logging
import urllib.error
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_FLATTEN_URL = "https://raw.githubusercontent.com/gingerbeardm0n/jCoin/main/FLATTEN.request"


def flatten_requested(url: str = DEFAULT_FLATTEN_URL) -> bool:
    """True if the trigger file exists on GitHub. Best-effort: any fetch error (network
    blip, DNS, etc) is treated as 'no request pending' -- this must never be the reason
    a trading tick fails."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        urllib.request.urlopen(req, timeout=10)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        log.warning("flatten_requested: unexpected HTTP %d checking %s", e.code, url)
        return False
    except Exception as e:
        log.warning("flatten_requested: check failed (treating as no request): %s", e)
        return False


def latch_path(state_dir: str) -> Path:
    return Path(state_dir) / "FLATTEN_HALT.latch"


def is_latched(state_dir: str) -> bool:
    p = latch_path(state_dir)
    if p.exists():
        log.error("FLATTEN HALT LATCHED (%s) — delete this file to resume trading. "
                  "If FLATTEN.request is still on GitHub main, delete that too or this "
                  "will just flatten and re-latch on the next tick.", p)
        return True
    return False


def handle_flatten(trader, state_dir: str, url: str = DEFAULT_FLATTEN_URL) -> bool:
    """Check for a pending flatten request; if present, close every open position at
    the trader's last known price and latch a halt. Returns True if a flatten just
    happened (caller should skip normal signal processing this tick — the account is
    now meant to sit flat and disabled)."""
    if not flatten_requested(url):
        return False

    acct = trader.engine.account
    if acct.open_count == 0:
        log.warning("REMOTE FLATTEN requested — no open positions, just latching the halt")
    else:
        log.warning("REMOTE FLATTEN requested — closing %d open position(s) NOW", acct.open_count)
        for symbol, pos in list(acct.positions.items()):
            price = trader._last_prices.get(symbol, pos.entry_price)
            if hasattr(trader, "_kraken"):
                trader._kraken.cancel_stop(pos.stop_order_id, symbol)
                fill = trader._kraken.exit(pos, price, _fake_bar(pos, price), "remote_flatten")
                price = fill.price
            trader.engine.force_close(pos, price, trader.last_ts or _utcnow(), "remote_flatten")

    trader.engine.entries_enabled = False
    latch_path(state_dir).parent.mkdir(parents=True, exist_ok=True)
    latch_path(state_dir).write_text(
        f"FLATTENED by remote request at {_utcnow().isoformat()}\n"
        f"Delete this file to resume trading. Also delete FLATTEN.request from the\n"
        f"GitHub repo (main branch) or the next tick will flatten+latch again.\n"
    )
    trader._save()
    log.error("REMOTE FLATTEN complete — account is flat and DISABLED until %s is deleted",
             latch_path(state_dir))
    return True


def _utcnow():
    import datetime as dt
    return dt.datetime.now(dt.timezone.utc)


def _fake_bar(pos, price: float):
    from jcoin.engine.types import Bar
    return Bar(pos.symbol, _utcnow(), price, price, price, price, 0.0)
