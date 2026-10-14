"""Core value types shared across the engine, strategy, and brokers."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import Enum


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"

    @property
    def sign(self) -> int:
        return 1 if self is Side.LONG else -1


@dataclass(frozen=True)
class Bar:
    """One OHLCV candle for one symbol."""
    symbol: str
    ts: dt.datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class EnterIntent:
    """Strategy's decision to open a position. Pure signal — no sizing/IO yet."""
    symbol: str
    side: Side
    stop_price: float      # initial protective stop
    atr: float             # ATR at signal (drives trailing distance)
    reason: str = ""


@dataclass(frozen=True)
class ExitIntent:
    symbol: str
    reason: str = ""


@dataclass
class Position:
    symbol: str
    side: Side
    entry_time: dt.datetime
    entry_price: float
    size: float                 # units of the asset
    risk_dollars: float         # $ risked (distance entry->init_stop * size)
    atr: float
    init_stop: float
    trail_stop: float
    extreme: float              # best price seen since entry (high for long, low for short)
    entry_cost: float = 0.0     # round-trip cost charged at entry
    stop_order_id: str | None = None      # resting exchange stop order id (live trading only)
    stop_order_price: float | None = None  # trigger price the resting order was last placed/moved at
    funding: float = 0.0        # cumulative $ funding PAID while open (negative = received); paper only
    funding_ts: dt.datetime | None = None  # bar ts funding has been accrued through (None = since entry)

    def unrealized_R(self, price: float) -> float:
        risk_per_unit = abs(self.entry_price - self.init_stop)
        if risk_per_unit == 0:
            return 0.0
        move = (price - self.entry_price) * self.side.sign
        return move / risk_per_unit


@dataclass
class Fill:
    symbol: str
    ts: dt.datetime
    side: Side
    price: float            # fill price BEFORE costs
    size: float
    cost: float             # $ fees + slippage charged on this fill
    kind: str               # "enter" | "exit"


@dataclass
class ClosedTrade:
    symbol: str
    side: Side
    entry_time: dt.datetime
    exit_time: dt.datetime
    entry_price: float
    exit_price: float
    size: float
    pnl: float              # net $ after costs
    R: float                # realized R-multiple (net, i.e. after costs AND funding)
    exit_reason: str
    funding: float = 0.0    # $ funding paid over the life of the trade (negative = received);
                            # already included in pnl and R, stored separately for reporting


@dataclass
class Account:
    equity: float
    positions: dict[str, Position] = field(default_factory=dict)
    closed: list[ClosedTrade] = field(default_factory=list)
    equity_curve: list[tuple[dt.datetime, float]] = field(default_factory=list)

    @property
    def open_count(self) -> int:
        return len(self.positions)
