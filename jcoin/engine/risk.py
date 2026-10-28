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
    # Whole-contract sizing (paper realism for venues that trade integer contracts, e.g.
    # Coinbase nano perps: BTC 0.01, ETH 0.1 per contract). symbol -> base units per
    # contract. None (default) = fractional sizes exactly as before. When set,
    # size_position() rounds to whole contracts AFTER the notional cap; max_risk_mult
    # bounds how far the rounded position's stop-out risk may exceed the target risk.
    lot_sizes: dict[str, float] | None = None
    max_risk_mult: float = 2.0   # paper runners use 1.0 (hard 1% cap, Joel 2026-10-28)


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

    lot = cfg.lot_sizes.get(intent.symbol) if cfg.lot_sizes else None
    if lot:
        size, risk_dollars = _round_to_lots(equity, intent, entry_price, cfg, lot,
                                            size, risk_dollars, stop_dist)

    return size, risk_dollars


def _round_to_lots(equity: float, intent: EnterIntent, entry_price: float, cfg: RiskConfig,
                   lot: float, size: float, risk_dollars: float, stop_dist: float):
    """Round `size` to whole contracts of `lot` units. Nearest lot; a size that rounds to
    zero lots is bumped to one lot only if that lot's risk is within max_risk_mult x the
    target risk. Skips (returns 0, 0) when the rounded risk is too large, there is no
    whole lot, or a lot would break the notional cap."""
    lots = int(size / lot + 0.5)
    if lots == 0:
        lots = 1
    max_risk = cfg.max_risk_mult * risk_dollars
    if entry_price > 0 and cfg.max_notional_frac > 0:
        max_lots = int((equity * cfg.max_notional_frac) / (entry_price * lot) + 1e-9)
        if lots > max_lots:
            lots = max_lots   # rounding up must not breach the notional cap
    if lots == 0:
        log.info("lot rounding skip for %s: no whole %.4g-unit contract fits the notional cap "
                 "(target size %.6f)", intent.symbol, lot, size)
        return 0.0, 0.0
    rounded_risk = lots * lot * stop_dist
    if rounded_risk > max_risk and lots > 1:
        # Nearest-lot rounding overshot the cap: fall back to the largest lot count that fits.
        lots = min(lots, int(max_risk / (lot * stop_dist) + 1e-9))
        rounded_risk = lots * lot * stop_dist
    if lots == 0 or rounded_risk > max_risk:
        log.info("lot rounding skip for %s: %d contract(s) risk %.2f > %.2fx target %.2f "
                 "(target size %.6f, lot %.4g)", intent.symbol, lots, rounded_risk,
                 cfg.max_risk_mult, risk_dollars, size, lot)
        return 0.0, 0.0
    if lots * lot != size:
        log.info("lot rounding for %s: %.6f -> %d contract(s) = %.6f units (risk %.2f vs target %.2f)",
                 intent.symbol, size, lots, lots * lot, rounded_risk, risk_dollars)
    return lots * lot, rounded_risk
