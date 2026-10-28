"""Coinbase venue support for the paper trader: public data fetch, cache naming,
whole-contract sizing and the funding source. No network (HTTP layer is monkeypatched)."""

from __future__ import annotations

import datetime as dt
import time

import pytest

import jcoin.data.coinbase_public as cb
import jcoin.data.live_source as ls_mod
from jcoin.data.config import COINBASE_MARKETS, CONTRACT_SIZES, LIVE_MARKETS, Market
from jcoin.engine.risk import RiskConfig, size_position
from jcoin.engine.types import EnterIntent, Side
from jcoin.live.funding import CoinbaseFundingSource, funding_cost

TF_S = 4 * 3600
CB_MARKET = Market(label="BTC", exchange="coinbase_cde", symbol="BIP-20DEC30-CDE")


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(cb, "_sleep", lambda s: None)


def _candle(start_s: int, px: float = 100.0) -> dict:
    return {"start": str(start_s), "open": str(px), "high": str(px + 1), "low": str(px - 1),
            "close": str(px), "volume": "10"}


def _fake_http(monkeypatch, all_starts: list[int], calls: list[str] | None = None):
    """Serve Coinbase-style (newest-first, window-limited, max 300) candles from all_starts."""
    def fake(url: str) -> dict:
        if calls is not None:
            calls.append(url)
        q = dict(p.split("=") for p in url.split("?")[1].split("&"))
        s, e = int(q["start"]), int(q["end"])
        got = sorted((t for t in all_starts if s <= t <= e), reverse=True)[:300]
        return {"candles": [_candle(t) for t in got]}
    monkeypatch.setattr(cb, "_http_get_json", fake)


def _recent_starts(n: int, forming: bool) -> list[int]:
    """n closed 4h bar starts ending at the latest closed bar (+1 forming bar if asked)."""
    now = int(time.time())
    cur = now // TF_S * TF_S              # start of the forming bar
    starts = [cur - TF_S * (i + 1) for i in range(n)]
    if forming:
        starts.append(cur)
    return sorted(starts)


# --- coinbase_public ---------------------------------------------------------------
def test_fetch_candles_parses_paginates_and_dedups(monkeypatch):
    starts = _recent_starts(700, forming=False)
    calls: list[str] = []
    _fake_http(monkeypatch, starts + starts[-5:], calls)   # duplicates across the feed
    rows = cb.fetch_candles("BIP-20DEC30-CDE", "4h", limit=720)   # > 700 so the window covers all
    assert len(calls) >= 3                                  # 700 bars needs >1 call of 300
    assert "granularity=FOUR_HOUR" in calls[0]
    assert [r[0] for r in rows] == [t * 1000 for t in starts]   # ascending, ms, deduped
    assert rows[0] == [starts[0] * 1000, 100.0, 101.0, 99.0, 100.0, 10.0]


def test_fetch_candles_one_hour_and_bad_timeframe(monkeypatch):
    calls: list[str] = []
    _fake_http(monkeypatch, [], calls)
    cb.fetch_candles("BIP-20DEC30-CDE", "1h", limit=5)
    assert "granularity=ONE_HOUR" in calls[0]
    with pytest.raises(ValueError):
        cb.fetch_candles("BIP-20DEC30-CDE", "15m")


def test_fetch_candles_returns_what_exists_when_history_short(monkeypatch):
    starts = _recent_starts(50, forming=False)
    _fake_http(monkeypatch, starts)
    rows = cb.fetch_candles("BIP-20DEC30-CDE", "4h", limit=400)
    assert len(rows) == 50


def test_get_json_retries_with_backoff(monkeypatch):
    waits, n = [], {"calls": 0}
    monkeypatch.setattr(cb, "_sleep", waits.append)

    def flaky(url):
        n["calls"] += 1
        if n["calls"] < 3:
            raise OSError("boom")
        return {"candles": []}
    monkeypatch.setattr(cb, "_http_get_json", flaky)
    cb._get_json("http://x")
    assert waits == [1, 2] and n["calls"] == 3

    def dead(url):
        raise OSError("down")
    monkeypatch.setattr(cb, "_http_get_json", dead)
    with pytest.raises(OSError):
        cb._get_json("http://x")


def test_product_details_funding_and_contract_size(monkeypatch):
    doc = {"future_product_details": {"funding_rate": "0.000005", "contract_size": "0.01",
                                      "perpetual_details": {"funding_rate": ""}}}
    monkeypatch.setattr(cb, "_http_get_json", lambda url: doc)
    assert cb.current_funding_rate("BIP-20DEC30-CDE") == pytest.approx(5e-6)
    assert cb.contract_size("BIP-20DEC30-CDE") == pytest.approx(0.01)
    monkeypatch.setattr(cb, "_http_get_json", lambda url: {"future_product_details": {"funding_rate": ""}})
    with pytest.raises(ValueError):
        cb.current_funding_rate("BIP-20DEC30-CDE")


