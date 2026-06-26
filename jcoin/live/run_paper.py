"""CLI for the paper trader.

  Replay (test the full stack on history):
      python -m jcoin.live.run_paper --mode replay --start 2024-01-01

  Live (process the latest closed bar — schedule this every 4h):
      python -m jcoin.live.run_paper --mode live
"""

from __future__ import annotations

import argparse
import datetime as dt

from jcoin.engine.kill_switch import KillSwitchConfig
from jcoin.engine.risk import RiskConfig
from jcoin.engine.strategy import StrategyConfig
from jcoin.live.paper_runner import PaperTrader


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="jCoin paper trader")
    p.add_argument("--mode", choices=["replay", "live"], default="live")
    p.add_argument("--labels", nargs="+",
                   default=["BTC", "ETH", "EGLD", "SAND", "IMX", "ADA", "XRP", "AVAX", "HBAR"])
    p.add_argument("--tf", default="4h")
    p.add_argument("--start", default=None, help="replay start date YYYY-MM-DD")
    p.add_argument("--state-dir", default="paper_state")
    p.add_argument("--start-equity", type=float, default=10_000)
    p.add_argument("--risk-frac", type=float, default=0.01)
    p.add_argument("--max-dd-pct", type=float, default=0.40,
                   help="kill-switch hard halt; set ABOVE strategy's expected DD (~27%)")
    p.add_argument("--reset-equity", type=float, default=None,
                   help="reset account equity to this value and drop open positions, then run")
    args = p.parse_args(argv)

    trader = PaperTrader(
        labels=args.labels, tf=args.tf,
        strat=StrategyConfig(), risk=RiskConfig(args.risk_frac, 1, 2),
        ks=KillSwitchConfig(max_dd_pct=args.max_dd_pct),
        start_equity=args.start_equity, state_dir=args.state_dir,
    )

    if args.reset_equity is not None:
        trader.reset_equity(args.reset_equity)

    if args.mode == "replay":
        start = dt.datetime.fromisoformat(args.start) if args.start else None
        trader.run_replay(start=start)
    else:
        trader.run_live_once()

    a = trader.engine.account
    print(f"\nSUMMARY | equity=${a.equity:,.2f} | open={a.open_count} | "
          f"closed_trades={len(a.closed)} | last_ts={trader.last_ts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
