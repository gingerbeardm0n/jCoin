# jCoin TODO

Ordered. Top item is next. (Updated 2026-10-12.)

## Joel's steps
- [ ] Phone alerts: healthchecks.io check (period 1h, grace 1h) → URL into `.env` as `JCOIN_PING_URL=`
- [ ] Laptop power: sleep "when plugged in" = Never (Settings → System → Power)
- [ ] Coinbase: account? futures enabled? fund $1k or $2k?
- [ ] Reddit: watch replies on the two posts (r/algotradingcrypto, r/CryptoTradingFloor); build karma for r/algotrading
- [ ] Google Cloud: activate billing (free trial), create project `jcoin`, then hand off to Claude for VM setup
- [ ] ~80 days after GCP free trial starts: click "Upgrade" to a paid account so the Always Free VM isn't paused when the trial ends (still $0 within free limits)
- [ ] Decide: should the daily −3% loss halt also flatten open positions? (currently pauses entries only)

## Claude's queue
1. [ ] Model perp funding costs; re-run the clean Jun 1 → Sep 18 replay with real Kraken funding history. Biggest open question on whether the strategy is profitable at all.
2. [ ] "Does this look right?" sanity check, every tick, alert even when nothing errors. E.g. cycle phase unchanged for unusually long, newest bar older than expected, price/ATR outside historical range. Do after phone alerts are live so it actually reaches Joel. (Idea from r/algotradingcrypto "5 silent data bugs" post; we've hit this bug family 3×.)
3. [ ] Reconcile code: confirm an exchange API error is treated as "unknown", never as "no position" (failure story from research sweep).
4. [ ] Write the kill rule before going live (e.g. stop if drawdown > 1.5–2× backtest worst; a losing streak alone is not a reason).
5. [ ] Coinbase US nano futures adapter (official `coinbase-advanced-py` SDK, not ccxt) — after Joel's Coinbase answer.
6. [ ] Remove unused `run_paper_live.ps1` / `run_watchdog.ps1` once the windowless `scripts/task_runner.pyw` launcher has run cleanly for a week.

## Reference
- Audit: `AUDIT_2026-09-18.md` · Validation rules + looks log: `VALIDATION_RULES.md` · Reading list: `community/READING_LIST.md`
