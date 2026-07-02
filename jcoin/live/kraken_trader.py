"""KrakenTrader — live/demo trading runner backed by real Kraken Futures orders.

Identical signal logic to PaperTrader. Only the broker differs:
  PaperTrader  -> PaperBroker  (simulated fills at bar close)
  KrakenTrader -> KrakenFuturesBroker (real market orders, demo-futures.kraken.com)

On each 4h bar:
  1. Fetch latest 4h bars from krakenfutures live feed
  2. Compute features + cycle phase
  3. Strategy emits signals
  4. KrakenFuturesBroker places real market orders on Kraken demo
  5. Pull actual USD equity from Kraken account (overrides engine simulation)
  6. Save state.json -> dashboard picks it up via SSE

Startup reconciliation:
  Kraken is the source of truth for WHAT positions exist. Our state.json is the
  source of truth for WHERE stops are. On startup we check for drift and log
  warnings, but trust state.json for stop management (we can't recover stop levels
  from the exchange).
"""

from __future__ import annotations

import datetime as dt
import logging

from jcoin.engine.kill_switch import KillSwitchConfig
from jcoin.engine.risk import RiskConfig
from jcoin.engine.strategy import StrategyConfig
from jcoin.engine.types import Position, Side
from jcoin.live.kraken_broker import KrakenFuturesBroker
from jcoin.live.paper_runner import PaperTrader

log = logging.getLogger(__name__)


