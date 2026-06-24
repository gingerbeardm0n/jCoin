"""Broker adapters — the ONE place that differs between backtest and live.

Broker (ABC): how an order becomes a fill.
  - BacktestBroker: simulated fills from candle data + a modeled cost.
  - (later) PaperBroker / LiveBroker: real exchange via ccxt, same interface.

The engine and strategy never know which broker they're running against — that's the
parity guarantee.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from jcoin.engine.types import Bar, Fill, Position, Side


class Broker(ABC):
    @abstractmethod
    def enter(self, symbol: str, side: Side, size: float, bar: Bar) -> Fill: ...

    @abstractmethod
    def exit(self, pos: Position, price: float, bar: Bar, reason: str) -> Fill: ...


class BacktestBroker(Broker):
    """Simulated fills. Entry at the breakout bar close (taker). Exit at the supplied
    price (stop level or close). Round-trip cost charged once on entry notional, which
    matches research/portfolio_backtest.py so the engine reproduces its results.
    """

    def __init__(self, cost_frac: float):
        self.cost_frac = cost_frac  # round-trip fee + slippage as a fraction

    def enter(self, symbol: str, side: Side, size: float, bar: Bar) -> Fill:
        price = bar.close
        cost = self.cost_frac * size * price  # full round-trip charged here
        return Fill(symbol, bar.ts, side, price, size, cost, "enter")

    def exit(self, pos: Position, price: float, bar: Bar, reason: str) -> Fill:
        # exit cost already accounted at entry (round-trip) -> 0 here, for parity
        return Fill(pos.symbol, bar.ts, pos.side, price, pos.size, 0.0, "exit")


class PaperBroker(BacktestBroker):
    """Self-simulated paper broker for live paper trading.

    Fill model is identical to BacktestBroker (modeled fills against the just-closed
    bar) — appropriate for a 4h swing strategy that isn't latency- or fill-sensitive.
    It is a distinct class so the live path is explicit and can later diverge (e.g.
    next-bar-open fills, partial fills, real-fee reconciliation) without touching the
    backtest. Cost defaults reflect live taker economics; override per venue.
    """

    def __init__(self, cost_frac: float = 0.0012):  # ~6bp fee + ~6bp slippage round-trip
        super().__init__(cost_frac)
