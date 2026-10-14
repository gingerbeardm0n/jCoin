"""Kill rule (KILL_RULE.md: hard halt on >33 consecutive R<=0 trades) and paper funding accrual.

No network: fake rate sources / fake ccxt exchange / synthetic rows only.
"""

from __future__ import annotations

import datetime as dt
import json

import pytest

from jcoin.data.config import Market
from jcoin.engine.kill_switch import HaltLevel, KillSwitch, KillSwitchConfig
from jcoin.engine.types import EnterIntent, Position, Side
from jcoin.live import killswitch_latch, run_paper
from jcoin.live.funding import KrakenFundingSource, funding_cost
from jcoin.live.paper_runner import PaperTrader

UTC = dt.timezone.utc
T0 = dt.datetime(2026, 1, 1, tzinfo=UTC)
H4 = dt.timedelta(hours=4)


def _row(sym, ts, close=100.0, high=None, low=None):
    return {"symbol": sym, "ts": ts, "open": close, "high": high or close + 1.0,
            "low": low or close - 1.0, "close": close, "volume": 1.0, "regime": "uptrend",
            "atr": 1.0, "brk_long": False, "brk_short": False, "conf_sh": 90.0, "conf_sl": 90.0}


# ---------------------------------------------------------------- kill switch: losing streak
def _ks(max_streak=33):
    return KillSwitch(KillSwitchConfig(daily_loss_pct=0.99, max_dd_pct=0.99,
                                       max_losing_streak=max_streak), 10_000.0)


def test_losing_streak_default_is_off():
    ks = KillSwitch(KillSwitchConfig(daily_loss_pct=0.99, max_dd_pct=0.99), 10_000.0)
    for _ in range(100):
        ks.on_trade_closed(-1.0, -1.0)
    assert ks.evaluate(T0, 10_000.0).level is HaltLevel.NONE


def test_hard_halt_on_34th_consecutive_nonwinner_not_before():
    ks = _ks(33)
    for i in range(33):
        ks.on_trade_closed(-10.0, -0.1)
        assert not ks.state.hard_halted, f"tripped early at trade {i + 1}"
    assert ks.evaluate(T0, 10_000.0).level is HaltLevel.NONE
    ks.on_trade_closed(-10.0, -0.1)  # the 34th
    assert ks.state.hard_halted
    d = ks.evaluate(T0, 10_000.0)
    assert d.level is HaltLevel.HARD and "losing streak" in d.reason


def test_r_exactly_zero_counts_as_nonwinner():
    ks = _ks(33)
    for _ in range(34):
        ks.on_trade_closed(0.0, 0.0)
    assert ks.state.hard_halted


def test_win_resets_streak():
    ks = _ks(33)
    for _ in range(33):
        ks.on_trade_closed(-1.0, -0.1)
    ks.on_trade_closed(5.0, 0.5)         # R > 0 resets
    assert ks.state.nonwin_streak == 0
    for _ in range(33):
        ks.on_trade_closed(-1.0, -0.1)
    assert not ks.state.hard_halted
    ks.on_trade_closed(-1.0, -0.1)
    assert ks.state.hard_halted


def test_streak_uses_R_not_pnl_sign():
    ks = _ks(1)
    ks.on_trade_closed(3.0, 0.0)   # positive pnl but R == 0 (no risk_dollars) -> non-winner
    ks.on_trade_closed(3.0, 0.0)
    assert ks.state.hard_halted


def _trip_trader(tmp_path, monkeypatch, losers=34):
    """Drive a PaperTrader through `losers` stop-outs on BTC (2 bars each) with an ETH
    position open at the end. Returns (trader, ts of next free bar)."""
    tr = PaperTrader(labels=["BTC", "ETH"], tf="4h", state_dir=str(tmp_path / "state"),
                     ks=KillSwitchConfig(daily_loss_pct=0.99, max_dd_pct=0.99, max_losing_streak=33),
                     start_equity=1_000_000.0)
    monkeypatch.setattr(
        tr.engine.strategy, "entry_signal",
        lambda row: EnterIntent("BTC", Side.LONG, row["close"] - 1.0, 1.0, "t")
        if row["symbol"] == "BTC" else None)
    ts = T0
    for i in range(losers):
        tr.process_step(ts, {"BTC": _row("BTC", ts)})                      # enter long @100, stop 99
        assert tr.engine.account.open_count == 1
        ts += H4
        if i == losers - 1:  # ETH position open at the moment the 34th loss lands
            tr.engine.account.positions["ETH"] = Position(
                "ETH", Side.LONG, ts - H4, 100.0, 1.0, 10.0, 1.0, 90.0, 90.0, 100.0)
            tr.engine._bars_held["ETH"] = 0
        rows = {"BTC": _row("BTC", ts, low=98.0), "ETH": _row("ETH", ts)}
        tr.process_step(ts, rows, allow_entries=False)                      # BTC stopped out @99
        ts += H4
        if i < losers - 1:
            assert not tr.ks.state.hard_halted
            assert tr.ks.state.nonwin_streak == i + 1
    return tr, ts


