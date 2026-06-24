"""Portfolio backtest — turns per-trade edge into an account equity curve.

Per-trade bps don't tell you if you'd make money. This does: sequential, risk-sized,
compounding, with fees AND slippage and a concurrent-position cap. Answers the real
questions: does the account grow, how deep are the drawdowns, and does it beat just
holding BTC?

Model:
  - Signals: trend-aligned breakout (long in uptrend, short in downtrend), per symbol.
  - Exit: ATR initial stop + chandelier trailing stop (same as backtest_breakout).
  - Sizing: risk `risk_frac` of CURRENT equity per trade; position notional set so that
    a stop-out loses exactly that risk. Outcome in R-multiples -> equity *= (1+risk_frac*R).
  - Concurrency: at most `max_per_symbol` open per symbol and `max_concurrent` total;
    signals arriving when full are SKIPPED (realistic — capital/attention is finite).
  - Costs: (fee_bps + slippage_bps) round-trip subtracted from each trade's price return.

Approximations (honest): intrabar fills at this timeframe's high/low; stops fill at the
stop price (no gap modeling — optimistic on fast moves); entry sizing uses realized
equity at entry time. Good enough to judge viability before paper trading.

Usage:
    python -m jcoin.research.portfolio_backtest --tf 4h --labels BTC ETH
    python -m jcoin.research.portfolio_backtest --slippage-bps 10   # stress costs
"""

from __future__ import annotations

import argparse
import datetime as dt

import numpy as np
import polars as pl

from jcoin.data.feed import DataFeed
from jcoin.strategy.breakout import detect_breakout
from jcoin.strategy.regime import REGIME_DOWNTREND, REGIME_UPTREND
from jcoin.research.backtest_breakout import _atr


def build_trades(tf, labels, atr_period, atr_init, atr_trail, max_hold, cost_frac):
    """Per symbol: produce closed trades with entry/exit times + R outcome (net of cost)."""
    feed = DataFeed()
    trades = []
    for label in labels:
        df = feed.get_candles(label, tf)
        df2, sigs = detect_breakout(df, k=2)
        high = df2["high"].to_numpy()
        low = df2["low"].to_numpy()
        close = df2["close"].to_numpy()
        ts = df2["ts"].to_list()
        atr = _atr(df2, atr_period)
        n = len(close)
        for s in sigs:
            if s["side"] == "long" and s["regime"] != REGIME_UPTREND:
                continue
            if s["side"] == "short" and s["regime"] != REGIME_DOWNTREND:
                continue
            i = s["idx"]
            if i + 1 >= n or atr[i] <= 0:
                continue
            long = s["side"] == "long"
            entry = close[i]
            a = atr[i]
            stop = entry - atr_init * a if long else entry + atr_init * a
            stop_dist = abs(entry - stop) / entry
            if stop_dist <= 0:
                continue
            best = high[i] if long else low[i]
            exit_price = None
            exit_idx = min(i + max_hold, n - 1)
            for j in range(i + 1, min(i + 1 + max_hold, n)):
                if long:
                    if low[j] <= stop:
                        exit_price, exit_idx = stop, j
                        break
                    best = max(best, high[j])
                    stop = max(stop, best - atr_trail * a)
                else:
                    if high[j] >= stop:
                        exit_price, exit_idx = stop, j
                        break
                    best = min(best, low[j])
                    stop = min(stop, best + atr_trail * a)
            if exit_price is None:
                exit_price = close[exit_idx]
            gross = (exit_price - entry) / entry if long else (entry - exit_price) / entry
            net = gross - cost_frac
            R = net / stop_dist
            trades.append({
                "symbol": label, "entry_time": ts[i], "exit_time": ts[exit_idx],
                "side": s["side"], "R": R,
            })
    return sorted(trades, key=lambda t: t["entry_time"])


def run_portfolio(trades, start_equity, risk_frac, max_per_symbol, max_concurrent):
    """Event-driven equity simulation. Returns equity curve + taken-trade R list."""
    events = []
    for idx, t in enumerate(trades):
        events.append((t["entry_time"], 0, idx))  # 0 = entry sorts before exit at same ts
        events.append((t["exit_time"], 1, idx))
    events.sort(key=lambda e: (e[0], e[1]))

    equity = start_equity
    open_by_symbol = {}
    open_count = 0
    taken = set()
    sized = {}  # idx -> risk_dollars
    curve = [(trades[0]["entry_time"], equity)] if trades else []
    taken_R = []

    for time, kind, idx in events:
        t = trades[idx]
        if kind == 0:  # entry
            sym = t["symbol"]
            if open_count >= max_concurrent or open_by_symbol.get(sym, 0) >= max_per_symbol:
                continue  # full -> skip signal
            sized[idx] = risk_frac * equity
            open_by_symbol[sym] = open_by_symbol.get(sym, 0) + 1
            open_count += 1
            taken.add(idx)
        else:  # exit
            if idx not in taken:
                continue
            risk_dollars = sized[idx]
            equity += risk_dollars * t["R"]
            open_by_symbol[t["symbol"]] -= 1
            open_count -= 1
            taken_R.append(t["R"])
            curve.append((time, equity))
    return curve, taken_R


