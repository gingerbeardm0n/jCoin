# jCoin TODO

Ordered. The top item is next. (Updated 2026-10-23, after `AUDIT_2026-10-23.md`; this replaces the old SWEEP_STATUS.md.)

## Joel's steps
- [x] Phone alerts: healthchecks.io URL set as `JCOIN_PING_URL` in the VM's `.env` (verified 2026-10-23). Failures now send `/fail`.
- [ ] Coinbase: enable US derivatives/futures on your account (questionnaire). Don't fund yet.
- [ ] **By ~2027-01-06:** click "Upgrade" in GCP billing. The trial ends 2027-01-13; without the upgrade the VM is stopped and its data deleted 30 days later.
- [ ] Decide: should the daily −3% loss halt also flatten open positions? It currently only pauses entries.
- [ ] Decide on capital. At ~$1k one BTC nano contract (~$820) is "1 contract or nothing", and real risk per trade runs 0.8–2.5% instead of 1%. Options: ≥$3–5k, ETH-only, or accept it.
- [ ] Optional: a daily GCE disk snapshot (~$0.25/mo), so the paper state survives losing the VM. The current backup is on the VM's own disk.
- [ ] Optional: make the GitHub repo private. Before any live keys go on the VM, turn auto-update off (`DEPLOY_GCP.md` §7).
- [ ] Work through `community/LEARNING_PLAN.md`.

## Claude's queue
1. [ ] **Wait for paper data.** Read `paper_state/parity_ledger.md` on the VM weekly. A_SR's real-money gate (`VALIDATION_RULES.md` §9) needs ≥ 6 months and ≥ 30 trades. Earliest check: ~2027-04-23.
2. [ ] Watchdog for a *stuck* daemon. The stale-feed `/fail` ping and the heartbeat ping cover most cases, but there is no subprocess timeout in `daemon.py`.
3. [ ] Reconcile code (Kraken path today, Coinbase adapter later): an exchange API error, or an empty `fetch_positions()`, must count as "unknown", never "no position" (`kraken_broker.py:254`, `kraken_trader.py:191-208`).
4. [ ] Log every skipped or lot-rounded signal at WARNING in A's paper path. `risk.py` logs at INFO with no handler, and `engine.py:71` skips silently.
5. [ ] A lagging symbol's missed bar is lost for good, because `paper_runner.py:281` uses a global `last_ts`. Track `last_ts` per symbol.
6. [ ] After the GCP public IPv4 starts costing (~$3.65/mo after the trial), consider IPv6-only. GitHub has no IPv6, so updates would need another path.
7. [ ] **Blocked:** Coinbase broker adapter (official `coinbase-advanced-py` SDK, not ccxt). Waits on the §9 gate. For A_SR it needs a ~1-minute spot poller plus a resting nano disaster stop.

## Done (recent)
- 2026-10-23:
  - Audit.
  - Auto-update gate fixed (tests a scratch copy first).
  - Stale-feed and missing-state guards.
  - Daily state backup.
  - §8 spot-stop test, and §9 A_SR paper bot.
  - Engine numbers, and the daily parity ledger.
  - Dead laptop scripts removed, docs corrected.
- 2026-10-22: Laptop tasks disabled; the VM runs everything.
- 2026-10-14 → 10-21:
  - Kill rule, funding in the backtests, head-to-head A vs B (A stays), sealed confirmation.
  - A_LO (fail), Coinbase parity diagnosis, A_CS (keep A), venue decision.
  - Carver/daily research (later retracted).

## Reference
- Audits: `AUDIT_2026-10-23.md`, `AUDIT_2026-09-18.md`
- Validation rules and Looks Log: `VALIDATION_RULES.md`
- Kill rule: `KILL_RULE.md`
- Deploy: `DEPLOY_GCP.md`
- Reading list: `community/READING_LIST.md`