# --- live_source routing + cache name ------------------------------------------------
def test_get_recent_candles_drops_forming_bar_for_coinbase(monkeypatch):
    starts = _recent_starts(10, forming=True)
    _fake_http(monkeypatch, starts)
    df = ls_mod.get_recent_candles(CB_MARKET, "4h", limit=11)
    assert df.height == 10                                   # forming bar gone
    assert int(df["ts"][-1].timestamp()) == starts[-2]
    assert df.schema["ts"].time_zone == "UTC"                # same ts dtype family as the ccxt path


def test_get_recent_candles_coinbase_since_ms(monkeypatch):
    starts = _recent_starts(20, forming=True)
    _fake_http(monkeypatch, starts)
    since = starts[-4] * 1000 + 1                            # as the cached path passes it
    df = ls_mod.get_recent_candles(CB_MARKET, "4h", limit=1000, since_ms=since)
    assert [int(t.timestamp()) for t in df["ts"]] == starts[-4:-1]


def test_cache_filename_includes_exchange(tmp_path, monkeypatch):
    kraken = Market(label="BTC", exchange="krakenfutures", symbol="BTC/USD:USD")
    assert ls_mod.cache_filename(CB_MARKET, "4h") == "coinbase_cde_BTC_4h.parquet"
    assert ls_mod.cache_filename(kraken, "4h") != ls_mod.cache_filename(CB_MARKET, "4h")
    _fake_http(monkeypatch, _recent_starts(30, forming=True))
    ls_mod.get_recent_candles_cached(CB_MARKET, "4h", tmp_path, limit=30)
    assert (tmp_path / "coinbase_cde_BTC_4h.parquet").exists()
    assert not (tmp_path / "BTC_4h.parquet").exists()


def test_config_coinbase_entries():
    assert [(m.label, m.exchange, m.symbol) for m in COINBASE_MARKETS] == [
        ("BTC", "coinbase_cde", "BIP-20DEC30-CDE"), ("ETH", "coinbase_cde", "ETP-20DEC30-CDE")]
    assert CONTRACT_SIZES == {"BTC": 0.01, "ETH": 0.1}
    assert all(m.exchange == "krakenfutures" for m in LIVE_MARKETS)


# --- whole-contract sizing -----------------------------------------------------------
def _size(equity, stop_dist, entry=80_000.0, **cfg_kw):
    cfg = RiskConfig(risk_frac=0.01, max_notional_frac=1.0, **cfg_kw)
    intent = EnterIntent(symbol="BTC", side=Side.LONG, stop_price=entry - stop_dist, atr=1.0)
    return size_position(equity, intent, entry, cfg)


def test_lot_rounding_nearest_lot():
    # target 100 / 1000 = 0.1 BTC = 10 lots exactly -> no change; 0.123 -> 12 lots
    assert _size(10_000, 1000.0, lot_sizes={"BTC": 0.01})[0] == pytest.approx(0.10)
    size, risk = _size(12_300, 1000.0, lot_sizes={"BTC": 0.01})
    assert size == pytest.approx(0.12) and risk == pytest.approx(0.12 * 1000.0)   # risk = actual
    size, _ = _size(12_700, 1000.0, lot_sizes={"BTC": 0.01})
    assert size == pytest.approx(0.13)


def test_hard_cap_rounds_down_instead_of_skipping():
    # target 0.0172 BTC (1.72 lots) -> nearest = 2 lots = 1.16x target; hard cap 1.0 -> 1 lot
    size, risk = _size(17_200, 10_000.0, lot_sizes={"BTC": 0.01}, max_risk_mult=1.0)
    assert size == pytest.approx(0.01) and risk == pytest.approx(100.0) and risk <= 172.0


def test_hard_cap_skips_when_one_contract_exceeds_target():
    # $910 equity, 1% = $9.10; 1 BTC lot with a $1,500 stop risks $15 -> skip
    assert _size(910, 1_500.0, lot_sizes={"BTC": 0.01}, max_risk_mult=1.0) == (0.0, 0.0)
    # ETH-like: 1 lot risking $7 fits under $9.10
    size, risk = _size(910, 70.0, entry=2_300.0, lot_sizes={"BTC": 0.1}, max_risk_mult=1.0)
    assert size == pytest.approx(0.1) and risk == pytest.approx(7.0)


