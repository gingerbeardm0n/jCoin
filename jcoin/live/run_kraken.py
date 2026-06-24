"""CLI for the Kraken Futures live/demo trader.

DEMO (default — safe, uses demo-futures.kraken.com):
    Set env vars then run:
        $env:KRAKEN_FUTURES_KEY    = "your-demo-api-key"
        $env:KRAKEN_FUTURES_SECRET = "your-demo-api-secret"
        python -m jcoin.live.run_kraken

LIVE (real money — requires explicit --live flag):
    Set live API keys in env vars, then:
        python -m jcoin.live.run_kraken --live

How to get demo API keys:
    1. Go to https://demo-futures.kraken.com
    2. Create account (separate from live Kraken account)
    3. Settings -> API -> Generate Key (enable: General (read), Trade)
    4. Withdrawals MUST be disabled — we never need them

Schedule (PowerShell, every 4h):
    python -m jcoin.live.run_kraken >> logs\kraken.log 2>&1
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

import dotenv
dotenv.load_dotenv()  # loads .env from cwd or any parent directory

from jcoin.engine.kill_switch import KillSwitchConfig
from jcoin.engine.risk import RiskConfig
from jcoin.engine.strategy import StrategyConfig
from jcoin.live.kraken_trader import KrakenTrader


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="jCoin Kraken Futures trader")
    p.add_argument("--live", action="store_true",
                   help="Use LIVE endpoint (real money). Default: demo.")
    p.add_argument("--labels", nargs="+",
                   default=["BTC", "ETH", "EGLD", "SAND", "IMX", "ADA", "XRP", "AVAX", "HBAR"])
    p.add_argument("--tf", default="4h")
    p.add_argument("--state-dir", default="kraken_state")
    p.add_argument("--start-equity", type=float, default=10_000.0,
                   help="Starting equity (informational — real equity pulled from Kraken)")
    p.add_argument("--risk-frac", type=float, default=0.01)
    p.add_argument("--max-dd-pct", type=float, default=0.40)
    args = p.parse_args(argv)

    demo = not args.live

    if args.live:
        print("=" * 60)
        print("  WARNING: LIVE MODE — real money will be used.")
        print("  Ctrl-C to abort. Continuing in 5 seconds...")
        print("=" * 60)
        import time; time.sleep(5)

    api_key = os.environ.get("KRAKEN_FUTURES_KEY")
    api_secret = os.environ.get("KRAKEN_FUTURES_SECRET")
    if not api_key or not api_secret:
        print("ERROR: set KRAKEN_FUTURES_KEY and KRAKEN_FUTURES_SECRET env vars.")
        print("Demo keys: https://demo-futures.kraken.com -> Settings -> API")
        return 1

    trader = KrakenTrader(
        api_key=api_key,
        api_secret=api_secret,
        demo=demo,
        labels=args.labels,
        tf=args.tf,
        strat=StrategyConfig(),
        risk=RiskConfig(args.risk_frac, 1, 2),
        ks=KillSwitchConfig(max_dd_pct=args.max_dd_pct),
        start_equity=args.start_equity,
        state_dir=args.state_dir,
    )

    import logging
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("jcoin.live.kraken_broker").setLevel(logging.DEBUG)

    mode = "DEMO (demo-futures.kraken.com)" if demo else "LIVE (futures.kraken.com)"
    print(f"[{dt.datetime.utcnow().isoformat()} UTC] jCoin Kraken Trader — {mode}")

    processed = trader.run_live_once()
    a = trader.engine.account
    print(f"DONE | processed={processed} | equity=${a.equity:,.2f} | "
          f"open={a.open_count} | trades={len(a.closed)} | ts={trader.last_ts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
