"""Tests for the live catch-up loop (audit 2026-09-18, item #2).

Uses synthetic 4h candles and a monkeypatched fetch function -- no network calls.
"""

from __future__ import annotations

import datetime as dt

import polars as pl
import pytest

import jcoin.live.paper_runner as pr_mod
from jcoin.engine.types import EnterIntent, Position, Side
from jcoin.live.paper_runner import PaperTrader

TF_HOURS = 4


def _recent_start(n: int) -> dt.datetime:
    """Start time so that the n-th (last) bar lands on the most recent 4h boundary --
    i.e. "now", not stale -- so the feed-staleness guard doesn't exclude it."""
    now = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    last_bar = now - dt.timedelta(hours=now.hour % TF_HOURS)
    return last_bar - dt.timedelta(hours=TF_HOURS * (n - 1))


def _make_df(n: int, start: dt.datetime, base_price: float = 100.0) -> pl.DataFrame:
    """n flat-ish 4h candles starting at `start`, spaced TF_HOURS apart."""
    rows = []
    for i in range(n):
        ts = start + dt.timedelta(hours=TF_HOURS * i)
        price = base_price
        rows.append([int(ts.timestamp() * 1000), price, price + 1.0, price - 1.0, price, 10.0])
    df = pl.DataFrame(rows, schema=["ts", "open", "high", "low", "close", "volume"], orient="row")
    return df.with_columns(
        pl.from_epoch(pl.col("ts"), time_unit="ms").dt.replace_time_zone("UTC").alias("ts")
    )


@pytest.fixture
def synthetic_feed(monkeypatch):
    """200 bars of history for BTC + ETH, ending on the most recent 4h boundary so the
    feed-staleness guard doesn't exclude the newest bar. Returns (dfs, all_ts_sorted)."""
    n = 200
    start = _recent_start(n)
    dfs = {"BTC": _make_df(n, start), "ETH": _make_df(n, start)}

    def fake_get_recent_candles_cached(market, tf, cache_dir, limit=2300, **kwargs):
        return dfs[market.label]

    monkeypatch.setattr(pr_mod, "get_recent_candles_cached", fake_get_recent_candles_cached)
    all_ts = sorted(dfs["BTC"]["ts"].to_list())
    return dfs, all_ts


def test_catchup_processes_all_missed_bars_in_order(tmp_path, synthetic_feed):
    dfs, all_ts = synthetic_feed
    trader = PaperTrader(labels=["BTC", "ETH"], tf="4h", state_dir=str(tmp_path / "state"))
    # Pretend we already processed everything except the last 5 bars.
    trader.last_ts = all_ts[-6]
    missed = all_ts[-5:]

    processed = trader.run_live_once()

    assert processed is True
    assert trader.last_ts == missed[-1]
    # Exactly the 5 missed bars should have advanced the equity curve, in order.
    assert len(trader.engine.account.equity_curve) == 5
    curve_ts = [t for t, _ in trader.engine.account.equity_curve]
    assert curve_ts == missed


def test_no_new_bar_returns_false(tmp_path, synthetic_feed):
    dfs, all_ts = synthetic_feed
    trader = PaperTrader(labels=["BTC", "ETH"], tf="4h", state_dir=str(tmp_path / "state"))
    trader.last_ts = all_ts[-1]  # already fully caught up

    processed = trader.run_live_once()

    assert processed is False
    assert trader.last_ts == all_ts[-1]


def test_lagging_symbol_does_not_freeze_catchup(tmp_path, monkeypatch):
    """If one symbol's fetch fails outright, the other symbol should still catch up
    instead of the whole tick returning False (audit 2026-09-18, item #2: 'robust
    per-symbol min() logic')."""
    n = 200
    start = _recent_start(n)
    btc_df = _make_df(n, start)

    def flaky_fetch(market, tf, cache_dir, limit=2300, **kwargs):
        if market.label == "ETH":
            raise RuntimeError("simulated exchange outage for ETH")
        return btc_df

    monkeypatch.setattr(pr_mod, "get_recent_candles_cached", flaky_fetch)

    trader = PaperTrader(labels=["BTC", "ETH"], tf="4h", state_dir=str(tmp_path / "state"))
    all_ts = sorted(btc_df["ts"].to_list())
    trader.last_ts = all_ts[-3]

    processed = trader.run_live_once()

    assert processed is True
    assert trader.last_ts == all_ts[-1]