def test_runner_trips_on_34th_loser_flattens_and_latches(tmp_path, monkeypatch):
    tr, _ = _trip_trader(tmp_path, monkeypatch, losers=34)
    assert tr.ks.state.hard_halted and tr.ks.state.nonwin_streak >= 34
    assert tr.engine.account.open_count == 0, "ETH position must be flattened immediately"
    assert tr.engine.entries_enabled is False
    assert killswitch_latch.is_latched(tr.dir)


def test_runner_not_halted_after_33_losers(tmp_path, monkeypatch):
    tr, _ = _trip_trader(tmp_path, monkeypatch, losers=33)
    # the helper opens ETH on the last loser; 33 losers -> not tripped, so ETH stays open
    assert not tr.ks.state.hard_halted
    assert not killswitch_latch.is_latched(tr.dir)
    assert tr.engine.account.open_count == 1  # the ETH position is untouched


def test_hard_halt_persists_across_restart_and_needs_human(tmp_path, monkeypatch, capsys):
    tr, ts = _trip_trader(tmp_path, monkeypatch, losers=34)
    d = tr.dir

    # restart: flag survives save/load; the runner refuses to start (exit 5)
    tr2 = PaperTrader(labels=["BTC", "ETH"], tf="4h", state_dir=str(d),
                      ks=KillSwitchConfig(max_dd_pct=0.99, max_losing_streak=33))
    assert tr2.ks.state.hard_halted and tr2.ks.state.nonwin_streak >= 34
    assert "losing streak" in tr2.ks.state.halt_reason
    assert run_paper.main(["--state-dir", str(d)]) == 5

    # even a strategy signal on a new bar cannot open a position
    monkeypatch.setattr(tr2.engine.strategy, "entry_signal",
                        lambda row: EnterIntent("BTC", Side.LONG, row["close"] - 1.0, 1.0, "t"))
    tr2.process_step(ts, {"BTC": _row("BTC", ts)})
    assert tr2.engine.account.open_count == 0

    # the equity-reset path cannot clear it while the latch exists
    with pytest.raises(RuntimeError):
        tr2.reset_equity(10_000.0)
    assert tr2.ks.state.hard_halted

    # deleting the latch alone does not resume: the persisted flag re-latches on the next bar
    killswitch_latch.latch_path(d).unlink()
    tr2.process_step(ts + H4, {"BTC": _row("BTC", ts + H4)})
    assert tr2.engine.account.open_count == 0 and killswitch_latch.is_latched(d)

    # explicit human action: delete the latch AND reset (new clock)
    killswitch_latch.latch_path(d).unlink()
    tr2.reset_equity(10_000.0)
    assert not tr2.ks.state.hard_halted and tr2.ks.state.nonwin_streak == 0
    tr2.process_step(ts + 2 * H4, {"BTC": _row("BTC", ts + 2 * H4)})
    assert tr2.engine.account.open_count == 1


def test_live_runner_cli_defaults(monkeypatch, tmp_path):
    captured = {}

    class Stop(Exception):
        pass

    def fake_trader(**kw):
        captured.update(kw)
        raise Stop

    monkeypatch.setattr(run_paper, "PaperTrader", fake_trader)
    with pytest.raises(Stop):
        run_paper.main(["--state-dir", str(tmp_path / "s")])
    cfg = captured["ks"]
    assert cfg.max_dd_pct == 0.398 and cfg.max_losing_streak == 33
    assert KillSwitchConfig().max_losing_streak == 0 and KillSwitchConfig().max_dd_pct == 0.25


# ---------------------------------------------------------------- funding
class FakeRates:
    """rate_fn(label, hour_start) -> float | None; records begin_run."""

    def __init__(self, rate_fn):
        self.rate_fn = rate_fn
        self.since = None

    def begin_run(self, since):
        self.since = since

    def hourly_rate(self, label, hour_start):
        return self.rate_fn(label, hour_start)


def _funding_trader(tmp_path, rates, side, size=2.0, entry_price=100.0):
    tr = PaperTrader(labels=["BTC"], tf="4h", state_dir=str(tmp_path / "state"),
                     start_equity=10_000.0, funding=rates)
    tr.engine.account.positions["BTC"] = Position(
        "BTC", side, T0, entry_price, size, 20.0, 1.0,
        entry_price - 50 * side.sign, entry_price - 50 * side.sign, entry_price, entry_cost=0.5)
    tr.engine._bars_held["BTC"] = 0
    return tr


