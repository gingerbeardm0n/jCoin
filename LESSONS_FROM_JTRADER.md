# Lessons From jTrader (Stock-Picker) — Applied to jTrader-crypto

**Source:** 3-agent sweep of the jTrader repo (`C:\Repositories\Stock-Picker`), 2026-06-19. Lessons-learned only — NOT the equity strategy (wrong market).
**Purpose:** Don't re-learn the hard way. Bake these into jTrader-crypto from line 1.

> Joel's 4 instincts going in — all validated by the sweep:
> 1. Keep tunable parameters LOW. ✅ (jTrader's 126-param monolith overfit by construction.)
> 2. Backtest↔sim↔paper↔live PARITY is the #1 design principle. ✅ (Months of silent drift cost them dearly.)
> 3. Venue must transfer seamlessly paper→live. ✅ (Their cloud-deploy/data-access mismatches caused silent prod failures.)
> 4. A repeatable method to absorb educators, start wide → boil down. ✅ (Already built once — fully reusable pipeline exists.)

---

## 1. PARITY — the #1 principle (build this way from the start)

**One engine, two adapters.** Never duplicate decision logic between sim and live. jTrader had per-minute logic copied into `simulation_engine.py` AND `live_scanner.py` — they drifted silently for *months* (dead indicator in sim, wrong sizing live, different volume timing). Fix was a single `Orchestrator` with sim/live reduced to pure **data-feed adapter** + **broker adapter**.
→ **jTrader-crypto: one strategy engine. Coinbase/Kraken/paper are just swappable adapters behind a Protocol interface.** This is also exactly our venue-agnostic goal.

**Silent no-op bugs are the real enemy — not crashes.** Every one of these ran undetected for months because nothing errored:
- Indicator never computed (history buffer too small) in sim, but active live → optimizer tuned a world that didn't exist.
- Missing data → silent fallback value (`rel_vol=10.0`) that disabled the most important filter in production.
- `prev_close=0.0` from the data feed → every symbol failed a gate → zero trades, no error, whole day lost.
- Indicator named `calculate_ema` actually computed an SMA — propagated for the entire project life.
→ **Defense: tests must assert output VALUES, not just "function ran." Audit every indicator against a reference number. Log when a fallback fires — a fallback should scream, not whisper.**

**Keep a written parity ledger + automated audit.** They found 11 sim/live divergences in a single audit after months of running blind. Created a living `PARITY.md` (categorize each gap: fixed / open / inherent) and a pre-commit hook running structural checks.
→ **jTrader-crypto: start a `PARITY.md` on day 1. Add a parity-check script before first paper deploy.**

**Parameterize account size** — never hardcode it one side. Sim $5k vs live $100k → same logic, P&L off 20×. (We already decided capital = config param. Good.)

**Same data source + timing on both sides.** Optimizer used cumulative volume at one snapshot; live used instantaneous quote volume (~2–3× inflated) → tuned thresholds live could never hit. Paper feeds may be delayed (15 min) — use the production/real-time data token even in paper mode.

**Fingerprint the data at backtest-seal time.** A sealed result (+$2,669, 90% WR) became +$19 / 40% WR after the DB was later repopulated — non-reproducible, blocked deploy. → Hash the data slice when you seal a result.

---

## 2. CONFIG / PARAMETER DISCIPLINE (Joel's instinct #1)

**Too many parameters = overfit by construction (math, not bad luck).** 126 params with no holdout → every great in-sample run collapsed out-of-sample, repeatedly. No objective-function tweak fixes it — the root cause is search-space size.
→ **jCoin: cap tunable params at ~13–15 per strategy. Lock the rest.** (Reinforces: build one engine ALONE, small and simple, first.)

**THE BIG REALIZATION (added 2026-06-21): cutting parameter count was the SINGLE HIGHEST-LEVERAGE fix — it nearly eliminated overfitting on its own.** The jTrader `ANTI_OVERFITTING_PLAYBOOK.md` names it directly: *"The single highest-leverage fix is cutting degrees of freedom — no objective tweak survives 126 knobs."* Their plan led with it: **126 → ~12 params.** Two linked principles:
- **Fewer knobs → smaller search space → less room for the optimizer to fit noise.** Everything else (holdout, walk-forward, deflated Sharpe) is damage control on a search space that's too big; shrinking the space is the root-cause fix.
- **Plateau, not peak** (playbook §2.7): a real edge sits in a *broad neighborhood* of good param values — insensitive to the exact numbers. A lone spike that dies when you nudge a param is overfit by definition.

**jCoin is this lesson applied + a live proof it works:** v1 has **~6 tunable params** (well under the cap) and we *never ran an optimizer* — just sensible defaults + a light manual grid. The overfit check IS the plateau test: the **un-tuned params (1.5/3.0) performed as well as the hand-picked ones (1.0/4.0)**, and the edge held across the whole grid, every year, and all cost levels. That insensitivity is the signature of a real edge, not a fitted one. We bought robustness up front by keeping the param count tiny — the cheapest anti-overfit insurance there is.

**They abandoned the monolith for small standalone strategies (~13 params, one pattern family each).** The monolith made overfitting unpreventable and parity unmanageable. → Our one-engine-at-a-time plan is the validated path.

**Run a sensitivity sweep (one-at-a-time) BEFORE the main optimizer** — prune flat params. Only ~15–20 of 43–46 mattered. Feeding dead params to the optimizer wastes trials on noise.

**Walk-forward, not shuffled CV** (shuffling leaks future data on time series). Train chronologically 70–75%, seal the rest, score the test set exactly once. Pass bar: test PF ≥ 80% of train PF. **Plateau-select** (a config in a robust neighborhood, not the lone peak).

**Optimize on Profit Factor (outlier-resistant); validate in real dollars.** Raw total-PnL rewards one lucky high-variance trade. Run 3 objectives (PF / total return / risk-adjusted) — convergence = real edge, divergence = a tradeoff to decide explicitly.

**Watch for false degrees of freedom** — params already constrained by an upstream gate can never fire but still bloat the search space. **Document mode-based bypasses** or the optimizer reports misleading importance.

**Universe/instrument quality > optimizer sophistication.** Restricting the candidate set 3×'d P&L. The optimizer drifts to whatever fires most often in a noisy universe (it converged on the easiest-to-trigger pattern). → For us: curate which instruments + setups feed the engine; don't let it pattern-promiscuously chase noise.

---

## 3. POSITION SIZING / RISK (crypto-critical ⚠️)

**Risk-based sizing WITHOUT an absolute position cap = catastrophic over-leverage.** `shares = max_loss / stop_distance` produced a position worth **131% of account** when the stop was tight ($0.06) on a cheap stock.
→ **This is MORE dangerous in crypto** (cheap, volatile alts; tight scalp stops). **Always: `size = min(risk_based_size, account × max_position_pct / price)`. Two orthogonal constraints, both enforced.** Ties directly to Stream 5's "liq ≥ 5× stop" + effective-leverage 1–2×.

**Portfolio-level rules live at the orchestrator, not the position exit.** Daily max-loss / green-to-red / give-back-half were completely missing because the exit engine only saw single positions. → Our daily −3% auto-flatten + kill-switch stack must be orchestrator-level account-state checks, run before/after every position.

**Validate sizing across a multi-day backtest**, not one-day logic checks — the bad combos only appear at specific price/stop pairs.

---

## 4. OPTIMIZER / WORKFLOW HYGIENE

- **Bayesian (Optuna) > grid search** for 5+ params. Gives parameter-importance for free.
- **Store every trial in SQL** (SQLite), not flat files → free post-hoc analysis across hundreds of thousands of rows; resume-safe after a crash/Ctrl+C (they lost 3.7h to a crash with no saved results).
- **10-trial smoke test on a short window before any multi-hour run** — caught a 46-min/trial bottleneck before it ruined a 1500-trial run.
- **Code-freeze during an optimization run** — mid-run objective/code changes make trials incomparable, wasting the whole run.
- **Don't act on interim importance scores** — the optimizer inverted its "best config" between early and late trials (explore → exploit).
- **"Oracle" / value-of-perfect-information test before building expensive infra** — compute the ceiling P&L of a proposed feature (e.g. regime detection) using ground-truth labels; if the ceiling ≈ 0, don't build it. **Apply this before building our CVD/regime-filter layer.**

---

## 5. REPO / INFRA HYGIENE (set up day 1)

- **Separate `production/` (live) from `research/` (analysis) trees, with a written file-placement rule in CLAUDE.md.** Otherwise research scripts drift into prod and break imports; debug one-offs pile up in root.
- **Gitignore generated output from commit #1** — they had 62MB of `.db` files + parquet caches + progress JSON in git; needed history rewrites to clean.
- **Don't assume DB access on the cloud deploy target.** jTrader's live runner went to Render (no DB) → silent fallbacks. Design the live runner stateless relative to the local DB; ship derived data as a versioned artifact.
- **Multi-level cache (memory LRU → parquet → DB) for historical bars** — 13× optimizer speedup (26s/day → 3.5s/day). Tie cache invalidation to data identity (a stale cache across a universe switch caused silent contamination + a crash).
- **Beware ephemeral cloud disk** — captured live session data was lost on redeploy; build the data-pull endpoint before first deploy, not after.
- **API key regeneration kills all old keys instantly, no grace period.** Don't regenerate mid-run.
- **Static lists go stale** — refresh any universe/instrument list from an authoritative source on a schedule.

---

## 6. EDUCATOR-ABSORPTION PIPELINE (Joel's instinct #4 — already built, reusable)

jTrader processed 1,799 Ross Cameron videos through a battle-tested pipeline. **Reuse it for TradingRiot + Trader Mayne.** Existing reusable assets in `Stock-Picker\Ross Cameron Day Trading Videos\prompts\` and `\scripts\`.

**The pipeline (7 stages):**
1. **Raw transcripts** (numbered files).
2. **Compress ~10×** to caveman format (drop filler, keep every trade datum). Haiku, batches of 20. *Key trick: later passes run on 10× smaller text → far more fits per agent call.*
3. **Extract** to a rigid template (header / trades table / summary / metadata JSON). Type-classify first. Chunk 100 files per output file.
4. **Enrich pass 1** — trade-mechanics table, reads summaries only (cheap).
5. **Enrich pass 2** — re-read raw transcript ONLY for fields pass 1 left blank.
6. **Aggregate stats + novelty report** — win rates per pattern; score transcripts by unseen-rule coverage → focus deep-reads where signal is highest (= "start wide → boil down").
7. **Concept synthesis** — one page per pattern, ending in a **pseudo-code "Decision Rules" block** = the bridge from educator content → bot logic.

**Concept-page template** (final output target): Definition → Setup Criteria (required/preferred) → Entry Trigger Variants (cite source files) → Add-On Mechanics → Stop Criteria → Profit Targets → Market-condition dependency → Red Flags → Example Trades → **Decision Rules (pseudo-code)** → Data Confidence.

**Apply these fixes from day 1 (they were learned mid-project):**
- **Finalize the extraction schema on paper BEFORE running agents** — jTrader changed format mid-run, orphaning the first ~450 files.
- **Pre-scan a sample of the educator first** — see which fields they actually state before building the schema (Ross rarely stated float/gap% → low fill). TradingRiot/Mayne will surface different fields (funding, OI, CVD, order-flow) → design crypto-specific vocab.
- **Keep spot-check QA on longer for the first crypto educator** — it sets the "good output" baseline; crypto patterns ≠ equity patterns.

---

## Read-in-full queue (for when we build each piece)

**Parity / architecture:** `docs/LIVE_SIM_PARITY_SPEC.md`, `docs/PARITY.md`, `docs/ENGINE_AUDIT_2026-05-29.md`
**Overfitting / optimizer:** `docs/ANTI_OVERFITTING_PLAYBOOK.md`, `research/optimizer/OPTIMIZER_AUDIT.md`, `production/strategy/SIMULATION_OPTIMIZATION_PLAN.md`, `research/optimizer/JTRADE_IMPLEMENTATION_GUIDE.md`
**Sizing / indicator bugs:** `POSITION_SIZING_FIX.md`, `RELATIVE_VOLUME_AUDIT.md`, `research/optimizer/PATTERN_EXIT_AUDIT.md`, `production/strategy/CATEGORY_C_GAP_ANALYSIS.md`
**Educator pipeline:** `Ross Cameron Day Trading Videos/prompts/COMPRESSION_PIPELINE.md`, `EXTRACTION_INSTRUCTIONS.md`, `ENRICHMENT_HAIKU_PROMPT.md`, `concepts/concept_gap_and_go.md`, `reference/Phase2_New_Rules_Report.md`
**Timeline:** `docs/PROJECT_HISTORY.md`
