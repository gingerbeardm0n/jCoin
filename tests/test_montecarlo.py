import numpy as np
import pytest

from jcoin.research import montecarlo as mc


def _R():
    rng = np.random.default_rng(7)
    return rng.normal(0.2, 1.5, size=200)


def test_fixed_seed_reproduces_identical_percentiles():
    a = mc.summarize(_R(), n_paths=2000, trades_per_path=60, seed=123)
    b = mc.summarize(_R(), n_paths=2000, trades_per_path=60, seed=123)
    assert a == b
    c = mc.summarize(_R(), n_paths=2000, trades_per_path=60, seed=124)
    assert c["max_dd"] != a["max_dd"]


def test_all_losses_streak_equals_trades_per_path():
    T = 37
    s = mc.summarize(np.full(50, -1.0), n_paths=500, trades_per_path=T)
    assert all(v == T for v in s["streak"].values())
    # every path is the same: T consecutive -1R trades at 1% risk
    expected_dd = 1 - (1 - 0.01) ** T
    assert all(v == pytest.approx(expected_dd) for v in s["max_dd"].values())


def test_all_wins_have_no_streak_and_no_drawdown():
    s = mc.summarize(np.full(50, 2.0), n_paths=200, trades_per_path=30)
    assert all(v == 0 for v in s["streak"].values())
    assert all(v == 0 for v in s["max_dd"].values())
