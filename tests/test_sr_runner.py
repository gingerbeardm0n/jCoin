"""A_SR paper runner (VALIDATION_RULES.md §9): minute-level spot stops, nano fills."""

import pytest

from jcoin.live import sr_runner as sr

H4, M1 = sr.BAR_MS, sr.MIN_MS
T0 = 1_760_000_000_000 - 1_760_000_000_000 % H4   # a 4h-aligned ms timestamp


class FakeData:
    def __init__(self, spot4, nano4, spot1=None, nano1=None, rate=0.0):
        self.spot4, self.nano4 = spot4, nano4
        self.spot1, self.nano1 = spot1 or {}, nano1 or {}
        self.rate = rate

    def bars_4h(self, pid, limit):
        return (self.spot4 if pid in sr.SPOT.values() else self.nano4)[pid][-limit:]

    def minutes(self, pid, start, end):
        src = self.spot1 if pid in sr.SPOT.values() else self.nano1
        return [r for r in src.get(pid, []) if start <= r[0] < end]

    def funding_rate(self, pid):
        return self.rate


def _bars(n, start, price=100.0):
    return [[start + i * H4, price, price + 1, price - 1, price, 1.0] for i in range(n)]


def _trader(tmp_path, data, now):
    t = sr.SRTrader(tmp_path / "s", data=data, now_ms=lambda: now)
    return t


def _feeds(n=30, price=100.0, nano_price=101.0):
    spot = {pid: _bars(n, T0, price) for pid in sr.SPOT.values()}
    nano = {pid: _bars(n, T0, nano_price) for pid in sr.NANO.values()}
    return spot, nano


def _open_long(t, label="BTC", entry_ms=None, stop=95.0, basis=1.01, atr=2.0):
    entry_ms = entry_ms if entry_ms is not None else t.s["last_bar_ms"]
    t.s["positions"][label] = {"side": "long", "entry_ms": entry_ms, "entry_fill": 101.0,
                               "entry_ref": 100.0, "stop": stop, "best": 101.0, "atr": atr,
                               "size": 1.0, "risk_dollars": 6.06, "basis": basis, "bars_held": 0,
                               "checked_ms": entry_ms + H4, "last_price": 101.0}


def test_init_marks_latest_closed_bar_and_takes_no_trades(tmp_path):
    spot, nano = _feeds()
    now = T0 + 30 * H4 + 5 * M1          # bar 29 closed exactly at T0+30*H4
    t = _trader(tmp_path, FakeData(spot, nano), now)
    t.init(1000.0)
    assert t.s["last_bar_ms"] == T0 + 29 * H4 and t.s["positions"] == {} and t.s["equity"] == 1000.0
    t.tick()
    assert t.s["closed"] == []


def test_spot_minute_breach_exits_at_stop_times_basis(tmp_path):
    spot, nano = _feeds()
    entry = T0 + 28 * H4
    breach = entry + H4 + 30 * M1
    spot1 = {"BTC-USD": [[breach, 96, 96, 94.5, 95.5, 1]]}
    nano1 = {"BIP-20DEC30-CDE": [[breach, 97, 97, 95.4, 96.48, 1]]}
    now = T0 + 30 * H4 + 5 * M1
    t = _trader(tmp_path, FakeData(spot, nano, spot1, nano1), now)
    t.init(1000.0)
    t.s["last_bar_ms"] = entry
    _open_long(t, entry_ms=entry)
    t.tick()
    c = t.s["closed"][0]
    assert c["exit_kind"] == "stop"
    assert c["exit_fill"] == pytest.approx(95.0 * 96.48 / 95.5)
    assert "BTC" not in t.s["positions"]


def test_nano_spike_hits_resting_disaster_stop(tmp_path):
    spot, nano = _feeds()
    entry = T0 + 28 * H4
    spike = entry + H4 + 10 * M1
    # spot calm; nano prints far below the disaster level (95 - 2*2) * 1.01 = 91.91
    spot1 = {"BTC-USD": [[spike, 100, 100.5, 99.5, 100, 1]]}
    nano1 = {"BIP-20DEC30-CDE": [[spike, 101, 101, 85.0, 100.9, 1]]}
    t = _trader(tmp_path, FakeData(spot, nano, spot1, nano1), T0 + 30 * H4 + 5 * M1)
    t.init(1000.0)
    t.s["last_bar_ms"] = entry
    _open_long(t, entry_ms=entry)
    t.tick()
    c = t.s["closed"][0]
    assert c["exit_kind"] == "disaster" and c["exit_fill"] == pytest.approx(91.91)


def test_trailing_stop_updates_from_spot_bar_high(tmp_path):
    spot, nano = _feeds()
    entry = T0 + 28 * H4
    spot["BTC-USD"][29] = [T0 + 29 * H4, 100, 130, 99, 129, 1]
    t = _trader(tmp_path, FakeData(spot, nano), T0 + 30 * H4 + 5 * M1)
    t.init(1000.0)
    t.s["last_bar_ms"] = entry
    _open_long(t, entry_ms=entry)
    t.tick()
    p = t.s["positions"]["BTC"]
    assert p["best"] == 130 and p["stop"] == pytest.approx(130 - sr.ATR_TRAIL * 2.0) and p["bars_held"] == 1


def test_stale_spot_feed_raises(tmp_path):
    spot, nano = _feeds()
    t = _trader(tmp_path, FakeData(spot, nano), T0 + 30 * H4 + 12 * 3600 * 1000)
    t.init(1000.0)
    with pytest.raises(sr.StaleFeed):
        t.tick()


def test_missing_state_refuses(tmp_path, monkeypatch):
    pings = []
    monkeypatch.setattr(sr, "ping", lambda suffix="": pings.append(suffix))
    assert sr.main(["--state-dir", str(tmp_path / "none")]) == 7
    assert pings == ["/fail"]


def test_entry_on_newest_bar_signal(tmp_path, monkeypatch):
    spot, nano = _feeds()
    last = 29

    def fake_detect(df, k=2):
        return df, [{"idx": last, "side": "long", "regime": sr.REGIME_UPTREND}]

    monkeypatch.setattr(sr, "detect_breakout", fake_detect)
    monkeypatch.setattr(sr, "_atr", lambda df, p: [2.0] * df.height)
    t = _trader(tmp_path, FakeData(spot, nano), T0 + 30 * H4 + 5 * M1)
    t.init(1000.0)
    t.s["last_bar_ms"] = T0 + 28 * H4
    t.tick()
    p = t.s["positions"]["BTC"]
    # entry at nano close 101; spot stop 100 - 2 = 98; nano-equivalent stop 98*1.01
    assert p["entry_fill"] == 101.0 and p["stop"] == pytest.approx(98.0)
    assert p["size"] == pytest.approx(round(p["size"] / 0.01) * 0.01)
