"""Coinbase US nano perpetual-style futures: PUBLIC market data (no API keys, no orders).

Used by the paper trader because Coinbase is the chosen live venue
(pipeline/VENUE_DECISION_2026-10.md). Two public endpoints, both unauthenticated:

  GET /api/v3/brokerage/market/products/{pid}/candles?granularity=&start=&end=
      -> {"candles": [{"start": unix_s, "open", "high", "low", "close", "volume"}, ...]}
      Newest-first, at most ~300 bars per call, window [start, end] in unix seconds.
      The still-forming bar IS included (start + bar > now); the caller drops it.
  GET /api/v3/brokerage/market/products/{pid}
      -> product JSON; contract size and the current funding rate live under
         future_product_details.

Units checked empirically against api.coinbase.com on 2026-10-19 (BIP-20DEC30-CDE and
ETP-20DEC30-CDE):
  - future_product_details.funding_rate is a decimal STRING, a FRACTION OF NOTIONAL PER
    HOUR: BTC "0.000005" (5e-6/h = 0.0005%/h), ETH "0.000003", alongside
    funding_interval "3600s". Positive = longs pay (same convention as the Kraken source).
    The same field under perpetual_details is an empty string -- do not use it.
  - future_product_details.contract_size is in BASE units per contract: BTC "0.01",
    ETH "0.1" (nano contracts); base_increment is "1" contract, so positions are whole
    contracts.
  - Native 4h granularity exists (FOUR_HOUR); 4h bars are aligned to 00/04/08/... UTC.
  - Candle `volume` is NOT comparable across granularities (4h volume is in a different
    unit from 1h); jCoin's strategy does not use volume, so it is passed through as is.
  - History starts 2025-07-18 (~2,700 4h bars as of 2026-10).
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request

log = logging.getLogger(__name__)

BASE_URL = "https://api.coinbase.com/api/v3/brokerage/market/products"
_GRANULARITY = {"1m": ("ONE_MINUTE", 60), "1h": ("ONE_HOUR", 3600), "4h": ("FOUR_HOUR", 4 * 3600)}
_MAX_BARS_PER_CALL = 300
_PAUSE_S = 0.2                      # politeness pause between paginated calls
_RETRY_WAITS_S = (1, 2, 4)          # backoff between attempts (4 attempts total)

_sleep = time.sleep                 # indirection so tests can run without waiting


def _http_get_json(url: str) -> dict:
    """GET a public Coinbase URL and parse the JSON body (the one network seam)."""
    req = urllib.request.Request(url, headers={"User-Agent": "jcoin-paper"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _get_json(url: str) -> dict:
    """_http_get_json with retry + backoff on any HTTP/network error."""
    for attempt, wait_s in enumerate(_RETRY_WAITS_S + (None,), start=1):
        try:
            return _http_get_json(url)
        except Exception as e:
            if wait_s is None:
                raise
            log.warning("coinbase GET failed (attempt %d), retrying in %ds: %s", attempt, wait_s, e)
            _sleep(wait_s)
    raise AssertionError("unreachable")


def fetch_candles(product_id: str, timeframe: str, since_ms: int | None = None,
                  limit: int = 300) -> list[list]:
    """Fetch up to `limit` candles starting at `since_ms` (default: `limit` bars back from
    now), paginating forward in <=300-bar windows. Returns ccxt-style rows
    [ts_ms, open, high, low, close, volume], ascending by ts, deduped. The still-forming
    bar is INCLUDED (like ccxt); live_source drops it. Returns fewer than `limit` rows
    if the product has less history (logged at INFO)."""
    if timeframe not in _GRANULARITY:
        raise ValueError(f"Unsupported Coinbase timeframe {timeframe!r} (have {sorted(_GRANULARITY)})")
    gran, bar_s = _GRANULARITY[timeframe]
    now_s = int(time.time())
    start_s = since_ms // 1000 if since_ms is not None else now_s - limit * bar_s
    by_ts: dict[int, list] = {}
    n_calls = 0
    while start_s < now_s and len(by_ts) < limit:
        end_s = min(start_s + _MAX_BARS_PER_CALL * bar_s, now_s)
        url = f"{BASE_URL}/{product_id}/candles?granularity={gran}&start={start_s}&end={end_s}"
        data = _get_json(url)
        n_calls += 1
        for c in data.get("candles", []):
            ts_ms = int(c["start"]) * 1000
            by_ts[ts_ms] = [ts_ms, float(c["open"]), float(c["high"]), float(c["low"]),
                            float(c["close"]), float(c["volume"])]
        start_s = end_s + 1   # the window is inclusive of `end`; +1s never skips a bar start
        if start_s < now_s:
            _sleep(_PAUSE_S)
    rows = [by_ts[t] for t in sorted(by_ts)]
    rows = rows[:limit] if since_ms is not None else rows[-limit:]   # tail = newest bars
    if since_ms is None and len(rows) < limit:
        log.info("coinbase %s %s: %d bars available (< %d requested) -- returning what exists",
                 product_id, timeframe, len(rows), limit)
    return rows


def product_details(product_id: str) -> dict:
    """Public product JSON (no auth). See the module docstring for the fields used."""
    return _get_json(f"{BASE_URL}/{product_id}")


def current_funding_rate(product_id: str) -> float:
    """Current funding rate, fraction of notional per hour (positive = longs pay).
    Raises ValueError if the product publishes none."""
    raw = (product_details(product_id).get("future_product_details") or {}).get("funding_rate")
    if raw in (None, ""):
        raise ValueError(f"{product_id}: no funding_rate in product details")
    return float(raw)


def contract_size(product_id: str) -> float:
    """Base units per contract (BTC nano = 0.01, ETH nano = 0.1)."""
    raw = (product_details(product_id).get("future_product_details") or {}).get("contract_size")
    if raw in (None, ""):
        raise ValueError(f"{product_id}: no contract_size in product details")
    return float(raw)
