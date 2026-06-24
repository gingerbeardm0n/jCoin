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

import logging

from jcoin.engine.kill_switch import KillSwitchConfig
from jcoin.engine.risk import RiskConfig
from jcoin.engine.strategy import StrategyConfig
from jcoin.engine.types import Side
from jcoin.live.kraken_broker import KrakenFuturesBroker
from jcoin.live.paper_runner import PaperTrader

log = logging.getLogger(__name__)


class KrakenTrader(PaperTrader):
    """PaperTrader subclass that routes orders through real Kraken Futures API."""

    def __init__(self, api_key: str, api_secret: str, demo: bool = True, **kwargs):
        broker = KrakenFuturesBroker(api_key, api_secret, demo=demo)
        # Filter labels to only those actually listed on this exchange (demo has fewer markets)
        if "labels" in kwargs and broker._markets:
            available = [l for l in kwargs["labels"] if broker.symbol_available(l)]
            skipped = set(kwargs["labels"]) - set(available)
            if skipped:
                log.warning("symbols not on exchange, skipping: %s", skipped)
            kwargs["labels"] = available
        super().__init__(broker=broker, **kwargs)
        self._kraken = broker

    def run_live_once(self) -> bool:
        """Fetch bar, run strategy, place real orders, then sync equity from Kraken."""
        result = super().run_live_once()
        if result:
            self._sync_equity()
            self._reconcile_positions()
        return result

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
        """Compare engine positions with Kraken positions, log any drift."""
        try:
            kraken_pos = self._kraken.fetch_open_positions()
            kraken_syms = {
                p["symbol"].split("/")[0]  # "BTC/USD:USD" -> "BTC"
                for p in kraken_pos
            }
            engine_syms = set(self.engine.account.positions.keys())

            ghost = engine_syms - kraken_syms   # engine thinks open, Kraken says closed
            unknown = kraken_syms - engine_syms  # Kraken has pos engine doesn't know about

            if ghost:
                log.warning("RECONCILE: engine has positions Kraken doesn't: %s "
                            "(possible manual close or liquidation — engine will still manage stops)",
                            ghost)
            if unknown:
                log.warning("RECONCILE: Kraken has positions engine doesn't track: %s "
                            "(manual order? — not managed by strategy)", unknown)
        except Exception as e:
            log.warning("position reconcile failed: %s", e)
