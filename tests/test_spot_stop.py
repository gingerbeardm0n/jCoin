"""A_SR harness regression: with ref == fill and no disaster stop it must equal A (intrabar)."""

import datetime as dt

import numpy as np
import polars as pl

from jcoin.research.close_stop_test import trades
from jcoin.research.spot_stop_test import ref_trades


def _frame(seed, n=3000):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n) + 0.0004 * np.sin(np.arange(n) / 150)))
    open_ = np.r_[close[0], close[:-1]]
    spread = np.abs(rng.normal(0, 0.01, n)) * close
    ts = [dt.datetime(2021, 1, 1, tzinfo=dt.timezone.utc) + dt.timedelta(hours=4 * i) for i in range(n)]
    return pl.DataFrame({"ts": ts, "open": open_, "high": np.maximum(open_, close) + spread,
                         "low": np.minimum(open_, close) - spread, "close": close, "volume": np.ones(n)})


def test_ref_equals_fill_reproduces_intrabar_A():
    frames = {"BTC": _frame(1), "ETH": _frame(2)}
    a = trades("intrabar", 0.0, frames)
    b = ref_trades(frames, frames, disaster_atr=None)
    assert len(a) > 20
    key = lambda t: (t["symbol"], t["entry_time"], t["side"])
    ra = {key(t): (t["exit_time"], round(t["R"], 9)) for t in a}
    rb = {key(t): (t["exit_time"], round(t["R"], 9)) for t in b}
    assert ra == rb


def test_disaster_stop_fires_on_fill_spike():
    ref = {"BTC": _frame(3)}
    spiky = ref["BTC"].with_columns(low=pl.col("low") * 0.5, high=pl.col("high") * 1.5)
    out = ref_trades(ref, {"BTC": spiky})
    assert out and all(t["exit_kind"] == "disaster" for t in out)
