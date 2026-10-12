"""Risk sizing and portfolio caps.

Risk-based sizing: each trade risks a fixed fraction of CURRENT equity. Position size
is set so that a stop-out loses exactly that fraction. Caps limit concurrent exposure.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from jcoin.engine.types import Account, EnterIntent

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RiskConfig:
    risk_frac: float = 0.01       # fraction of equity risked per trade
    max_per_symbol: int = 1
    max_concurrent: int = 2
    # Ceiling on notional per position as a fraction of equity (1.0 = no leverage).
    # size_position() had no ceiling at all (audit 2026-09-18, item #5): a small stop
    # distance could size an enormous, effectively-leveraged position. 1.0 caps a
    # single position's notional at 100% of current equity.
    max_notional_frac: float = 1.0


def can_open(account: Account, symbol: str, cfg: RiskConfig) -> bool:
    if account.open_count >= cfg.max_concurrent:
        return False
    if symbol in account.positions:  # max_per_symbol == 1 in v1
        return False
    return True


def size_position(equity: float, intent: EnterIntent, entry_price: float, cfg: RiskConfig):
    """Return (size_units, risk_dollars). size set so stop-out = risk_frac * equity,
    then capped so notional (size * entry_price) never exceeds max_notional_frac of
    equity. risk_dollars is recomputed after a cap so R-multiples still reflect the
    ACTUAL dollar risk of the (smaller) capped position, not the uncapped target."""
    stop_dist = abs(entry_price - intent.stop_price)
    if stop_dist <= 0:
        return 0.0, 0.0
    risk_dollars = cfg.risk_frac * equity
    size = risk_dollars / stop_dist

    if entry_price > 0 and cfg.max_notional_frac > 0:
        max_size = (equity * cfg.max_notional_frac) / entry_price
        if size > max_size:
            log.info("position size capped for %s: %.6f -> %.6f units "
                     "(max_notional_frac=%.2f, equity=%.2f)",
                     intent.symbol, size, max_size, cfg.max_notional_frac, equity)
            size = max_size
            risk_dollars = size * stop_dist

    return size, risk_dollars
