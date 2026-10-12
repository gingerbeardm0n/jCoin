"""Tests for jcoin/engine/kill_switch.py -- daily-loss and max-DD halt thresholds."""

from __future__ import annotations

import datetime as dt

from jcoin.engine.kill_switch import HaltLevel, KillSwitch, KillSwitchConfig

_TS = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)


def test_no_halt_when_equity_flat():
    cfg = KillSwitchConfig(daily_loss_pct=0.03, max_dd_pct=0.25)
    ks = KillSwitch(cfg, start_equity=10_000.0)
    decision = ks.evaluate(_TS, 10_000.0)
    assert decision.level is HaltLevel.NONE


def test_daily_loss_triggers_soft_halt():
    cfg = KillSwitchConfig(daily_loss_pct=0.03, max_dd_pct=0.50)
    ks = KillSwitch(cfg, start_equity=10_000.0)
    ks.evaluate(_TS, 10_000.0)  # establishes day_start_equity
    decision = ks.evaluate(_TS, 9_600.0)  # -4%, over the 3% daily threshold
    assert decision.level is HaltLevel.SOFT
    assert "daily loss" in decision.reason


def test_daily_loss_below_threshold_does_not_halt():
    cfg = KillSwitchConfig(daily_loss_pct=0.03, max_dd_pct=0.50)
    ks = KillSwitch(cfg, start_equity=10_000.0)
    ks.evaluate(_TS, 10_000.0)
    decision = ks.evaluate(_TS, 9_800.0)  # -2%, under the 3% threshold
    assert decision.level is HaltLevel.NONE


def test_max_drawdown_triggers_hard_halt_and_latches():
    cfg = KillSwitchConfig(daily_loss_pct=0.90, max_dd_pct=0.25)
    ks = KillSwitch(cfg, start_equity=10_000.0)
    ks.evaluate(_TS, 10_000.0)  # peak
    decision = ks.evaluate(_TS, 7_400.0)  # -26% from peak, over the 25% threshold
    assert decision.level is HaltLevel.HARD

    # Hard halt latches -- must stay halted even after equity "recovers".
    decision2 = ks.evaluate(_TS, 10_000.0)
    assert decision2.level is HaltLevel.HARD


def test_max_drawdown_below_threshold_does_not_halt():
    cfg = KillSwitchConfig(daily_loss_pct=0.90, max_dd_pct=0.25)
    ks = KillSwitch(cfg, start_equity=10_000.0)
    ks.evaluate(_TS, 10_000.0)
    decision = ks.evaluate(_TS, 8_000.0)  # -20% from peak, under the 25% threshold
    assert decision.level is HaltLevel.NONE


def test_equity_floor_triggers_hard_halt():
    cfg = KillSwitchConfig(daily_loss_pct=0.90, max_dd_pct=0.90, equity_floor=1_000.0)
    ks = KillSwitch(cfg, start_equity=10_000.0)
    ks.evaluate(_TS, 10_000.0)
    decision = ks.evaluate(_TS, 900.0)
    assert decision.level is HaltLevel.HARD
    assert "floor" in decision.reason
