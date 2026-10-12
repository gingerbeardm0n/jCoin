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
import time
import uuid

import ccxt

from jcoin.engine.broker import Broker
from jcoin.engine.types import Bar, Fill, Position, Side

log = logging.getLogger(__name__)

TAKER_FEE = 0.0005        # 0.05% per side (Kraken Futures taker tier 1)
ROUND_TRIP_FEE = TAKER_FEE * 2  # charge both sides at entry for consistency

# Fallback market list for demo when load_markets() fails.
# Kraken Futures demo supports only BTC and ETH perps.
_DEMO_FALLBACK_MARKETS = {"BTC/USD:USD", "ETH/USD:USD"}


def _ccxt_symbol(label: str) -> str:
    return f"{label}/USD:USD"


class KrakenFuturesBroker(Broker):
    """Submits market orders to Kraken Futures. demo=True by default (safe)."""

    def __init__(self, api_key: str, api_secret: str, demo: bool = True):
        self._ex = ccxt.krakenfutures({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })
        self._demo = demo
        if demo:
            self._ex.set_sandbox_mode(True)
        mode = "DEMO" if demo else "LIVE"
        log.info("KrakenFuturesBroker [%s]", mode)
        # Load available markets once; used to skip symbols not on this exchange/demo
        try:
            self._markets = set(self._ex.load_markets().keys())
            log.info("loaded %d markets", len(self._markets))
        except Exception as e:
            fallback = _DEMO_FALLBACK_MARKETS if demo else set()
            log.warning("could not load markets: %s — defaulting to %s", e, fallback or "none (will fail)")
            self._markets = fallback

    def symbol_available(self, label: str) -> bool:
        sym = _ccxt_symbol(label)
        if not self._markets:
            return False  # unknown and no fallback — block all to avoid BadSymbol
        return sym in self._markets

    # -- Broker interface ------------------------------------------------------

    def enter(self, symbol: str, side: Side, size: float, bar: Bar) -> Fill | None:
        ccxt_side = "buy" if side == Side.LONG else "sell"
        sym = _ccxt_symbol(symbol)

        # Round to exchange precision and enforce the exchange's minimum order
        # size/notional BEFORE placing anything (audit 2026-09-18, item #5). An
        # unrounded or too-small size either gets rejected by the exchange or fills
        # at a size we didn't expect -- either way we must not record a phantom
        # position for an order that never really went through as intended.
        try:
            size = float(self._ex.amount_to_precision(sym, size))
        except Exception as e:
            log.warning("amount_to_precision failed for %s size=%.6f: %s — using raw size",
                       symbol, size, e)

        market = (self._ex.markets or {}).get(sym)
        limits = (market or {}).get("limits") or {}
        min_amount = (limits.get("amount") or {}).get("min")
        min_cost = (limits.get("cost") or {}).get("min")

        if size <= 0:
            log.warning("ORDER SKIPPED %s: rounded size is zero/negative (%.8f) — not placed",
                       symbol, size)
            return None
        if min_amount is not None and size < min_amount:
            log.warning("ORDER SKIPPED %s: size %.8f < exchange minimum amount %.8f — not placed",
                       symbol, size, min_amount)
            return None
        if min_cost is not None and size * bar.close < min_cost:
            log.warning("ORDER SKIPPED %s: notional %.2f < exchange minimum cost %.2f — not placed",
                       symbol, size * bar.close, min_cost)
            return None

        # Deterministic client order id from the signal's identity (symbol+side+bar).
        # A network-retry of the same logical order carries the same id, so the
        # exchange rejects the duplicate instead of double-filling (safety item #5).
        cli_id = f"jcoin-e-{symbol}-{side.value}-{int(bar.ts.timestamp())}"
        log.info("ORDER  enter %s %s size=%.6f cliOrdId=%s", symbol, ccxt_side.upper(), size, cli_id)
        order = self._ex.create_order(sym, "market", ccxt_side, size,
                                      params={"clientOrderId": cli_id})
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
        cli_id = f"jcoin-x-{pos.symbol}-{pos.side.value}-{int(bar.ts.timestamp())}"
        log.info("ORDER  exit %s %s size=%.6f reason=%s cliOrdId=%s",
                 pos.symbol, ccxt_side.upper(), pos.size, reason, cli_id)
        order = self._ex.create_order(
            sym, "market", ccxt_side, pos.size,
            params={"reduceOnly": True, "clientOrderId": cli_id},
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

    # -- resting stop-loss (real exchange-side protection) --------------------

    def place_stop(self, symbol: str, side: Side, size: float, stop_price: float,
                    _retry: bool = True) -> str | None:
        """Place a reduce-only market-on-trigger stop, opposite side from the position
        (closes it, never flips it — reduceOnly blocks that).

        On failure, retries once after a 2s pause (transient network/rate-limit blips
        are common and a stop is too important to give up on after one try). If the
        retry also fails, returns None -- the caller (kraken_trader.py) escalates that
        to a CRITICAL halt rather than silently continuing with an unprotected position
        (audit 2026-09-18, item #6)."""
        ccxt_side = "sell" if side == Side.LONG else "buy"
        sym = _ccxt_symbol(symbol)
        cli_id = f"jcoin-stop-{uuid.uuid4().hex[:16]}"
        try:
            order = self._ex.create_order(
                sym, "market", ccxt_side, size, None,
                params={"stopPrice": stop_price, "reduceOnly": True, "clientOrderId": cli_id},
            )
            oid = order.get("id")
            log.info("STOP placed %s %s trigger=%.6f id=%s", symbol, ccxt_side.upper(), stop_price, oid)
            return oid
        except Exception as e:
            if _retry:
                log.warning("STOP place FAILED %s trigger=%.6f: %s — retrying once in 2s",
                           symbol, stop_price, e)
                time.sleep(2)
                return self.place_stop(symbol, side, size, stop_price, _retry=False)
            log.error("STOP place FAILED %s trigger=%.6f after retry: %s — position is UNPROTECTED",
                      symbol, stop_price, e)
            return None

    def move_stop(self, order_id: str | None, symbol: str, side: Side, size: float,
                   new_stop_price: float) -> str | None:
        if order_id:
            self.cancel_stop(order_id, symbol)
        return self.place_stop(symbol, side, size, new_stop_price)

    def cancel_stop(self, order_id: str | None, symbol: str) -> None:
        if not order_id:
            return
        try:
            self._ex.cancel_order(order_id, _ccxt_symbol(symbol))
            log.info("STOP canceled %s id=%s", symbol, order_id)
        except Exception as e:
            log.warning("STOP cancel failed (likely already filled/gone) %s id=%s: %s",
                        symbol, order_id, e)

    def fetch_stop_fill(self, order_id: str, symbol: str) -> dict | None:
        """Check whether a resting stop has filled. Returns {'price': avg, 'ts': ...} if
        filled, else None. Used by reconciliation to close our local state honestly
        instead of guessing when a stop fires between our checks."""
        try:
            order = self._ex.fetch_order(order_id, _ccxt_symbol(symbol))
            status = order.get("status")
            if status in ("closed", "filled"):
                price = order.get("average") or order.get("price")
                return {"price": float(price)} if price else None
            return None
        except Exception as e:
            log.warning("fetch_stop_fill failed %s id=%s: %s", symbol, order_id, e)
            return None

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

    def fetch_resting_stop(self, symbol: str) -> dict | None:
        """Look for an existing reduce-only stop order on this symbol — used when local
        state was lost (e.g. an ephemeral-disk wipe) but a position + its resting stop
        may still be sitting on Kraken from before the wipe. Returns {'id', 'price'} or
        None if no such order exists (caller must then place a fresh protective stop)."""
        try:
            orders = self._ex.fetch_open_orders(_ccxt_symbol(symbol))
        except Exception as e:
            log.warning("fetch_resting_stop failed for %s: %s", symbol, e)
            return None
        for o in orders:
            info = o.get("info", {})
            is_reduce_only = o.get("reduceOnly") or info.get("reduceOnly")
            trigger = o.get("triggerPrice") or o.get("stopPrice") or info.get("stopPrice")
            if is_reduce_only and trigger:
                return {"id": o.get("id"), "price": float(trigger)}
        return None

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