def metrics(curve, taken_R, start_equity, years):
    if len(curve) < 2:
        return {}
    eq = np.array([e for _, e in curve])
    total_ret = eq[-1] / start_equity - 1
    cagr = (eq[-1] / start_equity) ** (1 / years) - 1
    peak = np.maximum.accumulate(eq)
    max_dd = float(np.max((peak - eq) / peak))
    R = np.array(taken_R)
    wins = R[R > 0]
    losses = R[R <= 0]
    pf = (wins.sum() / abs(losses.sum())) if losses.size and losses.sum() != 0 else float("inf")
    # Sharpe from per-trade R, annualized by trade frequency
    trades_per_year = len(R) / years
    sharpe = (R.mean() / R.std() * np.sqrt(trades_per_year)) if R.std() > 0 else float("nan")
    return {
        "final_equity": eq[-1], "total_ret": total_ret, "cagr": cagr, "max_dd": max_dd,
        "n_trades": len(R), "win_pct": (R > 0).mean() * 100, "pf": pf,
        "avg_R": R.mean(), "sharpe": sharpe,
    }


def buy_hold(label, tf, start_equity, years):
    feed = DataFeed()
    df = feed.get_candles(label, tf)
    c = df["close"].to_numpy()
    eq = c / c[0] * start_equity
    peak = np.maximum.accumulate(eq)
    return {
        "total_ret": eq[-1] / start_equity - 1,
        "cagr": (eq[-1] / start_equity) ** (1 / years) - 1,
        "max_dd": float(np.max((peak - eq) / peak)),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Portfolio equity-curve backtest")
    p.add_argument("--tf", default="4h")
    p.add_argument("--labels", nargs="+", default=["BTC", "ETH"])
    p.add_argument("--start-equity", type=float, default=10_000)
    p.add_argument("--risk-frac", type=float, default=0.01, help="risk per trade (1%=0.01)")
    p.add_argument("--max-per-symbol", type=int, default=1)
    p.add_argument("--max-concurrent", type=int, default=2)
    p.add_argument("--atr-period", type=int, default=14)
    p.add_argument("--atr-init", type=float, default=1.0)
    p.add_argument("--atr-trail", type=float, default=4.0)
    p.add_argument("--max-hold", type=int, default=120)
    p.add_argument("--fee-bps", type=float, default=6.0, help="round-trip fee (Coinbase taker ~6)")
    p.add_argument("--slippage-bps", type=float, default=6.0, help="round-trip slippage")
    args = p.parse_args(argv)

    cost_frac = (args.fee_bps + args.slippage_bps) / 1e4
    trades = build_trades(args.tf, args.labels, args.atr_period, args.atr_init,
                          args.atr_trail, args.max_hold, cost_frac)
    if not trades:
        print("no trades")
        return 1
    span = (trades[-1]["exit_time"] - trades[0]["entry_time"]).days / 365.25
    years = max(span, 0.5)

    curve, taken_R = run_portfolio(trades, args.start_equity, args.risk_frac,
                                   args.max_per_symbol, args.max_concurrent)
    m = metrics(curve, taken_R, args.start_equity, years)

    print(f"PORTFOLIO BACKTEST | {args.labels} {args.tf} | risk={args.risk_frac:.1%}/trade "
          f"| cost={args.fee_bps+args.slippage_bps:.0f}bp rt | {years:.1f}y")
    print(f"  signals generated : {len(trades):,}   trades taken: {m['n_trades']:,} "
          f"(rest skipped, slots full)")
    print(f"  start equity      : ${args.start_equity:,.0f}")
    print(f"  final equity      : ${m['final_equity']:,.0f}")
    print(f"  total return      : {m['total_ret']*100:,.0f}%")
    print(f"  CAGR              : {m['cagr']*100:.1f}%")
    print(f"  max drawdown      : {m['max_dd']*100:.1f}%")
    print(f"  win rate / PF     : {m['win_pct']:.1f}% / {m['pf']:.2f}")
    print(f"  avg R / Sharpe    : {m['avg_R']:.3f} / {m['sharpe']:.2f}")
    print(f"\n  BENCHMARK — buy & hold:")
    for lb in args.labels:
        bh = buy_hold(lb, args.tf, args.start_equity, years)
        print(f"    {lb}: total {bh['total_ret']*100:,.0f}%  CAGR {bh['cagr']*100:.1f}%  "
              f"maxDD {bh['max_dd']*100:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
