# jCoin TODO

Ordered. Top item is next. (Updated 2026-10-12.)

## Joel's steps
- [ ] Phone alerts: healthchecks.io check (period 1h, grace 1h) → URL into the **VM's** `/opt/jcoin/.env` as `JCOIN_PING_URL=` (Claude can do the VM part)
- [ ] ~~Laptop power~~ — no longer needed once the VM is confirmed and the laptop tasks are disabled
- [ ] Coinbase: account? futures enabled? fund $1k or $2k?
- [ ] Reddit: watch replies on the two posts (r/algotradingcrypto, r/CryptoTradingFloor); build karma for r/algotrading
- [x] Google Cloud: free trial active, project `jcoin-511611`, VM `jcoin-bot` (e2-micro, us-central1-a) running the daemon since 2026-10-14; $5/mo budget alert
- [ ] **By ~2027-01-06:** click "Upgrade" in GCP billing (trial ends 2027-01-13; without it the VM is stopped and its data deleted 30 days later)
- [ ] Decide: should the daily −3% loss halt also flatten open positions? (currently pauses entries only)

## Claude's queue
0. [ ] 2026-10-15: compare VM vs laptop paper state (should match bar-for-bar); if equal, disable laptop scheduled tasks (ask Joel first)
1. [ ] Model perp funding costs; re-run the clean Jun 1 → Sep 18 replay with real Kraken funding history. Biggest open question on whether the strategy is profitable at all.
2. [ ] "Does this look right?" sanity check, every tick, alert even when nothing errors. E.g. cycle phase unchanged for unusually long, newest bar older than expected, price/ATR outside historical range. Do after phone alerts are live so it actually reaches Joel. (Idea from r/algotradingcrypto "5 silent data bugs" post; we've hit this bug family 3×.)
3. [ ] Reconcile code: confirm an exchange API error is treated as "unknown", never as "no position" (failure story from research sweep).
4. [ ] Write the kill rule before going live (e.g. stop if drawdown > 1.5–2× backtest worst; a losing streak alone is not a reason).
5. [ ] Venue research, side by side: (a) Coinbase US nano futures (hourly funding, API via `coinbase-advanced-py`); (b) **CME micro crypto futures via Interactive Brokers API** (no funding; must roll contracts; Micro BTC 0.1 BTC ≈ $8k is too big for $1k, Micro ETH 0.1 ETH ≈ $400 may fit; check for smaller spot-quoted contracts). Source: u/moritz_ka. Pick one before building an adapter.
5b. [ ] Broker adapter for the chosen venue (Coinbase: official `coinbase-advanced-py` SDK, not ccxt) (official `coinbase-advanced-py` SDK, not ccxt)
6. [ ] After the GCP public IPv4 starts costing (~$3.65/mo after trial), consider IPv6-only (GitHub has no IPv6, so updates would need another path)
7. [ ] Paper runner with a MISSING state.json silently replays ~2300 bars (a year) as if traded. Make a missing state file start from "now" (or refuse and alert) instead.
8. [ ] Remove unused `run_paper_live.ps1` / `run_watchdog.ps1` once the windowless `scripts/task_runner.pyw` launcher has run cleanly for a week.

## Reference
- Audit: `AUDIT_2026-09-18.md` · Validation rules + looks log: `VALIDATION_RULES.md` · Reading list: `community/READING_LIST.md`
