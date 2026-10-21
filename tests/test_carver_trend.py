"""Tests for the Carver continuous trend follower and daily breakout."""

import numpy as np
import pytest


def test_imports():
    from jcoin.research.carver_trend import (
        carver_forecast, carver_backtest, daily_breakout_trades, evaluate_daily,
    )


def test_forecast_clamp():
    """Forecast values outside [-20, +20] must be clamped."""
    from jcoin.research.carver_trend import carver_forecast

    # Construct arrays where close diverges wildly from EMA
    n = 100
    close = np.linspace(100, 10000, n)  # extreme ramp-up
    atr = np.ones(n) * 0.01  # tiny ATR to make forecast huge
    fc = carver_forecast(close, atr, fast=8, slow=32)
    assert fc.max() <= 20.0, f"forecast exceeded +20: {fc.max()}"
    assert fc.min() >= -20.0, f"forecast below -20: {fc.min()}"

    # Reverse: extreme ramp-down
    close_down = np.linspace(10000, 100, n)
    fc_down = carver_forecast(close_down, atr, fast=8, slow=32)
    assert fc_down.min() >= -20.0
    assert fc_down.max() <= 20.0


def test_forecast_zero_atr():
    """Zero ATR bars should produce zero forecast, not inf/nan."""
    from jcoin.research.carver_trend import carver_forecast

    close = np.array([100.0] * 50)
    atr = np.zeros(50)
    fc = carver_forecast(close, atr, fast=8, slow=32)
    assert np.all(np.isfinite(fc))
    assert np.all(fc == 0.0)


def test_daily_breakout_produces_trades():
    """Daily breakout must produce at least some trades over the dev window."""
    from jcoin.research.carver_trend import daily_breakout_trades

    trades, years = daily_breakout_trades()
    assert len(trades) > 0, "daily breakout produced zero trades"
    assert years > 4, f"dev window too short: {years} years"