class KrakenTrader(PaperTrader):
    """PaperTrader subclass that routes orders through real Kraken Futures API."""

    def __init__(self, api_key: str, api_secret: str, demo: bool = True, **kwargs):
        broker = KrakenFuturesBroker(api_key, api_secret, demo=demo)
        # Filter labels to only those listed on this exchange (demo has fewer markets).
        # Always filter — empty _markets means load failed, broker defaults to safe fallback.
        if "labels" in kwargs:
            available = [l for l in kwargs["labels"] if broker.symbol_available(l)]
            skipped = set(kwargs["labels"]) - set(available)
            if skipped:
                log.warning("symbols not on exchange, skipping: %s", skipped)
            kwargs["labels"] = available
            log.info("trading labels after filter: %s", available)
        super().__init__(broker=broker, **kwargs)
        self._kraken = broker

    def run_live_once(self) -> bool:
        """Fetch bar, run strategy, place real orders, then sync equity from Kraken."""
        before = dict(self.engine.account.positions)  # symbol -> Position, pre-tick snapshot
        result = super().run_live_once()
        if result:
            self._manage_resting_stops(before)
            self._sync_equity()
            self._reconcile_positions()
        return result

    # -- resting stop-loss management -----------------------------------------

    def _manage_resting_stops(self, before: dict) -> None:
        """Place a stop on every newly-opened position, move it when the trail tightens,
        and cancel it for anything the engine just closed itself (avoids an orphaned
        reduce-only order sitting on the exchange after we already exited via market
        order — see kraken_broker.place_stop docstring / STRATEGY_SPEC.md safety item #7).
        """
        acct = self.engine.account
        changed = False

        # Positions the engine closed THIS tick (software stop/max-hold/etc.) — the
        # resting order for these is now stale, cancel it before it can fire later.
        for sym, pos in before.items():
            if sym not in acct.positions and pos.stop_order_id:
                self._kraken.cancel_stop(pos.stop_order_id, sym)
                changed = True

        # Positions still (or newly) open — ensure a resting stop exists at the CURRENT
        # trail_stop, placing or moving as needed.
        for sym, pos in acct.positions.items():
            if pos.stop_order_id is None:
                oid = self._kraken.place_stop(sym, pos.side, pos.size, pos.trail_stop)
                pos.stop_order_id = oid
                pos.stop_order_price = pos.trail_stop if oid else None
                changed = True
            elif pos.stop_order_price != pos.trail_stop:
                oid = self._kraken.move_stop(pos.stop_order_id, sym, pos.side, pos.size, pos.trail_stop)
                pos.stop_order_id = oid
                pos.stop_order_price = pos.trail_stop if oid else None
                changed = True

        if changed:
            self._save()

    # -- Kraken sync ----------------------------------------------------------

    def _sync_equity(self) -> None:
        """Replace simulated equity with real Kraken account balance."""
        try:
            real = self._kraken.fetch_equity()
            if real > 0:
                self.engine.account.equity = real
                self.ks.state.peak_equity = max(self.ks.state.peak_equity, real)
                self._save()
                log.info("Kraken equity synced: %.2f", real)
            else:
                log.warning("Kraken equity returned %.2f — keeping simulated", real)
        except Exception as e:
            log.warning("equity sync failed: %s", e)

    def _reconcile_positions(self) -> None:
        """Compare engine positions with Kraken positions. A 'ghost' (engine thinks open,
        Kraken says closed) most likely means our resting stop fired between checks —
        resolve it honestly using the stop order's actual fill price instead of leaving
        our local state permanently wrong. Anything we can't explain just gets logged."""
        try:
            kraken_pos = self._kraken.fetch_open_positions()
            kraken_syms = {
                p["symbol"].split("/")[0]  # "BTC/USD:USD" -> "BTC"
                for p in kraken_pos
            }
            engine_syms = set(self.engine.account.positions.keys())

            ghost = engine_syms - kraken_syms   # engine thinks open, Kraken says closed
            unknown = kraken_syms - engine_syms  # Kraken has pos engine doesn't know about

            for sym in ghost:
                pos = self.engine.account.positions[sym]
                fill = self._kraken.fetch_stop_fill(pos.stop_order_id, sym) if pos.stop_order_id else None
                if fill:
                    log.warning("RECONCILE: %s closed on Kraken (stop fired between checks) — "
                                "reconciling engine state @ %.6f", sym, fill["price"])
                    self.engine.force_close(pos, fill["price"], dt.datetime.now(dt.timezone.utc),
                                            "reconcile:exchange_stop_fill")
                else:
                    est_price = self._last_prices.get(sym)
                    log.warning("RECONCILE: %s closed on Kraken, no confirmed stop fill found — "
                                "closing at last known price %.6f (possible manual close/liquidation, "
                                "P&L is an ESTIMATE)", sym, est_price if est_price else -1)
                    if est_price:
                        self.engine.force_close(pos, est_price, dt.datetime.now(dt.timezone.utc),
                                                "reconcile:unexplained_closure")
                    else:
                        log.error("RECONCILE: %s ghost position with no price to close at — "
                                  "left in local state, needs manual review", sym)
            if unknown:
                log.warning("RECONCILE: Kraken has positions engine doesn't track: %s — "
                            "ADOPTING into local state (most likely cause: state.json was "
                            "lost/wiped, e.g. an ephemeral-disk redeploy, while the position "
                            "and/or its resting stop survived on Kraken).", unknown)
                by_sym = {p["symbol"].split("/")[0]: p for p in kraken_pos}
                for sym in unknown:
                    self._adopt_position(sym, by_sym[sym])

            if ghost or unknown:
                self._save()
        except Exception as e:
            log.warning("position reconcile failed: %s", e)

    def _adopt_position(self, symbol: str, kpos: dict) -> None:
        """Reconstruct a Position from a real Kraken position we have no local record of.
        Cost basis / original risk sizing are unrecoverable — this is a best-effort safety
        net (stops the strategy from doubling up on a symbol it's blind to), not a precise
        accounting recovery. Always ensures a protective stop is resting before returning."""
        contracts = kpos.get("contracts") or 0
        side = Side.LONG if (kpos.get("side") == "long" or contracts > 0) else Side.SHORT
        size = abs(contracts)
        entry_price = kpos.get("entryPrice") or kpos.get("markPrice")
        if not entry_price or size <= 0:
            log.error("ADOPT %s: missing entry price/size from Kraken, cannot adopt safely — "
                      "MANUAL REVIEW NEEDED (position is real but untracked)", symbol)
            return

        existing_stop = self._kraken.fetch_resting_stop(symbol)
        if existing_stop:
            stop_price = existing_stop["price"]
            stop_order_id = existing_stop["id"]
            log.warning("ADOPT %s: recovered existing resting stop @ %.6f id=%s",
                        symbol, stop_price, stop_order_id)
        else:
            # No resting stop found on the exchange either — this position is currently
            # UNPROTECTED. Place a conservative fallback stop immediately (fixed 3% from
            # entry; we have no ATR history to compute a proper one) rather than leave it
            # naked until the next signal-driven trail update.
            fallback_pct = 0.03
            stop_price = entry_price * (1 - fallback_pct) if side == Side.LONG else entry_price * (1 + fallback_pct)
            stop_order_id = self._kraken.place_stop(symbol, side, size, stop_price)
            log.warning("ADOPT %s: NO existing stop found — placed fallback stop @ %.6f "
                        "(%.0f%% from entry, conservative default) id=%s",
                        symbol, stop_price, fallback_pct * 100, stop_order_id)

        risk_dollars = self.engine.risk.risk_frac * self.engine.account.equity  # best-effort estimate
        pos = Position(
            symbol=symbol, side=side, entry_time=dt.datetime.now(dt.timezone.utc),
            entry_price=entry_price, size=size, risk_dollars=risk_dollars, atr=0.0,
            init_stop=stop_price, trail_stop=stop_price, extreme=entry_price, entry_cost=0.0,
            stop_order_id=stop_order_id, stop_order_price=stop_price if stop_order_id else None,
        )
        self.engine.account.positions[symbol] = pos
        self.engine._bars_held[symbol] = 0
        log.warning("ADOPT %s: added to local state (approximate entry_time=now, "
                    "risk_dollars estimated from current equity — P&L on this position "
                    "will be approximate until it closes)", symbol)
