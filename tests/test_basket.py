"""Tests for strategy B (daily basket trend). Synthetic data, no network."""

from __future__ import annotations

import numpy as np

from jcoin.research import basket_trend_backtest as bt


def make_panel(closes: dict[str, np.ndarray], qvols: dict[str, np.ndarray] | None = None,
               opens: dict[str, np.ndarray] | None = None) -> bt.Panel:
    syms = list(closes)
    T = len(next(iter(closes.values())))
    dates = np.array([np.datetime64("2022-01-01") + np.timedelta64(i, "D") for i in range(T)])
    close = np.column_stack([closes[s] for s in syms]).astype(float)
    open_ = np.column_stack([(opens or closes)[s] for s in syms]).astype(float)
    if qvols is None:
        qv = np.where(np.isnan(close), np.nan, 1000.0)
    else:
        qv = np.column_stack([qvols[s] for s in syms]).astype(float)
    return bt.Panel(dates, syms, open_, close, qv)


def test_universe_uses_only_bars_before_rebalance_date():
    T, i = 300, 200
    flat = np.full(T, 100.0)
    vol = {"AAAUSDT": np.full(T, 1000.0), "BBBUSDT": np.full(T, 900.0),
           "CCCUSDT": np.full(T, 10.0), "DDDUSDT": np.full(T, 800.0)}
    vol["CCCUSDT"][i] = 1e12                                   # huge spike ON the rebalance date
    panel = make_panel({s: flat.copy() for s in vol}, vol)
    uni = [panel.symbols[j] for j in bt.select_universe(panel, i, top_n=2)]
    assert uni == ["AAAUSDT", "BBBUSDT"]
    assert "CCCUSDT" not in uni
    # the day after, the spike is history and the coin ranks first
    uni2 = [panel.symbols[j] for j in bt.select_universe(panel, i + 1, top_n=2)]
    assert uni2[0] == "CCCUSDT"


def test_universe_requires_history_and_excludes_stables():
    T, i = 300, 150
    flat = np.full(T, 100.0)
    young = flat.copy()
    young[:100] = np.nan                                       # only 50 bars before i=150
    closes = {"AAAUSDT": flat.copy(), "NEWUSDT": young, "USDCUSDT": flat.copy()}
    vol = {s: np.where(np.isnan(c), np.nan, 1000.0) for s, c in closes.items()}
    vol["NEWUSDT"] = np.where(np.isnan(young), np.nan, 5e6)
    vol["USDCUSDT"] = np.full(T, 9e9)
    panel = make_panel(closes, vol)
    uni = [panel.symbols[j] for j in bt.select_universe(panel, i, top_n=5)]
    assert uni == ["AAAUSDT"]


def test_signal_uses_closes_before_rebalance_date_only():
    T, i = 250, 200
    rng = np.random.default_rng(0)
    c1 = 100 * np.exp(np.cumsum(rng.normal(0.002, 0.02, T)))
    c2 = c1.copy()
    c2[i:] = c2[i - 1] * 0.01                                  # crash from day i on
    fast1, slow1 = bt.ema_matrix(c1[:, None], 20), bt.ema_matrix(c1[:, None], 100)
    fast2, slow2 = bt.ema_matrix(c2[:, None], 20), bt.ema_matrix(c2[:, None], 100)
    assert bt.long_signal(fast1, slow1, i)[0] == bt.long_signal(fast2, slow2, i)[0]
    # sanity: changing close[i-1] CAN change the signal (the signal is not constant)
    c3 = c1.copy()
    c3[i - 1] = c3[i - 1] * 1e-6
    f3, s3 = bt.ema_matrix(c3[:, None], 20), bt.ema_matrix(c3[:, None], 100)
    assert f3[i - 1, 0] != fast1[i - 1, 0]


def test_delisted_coin_exited_at_last_close():
    T, start = 260, 120
    last = 150
    x = 100 * 1.01 ** np.arange(T)                             # steady uptrend -> long
    x[last + 1:] = np.nan                                      # delisted after day `last`
    panel = make_panel({"XXXUSDT": x})
    cfg = bt.Config("t", ema=(5, 20), weighting="slot", top_n=1, cost_rate=0.0, min_history=100)
    res = bt.simulate(panel, cfg, start, T)
    exits = [e for e in res.log if "delist_exit" in e]
    assert len(exits) == 1
    assert exits[0]["delist_exit"] == "XXXUSDT"
    assert exits[0]["i"] == last
    assert exits[0]["price"] == x[last]
    # after exit the book is all cash and equity is flat at the exit value
    k = last - start
    assert res.n_held[k] == 0
    assert np.allclose(res.equity[k:], res.equity[k])
    assert np.isclose(res.equity[k], res.equity[k - 1] * x[last] / x[last - 1], rtol=1e-9)


def test_cost_is_half_percent_of_traded_notional():
    T, start = 60, 10
    flat = np.full(T, 100.0)
    # single-coin buy-and-hold on flat prices: one buy, equity falls by exactly the cost
    panel = make_panel({"BTCUSDT": flat.copy()})
    cfg = bt.Config("bh", ema=None, fixed_symbols=("BTCUSDT",), cost_rate=0.005)
    res = bt.simulate(panel, cfg, start, T)
    assert np.isclose(res.costs[0], 0.005 * res.traded[0])
    assert np.isclose(res.traded[0], 1 / 1.005)               # notional such that notional+cost = 1
    assert np.isclose(res.equity[0], 1 - res.costs[0])

    # hand-built 2-coin trim: B doubles before the 2nd rebalance (day 14)
    a = np.full(T, 100.0)
    b = np.full(T, 100.0)
    b[start + 1:] = 200.0
    panel2 = make_panel({"AAAUSDT": a, "BBBUSDT": b})
    cfg2 = bt.Config("ew", ema=None, weighting="slot", top_n=2, cost_rate=0.005, min_history=5)
    res2 = bt.simulate(panel2, cfg2, start, T)
    e = 1 / 1.005
    first, second = [r for r in res2.log if "traded" in r][:2]
    assert np.isclose(first["traded"], e)
    assert np.isclose(first["cost"], 0.005 * e)
    # day 14: A worth 0.5e, B worth e. A is topped up by 0.5*e2-0.5e, B trimmed by e-0.5*e2 -> total 0.5e
    assert np.isclose(second["traded"], 0.5 * e)
    assert np.isclose(second["cost"], 0.005 * 0.5 * e)
    assert np.isclose(res2.costs[14], 0.005 * res2.traded[14])
