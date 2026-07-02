"""Parity audit — verify live paper trades match what the validated strategy SHOULD do.

THE gate between paper trading and real money (LESSONS_FROM_JTRADER.md #1: silent
sim/live drift ran undetected for months and was jTrader's most expensive failure mode).
Run this against every closed live-window trade before flipping demo=False.

For each closed paper trade with entry_time >= --since (default: the verified live
boundary, 2026-06-22 20:00 UTC — first genuinely-live processed bar per paper.log
wall-clock analysis 2026-07-01):

  1. SIGNAL     — refetch the same Kraken 4h candles the live runner saw (closed bars
                  are immutable, so a refetch reproduces them), recompute features with
                  the same params (k=2, atr_period=14), and confirm a breakout signal
                  aligned with regime actually existed on the entry bar.
  2. ENTRY FILL — entry_price must equal the entry bar's close (PaperBroker convention).
  3. SIZING     — size must equal risk_dollars / stop_dist where stop_dist =
                  atr_init * ATR(entry bar), within tolerance.
  4. EXIT PATH  — replay manage_position() bar-by-bar from entry with the recorded
                  entry state and confirm exit bar, exit price, and exit reason match.

Tolerances are configurable; default 0.1% on prices (Kraken feed is the same source
live used, so drift should be ~0; tolerance absorbs float/rounding only).

Any FAIL = a parity bug to fix BEFORE real money. No-trades-yet = the audit passes
vacuously but tells you n is still too small to mean anything.

Usage:
    python -m jcoin.research.parity_audit
    python -m jcoin.research.parity_audit --since 2026-06-22T20:00:00 --tol-pct 0.1
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import polars as pl

from jcoin.data.config import LIVE_MARKETS
from jcoin.data.live_source import get_recent_candles
from jcoin.engine.features import compute_features
from jcoin.engine.strategy import BreakoutStrategy, StrategyConfig
from jcoin.engine.types import Position, Side

UTC = dt.timezone.utc
LIVE_BOUNDARY = dt.datetime(2026, 6, 22, 20, 0, tzinfo=UTC)
K, ATR_PERIOD = 2, 14


def _feat_for(label: str) -> pl.DataFrame:
    mkt = next((m for m in LIVE_MARKETS if m.label == label), None)
    if mkt is None:
        raise KeyError(f"{label} not in LIVE_MARKETS")
    df = get_recent_candles(mkt, "4h", limit=2300)
    return compute_features(df, k=K, atr_period=ATR_PERIOD).with_columns(symbol=pl.lit(label))


def _audit_trade(t: dict, feat: pl.DataFrame, strat: BreakoutStrategy,
                 equity_at_entry: float | None, tol: float) -> list[tuple[str, bool, str]]:
    """Returns [(check_name, passed, detail), ...] for one closed trade."""
    checks: list[tuple[str, bool, str]] = []
    entry_ts = dt.datetime.fromisoformat(t["entry_time"])
    exit_ts = dt.datetime.fromisoformat(t["exit_time"])
    side = Side(t["side"])

    rows = feat.filter(pl.col("ts") == entry_ts)
    if rows.height == 0:
        checks.append(("entry-bar-found", False,
                       f"entry bar {entry_ts} not in refetched feed (history window too short?)"))
        return checks
    row = rows.to_dicts()[0]

    # 1. SIGNAL existed, aligned with regime
    if side is Side.LONG:
        sig_ok = bool(row["brk_long"]) and row["regime"] == "uptrend"
        want = "brk_long+uptrend"
    else:
        sig_ok = bool(row["brk_short"]) and row["regime"] == "downtrend"
        want = "brk_short+downtrend"
    checks.append(("signal", sig_ok,
                   f"want {want}; got brk_long={row['brk_long']} brk_short={row['brk_short']} "
                   f"regime={row['regime']}"))

    # 2. ENTRY FILL at bar close
    close = row["close"]
    fill_ok = abs(t["entry_price"] - close) / close <= tol
    checks.append(("entry-fill", fill_ok,
                   f"recorded {t['entry_price']:.6g} vs bar close {close:.6g}"))

    # 3. SIZING = risk_dollars / stop_dist (only checkable if we know equity at entry)
    atr = row["atr"]
    stop_dist = strat.cfg.atr_init * atr
    if equity_at_entry is not None and stop_dist > 0:
        # cycle filter may have scaled risk to 75% in bear phase — accept either
        for frac, tag in ((0.01, "1%"), (0.0075, "0.75% bear-scaled")):
            expect_size = frac * equity_at_entry / stop_dist
            if abs(t["size"] - expect_size) / expect_size <= max(tol, 0.02):
                checks.append(("sizing", True, f"matches {tag} risk sizing ({expect_size:.6g})"))
                break
        else:
            checks.append(("sizing", False,
                           f"recorded {t['size']:.6g}; expected {0.01*equity_at_entry/stop_dist:.6g} (1%) "
                           f"or {0.0075*equity_at_entry/stop_dist:.6g} (0.75%)"))
    else:
        checks.append(("sizing", True, "skipped (equity at entry unknown)"))

    # 4. EXIT PATH — replay manage_position from entry
    pos = Position(
        symbol=t["symbol"], side=side, entry_time=entry_ts, entry_price=t["entry_price"],
        size=t["size"], risk_dollars=0.0, atr=atr,
        init_stop=close - strat.cfg.atr_init * atr if side is Side.LONG
        else close + strat.cfg.atr_init * atr,
        trail_stop=close - strat.cfg.atr_init * atr if side is Side.LONG
        else close + strat.cfg.atr_init * atr,
        extreme=row["high"] if side is Side.LONG else row["low"],
    )
    later = feat.filter(pl.col("ts") > entry_ts).sort("ts")
    sim_exit_ts, sim_exit_price, sim_reason = None, None, None
    for i, r in enumerate(later.iter_rows(named=True), start=1):
        d = strat.manage_position(pos, r, i)
        if d.exit:
            sim_exit_ts, sim_exit_price, sim_reason = r["ts"], d.price, d.reason
            break
    if sim_exit_ts is None:
        checks.append(("exit-path", False, "replay never exits within available bars"))
    else:
        ts_ok = sim_exit_ts == exit_ts
        px_ok = abs(sim_exit_price - t["exit_price"]) / t["exit_price"] <= tol
        rsn_ok = sim_reason == t["exit_reason"]
        checks.append(("exit-path", ts_ok and px_ok and rsn_ok,
                       f"replay: {sim_exit_ts} @ {sim_exit_price:.6g} ({sim_reason}) vs "
                       f"recorded: {exit_ts} @ {t['exit_price']:.6g} ({t['exit_reason']})"))
    return checks


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Live-paper vs strategy parity audit")
    p.add_argument("--state", default="paper_state/state.json")
    p.add_argument("--since", default=LIVE_BOUNDARY.isoformat(),
                   help="audit trades entered at/after this UTC timestamp")
    p.add_argument("--tol-pct", type=float, default=0.1, help="price tolerance in percent")
    args = p.parse_args(argv)

    since = dt.datetime.fromisoformat(args.since)
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    tol = args.tol_pct / 100.0
    state = json.loads(Path(args.state).read_text())

    live_trades = [t for t in state["closed"]
                   if dt.datetime.fromisoformat(t["entry_time"]) >= since]
    print(f"PARITY AUDIT | trades entered since {since.isoformat()} : {len(live_trades)}")
    if not live_trades:
        print("\nNo fully-live trades to audit yet. Vacuous pass — keep the sim running.")
        return 0

    # equity at each trade's entry: walk the equity curve backward
    curve = [(dt.datetime.fromisoformat(ts), eq) for ts, eq in state["equity_curve"]]

    def equity_at(ts: dt.datetime) -> float | None:
        prior = [eq for t2, eq in curve if t2 < ts]
        return prior[-1] if prior else None

    strat = BreakoutStrategy(StrategyConfig())
    feats: dict[str, pl.DataFrame] = {}
    n_fail = 0
    for t in live_trades:
        label = t["symbol"]
        if label not in feats:
            feats[label] = _feat_for(label)
        entry_ts = dt.datetime.fromisoformat(t["entry_time"])
        print(f"\n--- {label} {t['side']} entered {t['entry_time']} "
              f"(pnl={t['pnl']:.2f}, R={t['R']:.3f}, exit={t['exit_reason']}) ---")
        checks = _audit_trade(t, feats[label], strat, equity_at(entry_ts), tol)
        for name, ok, detail in checks:
            mark = "PASS" if ok else "FAIL"
            if not ok:
                n_fail += 1
            print(f"  [{mark}] {name:<12} {detail}")

    print("\n" + "=" * 70)
    if n_fail == 0:
        print(f"ALL CHECKS PASSED across {len(live_trades)} live trade(s).")
        print("NOTE: parity confidence scales with n. Spec bar: >= 8 clean live trades "
              "before real money.")
    else:
        print(f"{n_fail} CHECK(S) FAILED — fix before real money. A parity failure here "
              "is exactly the silent-drift bug class that killed jTrader.")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
