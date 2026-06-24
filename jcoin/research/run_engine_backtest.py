"""Drive the TradingEngine over history and check PARITY vs portfolio_backtest.

Acceptance test for the engine: running it in backtest mode must reproduce the validated
numbers (CAGR ~28%, maxDD ~27%, PF ~1.48, ~441 trades, final ~$38.6k for the base case).
If it matches, the engine is correct and the same code is ready for a paper/live broker.

Usage:
    python -m jcoin.research.run_engine_backtest
"""

from __future__ import annotations

import argparse

from jcoin.data.feed import DataFeed
from jcoin.engine.broker import BacktestBroker
from jcoin.engine.engine import TradingEngine
from jcoin.engine.features import compute_features
from jcoin.engine.risk import RiskConfig
from jcoin.engine.strategy import BreakoutStrategy, StrategyConfig
from jcoin.research.portfolio_backtest import metrics

_COLS = ["symbol", "ts", "open", "high", "low", "close", "volume",
         "regime", "atr", "brk_long", "brk_short", "conf_sh", "conf_sl"]


def build_rows_by_ts(labels, tf, k, atr_period):
    feed = DataFeed()
    by_ts: dict = {}
    for label in labels:
        df = compute_features(feed.get_candles(label, tf), k=k, atr_period=atr_period)
        df = df.with_columns(symbol=__import__("polars").lit(label))
        for row in df.select(_COLS).iter_rows(named=True):
            by_ts.setdefault(row["ts"], {})[label] = row
    return by_ts


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Engine backtest parity run")
    p.add_argument("--tf", default="4h")
    p.add_argument("--labels", nargs="+", default=["BTC", "ETH"])
    p.add_argument("--start-equity", type=float, default=10_000)
    p.add_argument("--risk-frac", type=float, default=0.01)
    p.add_argument("--atr-init", type=float, default=1.0)
    p.add_argument("--atr-trail", type=float, default=4.0)
    p.add_argument("--max-hold", type=int, default=120)
    p.add_argument("--fee-bps", type=float, default=6.0)
    p.add_argument("--slippage-bps", type=float, default=6.0)
    args = p.parse_args(argv)

    cost_frac = (args.fee_bps + args.slippage_bps) / 1e4
    engine = TradingEngine(
        strategy=BreakoutStrategy(StrategyConfig(args.atr_init, args.atr_trail, args.max_hold)),
        broker=BacktestBroker(cost_frac),
        risk=RiskConfig(args.risk_frac, max_per_symbol=1, max_concurrent=2),
        start_equity=args.start_equity,
    )

    by_ts = build_rows_by_ts(args.labels, args.tf, k=2, atr_period=14)
    for ts in sorted(by_ts):
        engine.step(ts, by_ts[ts])

    acct = engine.account
    first_ts = min(by_ts)
    curve = [(first_ts, args.start_equity)] + acct.equity_curve
    years = max((curve[-1][0] - curve[0][0]).days / 365.25, 0.5)
    R = [t.R for t in acct.closed]
    m = metrics(curve, R, args.start_equity, years)

    print(f"ENGINE BACKTEST | {args.labels} {args.tf} | risk={args.risk_frac:.1%} "
          f"cost={args.fee_bps+args.slippage_bps:.0f}bp | {years:.1f}y")
    print(f"  trades taken : {m['n_trades']:,}")
    print(f"  final equity : ${m['final_equity']:,.0f}")
    print(f"  CAGR         : {m['cagr']*100:.1f}%")
    print(f"  max drawdown : {m['max_dd']*100:.1f}%")
    print(f"  PF / win%    : {m['pf']:.2f} / {m['win_pct']:.1f}%")
    print(f"  Sharpe       : {m['sharpe']:.2f}")
    print("\n  PARITY TARGET (portfolio_backtest base case): "
          "~441 trades, ~$38,576, CAGR ~28.1%, maxDD ~27.1%, PF ~1.48")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
