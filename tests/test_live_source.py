"""Unit tests for the forming-bar heuristic in live_source.get_recent_candles.

BUG FOUND 2026-09-18: get_recent_candles() used to drop the last returned row
unconditionally, assuming the exchange always includes one still-forming bar. With
the incremental since-based fetch used by get_recent_candles_cached(), Kraken
sometimes returns rows that already end at the latest CLOSED bar (no forming bar
attached) -- the unconditional drop silently discarded that closed bar, making the
runner think its feed was hours stale when it was not (observed 2026-09-18 22:25
UTC: 16:00 bar dropped, then reported 10.4h-old 12:00 bar as latest).

Fix: only drop the last row if it has not closed yet, i.e. `row_open_ms + tf_ms >
now_ms`. These tests use a fake exchange object (no network) to exercise both cases.
"""

from __future__ import annotations

import time

import jcoin.data.live_source as ls_mod
from jcoin.data.config import Market

TF = "4h"
TF_MS = 14_400_000

MARKET = Market(label="BTC", exchange="krakenfutures", symbol="BTC/USD:USD")


class _FakeExchange:
    """Minimal ccxt-like stub: only what get_recent_candles() touches."""

    def __init__(self, rows: list[list]):
        self._rows = rows

    def load_markets(self):
        return {}

    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=None):
        batch = [r for r in self._rows if since is None or r[0] >= since]
        return batch[:limit] if limit is not None else batch


def _rows(opens_ms: list[int]) -> list[list]:
    return [[ts, 100.0, 101.0, 99.0, 100.0, 10.0] for ts in opens_ms]


def _install_fake(monkeypatch, rows: list[list]) -> None:
    fake = _FakeExchange(rows)
    monkeypatch.setattr(ls_mod, "_make_exchange", lambda exchange_id: fake)
    monkeypatch.setattr(ls_mod, "_verify_symbol", lambda ex, symbol: None)


def test_forming_last_bar_is_dropped(monkeypatch):
    """Rows ending with a bar that has not closed yet -> that bar is dropped."""
    now_ms = int(time.time() * 1000)
    current_open = now_ms - (now_ms % TF_MS)  # start of the bar containing "now" -- forming
    opens = [current_open - TF_MS * i for i in range(4, -1, -1)]  # 5 bars, last = forming
    _install_fake(monkeypatch, _rows(opens))

    df = ls_mod.get_recent_candles(MARKET, TF, limit=10)

    got = [int(t.timestamp() * 1000) for t in df["ts"].to_list()]
    assert current_open not in got
    assert got == opens[:-1]


def test_closed_last_bar_is_kept(monkeypatch):
    """Rows ending with a bar that HAS already closed -> nothing is dropped, even
    though it is the last row (this is the bug scenario: an incremental fetch can
    legitimately end at the newest closed bar with no forming bar attached)."""
    now_ms = int(time.time() * 1000)
    current_open = now_ms - (now_ms % TF_MS)
    last_closed = current_open - TF_MS  # the most recently CLOSED bar
    opens = [last_closed - TF_MS * i for i in range(4, -1, -1)]  # 5 bars, last = closed
    _install_fake(monkeypatch, _rows(opens))

    df = ls_mod.get_recent_candles(MARKET, TF, limit=10)

    got = [int(t.timestamp() * 1000) for t in df["ts"].to_list()]
    assert got == opens  # nothing dropped -- the last row is a genuinely closed bar


def test_cached_fetch_retries_then_raises(tmp_path, monkeypatch):
    """Network down right after wake: retry, then fail loudly instead of serving stale cache."""
    import datetime as dt
    import polars as pl
    import pytest
    from jcoin.data import live_source
    from jcoin.data.config import market_by_label

    mkt = market_by_label("BTC")
    ts = [dt.datetime(2026, 10, 12, h, tzinfo=dt.timezone.utc) for h in (0, 4, 8)]
    pl.DataFrame({"ts": ts, "open": [1.0] * 3, "high": [1.0] * 3, "low": [1.0] * 3,
                  "close": [1.0] * 3, "volume": [1.0] * 3}).write_parquet(tmp_path / "BTC_4h.parquet")

    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise ConnectionError("network unreachable")

    monkeypatch.setattr(live_source, "get_recent_candles", boom)
    monkeypatch.setattr(live_source.time, "sleep", lambda s: None)
    with pytest.raises(RuntimeError, match="incremental fetch failed for BTC after 3"):
        live_source.get_recent_candles_cached(mkt, "4h", tmp_path, retry_waits_s=(1, 1))
    assert len(calls) == 3


def test_cached_fetch_recovers_on_retry(tmp_path, monkeypatch):
    import datetime as dt
    import polars as pl
    from jcoin.data import live_source
    from jcoin.data.config import market_by_label

    mkt = market_by_label("BTC")
    ts = [dt.datetime(2026, 10, 12, h, tzinfo=dt.timezone.utc) for h in (0, 4)]
    base = {"open": [1.0] * 2, "high": [1.0] * 2, "low": [1.0] * 2, "close": [1.0] * 2, "volume": [1.0] * 2}
    pl.DataFrame({"ts": ts, **base}).write_parquet(tmp_path / "BTC_4h.parquet")
    new = pl.DataFrame({"ts": [dt.datetime(2026, 10, 12, 8, tzinfo=dt.timezone.utc)],
                        "open": [2.0], "high": [2.0], "low": [2.0], "close": [2.0], "volume": [2.0]})
    attempts = iter([ConnectionError("down"), new])

    def flaky(*a, **k):
        r = next(attempts)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(live_source, "get_recent_candles", flaky)
    monkeypatch.setattr(live_source.time, "sleep", lambda s: None)
    out = live_source.get_recent_candles_cached(mkt, "4h", tmp_path, retry_waits_s=(1,))
    assert out["ts"].max() == dt.datetime(2026, 10, 12, 8, tzinfo=dt.timezone.utc)
