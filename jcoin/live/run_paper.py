"""CLI for the paper trader.

  Replay (test the full stack on history):
      python -m jcoin.live.run_paper --mode replay --start 2024-01-01

  Live (process the latest closed bar — schedule this every 4h):
      python -m jcoin.live.run_paper --mode live
"""

from __future__ import annotations

import argparse
import datetime as dt

from jcoin.data.config import DEFAULT_LIVE_LABELS
from jcoin.engine.kill_switch import KillSwitchConfig
from jcoin.engine.risk import RiskConfig
from jcoin.engine.strategy import StrategyConfig
from jcoin.live.error_breaker import ErrorBreaker
from jcoin.live.paper_runner import PaperTrader
from jcoin.live.ping import ping
from jcoin.live import remote_flatten


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="jCoin paper trader")
    p.add_argument("--mode", choices=["replay", "live"], default="live")
    # --symbols is an alias for --labels (audit 2026-09-18): both flags select the same
    # symbol universe, kept under one dest so existing --labels callers are unaffected.
    p.add_argument("--labels", "--symbols", dest="labels", nargs="+",
                   default=list(DEFAULT_LIVE_LABELS))
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

    breaker = ErrorBreaker(args.state_dir)
    if breaker.halted():
        print("HALTED by error breaker — see ERROR_HALT.latch in state dir")
        return 2

    if remote_flatten.is_latched(args.state_dir):
        print("HALTED by remote flatten latch — see FLATTEN_HALT.latch in state dir.")
        return 3

    trader = PaperTrader(
        labels=args.labels, tf=args.tf,
        strat=StrategyConfig(), risk=RiskConfig(args.risk_frac, 1, 2),
        ks=KillSwitchConfig(max_dd_pct=args.max_dd_pct),
        start_equity=args.start_equity, state_dir=args.state_dir,
    )

    if args.reset_equity is not None:
        trader.reset_equity(args.reset_equity)

    try:
        if args.mode == "replay":
            start = dt.datetime.fromisoformat(args.start) if args.start else None
            trader.run_replay(start=start)
        elif remote_flatten.handle_flatten(trader, args.state_dir):
            pass  # flattened + latched this tick, skipped normal signal processing
        else:
            trader.run_live_once()
        breaker.record_success()
        failures = getattr(trader, "fetch_failures", [])
        if failures:
            # Don't ping "alive" when market data is broken: the dead-man's switch
            # should go quiet so a human hears about it. Non-zero exit shows up in
            # Task Scheduler history. Not counted by the error breaker -- a network
            # blip after sleep shouldn't latch a halt; the next run catches up.
            print(f"\nFETCH FAILED for {failures} -- no heartbeat ping this run")
            return 4
        ping()  # optional dead-man's-switch ping (no-op unless JCOIN_PING_URL is set)
    except Exception as e:
        breaker.record_failure(repr(e))
        raise

    a = trader.engine.account
    print(f"\nSUMMARY | equity=${a.equity:,.2f} | open={a.open_count} | "
          f"closed_trades={len(a.closed)} | last_ts={trader.last_ts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
