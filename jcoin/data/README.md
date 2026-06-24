# jCoin Data Layer

Phase-1 data layer: fetch historical OHLCV → parquet, read it back through one
parity-safe interface. No server DB — parquet files + DuckDB/Polars. A real
database is deferred to the live phase (24/7 streaming writes).

## Pieces

- `config.py` — paths, canonical OHLCV schema, the `Market` registry (label →
  exchange + ccxt symbol), partition-path scheme.
- `fetch.py` — ccxt → parquet. Incremental + idempotent. Stores the **base
  timeframe (1m) only**; higher timeframes are derived on read.
- `feed.py` — `DataFeed.get_candles(label, timeframe, start, end)`. THE read
  interface. Backtest/sim/live all go through it → no parity drift. Resamples
  1m → 5m/15m/1h/4h/1d.

## Storage layout

```
data/ohlcv/<exchange>/<label>/1m.parquet   # gitignored, regenerable
```

## Usage

```bash
# fetch
python -m jcoin.data.fetch --label BTC --days 365
python -m jcoin.data.fetch --all --days 730
```

```python
from jcoin.data.feed import DataFeed
f = DataFeed()
df = f.get_candles("BTC", "1h", start=..., end=...)   # polars DataFrame
f.coverage("BTC")                                       # rows, first/last bar
```

## Key design choices

- **1m base, derive the rest** → timeframes can never disagree.
- **Source ≠ venue.** For thesis validation we may pull long history from a
  data-rich source; for live we switch to the traded venue. Parity lives at the
  `DataFeed` interface, not at the source.
- **Fail loudly** — unknown symbols raise with close matches, never silent no-op.

## Known venue quirks

- **Coinbase** caps `fetch_ohlcv` at ~300 bars/request and its `since`
  pagination is awkward; deep history is slow (many calls) and shallow.
- **Kraken** spot OHLC returns only the most recent ~720 candles regardless of
  `since` — not usable for deep history.
- → For multi-year history, source selection is an open decision (see project
  notes): data-rich public source vs paid provider.
