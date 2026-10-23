"""Parity ledger flags paper trades the tested harness can't reproduce."""

import datetime as dt

from jcoin.research import parity_ledger as pl_
from jcoin.research.close_stop_test import trades as harness_trades
from tests.test_spot_stop import _frame


def _paper(t, R=None, shift=dt.timedelta(0)):
    return {"symbol": t["symbol"], "side": t["side"],
            "entry_time": (t["entry_time"] + shift).isoformat(), "R": t["R"] if R is None else R}


def test_matching_trades_pass_and_mismatches_flag():
    spot = {"BTC": _frame(11), "ETH": _frame(12)}
    nano = {k: v for k, v in spot.items()}
    a = harness_trades("intrabar", 0.0, nano)[:5]
    rows, flags = pl_.build([_paper(t) for t in a], [], spot, nano)
    assert flags == 0 and all(r[7] == "ok" for r in rows)

    bad = [_paper(a[0], R=a[0]["R"] + 1.0), {**_paper(a[1]), "side": "short" if a[1]["side"] == "long" else "long"}]
    rows, flags = pl_.build(bad, [], spot, nano)
    assert flags == 2


def test_sr_trades_matched_one_bar_later():
    spot = {"BTC": _frame(13), "ETH": _frame(14)}
    nano = spot
    from jcoin.research.spot_stop_test import ref_trades
    sr = ref_trades(spot, nano)[:3]
    rows, flags = pl_.build([], [_paper(t, shift=pl_.H4) for t in sr], spot, nano)
    assert flags == 0 and len(rows) == 3
