"""Canonical A numbers from the code that actually trades (AUDIT_2026-10-23 W2, item 7).

Runs jcoin.engine.TradingEngine (the paper/live engine) over the dev period and peels
the differences from the research harness one at a time:
  1. harness (portfolio_backtest)        -- the numbers every decision so far used
  2. engine, no notional cap             -- should match the harness closely
  3. engine as live: notional cap 1x equity
  4. engine as live + cycle filter       -- what paper A actually runs (0.75x risk in bear)
  5. #4 at $1,000 with whole nano contracts (BTC 0.01, ETH 0.1)
All at 12bp, funding 0x (the engine backtest has no funding feed; the harness 1x row
shows the funding drag). Then the kill-rule Monte Carlo is re-run on #4's trades for
comparison with KILL_RULE.md (39.8% / 33). Report only: nothing here changes the rule.

Usage:
    python -m jcoin.research.engine_numbers
Writes pipeline/A_ENGINE_NUMBERS_2026-10.md
"""

from __future__ import annotations

import sys

import polars as pl

from jcoin.data.config import CONTRACT_SIZES, ROOT
from jcoin.data.feed import DataFeed
from jcoin.engine.broker import BacktestBroker
from jcoin.engine.engine import TradingEngine
from jcoin.engine.features import compute_features
from jcoin.engine.risk import RiskConfig
from jcoin.engine.strategy import BreakoutStrategy, StrategyConfig
from jcoin.research import splits
from jcoin.research.montecarlo import summarize
from jcoin.research.phase1_honest_a import (
    ATR_INIT, ATR_PERIOD, ATR_TRAIL, COST_FRAC, LABELS, MAX_HOLD, TF, _END, dev_trades_A, evaluate,
    taken_dev_R,
)
from jcoin.research.portfolio_backtest import metrics
from jcoin.strategy.cycle import CYCLE_BEAR, add_cycle_filter

REPORT_PATH = ROOT / "pipeline" / "A_ENGINE_NUMBERS_2026-10.md"
_COLS = ["symbol", "ts", "open", "high", "low", "close", "volume",
         "regime", "atr", "brk_long", "brk_short", "conf_sh", "conf_sl"]


def _rows_and_cycle():
    feed = DataFeed()
    by_ts: dict = {}
    cycle = {}
    for label in LABELS:
        candles = feed.get_candles(label, TF, end=_END)
        df = compute_features(candles, k=2, atr_period=ATR_PERIOD).with_columns(symbol=pl.lit(label))
        for row in df.select(_COLS).iter_rows(named=True):
            by_ts.setdefault(row["ts"], {})[label] = row
        if label == "BTC":
            c = add_cycle_filter(candles.sort("ts"))
            cycle = dict(zip(c["ts"].to_list(), c["cycle_phase"].to_list()))
    return by_ts, cycle


def run_engine(by_ts, cycle, lo, hi, *, cap=True, cycle_filter=False, start_equity=10_000.0, lots=None):
    base = RiskConfig(0.01, 1, 2, max_notional_frac=1.0 if cap else 0.0, lot_sizes=lots)
    bear = RiskConfig(0.0075, 1, 2, max_notional_frac=base.max_notional_frac, lot_sizes=lots)
    eng = TradingEngine(strategy=BreakoutStrategy(StrategyConfig(ATR_INIT, ATR_TRAIL, MAX_HOLD)),
                        broker=BacktestBroker(COST_FRAC), risk=base, start_equity=start_equity)
    for ts in sorted(t for t in by_ts if t <= hi):
        if cycle_filter:
            eng.risk = bear if cycle.get(ts) == CYCLE_BEAR else base
        eng.step(ts, by_ts[ts], allow_entries=ts >= lo)
    a = eng.account
    closed = [t for t in a.closed if lo <= t.entry_time < hi]
    curve = [(lo, start_equity)] + [(t, e) for t, e in a.equity_curve if lo <= t <= hi]
    years = (hi - lo).days / 365.25
    m = metrics(curve, [t.R for t in closed], start_equity, years)
    m["mar"] = m["cagr"] / m["max_dd"] if m["max_dd"] > 0 else float("nan")
    m["avg_R"] = sum(t.R for t in closed) / len(closed)
    return m, closed


def _row(name, m):
    return (f"| {name} | {m['cagr']:.1%} | {m['max_dd']:.1%} | {m['mar']:.2f} | {m['sharpe']:.2f} | "
            f"{m['pf']:.2f} | {m['n_trades']} | {m['avg_R']:+.3f} | {m['win_pct']:.1f}% |")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    lo, hi = splits.dev_window()
    splits.check_window(lo, hi)
    by_ts, cycle = _rows_and_cycle()

    h0, _ = dev_trades_A(0.0)
    h1, _ = dev_trades_A(1.0)
    rows = {
        "1. Harness (decision numbers), 0x funding": evaluate(h0, lo, hi),
        "1b. Harness, 1x funding (reference)": evaluate(h1, lo, hi),
    }
    for m in rows.values():
        m["avg_R"] = m.get("avg_R", float("nan"))
    variants = {
        "2. Engine, no notional cap": dict(cap=False),
        "3. Engine as live (cap 1x equity)": dict(cap=True),
        "4. Engine as live + cycle filter (= paper A)": dict(cap=True, cycle_filter=True),
        "5. #4 at $1,000, whole nano contracts": dict(cap=True, cycle_filter=True, start_equity=1000.0,
                                                     lots=dict(CONTRACT_SIZES)),
    }
    closed4 = None
    for name, kw in variants.items():
        m, closed = run_engine(by_ts, cycle, lo, hi, **kw)
        rows[name] = m
        if name.startswith("4."):
            closed4 = closed

    years = (hi - lo).days / 365.25
    R4 = [t.R for t in closed4]
    per_year = int(round(len(R4) / years))
    mc4 = summarize(R4, trades_per_path=per_year)
    mc_h = summarize(taken_dev_R(h1), trades_per_path=73)

    hdr = ["| Run | CAGR | Max DD | MAR | Sharpe | PF | Trades | avg R | Win % |",
           "|---|---|---|---|---|---|---|---|---|"]
    out = ["# A: canonical numbers from the trading engine", "",
           "Dev period 2021-01-01 → 2026-05-31, Binance 4h prices, 12bp round trip. Funding 0x unless noted",
           "(the engine backtest has no funding feed; compare row 1 vs 1b for the funding drag).",
           "Generated by `jcoin/research/engine_numbers.py`. Report only: no rule changes here.", ""] + hdr
    out += [_row(k, v) for k, v in rows.items()]
    out += ["", "## Kill-rule Monte Carlo on the engine's trades (report only)", "",
            "| Source | Trades/yr | p95 max DD | p99 max DD | p95 streak | p99 streak |", "|---|---|---|---|---|---|",
            f"| Harness, 1x funding (KILL_RULE.md basis) | 73 | {mc_h['max_dd'][95]:.1%} | {mc_h['max_dd'][99]:.1%} | "
            f"{mc_h['streak'][95]} | {mc_h['streak'][99]} |",
            f"| Engine as live + cycle (row 4), 0x funding | {per_year} | {mc4['max_dd'][95]:.1%} | "
            f"{mc4['max_dd'][99]:.1%} | {mc4['streak'][95]} | {mc4['streak'][99]} |",
            "", "KILL_RULE.md thresholds stay 39.8% / 33 unless Joel adopts a new dated rule."]
    REPORT_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
