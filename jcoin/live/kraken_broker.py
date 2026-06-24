"""KrakenFuturesBroker — routes real market orders through Kraken Futures API.

Demo by default (demo-futures.kraken.com). Never touches live endpoint unless
caller explicitly passes demo=False — that gate must be an explicit human action.

Symbol mapping: jCoin label "BTC" -> ccxt "BTC/USD:USD" (Kraken perp format).

Fees: Kraken Futures taker 0.05% per side. We charge entry only (round-trip pre-paid
at entry to match BacktestBroker convention so engine PnL accounting stays consistent).
"""

from __future__ import annotations

import datetime as dt
import logging

import ccxt

from jcoin.engine.broker import Broker
from jcoin.engine.types import Bar, Fill, Position, Side

log = logging.getLogger(__name__)

TAKER_FEE = 0.0005        # 0.05% per side (Kraken Futures taker tier 1)
ROUND_TRIP_FEE = TAKER_FEE * 2  # charge both sides at entry for consistency

# Demo base URL — all API paths are identical to live, just different host.
_DEMO_BASE = "https://demo-futures.kraken.com/derivatives"
_LIVE_BASE = "https://futures.kraken.com/derivatives"


def _ccxt_symbol(label: str) -> str:
    return f"{label}/USD:USD"


class KrakenFuturesBroker(Broker):
    """Submits market orders to Kraken Futures. demo=True by default (safe)."""

    def __init__(self, api_key: str, api_secret: str, demo: bool = True):
        base = _DEMO_BASE if demo else _LIVE_BASE
        self._ex = ccxt.krakenfutures({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "urls": {
                "api": {
                    "public":  base,
                    "private": base,
                }
            },
        })
        self._demo = demo
        mode = "DEMO" if demo else "LIVE"
        log.info("KrakenFuturesBroker [%s] base=%s", mode, base)
        # Load available markets once; used to skip symbols not on this exchange/demo
        try:
            self._markets = set(self._ex.load_markets().keys())
            log.info("loaded %d markets", len(self._markets))
        except Exception as e:
            log.warning("could not load markets: %s — will attempt all symbols", e)
            self._markets = set()

    def symbol_available(self, label: str) -> bool:
        sym = _ccxt_symbol(label)
        if not self._markets:
            return True  # unknown — try anyway
        return sym in self._markets

    # -- Broker interface ------------------------------------------------------

    def enter(self, symbol: str, side: Side, size: float, bar: Bar) -> Fill:
        ccxt_side = "buy" if side == Side.LONG else "sell"
        sym = _ccxt_symbol(symbol)
        log.info("ORDER  enter %s %s size=%.6f", symbol, ccxt_side.upper(), size)
        order = self._ex.create_order(sym, "market", ccxt_side, size)
        price = _fill_price(order, bar.close)
        cost = price * size * ROUND_TRIP_FEE
        log.info("FILL   enter %s @ %.6f cost=%.4f id=%s", symbol, price, cost, order.get("id", "?"))
        return Fill(
            symbol=symbol,
            ts=dt.datetime.now(dt.timezone.utc),
            side=side,
            price=price,
            size=size,
            cost=cost,
            kind="enter",
        )

    def exit(self, pos: Position, price: float, bar: Bar, reason: str) -> Fill:
        ccxt_side = "sell" if pos.side == Side.LONG else "buy"
        sym = _ccxt_symbol(pos.symbol)
        log.info("ORDER  exit %s %s size=%.6f reason=%s", pos.symbol, ccxt_side.upper(), pos.size, reason)
        order = self._ex.create_order(
            sym, "market", ccxt_side, pos.size,
            params={"reduceOnly": True},
        )
        fill_price = _fill_price(order, price)
        log.info("FILL   exit %s @ %.6f id=%s", pos.symbol, fill_price, order.get("id", "?"))
        return Fill(
            symbol=pos.symbol,
            ts=dt.datetime.now(dt.timezone.utc),
            side=pos.side,
            price=fill_price,
            size=pos.size,
            cost=0.0,   # round-trip already charged at entry
            kind="exit",
        )

    # -- Kraken-specific helpers (used by KrakenTrader) -----------------------

    def fetch_equity(self) -> float:
        """USD total balance from Kraken account. Includes unrealized PnL."""
        # ccxt's fetch_balance() throws if demo account has no 'flex' account type.
        # Use raw privateGetAccounts() instead and parse whatever account types exist.
        raw = self._ex.privateGetAccounts()
        accounts = raw.get("accounts", {})
        log.debug("Kraken accounts keys: %s", list(accounts.keys()))

        # flex account (live + some demo accounts)
        flex = accounts.get("flex", {})
        pv = flex.get("portfolioValue")
        if pv is not None:
            return float(pv)
        usd = (flex.get("currencies") or {}).get("USD", {})
        if usd.get("quantity") is not None:
            return float(usd["quantity"])

        # cash account (simpler demo accounts)
        cash = accounts.get("cash", {})
        balances = cash.get("balances", {})
        if "USD" in balances:
            return float(balances["USD"])

        # individual futures accounts (fi_xbtusd etc.) — sum all USD values
        total = 0.0
        for name, acct in accounts.items():
            if name in ("flex", "cash"):
                continue
            for ccy, val in (acct.get("balances") or {}).items():
                if "usd" in ccy.lower():
                    total += float(val or 0)
        if total > 0:
            return total

        # last resort: ccxt unified balance (may throw on demo — caught by caller)
        bal = self._ex.fetch_balance()
        for key in ("USD", "FLEX_USD", "PI_USD"):
            entry = bal.get(key)
            if entry and entry.get("total") is not None:
                return float(entry["total"])
        return 0.0

    def fetch_open_positions(self) -> list[dict]:
        """All positions with non-zero size, raw ccxt format."""
        positions = self._ex.fetch_positions() or []
        return [p for p in positions if (p.get("contracts") or 0) != 0]

    def cancel_all_orders(self, symbol: str | None = None) -> None:
        """Cancel any open orders (e.g. stale limit orders from a crash)."""
        try:
            if symbol:
                self._ex.cancel_all_orders(_ccxt_symbol(symbol))
            else:
                self._ex.cancel_all_orders()
        except Exception as e:
            log.warning("cancel_all_orders failed: %s", e)


def _fill_price(order: dict, fallback: float) -> float:
    for field in ("average", "price"):
        v = order.get(field)
        if v:
            return float(v)
    return fallback