def test_lot_rounding_rounds_up_to_one_lot_within_max_risk_mult():
    # target size 0.004 BTC (0.4 lot); one lot (0.01) risks 2.5x the target -> OK at mult 3
    size, risk = _size(400, 1000.0, entry=5_000.0, lot_sizes={"BTC": 0.01}, max_risk_mult=3.0)
    assert size == pytest.approx(0.01) and risk == pytest.approx(10.0)   # target risk was 4


def test_lot_rounding_skips_when_too_risky_or_zero():
    # same as above but default max_risk_mult 2.0 -> 2.5x target -> skip
    assert _size(400, 1000.0, entry=5_000.0, lot_sizes={"BTC": 0.01}) == (0.0, 0.0)
    # tiny equity: target risk $0.1, one lot risks $10 -> skip
    assert _size(10, 1000.0, lot_sizes={"BTC": 0.01}) == (0.0, 0.0)


def test_lot_rounding_respects_notional_cap():
    # equity 500, price 80k: cap = 500/80000 = 0.00625 BTC < 1 lot (0.01) -> no whole lot fits
    assert _size(500, 10.0, lot_sizes={"BTC": 0.01}, max_risk_mult=100.0) == (0.0, 0.0)
    # equity 4000 -> cap 0.05 BTC (5 lots); tiny stop would want far more -> capped at 5 lots
    size, _ = _size(4_000, 1.0, lot_sizes={"BTC": 0.01})
    assert size == pytest.approx(0.05)


def test_risk_config_defaults_leave_sizing_unchanged():
    cfg = RiskConfig()
    assert cfg.lot_sizes is None and cfg.max_risk_mult == 2.0
    intent = EnterIntent(symbol="BTC", side=Side.LONG, stop_price=79_000.0, atr=1.0)
    size, risk = size_position(12_345.0, intent, 80_000.0, cfg)
    assert size == pytest.approx(12_345.0 * 0.01 / 1000.0)      # fractional, untouched
    assert risk == pytest.approx(123.45)
    # a lot_sizes dict that lacks the symbol also leaves it untouched
    assert size_position(12_345.0, intent, 80_000.0, RiskConfig(lot_sizes={"ETH": 0.1})) == (size, risk)


def test_engine_treats_skipped_size_as_no_entry():
    from jcoin.engine.broker import PaperBroker
    from jcoin.engine.engine import TradingEngine
    from jcoin.engine.strategy import BreakoutStrategy, StrategyConfig

    class _Always(BreakoutStrategy):
        def entry_signal(self, row):
            return EnterIntent(symbol=row["symbol"], side=Side.LONG,
                               stop_price=row["close"] - 1000.0, atr=1.0)

    eng = TradingEngine(_Always(StrategyConfig()), PaperBroker(0.0012),
                        RiskConfig(0.01, 1, 2, lot_sizes={"BTC": 0.01}), 10.0)   # tiny account
    t = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    row = {"symbol": "BTC", "ts": t, "open": 80_000.0, "high": 80_000.0, "low": 80_000.0,
           "close": 80_000.0, "volume": 1.0}
    eng.step(t, {"BTC": row})
    assert eng.account.open_count == 0 and eng.account.equity == 10.0


# --- CoinbaseFundingSource -----------------------------------------------------------
def test_coinbase_funding_returns_current_rate_every_hour_fetched_once():
    calls = []

    def fetch(pid):
        calls.append(pid)
        return 5e-6
    src = CoinbaseFundingSource({m.label: m for m in COINBASE_MARKETS}, fetch_rate=fetch)
    src.begin_run(dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc))
    h0 = dt.datetime(2026, 1, 1, 0, tzinfo=dt.timezone.utc)
    assert src.hourly_rate("BTC", h0) == 5e-6
    assert src.hourly_rate("BTC", h0 + dt.timedelta(hours=100)) == 5e-6
    assert calls == ["BIP-20DEC30-CDE"]
    cost, complete = funding_cost(src, "BTC", Side.LONG, 10_000.0, h0, h0 + dt.timedelta(hours=4))
    assert complete and cost == pytest.approx(4 * 5e-6 * 10_000.0)


def test_coinbase_funding_none_on_failure():
    def boom(pid):
        raise OSError("down")
    src = CoinbaseFundingSource({m.label: m for m in COINBASE_MARKETS}, fetch_rate=boom)
    h0 = dt.datetime(2026, 1, 1, 0, tzinfo=dt.timezone.utc)
    assert src.hourly_rate("BTC", h0) is None
    cost, complete = funding_cost(src, "BTC", Side.LONG, 10_000.0, h0, h0 + dt.timedelta(hours=2))
    assert cost == 0.0 and complete is False
