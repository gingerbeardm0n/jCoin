"""CLI for the paper trader.

  Replay (test the full stack on history):
      python -m jcoin.live.run_paper --mode replay --start 2024-01-01

  Live (process the latest closed bar — schedule this every 4h):
      python -m jcoin.live.run_paper --mode live
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from jcoin.data.config import DEFAULT_LIVE_LABELS
from jcoin.engine.kill_switch import KillSwitchConfig
from jcoin.engine.risk import RiskConfig
from jcoin.engine.strategy import StrategyConfig
from jcoin.data.config import CONTRACT_SIZES, COINBASE_MARKETS, LIVE_MARKETS
from jcoin.live.error_breaker import ErrorBreaker
from jcoin.live.funding import CoinbaseFundingSource, KrakenFundingSource
from jcoin.live import killswitch_latch
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
    p.add_argument("--venue", choices=["coinbase", "kraken"], default="coinbase",
                   help="market-data/funding/contract-size source for LIVE mode: coinbase = "
                        "Coinbase US nano perps (the chosen live venue; whole-contract "
                        "sizing), kraken = Kraken Futures data, fractional sizes (old behaviour)")
    p.add_argument("--start", default=None, help="replay start date YYYY-MM-DD")
    p.add_argument("--state-dir", default="paper_state")
    p.add_argument("--start-equity", type=float, default=10_000)
    p.add_argument("--risk-frac", type=float, default=0.01)
    # LIVE runner defaults = the fixed kill rule in KILL_RULE.md (99th-percentile bad-luck
    # year for strategy A). Engine/backtest module defaults are deliberately different.
    p.add_argument("--max-dd-pct", type=float, default=0.398,
                   help="kill-switch hard halt on drawdown from peak (KILL_RULE.md: 39.8%%)")
    p.add_argument("--max-losing-streak", type=int, default=33,
                   help="kill-switch hard halt when MORE than this many consecutive closed "
                        "trades have R<=0 (KILL_RULE.md: 33, the 34th trips); 0 = off")
    p.add_argument("--reset-equity", type=float, default=None,
                   help="reset account equity to this value and drop open positions, then run")
    p.add_argument("--init", action="store_true",
                   help="allow a LIVE run to start with no state.json (fresh paper clock)")
    args = p.parse_args(argv)

    breaker = ErrorBreaker(args.state_dir)
    if breaker.halted():
        print("HALTED by error breaker — see ERROR_HALT.latch in state dir")
        return 2

    if remote_flatten.is_latched(args.state_dir):
        print("HALTED by remote flatten latch — see FLATTEN_HALT.latch in state dir.")
        return 3

    if killswitch_latch.is_latched(args.state_dir):
        print("HALTED by kill-switch latch — see KILLSWITCH_HALT.latch in state dir "
              "and KILL_RULE.md for the human-review restart procedure.")
        return 5

    # Perp funding accrual is paper-only (live mode); replay runs on stored history
    # with no funding feed, as before.
    # --venue picks the market data, funding source and contract sizes for LIVE mode.
    # Replay runs on stored (Binance) history, so it never gets whole-contract sizing.
    if args.venue == "coinbase":
        markets, funding_cls = COINBASE_MARKETS, CoinbaseFundingSource
        lots = dict(CONTRACT_SIZES) if args.mode == "live" else None
        # Hard cap: a whole-contract trade may never risk more than the target (Joel,
        # 2026-10-28). With ~$1k equity this skips most BTC signals; ETH sizes fine.
        risk = RiskConfig(args.risk_frac, 1, 2, lot_sizes=lots, max_risk_mult=1.0)
    else:
        markets, funding_cls = LIVE_MARKETS, KrakenFundingSource
        risk = RiskConfig(args.risk_frac, 1, 2)
    funding = funding_cls({m.label: m for m in markets}) if args.mode == "live" else None
    had_state = (Path(args.state_dir) / "state.json").exists()
    trader = PaperTrader(
        labels=args.labels, tf=args.tf,
        strat=StrategyConfig(), risk=risk, live_markets=markets,
        ks=KillSwitchConfig(max_dd_pct=args.max_dd_pct,
                            max_losing_streak=args.max_losing_streak),
        start_equity=args.start_equity, state_dir=args.state_dir, funding=funding,
    )

    if args.reset_equity is not None:
        trader.reset_equity(args.reset_equity)
    elif args.mode == "live" and not had_state and not args.init:
        # A lost state.json would otherwise silently replay ~2300 bars from
        # --start-equity and could latch the kill switch on fake trades.
        print(f"NO STATE: {args.state_dir}/state.json missing -- restore it from backup, "
              "or start fresh deliberately with --init (or --reset-equity <amount>)")
        ping(suffix="/fail")
        return 7

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
        stale = getattr(trader, "stale_feed", None)
        if stale is not None:
            # A frozen feed must not look healthy: tell the monitor explicitly.
            print(f"\nFEED STALE (newest bar {stale}) -- sending /fail ping")
            ping(suffix="/fail")
            return 6
        ping()  # optional dead-man's-switch ping (no-op unless JCOIN_PING_URL is set)
    except Exception as e:
        breaker.record_failure(repr(e))
        raise

    a = trader.engine.account
    # win% / avg R since the last equity reset. reset_equity() clears equity_curve, so
    # its first timestamp marks the restart; closed[] still holds older history (incl.
    # seeded backtest trades), which would make an all-trades average meaningless.
    since = a.equity_curve[0][0] if a.equity_curve else None
    recent = [t for t in a.closed if since is None or t.entry_time >= since]
    if recent:
        wins = sum(1 for t in recent if t.R > 0)
        stats = (f"win%={100 * wins / len(recent):.1f}% | "
                 f"avgR={sum(t.R for t in recent) / len(recent):+.3f} "
                 f"over {len(recent)} trades")
    else:
        stats = "win%=n/a | avgR=n/a over 0 trades"
    since_txt = since.date().isoformat() if since else "start"
    print(f"\nSUMMARY | venue={args.venue} | equity=${a.equity:,.2f} | open={a.open_count} | "
          f"closed_trades={len(a.closed)} | {stats} since {since_txt} | "
          f"last_ts={trader.last_ts} | funding_missing_bars={trader.funding_missing_bars}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
