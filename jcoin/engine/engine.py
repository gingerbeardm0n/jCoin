"""TradingEngine — the bar loop. Identical for backtest and live.

Per timestamp it (1) manages open positions, then (2) considers new entries, subject to
risk caps. The same `step()` is driven by historical bars in backtest and by live bars
as they close. Only the Broker differs.

Manage-before-enter ordering + the trail/stop sequence reproduce
research/backtest_breakout.py and portfolio_backtest.py — the parity acceptance test.
"""

from __future__ import annotations

import datetime as dt

from jcoin.engine.broker import Broker
from jcoin.engine.risk import RiskConfig, can_open, size_position
from jcoin.engine.strategy import BreakoutStrategy
from jcoin.engine.types import Account, Bar, ClosedTrade, Position


class TradingEngine:
    def __init__(self, strategy: BreakoutStrategy, broker: Broker, risk: RiskConfig,
                 start_equity: float = 10_000.0):
        self.strategy = strategy
        self.broker = broker
        self.risk = risk
        self.account = Account(equity=start_equity)
        self._bars_held: dict[str, int] = {}
        self.entries_enabled: bool = True   # kill-switch can pause new entries

    def step(self, ts: dt.datetime, rows: dict[str, dict]) -> None:
        """rows: symbol -> feature row (dict with ohlc + features) for this timestamp."""
        # --- Phase 1: manage open positions (exits) ---
        for symbol, pos in list(self.account.positions.items()):
            row = rows.get(symbol)
            if row is None:
                continue
            self._bars_held[symbol] += 1
            decision = self.strategy.manage_position(pos, row, self._bars_held[symbol])
            if decision.exit:
                self._close(pos, decision.price, _bar(row), decision.reason)

        # --- Phase 2: consider entries for flat symbols (unless paused) ---
        if not self.entries_enabled:
            return
        for symbol, row in rows.items():
            if symbol in self.account.positions:
                continue
            intent = self.strategy.entry_signal(row)
            if intent is None:
                continue
            if not can_open(self.account, symbol, self.risk):
                continue
            size, risk_dollars = size_position(self.account.equity, intent, row["close"], self.risk)
            if size <= 0:
                continue
            self._open(intent, size, risk_dollars, _bar(row))

    def flatten_all(self, ts: dt.datetime, rows: dict[str, dict], reason: str) -> None:
        """Close every open position at the current bar close (kill-switch hard halt)."""
        for symbol, pos in list(self.account.positions.items()):
            row = rows.get(symbol)
            if row is None:
                continue
            self._close(pos, row["close"], _bar(row), reason)

    # -- internals -----------------------------------------------------------
    def _open(self, intent, size, risk_dollars, bar: Bar):
        fill = self.broker.enter(intent.symbol, intent.side, size, bar)
        pos = Position(
            symbol=intent.symbol, side=intent.side, entry_time=bar.ts,
            entry_price=fill.price, size=size, risk_dollars=risk_dollars,
            atr=intent.atr, init_stop=intent.stop_price, trail_stop=intent.stop_price,
            extreme=bar.high if intent.side.value == "long" else bar.low,
            entry_cost=fill.cost,
        )
        self.account.positions[intent.symbol] = pos
        self._bars_held[intent.symbol] = 0

    def _close(self, pos: Position, price: float, bar: Bar, reason: str):
        fill = self.broker.exit(pos, price, bar, reason)
        gross = (fill.price - pos.entry_price) * pos.side.sign * pos.size
        net = gross - pos.entry_cost - fill.cost
        self.account.equity += net
        R = net / pos.risk_dollars if pos.risk_dollars else 0.0
        self.account.closed.append(ClosedTrade(
            symbol=pos.symbol, side=pos.side, entry_time=pos.entry_time, exit_time=bar.ts,
            entry_price=pos.entry_price, exit_price=fill.price, size=pos.size,
            pnl=net, R=R, exit_reason=reason,
        ))
        self.account.equity_curve.append((bar.ts, self.account.equity))
        del self.account.positions[pos.symbol]


def _bar(row: dict) -> Bar:
    return Bar(row["symbol"], row["ts"], row["open"], row["high"], row["low"],
               row["close"], row["volume"])