def test_allow_stale_entries_false_skips_entry_on_stale_bar(tmp_path, monkeypatch):
    """With allow_stale_entries=False, a bar that is NOT the newest in the batch must
    only manage/exit positions, never open a new one -- even if the strategy signals
    an entry on it."""
    trader = PaperTrader(labels=["BTC"], tf="4h", state_dir=str(tmp_path / "state"),
                         allow_stale_entries=False)
    # Force the strategy to always want to enter, isolating the allow_entries gate
    # from the real feature/breakout pipeline.
    monkeypatch.setattr(
        trader.engine.strategy, "entry_signal",
        lambda row: EnterIntent(row["symbol"], Side.LONG, row["close"] - 1.0, 1.0, "test-signal"),
    )
    ts0 = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    row = {"symbol": "BTC", "ts": ts0, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0,
          "volume": 1.0, "regime": "uptrend", "atr": 1.0, "brk_long": True, "brk_short": False,
          "conf_sh": 90.0, "conf_sl": 90.0}

    # Stale (catch-up) bar: allow_entries=False -> must NOT open a position.
    trader.process_step(ts0, {"BTC": dict(row, ts=ts0)}, allow_entries=False)
    assert trader.engine.account.open_count == 0

    # Fresh (newest) bar: allow_entries=True -> entry signal should be taken.
    ts1 = ts0 + dt.timedelta(hours=TF_HOURS)
    trader.process_step(ts1, {"BTC": dict(row, ts=ts1)}, allow_entries=True)
    assert trader.engine.account.open_count == 1


def test_allow_stale_entries_true_allows_entry_on_backlog_bar(tmp_path, monkeypatch):
    """Paper trading defaults to allow_stale_entries=True: catch-up bars are allowed
    to open positions too (matches replay/backtest parity)."""
    trader = PaperTrader(labels=["BTC"], tf="4h", state_dir=str(tmp_path / "state"))
    assert trader.allow_stale_entries is True
    monkeypatch.setattr(
        trader.engine.strategy, "entry_signal",
        lambda row: EnterIntent(row["symbol"], Side.LONG, row["close"] - 1.0, 1.0, "test-signal"),
    )
    ts0 = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    row = {"symbol": "BTC", "ts": ts0, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0,
          "volume": 1.0, "regime": "uptrend", "atr": 1.0, "brk_long": True, "brk_short": False,
          "conf_sh": 90.0, "conf_sl": 90.0}

    # Even marked as a stale/backlog bar (allow_entries=False would be the runner's
    # choice, not forced here), a default paper trader processing a backlog bar with
    # allow_entries=True (its own default) should be allowed to enter.
    trader.process_step(ts0, {"BTC": row}, allow_entries=True)
    assert trader.engine.account.open_count == 1


def test_orphan_position_managed_but_not_reentered(tmp_path, monkeypatch, caplog):
    """Orphan-position fix (audit 2026-09-18): universe is [BTC] only, but an open
    ADA short exists from before ADA left the universe. run_live_once() must still
    fetch ADA and manage/exit it (engine.step only manages symbols present in
    `rows`), but must never let ADA open a NEW position -- only symbols in
    trader.labels may enter."""
    n = 200
    start = _recent_start(n)
    btc_df = _make_df(n, start)
    ada_df = _make_df(n, start)

    def fake_get_recent_candles_cached(market, tf, cache_dir, limit=2300, **kwargs):
        return {"BTC": btc_df, "ADA": ada_df}[market.label]

    monkeypatch.setattr(pr_mod, "get_recent_candles_cached", fake_get_recent_candles_cached)

    trader = PaperTrader(labels=["BTC"], tf="4h", state_dir=str(tmp_path / "state"))
    all_ts = sorted(btc_df["ts"].to_list())
    trader.last_ts = all_ts[-3]  # 2 new bars to process

    # Pre-existing ADA short that fell outside the universe. trail_stop is set well
    # below the synthetic candles' constant high (101.0) so the very first processed
    # bar triggers a stop exit.
    ada_pos = Position(
        symbol="ADA", side=Side.SHORT, entry_time=all_ts[-3],
        entry_price=100.0, size=10.0, risk_dollars=5.0, atr=1.0,
        init_stop=105.0, trail_stop=50.0, extreme=100.0, entry_cost=0.0,
    )
    trader.engine.account.positions["ADA"] = ada_pos
    trader.engine._bars_held["ADA"] = 0

    # Force ADA to always show a breakout entry signal (even once flat) so we can
    # confirm the universe restriction -- not the absence of a signal -- is what
    # blocks re-entry. BTC keeps its real (signal-less on flat data) entry_signal.
    real_entry_signal = trader.engine.strategy.entry_signal

    def fake_entry_signal(row):
        if row["symbol"] == "ADA":
            return EnterIntent("ADA", Side.SHORT, row["close"] + 1.0, 1.0, "test-breakout")
        return real_entry_signal(row)

    monkeypatch.setattr(trader.engine.strategy, "entry_signal", fake_entry_signal)

    with caplog.at_level("WARNING"):
        processed = trader.run_live_once()

    assert processed is True
    assert "managing 1 orphan position(s) outside universe" in caplog.text
    assert "ADA" in caplog.text

    # The stop-hit closed the orphan ADA position ...
    assert "ADA" not in trader.engine.account.positions
    assert any(t.symbol == "ADA" and t.exit_reason == "stop" for t in trader.engine.account.closed)
    # ... and it was never allowed to re-enter despite signalling a breakout every bar.
    assert "ADA" not in trader.engine.account.positions