def test_funding_cost_helper_partial_hours():
    src = FakeRates(lambda l, h: 0.001)
    # 90 minutes starting 00:30 on a 1000 notional long -> 1.5h * 0.001 * 1000
    cost, ok = funding_cost(src, "BTC", Side.LONG, 1000.0, T0 + dt.timedelta(minutes=30),
                            T0 + dt.timedelta(hours=2))
    assert ok and cost == pytest.approx(1.5)


def test_long_pays_and_short_receives_positive_funding_over_n_hours(tmp_path):
    rate = 1e-5
    n_bars = 3                       # 12 hours
    exp = 2.0 * 100.0 * rate * 4 * n_bars   # notional * rate * hours = 0.024
    for side, sign in ((Side.LONG, 1), (Side.SHORT, -1)):
        tr = _funding_trader(tmp_path / side.value, FakeRates(lambda l, h: rate), side)
        eq0 = tr.engine.account.equity
        for k in range(1, n_bars + 1):
            ts = T0 + k * H4
            tr.process_step(ts, {"BTC": _row("BTC", ts)}, allow_entries=False)
        pos = tr.engine.account.positions["BTC"]
        assert pos.funding == pytest.approx(sign * exp)
        assert tr.engine.account.equity == pytest.approx(eq0 - sign * exp)
        assert tr.funding_missing_bars == 0


def test_closed_trade_pnl_and_R_include_funding_without_double_charge(tmp_path):
    rate = 1e-4
    tr = _funding_trader(tmp_path, FakeRates(lambda l, h: rate), Side.LONG, size=2.0)
    eq0 = tr.engine.account.equity
    for k in (1, 2):
        ts = T0 + k * H4
        tr.process_step(ts, {"BTC": _row("BTC", ts)}, allow_entries=False)
    funding = 2 * (2.0 * 100.0 * rate * 4)   # 0.16
    # bar 3: price spikes then the stop is hit (stop = 50, trail unchanged)
    ts = T0 + 3 * H4
    tr.engine.account.positions["BTC"].trail_stop = 95.0
    tr.process_step(ts, {"BTC": _row("BTC", ts, low=90.0)}, allow_entries=False)
    funding += 2.0 * 100.0 * rate * 4       # third window accrued before the exit
    (t,) = tr.engine.account.closed
    gross = (95.0 - 100.0) * 2.0
    assert t.funding == pytest.approx(funding)
    assert t.pnl == pytest.approx(gross - 0.5 - funding)
    assert t.R == pytest.approx(t.pnl / 20.0)
    # equity: deducted once as it accrued, not again at close
    assert tr.engine.account.equity == pytest.approx(eq0 + gross - 0.5 - funding)


def test_missing_funding_charges_zero_and_counts_bar(tmp_path, caplog):
    tr = _funding_trader(tmp_path, FakeRates(lambda l, h: None), Side.LONG)
    eq0 = tr.engine.account.equity
    with caplog.at_level("WARNING"):
        for k in (1, 2):
            ts = T0 + k * H4
            tr.process_step(ts, {"BTC": _row("BTC", ts)}, allow_entries=False)
    assert tr.engine.account.equity == eq0
    assert tr.engine.account.positions["BTC"].funding == 0.0
    assert tr.funding_missing_bars == 2
    assert any("FUNDING UNAVAILABLE" in r.getMessage() for r in caplog.records)
    # persisted
    tr2 = PaperTrader(labels=["BTC"], tf="4h", state_dir=str(tmp_path / "state"))
    assert tr2.funding_missing_bars == 2


def test_funding_disabled_by_default_leaves_equity_alone(tmp_path):
    tr = PaperTrader(labels=["BTC"], tf="4h", state_dir=str(tmp_path / "state"))
    tr.engine.account.positions["BTC"] = Position("BTC", Side.LONG, T0, 100.0, 2.0, 20.0, 1.0,
                                                 50.0, 50.0, 100.0)
    tr.engine._bars_held["BTC"] = 0
    eq0 = tr.engine.account.equity
    tr.process_step(T0 + H4, {"BTC": _row("BTC", T0 + H4)}, allow_entries=False)
    assert tr.engine.account.equity == eq0 and tr.funding_missing_bars == 0


class FakeKraken:
    def __init__(self, hist=None, current=0.00002, fail_hist=False, fail_current=False):
        self.hist = hist or []
        self.current = current
        self.fail_hist, self.fail_current = fail_hist, fail_current
        self.calls = []

    def fetch_funding_rate_history(self, symbol, since=None, limit=None):
        self.calls.append(("hist", symbol, since))
        if self.fail_hist:
            raise RuntimeError("boom")
        return [r for r in self.hist if since is None or r["timestamp"] >= since]

    def fetch_funding_rate(self, symbol):
        self.calls.append(("cur", symbol))
        if self.fail_current:
            raise RuntimeError("boom")
        return {"fundingRate": self.current}


