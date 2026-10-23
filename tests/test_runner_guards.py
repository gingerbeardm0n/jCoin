"""run_paper guards: a frozen feed must not ping healthy; a missing state.json must not replay."""

from jcoin.live import run_paper


class _FakeTrader:
    def __init__(self, stale=None, **kw):
        self.stale_feed = stale
        self.fetch_failures = []

    def run_live_once(self):
        pass


def _patch(monkeypatch, stale=None):
    pings = []
    monkeypatch.setattr(run_paper, "PaperTrader", lambda **kw: _FakeTrader(stale, **kw))
    monkeypatch.setattr(run_paper, "ping", lambda suffix="": pings.append(suffix))
    monkeypatch.setattr(run_paper.remote_flatten, "handle_flatten", lambda t, d: False)
    return pings


def test_missing_state_refuses_live_run(monkeypatch, tmp_path):
    pings = _patch(monkeypatch)
    assert run_paper.main(["--state-dir", str(tmp_path / "s")]) == 7
    assert pings == ["/fail"]


def test_missing_state_allowed_with_init(monkeypatch, tmp_path):
    pings = _patch(monkeypatch)
    monkeypatch.setattr(run_paper, "PaperTrader",
                        lambda **kw: type("T", (_FakeTrader,), {"engine": None})(None))
    try:
        run_paper.main(["--state-dir", str(tmp_path / "s"), "--init"])
    except AttributeError:
        pass  # got past the guard into the summary block, which the fake can't serve
    assert "/fail" not in pings and pings == [""]


def test_stale_feed_sends_fail_ping(monkeypatch, tmp_path):
    d = tmp_path / "s"
    d.mkdir()
    (d / "state.json").write_text("{}")
    pings = _patch(monkeypatch, stale="2026-10-23T00:00:00Z")
    assert run_paper.main(["--state-dir", str(d)]) == 6
    assert pings == ["/fail"]
