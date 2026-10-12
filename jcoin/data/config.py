"""Data-layer configuration: paths, schema, and the market registry.

Venue-agnostic by design. A "market" is (exchange, ccxt_symbol, label). The label
is jCoin's internal name; the exchange + ccxt_symbol are what ccxt actually queries.
This indirection lets the same logical instrument (e.g. BTC perp) be sourced from
whichever exchange has the data, without the strategy code knowing or caring.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# --- Paths -------------------------------------------------------------------
# Repo root = two levels up from this file (jcoin/data/config.py -> jCoin/)
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
OHLCV_DIR = DATA_DIR / "ohlcv"

# --- Canonical OHLCV schema --------------------------------------------------
# Every stored candle table has exactly these columns, in this order.
# `ts` is the candle OPEN time, UTC, milliseconds since epoch (ccxt convention).
OHLCV_COLUMNS = ["ts", "open", "high", "low", "close", "volume"]


@dataclass(frozen=True)
class Market:
    """One instrument on one exchange.

    label:    jCoin internal name (used in file paths + strategy code).
    exchange: ccxt exchange id (e.g. "coinbase", "kraken", "krakenfutures").
    symbol:   the exact ccxt market symbol (verify via exchange.load_markets()).
    """

    label: str
    exchange: str
    symbol: str


# --- Market registry ---------------------------------------------------------
# NOTE: the ccxt symbol strings below are best-effort defaults and MUST be
# verified against exchange.load_markets() before trusting a fetch (perp symbol
# formats differ per exchange and change over time). The fetcher validates and
# fails loudly if a symbol is not found, listing close matches.
#
# For THESIS VALIDATION (does range-time mean-revert?) we want long history, so
# a data-rich source is fine even if we will not trade there — parity lives at
# the DataFeed interface, not at the data source. For LIVE we switch the source
# to the actual traded venue. Both write the same canonical schema.
# For THESIS VALIDATION we source deep 1m history from Binance public data dumps
# (data.binance.vision) — USDT-margined perpetual klines, the most liquid perps in
# the world and a venue-independent proxy for BTC/ETH/SOL price behavior. We only
# READ this static data; we never trade Binance. For LIVE we add Coinbase/Kraken
# markets and switch the source — parity is at the DataFeed interface, not here.
# `symbol` here is the raw Binance-vision symbol (no slash), used by
# fetch_binance_vision.py.
DEFAULT_MARKETS: list[Market] = [
    Market(label="BTC",  exchange="binanceusdm", symbol="BTCUSDT"),
    Market(label="ETH",  exchange="binanceusdm", symbol="ETHUSDT"),
    Market(label="SOL",  exchange="binanceusdm", symbol="SOLUSDT"),
    # Watch-list: 4h parquets available from breadth study (no 1m base; DataFeed falls back)
    # Sealed-test validated:
    Market(label="EGLD", exchange="binanceusdm", symbol="EGLDUSDT"),
    Market(label="SAND", exchange="binanceusdm", symbol="SANDUSDT"),
    Market(label="IMX",  exchange="binanceusdm", symbol="IMXUSDT"),
    # Watch-list:
    Market(label="ADA",  exchange="binanceusdm", symbol="ADAUSDT"),
    Market(label="XRP",  exchange="binanceusdm", symbol="XRPUSDT"),
    Market(label="AVAX", exchange="binanceusdm", symbol="AVAXUSDT"),
    Market(label="HBAR", exchange="binanceusdm", symbol="HBARUSDT"),
    Market(label="NEAR", exchange="binanceusdm", symbol="NEARUSDT"),
]

# Live-venue markets for paper/live (sourced via ccxt).
# CORRECTION (audit 2026-09-18): this comment used to call krakenfutures "US-legal" --
# that is WRONG. Kraken Futures (futures.kraken.com) does NOT accept US residents for
# real order placement; it has only ever been safe to use here as a market-data source
# for paper trading. The actual live venue is still TBD -- Coinbase US nano perpetuals
# are a candidate, but nothing has been selected/verified yet. Do not route real orders
# to krakenfutures. Native 4h (240-min) candles here return ~720 bars — enough trailing
# history for the regime/ATR features each call. (Coinbase has no native 4h granularity
# + a 300-bar cap, part of why the venue choice is still open.)
LIVE_MARKETS: list[Market] = [
    # krakenfutures (futures.kraken.com) — data source only (paper trading); confirmed
    # active 2026-06-22. NOT available to US residents for real orders.
    # Symbol format: {BASE}/USD:USD (linear, USD-settled perpetual swap).
    Market(label="BTC",  exchange="krakenfutures", symbol="BTC/USD:USD"),
    Market(label="ETH",  exchange="krakenfutures", symbol="ETH/USD:USD"),
    # Watch-list coins: positive edge on shared config, paper-trading to accumulate live data.
    # Sealed TEST(25-26) weak due to cycle bear phase — re-evaluate when BTC reclaims 365-day SMA.
    # Sealed-test validated (shared config, all pass gate on TEST 2025-26):
    Market(label="EGLD", exchange="krakenfutures", symbol="EGLD/USD:USD"),
    Market(label="SAND", exchange="krakenfutures", symbol="SAND/USD:USD"),
    Market(label="IMX",  exchange="krakenfutures", symbol="IMX/USD:USD"),
    # Watch-list (bear-phase weak, re-test when BTC reclaims 365-day SMA):
    Market(label="ADA",  exchange="krakenfutures", symbol="ADA/USD:USD"),
    Market(label="XRP",  exchange="krakenfutures", symbol="XRP/USD:USD"),
    Market(label="AVAX", exchange="krakenfutures", symbol="AVAX/USD:USD"),
    Market(label="HBAR", exchange="krakenfutures", symbol="HBAR/USD:USD"),
]

# Default symbol universe for live/paper runners (audit 2026-09-18: the full 9-coin
# universe above was the DEFAULT for scheduled runs, which multiplied fetch cost and
# catch-up cost when the runner missed bars. BTC+ETH is now the default; the other
# Market entries in LIVE_MARKETS above stay defined and usable via explicit
# `--labels`/`--symbols` once re-validated at size.)
DEFAULT_LIVE_LABELS: list[str] = ["BTC", "ETH"]

# Base timeframe we fetch + store. Higher timeframes are derived on read in the
# DataFeed (resample), so stored data has a single source of truth and cannot
# drift between timeframes.
BASE_TIMEFRAME = "1m"

# Timeframes the strategy is allowed to request from the feed (derived from base).
ALLOWED_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]


def market_by_label(label: str, markets: list[Market] | None = None) -> Market:
    """Look up a Market by its jCoin label."""
    for m in (markets or DEFAULT_MARKETS):
        if m.label == label:
            return m
    raise KeyError(f"No market with label {label!r} in registry")


def partition_path(exchange: str, label: str, timeframe: str) -> Path:
    """Canonical on-disk location for one candle table.

    Layout: data/ohlcv/<exchange>/<label>/<timeframe>.parquet
    """
    return OHLCV_DIR / exchange / label / f"{timeframe}.parquet"
