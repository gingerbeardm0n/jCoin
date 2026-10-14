"""Perp funding for PAPER trading (the paper broker does not otherwise model it).

Backtests already charge funding in research/portfolio_backtest.py (funding_mult); a
paper position that is held across funding prints would otherwise be flattered. This
module supplies the hourly funding rate and the accrual maths; PaperTrader does the
bookkeeping (equity, Position.funding, ClosedTrade.funding).

NOT used by KrakenTrader: on the real exchange funding is settled into the account
balance, and KrakenTrader overwrites engine equity with the exchange balance every tick
(_sync_equity), so accruing here as well would double count.

Rate source and units (checked empirically against futures.kraken.com on 2026-10-14,
ccxt 4.5.59, BTC/USD:USD and ETH/USD:USD):
  - Kraken Futures perpetuals publish a funding rate EVERY HOUR (ccxt reports
    interval="1h"; fetch_funding_rate_history returns one row per hour, ~1y of history,
    timestamps on the hour, and honours `since`).
  - ccxt's unified `fundingRate` is Kraken's `relativeFundingRate`: a FRACTION OF
    NOTIONAL PER HOUR (BTC ~1.5e-5/h = 0.0015%/h ~ 0.036%/day). The raw
    `info.fundingRate` is the absolute USD per contract per hour; the ratio of the two is
    the contract price, so do not use the raw field.
  - The history row stamped HH:00 is the rate in effect for the hour starting HH:00
    (the 20:00 row equalled the live ticker's rate at 20:07).
  - Positive rate: longs pay, shorts receive.

Approximations (all logged, none silent):
  - Hours at/after the newest published history row (the live edge, not yet in history)
    use the CURRENT rate from fetch_funding_rate.
  - Any fetch failure -> the rate is None; the caller charges 0 and counts the bar in
    funding_missing_bars. A rate is never assumed.
"""

from __future__ import annotations

import datetime as dt
import logging

from jcoin.data.config import Market
from jcoin.data.fetch import _make_exchange
from jcoin.engine.types import Side

log = logging.getLogger(__name__)

_HOUR = dt.timedelta(hours=1)
_HOUR_MS = 3_600_000


def funding_cost(source, label: str, side: Side, notional: float,
                 t0: dt.datetime, t1: dt.datetime) -> tuple[float, bool]:
    """Funding PAID (USD; negative = received) for holding `notional` of `label` from t0 to
    t1: sum over hourly segments of  side.sign * rate_per_hour * hours * notional.
    Returns (cost, complete). complete is False if any hour's rate was unavailable; the
    cost is then partial and the caller decides how to treat it."""
    cost, complete = 0.0, True
    t = t0
    while t < t1:
        hour = t.replace(minute=0, second=0, microsecond=0)
        seg_end = min(hour + _HOUR, t1)
        rate = source.hourly_rate(label, hour)
        if rate is None:
            complete = False
        else:
            cost += side.sign * rate * ((seg_end - t).total_seconds() / 3600.0) * notional
        t = seg_end
    return cost, complete


class KrakenFundingSource:
    """Hourly funding rates from Kraken Futures public endpoints via ccxt (no keys).

    Fetched lazily, once per label per run (a run is one process). `exchange` can be
    injected for tests; anything with fetch_funding_rate / fetch_funding_rate_history works."""

    def __init__(self, markets: dict[str, Market], exchange=None):
        self.markets = markets
        self._exchange = exchange
        self._since: dt.datetime | None = None
        self._hist: dict[str, dict[int, float] | None] = {}   # label -> {hour_idx: rate} | None=failed
        self._current: dict[str, float | None] = {}

    def begin_run(self, since: dt.datetime) -> None:
        """Start a run: drop caches; history is fetched from `since` (UTC) on first use."""
        self._since = since
        self._hist.clear()
        self._current.clear()

    def _ex(self):
        if self._exchange is None:
            self._exchange = _make_exchange("krakenfutures")
        return self._exchange

    def _load_hist(self, label: str, first_hour: dt.datetime) -> dict[int, float] | None:
        if label not in self._hist:
            since = min(self._since, first_hour) if self._since else first_hour
            since_ms = int((since - _HOUR).timestamp() * 1000)
            try:
                rows = self._ex().fetch_funding_rate_history(self.markets[label].symbol, since=since_ms)
                self._hist[label] = {int(r["timestamp"]) // _HOUR_MS: float(r["fundingRate"])
                                     for r in rows if r.get("fundingRate") is not None}
            except Exception as e:
                log.warning("funding history fetch FAILED for %s: %s", label, e)
                self._hist[label] = None
        return self._hist[label]

    def _load_current(self, label: str) -> float | None:
        if label not in self._current:
            try:
                r = self._ex().fetch_funding_rate(self.markets[label].symbol)
                self._current[label] = float(r["fundingRate"])
            except Exception as e:
                log.warning("current funding rate fetch FAILED for %s: %s", label, e)
                self._current[label] = None
        return self._current[label]

    def hourly_rate(self, label: str, hour_start: dt.datetime) -> float | None:
        """Fraction of notional per hour for the hour starting `hour_start`, or None."""
        hist = self._load_hist(label, hour_start)
        if not hist:
            return None
        idx = int(hour_start.timestamp()) // 3600
        if idx in hist:
            return hist[idx]
        if idx > max(hist):  # live edge: not published yet -> current rate (approximation)
            cur = self._load_current(label)
            if cur is not None:
                log.info("funding %s %s: not in history yet, using current rate %.3e/h",
                         label, hour_start.isoformat(), cur)
            return cur
        return None  # a gap inside the fetched history: unknown, never guessed
