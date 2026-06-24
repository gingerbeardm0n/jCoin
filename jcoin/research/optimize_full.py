"""Full-range 5-parameter study with a per-year consistency lie-detector.

Per the decision to optimize on the entire history (justified by the very low param
count) — but with a guardrail: we rank on full-range MAR AND print the winner's per-year
breakdown. A config that only wins because of one big year (and is weak/negative in
others) is overfit, even on the full range. We trust a config that is good in MOST years
and beats the current defaults.

Tuned (all 5 edge params):
  k (swing), atr_period, atr_init, atr_trail, max_hold
Locked: symbols BTC+ETH, tf 4h, risk 1%, cost 12bp, caps 1/2.

Features depend only on (k, atr_period) -> computed once per pair and cached; the exit
params are swept cheaply on top. Keeps the whole 5-D grid fast.

Usage:
    python -m jcoin.research.optimize_full
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from jcoin.data.feed import DataFeed
from jcoin.engine.features import compute_features
from jcoin.engine.strategy import StrategyConfig  # for default reference
from jcoin.research.portfolio_backtest import metrics, run_portfolio

TF, LABELS = "4h", ["BTC", "ETH"]
COST_FRAC, RISK_FRAC = 0.0012, 0.01

K_GRID = [1, 2, 3]
ATRP_GRID = [10, 14, 20]
INIT_GRID = [0.5, 1.0, 1.5, 2.0]
TRAIL_GRID = [3.0, 4.0, 5.0, 6.0]
HOLD_GRID = [80, 120, 160]

DEFAULT = (2, 14, 1.0, 4.0, 120)  # current locked config (k, atrp, init, trail, hold)

_feat_cache: dict = {}


def _features(k, atrp):
    key = (k, atrp)
    if key in _feat_cache:
        return _feat_cache[key]
    feed = DataFeed()
    out = {}
    for label in LABELS:
        f = compute_features(feed.get_candles(label, TF), k=k, atr_period=atrp)
        out[label] = {
            "high": f["high"].to_numpy(), "low": f["low"].to_numpy(),
            "close": f["close"].to_numpy(), "atr": f["atr"].to_numpy(),
            "regime": f["regime"].to_numpy(),
            "bl": f["brk_long"].to_numpy(), "bs": f["brk_short"].to_numpy(),
            "ts": f["ts"].to_list(),
        }
    _feat_cache[key] = out
    return out


def _sim(feat, init, trail, max_hold):
    trades = []
    for label, d in feat.items():
        high, low, close, atr = d["high"], d["low"], d["close"], d["atr"]
        regime, bl, bs, ts = d["regime"], d["bl"], d["bs"], d["ts"]
        n = len(close)
        for i in range(n):
            if bl[i] and regime[i] == "uptrend":
                long = True
            elif bs[i] and regime[i] == "downtrend":
                long = False
            else:
                continue
            if i + 1 >= n or atr[i] <= 0:
                continue
            entry, a = close[i], atr[i]
            stop = entry - init * a if long else entry + init * a
            sd = abs(entry - stop) / entry
            if sd <= 0:
                continue
            best = high[i] if long else low[i]
            exit_price, exit_idx = None, min(i + max_hold, n - 1)
            for j in range(i + 1, min(i + 1 + max_hold, n)):
                if long:
                    if low[j] <= stop:
                        exit_price, exit_idx = stop, j; break
                    best = max(best, high[j]); stop = max(stop, best - trail * a)
                else:
                    if high[j] >= stop:
                        exit_price, exit_idx = stop, j; break
                    best = min(best, low[j]); stop = min(stop, best + trail * a)
            if exit_price is None:
                exit_price = close[exit_idx]
            gross = (exit_price - entry) / entry if long else (entry - exit_price) / entry
            trades.append({"symbol": label, "entry_time": ts[i], "exit_time": ts[exit_idx],
                           "side": "long" if long else "short", "R": (gross - COST_FRAC) / sd})
    return sorted(trades, key=lambda t: t["entry_time"])


def _port(trades, lo=None, hi=None):
    sub = trades if lo is None else [t for t in trades if lo <= t["entry_time"] < hi]
    if len(sub) < 12:
        return None
    curve, R = run_portfolio(sub, 10_000, RISK_FRAC, 1, 2)
    span = (sub[-1]["exit_time"] - sub[0]["entry_time"]).days / 365.25
    m = metrics(curve, R, 10_000, max(span, 0.5))
    m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else 0.0
    return m


def _per_year(trades):
    out = {}
    for yr in range(2021, 2027):
        lo = dt.datetime(yr, 1, 1, tzinfo=dt.timezone.utc)
        hi = dt.datetime(yr + 1, 1, 1, tzinfo=dt.timezone.utc)
        m = _port(trades, lo, hi)
        out[yr] = m["cagr"] * 100 if m else None
    return out


def main() -> int:
    print("FULL-RANGE 5-PARAM STUDY (rank on full-range MAR; per-year = lie detector)")
    print(f"tuning k x atr_period x atr_init x atr_trail x max_hold | locked: {LABELS} {TF} "
          f"risk={RISK_FRAC:.0%} cost=12bp\n")
    combos = []
    for k in K_GRID:
        for atrp in ATRP_GRID:
            feat = _features(k, atrp)
            for init in INIT_GRID:
                for trail in TRAIL_GRID:
                    for hold in HOLD_GRID:
                        m = _port(_sim(feat, init, trail, hold))
                        if m:
                            combos.append(((k, atrp, init, trail, hold), m))
    # rank by full-range MAR
    combos.sort(key=lambda c: c[1]["mar"], reverse=True)

    print(f"Tested {len(combos)} configs. Top 8 by full-range MAR (CAGR/MaxDD):")
    print(f"{'k':>2} {'atrp':>4} {'init':>4} {'trail':>5} {'hold':>4} | {'CAGR':>6} {'maxDD':>6} {'MAR':>5} {'PF':>5} {'Shrp':>5} {'n':>4}")
    for cfg, m in combos[:8]:
        print(f"{cfg[0]:>2} {cfg[1]:>4} {cfg[2]:>4} {cfg[3]:>5} {cfg[4]:>4} | "
              f"{m['cagr']*100:>5.0f}% {m['max_dd']*100:>5.0f}% {m['mar']:>5.2f} {m['pf']:>5.2f} "
              f"{m['sharpe']:>5.2f} {m['n_trades']:>4}")

    best_cfg, best_m = combos[0]
    print(f"\nBEST config: k={best_cfg[0]} atr_period={best_cfg[1]} atr_init={best_cfg[2]} "
          f"atr_trail={best_cfg[3]} max_hold={best_cfg[4]}")

    # per-year lie detector: winner vs current default
    def py_line(name, cfg):
        feat = _features(cfg[0], cfg[1])
        trades = _sim(feat, cfg[2], cfg[3], cfg[4])
        py = _per_year(trades)
        cells = " ".join(f"{py[y]:>6.0f}%" if py[y] is not None else f"{'-':>7}" for y in range(2021, 2027))
        full = _port(trades)
        print(f"{name:<16} | full CAGR {full['cagr']*100:>4.0f}% MAR {full['mar']:.2f} | yrs: {cells}")

    print("\n=== PER-YEAR CONSISTENCY (the lie detector) — CAGR by year ===")
    print(f"{'config':<16} | {'full-range':>22} | 2021   2022   2023   2024   2025   2026")
    py_line("BEST", best_cfg)
    py_line("DEFAULT(2,14,1,4)", DEFAULT)

    print("\nADOPT only if BEST beats DEFAULT on full-range AND is positive in most years\n"
          "(not carried by one). A marginal or one-year-driven win => keep DEFAULT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
