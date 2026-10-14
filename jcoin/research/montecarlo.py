"""Monte Carlo of a strategy's per-trade R values -> drawdown / losing-streak envelopes.

Bootstrap (with replacement, fixed seed) a strategy's realized per-trade R values into
many synthetic one-year paths, compound each at a fixed risk fraction per trade, and
read off the distribution of the worst drawdown and the longest losing streak. The 99th
percentiles become the kill-rule thresholds (KILL_RULE.md).

Honest limits: resampling trades i.i.d. destroys serial correlation and regime
clustering (losses really do bunch up in chop), so real drawdowns/streaks can be worse
than this envelope. It is a floor on "how bad can ordinary bad luck look", not a ceiling.

Usage:
    python -m jcoin.research.montecarlo          # A, dev period, funding_mult 1
"""

from __future__ import annotations

import numpy as np

SEED = 20261014
N_PATHS = 10_000
PCTS = (50, 90, 95, 99)


def simulate_paths(R, n_paths=N_PATHS, trades_per_path=73, risk_frac=0.01,
                   start_equity=1.0, seed=SEED):
    """Bootstrap `n_paths` paths of `trades_per_path` trades from R.

    Returns (max_dd, longest_streak): arrays of length n_paths.
      max_dd         peak-to-trough fraction of the compounded equity path (0.3 = 30%)
      longest_streak longest run of consecutive losing trades (R <= 0)
    Equity compounds as eq *= (1 + risk_frac * R), floored at 0 (ruin).
    """
    R = np.asarray(R, dtype=float)
    if R.size == 0:
        raise ValueError("no R values to bootstrap")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, R.size, size=(n_paths, trades_per_path))
    r = R[idx]

    growth = np.maximum(1.0 + risk_frac * r, 0.0)
    eq = start_equity * np.cumprod(growth, axis=1)
    eq = np.concatenate([np.full((n_paths, 1), start_equity), eq], axis=1)
    peak = np.maximum.accumulate(eq, axis=1)
    max_dd = np.max((peak - eq) / peak, axis=1)

    loss = r <= 0
    cur = np.zeros(n_paths, dtype=int)
    best = np.zeros(n_paths, dtype=int)
    for j in range(trades_per_path):
        cur = (cur + 1) * loss[:, j]
        best = np.maximum(best, cur)
    return max_dd, best


def summarize(R, n_paths=N_PATHS, trades_per_path=73, risk_frac=0.01, seed=SEED):
    """Percentiles (50/90/95/99) of max drawdown and longest losing streak."""
    dd, streak = simulate_paths(R, n_paths, trades_per_path, risk_frac, seed=seed)
    return {
        "n_paths": n_paths, "trades_per_path": trades_per_path, "risk_frac": risk_frac,
        "seed": seed, "n_source_trades": int(np.asarray(R).size),
        "max_dd": {p: float(np.percentile(dd, p)) for p in PCTS},
        # "higher": streak thresholds are whole trades, round the percentile up (conservative)
        "streak": {p: int(np.percentile(streak, p, method="higher")) for p in PCTS},
    }


def main(argv=None) -> int:
    from jcoin.research.phase1_honest_a import dev_trades_A, taken_dev_R

    trades, years = dev_trades_A(1.0)
    R = taken_dev_R(trades)
    per_year = int(round(len(R) / years))
    s = summarize(R, trades_per_path=per_year)
    print(f"MC | {s['n_source_trades']} dev trades | {per_year} trades/path | "
          f"{s['n_paths']:,} paths | risk {s['risk_frac']:.1%} | seed {s['seed']}")
    for p in PCTS:
        print(f"  p{p}: maxDD {s['max_dd'][p]*100:5.1f}%   longest losing streak {s['streak'][p]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
