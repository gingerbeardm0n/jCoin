"""Risk sizing and portfolio caps.

Risk-based sizing: each trade risks a fixed fraction of CURRENT equity. Position size
is set so that a stop-out loses exactly that fraction. Caps limit concurrent exposure.
"""

from __future__ import annotations

from dataclasses import dataclass

from jcoin.engine.types import Account, EnterIntent


@dataclass(frozen=True)
class RiskConfig:
    risk_frac: float = 0.01       # fraction of equity risked per trade
    max_per_symbol: int = 1
    max_concurrent: int = 2


def can_open(account: Account, symbol: str, cfg: RiskConfig) -> bool:
    if account.open_count >= cfg.max_concurrent:
        return False
    if symbol in account.positions:  # max_per_symbol == 1 in v1
        return False
    return True


def size_position(equity: float, intent: EnterIntent, entry_price: float, cfg: RiskConfig):
    """Return (size_units, risk_dollars). size set so stop-out = risk_frac * equity."""
    stop_dist = abs(entry_price - intent.stop_price)
    if stop_dist <= 0:
        return 0.0, 0.0
    risk_dollars = cfg.risk_frac * equity
    size = risk_dollars / stop_dist
    return size, risk_dollars
