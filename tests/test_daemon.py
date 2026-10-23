"""Daemon scheduling + safety defaults (2026-10-12 rewrite)."""
import datetime as dt

from jcoin.live import daemon

UTC = dt.timezone.utc


def test_next_fire_is_hh05_after_now():
    assert daemon.next_fire_utc(dt.datetime(2026, 10, 12, 14, 0, tzinfo=UTC)) == \
        dt.datetime(2026, 10, 12, 14, 5, tzinfo=UTC)
    assert daemon.next_fire_utc(dt.datetime(2026, 10, 12, 14, 5, tzinfo=UTC)) == \
        dt.datetime(2026, 10, 12, 15, 5, tzinfo=UTC)
    assert daemon.next_fire_utc(dt.datetime(2026, 10, 12, 23, 59, tzinfo=UTC)) == \
        dt.datetime(2026, 10, 13, 0, 5, tzinfo=UTC)


def test_default_mode_is_paper_and_never_touches_kraken(monkeypatch):
    calls = []
    monkeypatch.setattr(daemon, "run_module", lambda m, a=None: calls.append(m) or 0)
    monkeypatch.setattr(daemon, "RotatingFileHandler", lambda *a, **k: __import__("logging").NullHandler())
    assert daemon.main(["--once"]) == 0
    assert calls == ["jcoin.live.run_paper", "jcoin.live.sr_runner"]


def test_tick_reports_runner_failure(monkeypatch):
    monkeypatch.setattr(daemon, "run_module", lambda m, a=None: 4)
    assert daemon.tick("paper") == {"paper": 4, "sr": 4}


def test_state_root_routes_state_dir(monkeypatch):
    seen = {}
    monkeypatch.setattr(daemon, "_STATE_ROOT", "/var/data")
    monkeypatch.setattr(daemon, "run_module", lambda m, a=None: seen.setdefault(m, a) and 0)
    daemon.tick("paper")
    assert seen["jcoin.live.run_paper"] == ["--state-dir", "/var/data/paper_state"]
