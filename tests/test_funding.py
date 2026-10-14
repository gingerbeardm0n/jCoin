"""Funding adjustment in portfolio_backtest.build_trades: sign, amount, R conversion."""

import datetime as dt

import numpy as np
import polars as pl
import pytest

from jcoin.research import portfolio_backtest as pb
from jcoin.strategy.regime import REGIME_DOWNTREND, REGIME_UPTREND

UTC = dt.timezone.utc
T0 = dt.datetime(2024, 1, 1, tzinfo=UTC)


def _ms(t):
    return int(t.timestamp() * 1000)


def _bars(n=8):
    """Flat 4h price series at 100 so price P&L is exactly 0; only funding moves R."""
    return pl.DataFrame({
        "ts": [T0 + dt.timedelta(hours=4 * i) for i in range(n)],
        "open": [100.0] * n, "high": [100.0] * n, "low": [100.0] * n, "close": [100.0] * n,
        "volume": [1.0] * n,
    })


def _write_funding(tmp_path, label="BTC"):
    # entry bar opens 04:00 (idx 1); max_hold=3 -> exit bar opens 16:00 (idx 4).
    # Prints carry a few ms of jitter like Binance's calc_time.
    rows = [
        (T0 + dt.timedelta(hours=0), 0.5),    # before entry         -> excluded
        (T0 + dt.timedelta(hours=4), 0.5),    # exactly at entry     -> excluded (strict >)
        (T0 + dt.timedelta(hours=8), 0.001),  # inside               -> included
        (T0 + dt.timedelta(hours=16), 0.001), # exactly at exit      -> included (<=)
        (T0 + dt.timedelta(hours=24), 0.5),   # after exit           -> excluded
    ]
    df = pl.DataFrame({"ts": [_ms(t) + 3 for t, _ in rows],
                       "funding_rate": [r for _, r in rows]})
    d = tmp_path / label
    d.mkdir(parents=True)
    df.write_parquet(d / "funding.parquet")
    return tmp_path


class _FakeFeed:
    def get_candles(self, label, tf, start=None, end=None, market=None):
        return _bars()


def _build(monkeypatch, tmp_path, side, mult):
    regime = REGIME_UPTREND if side == "long" else REGIME_DOWNTREND
    monkeypatch.setattr(pb, "DataFeed", _FakeFeed)
    monkeypatch.setattr(pb, "detect_breakout",
                        lambda df, k=2: (df, [{"idx": 1, "side": side, "regime": regime}]))
    monkeypatch.setattr(pb, "_atr", lambda df, period: np.full(df.height, 2.0))
    # entry 100, ATR 2, init 1.0 -> stop distance 2 / 100 = 0.02 of entry price
    return pb.build_trades("4h", ["BTC"], 14, 1.0, 6.0, 3, 0.0, funding_mult=mult,
                           funding_dir=_write_funding(tmp_path))


def test_long_pays_positive_funding(monkeypatch, tmp_path):
    (t,) = _build(monkeypatch, tmp_path, "long", 1.0)
    # two prints of +0.001 in (entry, exit] -> long pays 0.002 of notional
    # R = -0.002 / 0.02 = -0.1
    assert t["funding_R"] == pytest.approx(-0.1)
    assert t["R"] == pytest.approx(-0.1)


def test_short_receives_positive_funding(monkeypatch, tmp_path):
    (t,) = _build(monkeypatch, tmp_path, "short", 1.0)
    assert t["funding_R"] == pytest.approx(+0.1)
    assert t["R"] == pytest.approx(+0.1)


def test_funding_multiplier_scales(monkeypatch, tmp_path):
    (t,) = _build(monkeypatch, tmp_path, "long", 2.0)
    assert t["funding_R"] == pytest.approx(-0.2)


def test_mult_zero_leaves_R_unchanged_and_needs_no_funding_file(monkeypatch, tmp_path):
    monkeypatch.setattr(pb, "DataFeed", _FakeFeed)
    monkeypatch.setattr(pb, "detect_breakout",
                        lambda df, k=2: (df, [{"idx": 1, "side": "long", "regime": REGIME_UPTREND}]))
    monkeypatch.setattr(pb, "_atr", lambda df, period: np.full(df.height, 2.0))
    # cost 20bp -> R = -0.002 / 0.02 = -0.1, with no funding dir at all
    (t,) = pb.build_trades("4h", ["BTC"], 14, 1.0, 6.0, 3, 0.002,
                           funding_mult=0.0, funding_dir=tmp_path / "does_not_exist")
    assert t["R"] == pytest.approx(-0.1)
    assert t["funding_R"] == 0.0
    # default call (no funding args) is identical
    (t2,) = pb.build_trades("4h", ["BTC"], 14, 1.0, 6.0, 3, 0.002)
    assert t2["R"] == t["R"]


def test_conversion_helpers_explicit():
    # funding is a fraction of notional; R divides by stop distance (fraction of entry)
    assert pb.funding_return("long", 0.003) == pytest.approx(-0.003)
    assert pb.funding_return("short", 0.003) == pytest.approx(+0.003)
    assert pb.funding_return("long", -0.003) == pytest.approx(+0.003)   # negative rate: long receives
    assert pb.funding_to_R(-0.003, 0.015) == pytest.approx(-0.2)
    ts = np.array([_ms(T0 + dt.timedelta(hours=h)) for h in (0, 8, 16)], dtype=np.int64)
    rates = np.array([0.1, 0.2, 0.4])
    # (00:00, 16:00] -> picks 08:00 and 16:00
    assert pb.funding_rate_sum(ts, rates, T0, T0 + dt.timedelta(hours=16)) == pytest.approx(0.6)
