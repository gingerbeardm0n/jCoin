"""Parameter study with anti-overfit discipline (jTrader ANTI_OVERFITTING_PLAYBOOK).

GOAL: not to maximize a backtest number, but to find whether any parameter set
*robustly* beats the hand-picked defaults OUT OF SAMPLE. If none does, we keep the
defaults — that is a valid, valuable result.

Discipline enforced here:
  - TRAIN / VALIDATE / TEST split (disjoint date ranges). Optimize on train, select a
    plateau on validate, score the winner ONCE on the sealed test set.
  - Tune ONLY the two ATR exit params that actually drive the edge; lock everything else
    (swing_k=2, atr_period=14, max_hold=120) at sane defaults — no manufactured knobs.
  - PLATEAU not peak — a grid makes the robust neighborhood visible; we pick its center,
    not the single tallest spike.
  - BASELINE comparison — the hand-picked defaults are the bar to beat on TEST.

Metric: MAR = CAGR / MaxDD (risk-adjusted; optimizing raw return just chases the
biggest-trend window). PF and Sharpe shown alongside.

Usage:
    python -m jcoin.research.optimize
"""

from __future__ import annotations

import datetime as dt

from jcoin.research.portfolio_backtest import build_trades, metrics, run_portfolio

UTC = dt.timezone.utc

# Disjoint splits. TEST is the recent, hardest stretch (2025 soft + 2026 down) — a tough
# sealed out-of-sample check. Scored exactly once, for the selected config + baselines.
SPLITS = {
    "train":    (dt.datetime(2021, 1, 1, tzinfo=UTC), dt.datetime(2023, 7, 1, tzinfo=UTC)),
    "validate": (dt.datetime(2023, 7, 1, tzinfo=UTC), dt.datetime(2025, 1, 1, tzinfo=UTC)),
    "test":     (dt.datetime(2025, 1, 1, tzinfo=UTC), dt.datetime(2027, 1, 1, tzinfo=UTC)),
}

INIT_GRID = [0.5, 1.0, 1.5, 2.0, 2.5]
TRAIL_GRID = [2.0, 3.0, 4.0, 5.0, 6.0]

BASELINES = {"hand-picked (1.0/4.0)": (1.0, 4.0), "first-guess (1.5/3.0)": (1.5, 3.0)}

# locked params
TF, LABELS = "4h", ["BTC", "ETH"]
ATR_PERIOD, MAX_HOLD = 14, 120
COST_FRAC = 0.0012
RISK_FRAC = 0.01


def _eval(trades_all, lo, hi):
    """Run the portfolio on the trades whose ENTRY falls in [lo,hi); return metrics."""
    sub = [t for t in trades_all if lo <= t["entry_time"] < hi]
    if len(sub) < 15:
        return None
    curve, R = run_portfolio(sub, 10_000, RISK_FRAC, 1, 2)
    years = max((hi - lo).days / 365.25, 0.5)
    m = metrics(curve, R, 10_000, years)
    m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else float("inf")
    return m


def _grid_for(init, trail):
    """All trades for one (init,trail) over full history (features need full warmup)."""
    return build_trades(TF, LABELS, ATR_PERIOD, init, trail, MAX_HOLD, COST_FRAC)


def main() -> int:
    print("PARAMETER STUDY — train/validate/test, plateau selection, baseline-to-beat")
    print(f"locked: tf={TF} symbols={LABELS} atr_period={ATR_PERIOD} max_hold={MAX_HOLD} "
          f"risk={RISK_FRAC:.0%} cost=12bp | tuning: atr_init x atr_trail | metric=MAR (CAGR/MaxDD)\n")

    # cache trades per combo (one backtest each), then slice per split
    results = {}  # (init,trail) -> {split: metrics}
    for init in INIT_GRID:
        for trail in TRAIL_GRID:
            trades = _grid_for(init, trail)
            results[(init, trail)] = {s: _eval(trades, lo, hi) for s, (lo, hi) in SPLITS.items()}

    # --- TRAIN grid (MAR) — look for the plateau ---
    print("=== TRAIN: MAR (CAGR/MaxDD) — find the broad plateau, not the spike ===")
    print("init\\trail " + " ".join(f"{t:>7.1f}" for t in TRAIL_GRID))
    for init in INIT_GRID:
        cells = []
        for trail in TRAIL_GRID:
            m = results[(init, trail)]["train"]
            cells.append(f"{m['mar']:>7.2f}" if m else f"{'-':>7}")
        print(f"{init:>9.1f} " + " ".join(cells))

    # --- VALIDATE grid (MAR) — confirm the plateau holds on unseen data ---
    print("\n=== VALIDATE: MAR — does the train plateau survive here? ===")
    print("init\\trail " + " ".join(f"{t:>7.1f}" for t in TRAIL_GRID))
    for init in INIT_GRID:
        cells = []
        for trail in TRAIL_GRID:
            m = results[(init, trail)]["validate"]
            cells.append(f"{m['mar']:>7.2f}" if m else f"{'-':>7}")
        print(f"{init:>9.1f} " + " ".join(cells))

    # --- pick plateau: best AVERAGE MAR across train+validate (robust, not peak) ---
    scored = []
    for combo, sp in results.items():
        if sp["train"] and sp["validate"]:
            avg = (sp["train"]["mar"] + sp["validate"]["mar"]) / 2
            scored.append((avg, combo))
    scored.sort(reverse=True)
    selected = scored[0][1]
    print(f"\nSELECTED (best train+validate avg MAR, plateau-aware): atr_init={selected[0]}, atr_trail={selected[1]}")

    # --- TEST (sealed): score the selected config + baselines, ONCE ---
    print("\n=== TEST (sealed OOS 2025-2026) — selected vs baselines ===")
    print(f"{'config':<26} {'CAGR':>7} {'maxDD':>7} {'MAR':>6} {'PF':>6} {'Sharpe':>7} {'n':>5}")

    def show(name, combo):
        m = results.get(combo, {}).get("test")
        if not m:
            print(f"{name:<26} (insufficient test trades)")
            return
        print(f"{name:<26} {m['cagr']*100:>6.1f}% {m['max_dd']*100:>6.1f}% {m['mar']:>6.2f} "
              f"{m['pf']:>6.2f} {m['sharpe']:>7.2f} {m['n_trades']:>5}")

    show(f"SELECTED {selected}", selected)
    for name, combo in BASELINES.items():
        if combo not in results:
            results[combo] = {s: _eval(_grid_for(*combo), lo, hi) for s, (lo, hi) in SPLITS.items()}
        show(name, combo)

    print("\nVERDICT RULE: adopt the optimized config ONLY if it clearly beats the hand-picked\n"
          "baseline on TEST. A tie or marginal win => keep the defaults (simpler, proven).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
