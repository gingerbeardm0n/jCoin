"""Cross-sectional momentum / rotation backtest — a fourth strategy FAMILY.

Different edge source than breakout (which trends ONE coin against ITS OWN history): this
bets on RELATIVE STRENGTH between coins — rank the universe by trailing return, go long the
strongest, short the weakest, dollar-neutral. Institutional cross-sectional momentum
(Jegadeesh-Titman lineage) is a decades-old, well-documented edge in equities; this tests
whether it holds in this coin universe, using candle data already cached on disk (no new
data plumbing needed).

Mechanics:
  - Universe: breadth_study.UNIVERSE (17 liquid coins, full 2021-2026 4h history already
    fetched by an earlier study).
  - Every REBAL_BARS (~7 days): rank coins by trailing LOOKBACK_BARS (~30 days) return.
  - Long top-K, short bottom-K, equal-weight each leg, dollar-neutral (half capital per side).
  - Hold to next rebalance; portfolio period return = avg(long leg fwd return) minus
    avg(short leg fwd return), scaled by 0.5 (half capital per leg), minus a round-trip cost
    charged on ALL 2*K legs every rebalance.
  - CAVEAT (honest, not modeled): the cost model is conservative — it re-charges the full
    round-trip on every leg each period, even when a coin stays in the same bucket and a
    real implementation wouldn't need to re-trade it. Overstates cost, not understates.
  - Same 3-way train/valid/TEST split discipline as the other sealed screens, but the gate
    metric here is Sharpe + CAGR on the equity curve (no discrete "trades" — this is a
    continuously rebalanced book, not a trade-list strategy).

Usage:
    python -m jcoin.research.cross_sectional_momentum_backtest
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from jcoin.research.breadth_study import UNIVERSE, _fetch_4h

REBAL_BARS = 42        # ~7 days at 4h
LOOKBACK_BARS = 180    # ~30 days trailing return for ranking
TOP_K = 3
COST_FRAC = 0.0012     # 12bp round-trip per leg (matches breakout convention)

UTC = dt.timezone.utc
SPLITS = [
    ("train(21-23)",  dt.datetime(2021, 1, 1, tzinfo=UTC), dt.datetime(2023, 7, 1, tzinfo=UTC)),
    ("valid(23-25)",  dt.datetime(2023, 7, 1, tzinfo=UTC), dt.datetime(2025, 1, 1, tzinfo=UTC)),
    ("TEST(25-26)*",  dt.datetime(2025, 1, 1, tzinfo=UTC), dt.datetime(2027, 1, 1, tzinfo=UTC)),
]
GATE_SHARPE, GATE_CAGR = 0.5, 0.10


def _load_universe() -> dict[str, pl.DataFrame]:
    out = {}
    for sym in UNIVERSE:
        label = sym.replace("USDT", "")
        out[label] = _fetch_4h(sym, label).select(["ts", "close"])
    return out


def _build_aligned_matrix(data: dict[str, pl.DataFrame]):
    """Inner-join all coins on ts. Returns (ts_list[int64 ms], close_matrix[n_bars,n_coins], labels)."""
    labels = list(data.keys())
    dfs = [data[l].rename({"close": l}) for l in labels]
    merged = dfs[0]
    for d in dfs[1:]:
        merged = merged.join(d, on="ts", how="inner")
    merged = merged.sort("ts")
    ts = merged["ts"].to_list()
    mat = merged.select(labels).to_numpy()
    return ts, mat, labels


def _run_rotation(ts, mat, lo_ms, hi_ms):
    idx = [i for i, t in enumerate(ts) if lo_ms <= t < hi_ms]
    if len(idx) < LOOKBACK_BARS + REBAL_BARS * 4:
        return None
    lo_i, hi_i = idx[0], idx[-1]
    equity = 1.0
    curve = [equity]
    rebal_points = list(range(lo_i + LOOKBACK_BARS, hi_i - REBAL_BARS, REBAL_BARS))
    for t in rebal_points:
        lookback_ret = mat[t] / mat[t - LOOKBACK_BARS] - 1.0
        order = np.argsort(lookback_ret)
        bottom = order[:TOP_K]
        top = order[-TOP_K:]
        fwd_ret = mat[t + REBAL_BARS] / mat[t] - 1.0
        long_ret = fwd_ret[top].mean()
        short_ret = fwd_ret[bottom].mean()
        period_ret = (long_ret - short_ret) / 2.0 - COST_FRAC * 2  # half capital/leg; cost on all 2K legs
        equity *= (1 + period_ret)
        curve.append(equity)
    n_periods = len(rebal_points)
    if n_periods < 8:
        return None
    span_years = (ts[hi_i] - ts[lo_i]) / 1000 / 86400 / 365.25
    eq = np.array(curve)
    total_ret = eq[-1] / eq[0] - 1
    cagr = (eq[-1] / eq[0]) ** (1 / max(span_years, 0.25)) - 1
    peak = np.maximum.accumulate(eq)
    max_dd = float(np.max((peak - eq) / peak)) if len(eq) > 1 else 0.0
    period_rets = eq[1:] / eq[:-1] - 1
    periods_per_year = n_periods / max(span_years, 0.25)
    sharpe = float(period_rets.mean() / period_rets.std() * np.sqrt(periods_per_year)) if period_rets.std() > 0 else 0.0
    return {"n": n_periods, "total_ret": total_ret, "cagr": cagr, "max_dd": max_dd, "sharpe": sharpe}


def main() -> int:
    print(f"CROSS-SECTIONAL MOMENTUM/ROTATION | long top-{TOP_K} / short bottom-{TOP_K}, "
          f"dollar-neutral | rebal={REBAL_BARS}bars(~7d) lookback={LOOKBACK_BARS}bars(~30d) "
          f"cost={COST_FRAC*1e4:.0f}bp/leg | gate: TEST Sharpe>={GATE_SHARPE} AND CAGR>={GATE_CAGR:.0%}\n")

    data = _load_universe()
    ts, mat, labels = _build_aligned_matrix(data)
    print(f"universe ({len(labels)}): {labels}\naligned bars: {len(ts)}\n")

    print(f"{'split':<14} {'n':>4} {'CAGR':>7} {'maxDD':>7} {'Sharpe':>7} {'total%':>8}")
    print("-" * 55)
    test_m = None
    for sname, lo, hi in SPLITS:
        lo_ms, hi_ms = int(lo.timestamp() * 1000), int(hi.timestamp() * 1000)
        m = _run_rotation(ts, mat, lo_ms, hi_ms)
        if m:
            if "TEST" in sname:
                test_m = m
            flag = ""
            if "TEST" in sname:
                ok = m["sharpe"] >= GATE_SHARPE and m["cagr"] >= GATE_CAGR
                flag = "  PASS" if ok else "  FAIL"
            print(f"{sname:<14} {m['n']:>4} {m['cagr']*100:>6.1f}% {m['max_dd']*100:>6.1f}% "
                  f"{m['sharpe']:>7.2f} {m['total_ret']*100:>7.0f}%{flag}")
        else:
            print(f"{sname:<14}  (insufficient data)")

    print("\n" + "=" * 55)
    if test_m:
        ok = test_m["sharpe"] >= GATE_SHARPE and test_m["cagr"] >= GATE_CAGR
        print(f"GATE: TEST Sharpe>={GATE_SHARPE} AND CAGR>={GATE_CAGR:.0%} -> {'PASS' if ok else 'FAIL'}")
    else:
        print("GATE: insufficient TEST data")
    print("\nCost model is conservative (re-charges full round-trip every rebalance on all\n"
          "2*K legs, even for coins that stay in the same bucket) — see module docstring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
