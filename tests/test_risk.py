"""Tests for jcoin/engine/risk.py -- position-size cap (audit 2026-09-18, item #5)."""

from __future__ import annotations

from jcoin.engine.risk import RiskConfig, size_position
from jcoin.engine.types import EnterIntent, Side


def test_cap_applies_when_size_would_be_oversized():
    # risk_frac=0.5 with a tight $1 stop distance would otherwise size a position far
    # bigger than the account -- max_notional_frac must clamp it.
    cfg = RiskConfig(risk_frac=0.5, max_notional_frac=1.0)
    intent = EnterIntent(symbol="BTC", side=Side.LONG, stop_price=99.0, atr=1.0)
    equity = 10_000.0
    entry_price = 100.0

    size, risk_dollars = size_position(equity, intent, entry_price, cfg)

    # Uncapped size would be (0.5*10000)/1 = 5000 units -> $500,000 notional.
    # Capped: equity * max_notional_frac / entry_price = 10000*1.0/100 = 100 units.
    assert size == 100.0
    # risk_dollars must reflect the ACTUAL (capped) position, not the uncapped target.
    assert risk_dollars == size * abs(entry_price - intent.stop_price)
    assert risk_dollars == 100.0


def test_uncapped_when_small():
    # A modest risk_frac with normal stop distance should size well under the cap and
    # be returned unmodified.
    cfg = RiskConfig(risk_frac=0.01, max_notional_frac=1.0)
    intent = EnterIntent(symbol="BTC", side=Side.LONG, stop_price=95.0, atr=1.0)
    equity = 10_000.0
    entry_price = 100.0

    size, risk_dollars = size_position(equity, intent, entry_price, cfg)

    # risk_dollars = 0.01*10000 = 100; stop_dist=5 -> size=20 units -> notional $2,000,
    # well under the $10,000 cap (max_notional_frac=1.0) so no capping should occur.
    assert size == 20.0
    assert risk_dollars == 100.0


def test_zero_stop_distance_returns_zero():
    cfg = RiskConfig()
    intent = EnterIntent(symbol="BTC", side=Side.LONG, stop_price=100.0, atr=1.0)
    size, risk_dollars = size_position(10_000.0, intent, 100.0, cfg)
    assert size == 0.0
    assert risk_dollars == 0.0


def test_cap_disabled_when_max_notional_frac_is_zero():
    # max_notional_frac<=0 disables the cap entirely (defensive: a misconfigured 0
    # must not silently zero out every position).
    cfg = RiskConfig(risk_frac=0.5, max_notional_frac=0.0)
    intent = EnterIntent(symbol="BTC", side=Side.LONG, stop_price=99.0, atr=1.0)
    size, risk_dollars = size_position(10_000.0, intent, 100.0, cfg)
    assert size == 5000.0
    assert risk_dollars == 5000.0