def _hist_row(hour_dt, rate):
    return {"timestamp": int(hour_dt.timestamp() * 1000), "fundingRate": rate}


_MK = {"BTC": Market(label="BTC", exchange="krakenfutures", symbol="BTC/USD:USD")}


def test_kraken_source_uses_history_and_current_at_live_edge():
    hrs = [T0 + dt.timedelta(hours=i) for i in range(4)]
    ex = FakeKraken(hist=[_hist_row(h, 1e-5 * (i + 1)) for i, h in enumerate(hrs)], current=9e-5)
    src = KrakenFundingSource(_MK, exchange=ex)
    src.begin_run(T0)
    assert src.hourly_rate("BTC", hrs[1]) == pytest.approx(2e-5)
    assert src.hourly_rate("BTC", hrs[3]) == pytest.approx(4e-5)
    assert src.hourly_rate("BTC", hrs[3] + dt.timedelta(hours=1)) == pytest.approx(9e-5)  # live edge
    assert sum(1 for c in ex.calls if c[0] == "hist") == 1    # fetched once per run
    assert sum(1 for c in ex.calls if c[0] == "cur") == 1


def test_kraken_source_failures_return_none_never_a_guess():
    src = KrakenFundingSource(_MK, exchange=FakeKraken(fail_hist=True))
    src.begin_run(T0)
    assert src.hourly_rate("BTC", T0) is None
    # history ok but current fails at the live edge -> None
    ex = FakeKraken(hist=[_hist_row(T0, 1e-5)], fail_current=True)
    src = KrakenFundingSource(_MK, exchange=ex)
    src.begin_run(T0)
    assert src.hourly_rate("BTC", T0 + dt.timedelta(hours=1)) is None
    # a hole inside fetched history is unknown, not filled
    ex = FakeKraken(hist=[_hist_row(T0, 1e-5), _hist_row(T0 + dt.timedelta(hours=3), 1e-5)])
    src = KrakenFundingSource(_MK, exchange=ex)
    src.begin_run(T0)
    assert src.hourly_rate("BTC", T0 + dt.timedelta(hours=1)) is None


# ---------------------------------------------------------------- old-format state.json
def test_old_format_state_json_loads(tmp_path):
    d = tmp_path / "state"
    d.mkdir()
    t = lambda h: (T0 + dt.timedelta(hours=h)).isoformat()
    closed = [{"symbol": "BTC", "side": "long", "entry_time": t(4 * i), "exit_time": t(4 * i + 4),
               "entry_price": 100.0, "exit_price": 99.0, "size": 1.0, "pnl": -1.0, "R": -0.1,
               "exit_reason": "stop"} for i in range(1, 5)]
    closed[0].update(pnl=5.0, R=0.5)  # a win, then 3 non-winners
    old = {
        "equity": 957.23, "last_ts": t(40), "bars_held": {"BTC": 3}, "cycle_phase": "bull",
        "last_prices": {"BTC": 100.0},
        "positions": [{"symbol": "BTC", "side": "long", "entry_time": t(36), "entry_price": 100.0,
                       "size": 1.0, "risk_dollars": 10.0, "atr": 1.0, "init_stop": 99.0,
                       "trail_stop": 99.0, "extreme": 100.0, "entry_cost": 0.1,
                       "stop_order_id": None, "stop_order_price": None}],
        "closed": closed,
        "equity_curve": [[t(0), 1000.0], [t(40), 957.23]],
        "killswitch": {"peak_equity": 1000.0, "day": "2026-01-02", "day_start_equity": 960.0,
                       "loss_streak": 3, "halted_until_day": None, "hard_halted": False},
    }
    (d / "state.json").write_text(json.dumps(old))
    tr = PaperTrader(labels=["BTC"], tf="4h", state_dir=str(d))
    assert tr.engine.account.equity == 957.23
    pos = tr.engine.account.positions["BTC"]
    assert pos.funding == 0.0 and pos.funding_ts is None
    assert all(c.funding == 0.0 for c in tr.engine.account.closed)
    assert tr.funding_missing_bars == 0
    assert not tr.ks.state.hard_halted and tr.ks.state.halt_reason == ""
    assert tr.ks.state.nonwin_streak == 3    # rebuilt from trailing trades since the clock start
    tr._save()                               # and the new format round-trips
    tr2 = PaperTrader(labels=["BTC"], tf="4h", state_dir=str(d))
    assert tr2.ks.state.nonwin_streak == 3 and tr2.engine.account.equity == 957.23
