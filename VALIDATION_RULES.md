# jCoin — Validation Rules

**Date:** 2026-09-18
**Why this file exists:** the previous "sealed" test window was not sealed — it was looked
at more than 1,000 times while choosing parameters and coins, so its "validated" label
carried little weight. This file draws a hard line going forward.

Acronyms: PF = profit factor (gross profit ÷ gross loss). MAR = annual return ÷ max
drawdown. ATR = average true range. OOS = out-of-sample (data never used to choose
parameters, coins, or strategy family).

## 1. The sealed-window rule

**2026-06-01 onward is the new sealed OOS window.** No parameter, coin, or strategy-family
choice may be made using any data from this window. This is not "use it carefully" — it is
"do not look at it while deciding anything."

- Selection (choosing params, coins, or strategy family) may use only data **before
  2026-06-01**.
- Any future selection process must use a **walk-forward** scheme or a **fresh holdout**
  that is declared, in writing, **before** anyone looks at it.
- Every evaluation that touches data from 2026-06-01 onward — even a "just checking" run —
  must be logged in the Looks Log below: date, script, config, coins, purpose. No exceptions
  for read-only or "informal" runs; a look is a look.

## 2. Looks Log

*(Rules §5–§9 are further down.)*

The first rows below summarize the historical looks that broke the previous seal (the
≥1,000 figure and how it was derived). All rows after the horizontal rule are logged going
forward, one row per evaluation.

| Date | Script | Config(s) | Coins | Purpose | Touched sealed window? |
|---|---|---|---|---|---|
| pre-2026-09-18 | `optimize_full.py` | 432 configs | 2 | Parameter grid search, full range incl. 2025–26 | Yes |
| pre-2026-09-18 | `grid_per_coin.py` | 28 configs | 4 | Per-coin grid, full range | Yes |
| pre-2026-09-18 | `validate_coins.py` → `validate_coins4.py` (4 scripts) | pass/fail gate | ~20 | Used 2025–26 pass/fail as the coin ADD/keep gate; `validate_coins4.py` docstring states the goal was "Joel wants XRP + HBAR promoted" | Yes |
| pre-2026-09-18 | (various, folded into above) | per-coin tuned init/trail (e.g. IMX 2.0/7.0) | 1+ | Per-coin parameter tuning using the same window | Yes |
| **Total (floor)** | — | **≥1,000 config-by-coin evaluations** (864 from `optimize_full.py` [432×2] + 112 from `grid_per_coin.py` [28×4] + additional coin-gate passes across ~20 coins in the `validate_coins*` series) | ~20 | Selection basis for the now-reverted 9-coin universe | Yes |
| 2026-09-18 | fresh replay, unmodified engine | live config | 9 | Confirm 40%-drawdown halt reproduces (Apr 2025→May 2026) | No (pre-06-01 only) |
| 2026-09-18 | fresh replay, unmodified engine | live config vs BTC+ETH vs 7-coin | 9 / 2 / 7 | Report clean OOS numbers for the audit — **results reported, not used to pick a config** | **Yes — logged for transparency; not a selection step** |
| 2026-10-14 | (protocol only, no runs) | — | — | Head-to-head protocol A vs B registered in §5 **before** any results | No |
| 2026-10-14 | `phase1_honest_a.py` (first baseline run, discarded) | A, fixed config | 2 | Unbounded 1m data let a few trades entered before 06-01 exit after it; numbers discarded, all reported results capped at 2026-05-31 | **Yes (minor leak, discarded)** |
| 2026-10-14 | `phase1_honest_a.py`, `basket_trend_backtest.py` | A fixed; B fixed + 2 report-only variants | 2 / ≤30 of 729 | Head-to-head on dev period; decision recorded in `pipeline/HEAD_TO_HEAD_2026-10.md` (A stays) | No |
| 2026-10-14 | `jcoin/research/sealed_confirmation.py` (`allow_sealed=True`) | A fixed, B fixed main | 2 / ≤30 per rebalance of 895 | Single §5 confirmation look (2026-06-01 → 09-30) | Yes — the one allowed look |
| 2026-10-18 | (protocol only, no runs) | — | — | A_LO spot long-only pass rule registered in §6 **before** any results | No |
| 2026-10-18 | `spot_long_only.py` | A_LO fixed; costs 1.00% (decision), 0.50% / 2.60% (report only) | 2 | §6 test on dev data → **FAIL** (PF 1.14, MAR 0.02, 3/6 slices). No sealed look (protocol confirms passes only). | No |
| 2026-10-19 | `noise_robustness.py`, Coinbase parity diagnostics | A fixed | 2 | Diagnostics only (noise, spikes); no selection | No |
| 2026-10-19 | (protocol only, no runs) | — | — | A_CS close-based stop rule registered in §7 **before** any results | No |
| 2026-10-19 | `close_stop_test.py` | A vs A_CS (fixed) | 2 | §7 test → **KEEP A** (dev MAR 0.85 < 1.11 threshold; Coinbase PF 0.98 vs 0.59 improved but not enough) | No |
| 2026-10-21 | `carver_trend.py` (Carver EWMAC ×6, A on daily) | report-only, NOT pre-registered (logged late, 2026-10-23) | 2 | Research comparison; later found invalid (sizing bug, AUDIT_2026-10-23 W8) | No |
| 2026-10-23 | (protocol only, no runs) | — | — | A_SR spot-referenced stop rule registered in §8 **before** any code or results | No |
| 2026-10-23 | `spot_stop_test.py` | A vs A_SR (fixed); A on Coinbase spot (dev) | 2 | §8 test → **DO NOT ADOPT** (Coinbase PF 1.17 vs 0.59 passes; spot dev MAR 0.99 < 1.23 fails). Report regenerated once to fix a label; numbers identical | No |
| 2026-10-23 | (protocol only, no runs; one dev-only bootstrap for gate 3) | A on Coinbase spot dev trades | 2 | §9 registered after §8 (disclosed): A_SR to paper alongside A; real-money gate fixed before any A_SR paper data | No |
| — | — | — | — | *(add new rows here going forward)* | — |

## 3. The gate definition

Scripts in this repo (`validate_coins*.py`, `optimize_full.py`, `grid_per_coin.py`) use
**PF ≥ 1.15 and MAR ≥ 0.40** as the pass/fail bar for adding or keeping a coin or config.
**`STRATEGY_SPEC.md` never defined this gate** — it was an implicit convention baked into
the scripts, not a documented, deliberate threshold. Treat it as provisional until it is
written into the spec with a stated rationale.

## 4. Minimum-sample honesty

Each of the historical "validated" coins had only **~50–68 trades** in the sealed window.
Being honest about statistics: with roughly 60 trades, you cannot reliably tell a PF of 1.15
apart from a PF of 1.0 — the sampling noise is comparable to the effect size being tested.
This gets worse, not better, the more configurations you tried and picked the best of (which
is exactly what happened here — see the Looks Log above). For the correct treatment of
multiple-testing bias in performance-metric selection, see Bailey, D. H. & López de Prado, M.
(2014), "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and
Non-Normality," SSRN 2460551. Any future gate should account for the number of
configurations/coins tried, not just the raw PF/MAR of the survivor.


## 5. Head-to-head protocol: A vs B (registered 2026-10-14, before any results)

Written and committed before any Phase 1/2 numbers exist. The commit date is the proof.

**Contestants (fixed configs, no tuning):**
- **A: current bot.** BTC+ETH, 4h trend-aligned breakout, ATR init 1.0 / trail 6.0, max_hold 120,
  1% risk, max 1 per symbol / 2 concurrent. Costs: 12bp round trip **plus perp funding**
  (Binance history), reported at 1× and 2× funding. Decision uses **1× funding**.
- **B: daily basket, long-only spot.** Point-in-time top 30 USDT coins by trailing 90-day dollar
  volume (stablecoins excluded, delisted coins included), long when EMA(20) > EMA(100), else flat;
  equal weight, total exposure ≤ 1× equity, rebalance every 14 days, no stops. Costs: 0.40% taker
  + 0.10% slippage per side on every rebalance trade.
  Sensitivity variant EMA(50)/EMA(200) is **reported only, never used to decide**.
- **Benchmarks (context only):** BTC buy-and-hold; equal-weight top-30 buy-and-hold, same rebalance.

**Data:** dev period 2021-01-01 → 2026-05-31 only, via `jcoin/research/splits.py`
(slices 2021, 2022, 2023, 2024, 2025, 2026H1).

**Metrics:** CAGR, max drawdown, MAR (CAGR ÷ max drawdown), Sharpe, number of trades, average R (A),
turnover (B), per slice and full period.

**Decision rule:** B replaces A **only if both** hold:
1. B's full-dev-period Sharpe after costs is higher than A's (1× funding), **and**
2. B's MAR beats A's in **at least 4 of the 6** slices.

Otherwise A stays. Ties go to A (incumbent; no switching cost to justify).

**Sealed-window confirmation (the only allowed look):** after the winner is named, run **both**
once on 2026-06-01 → present, log it in the Looks Log, and report it. It **confirms, it does not
select**: the winner is not swapped based on it. If the winner's sealed-window drawdown exceeds its
own worst dev-slice drawdown, **stop and reassess** with Joel before paper-trading it.

**Disclosure:** A's behaviour on 2026-06-01 → 2026-09-18 was already seen once (2026-09-18 audit
replay, logged above), so A's sealed look is not fully blind; B's is.

## 6. Spot long-only test: A_LO (registered 2026-10-18, before any results)

Motivation: r/algotradingcrypto (iSnake37) — "spot long-only is perfectly fine, might even be the
better option" at small size. A spot version could trade today via a US-legal spot API (Kraken),
with no futures venue, no funding, no leverage.

**Contestant A_LO:** strategy A's exact signals and config (BTC+ETH, 4h breakout, ATR init 1.0 /
trail 6.0, max_hold 120, 1% risk, max 1 per symbol / 2 concurrent), **long trades only** — when A
would short, A_LO stays flat. No funding. **Cost: 1.00% round trip** (Kraken spot taker 0.40% +
0.10% slippage, per side). Report-only cost variants: 0.50% round trip (maker-ish) and 2.60% round
trip (Coinbase Advanced lowest-tier taker 1.20% + 0.10% slippage per side). Never used to decide.

**Data:** dev period 2021-01-01 → 2026-05-31 via `splits.py`, same slices as §5. Binance perp
prices as a spot proxy (same as §5).

**Pass rule (all three, on dev data at 1.00% cost):**
1. Profit factor ≥ 1.20 over the full dev period.
2. Full-dev MAR > BTC buy-and-hold MAR over the same period (0.24 from §5), and > 0.
3. Positive return in at least 4 of the 6 slices.

**Sealed confirmation (one look, 2026-06-01 → 2026-09-30, logged):** confirms only. If A_LO's
sealed drawdown exceeds its own worst dev-slice drawdown → stop and reassess with Joel.

If A_LO passes, the next step is a Kraken spot broker adapter + paper run; A (futures) keeps
running in paper in parallel. If it fails, A stays the only candidate and the venue question
(Coinbase nano vs CME micros) remains open.

## 7. Close-based stops: A_CS (registered 2026-10-19, before any results)

Motivation: Coinbase nano futures print rare extreme spikes (>1% beyond Binance ~2×/month per coin) that hit
A's intrabar stops early (`pipeline/COINBASE_PARITY_2026-10.md`). A live resting stop would trigger on them too.

**Contestant A_CS:** strategy A unchanged except stop handling:
- The protective/trailing stop triggers only when a 4h bar **closes** beyond it; exit at that bar's **close**
  (not the stop price — realistic, usually worse).
- Trailing "best" price is tracked on **closes** (not highs/lows).
- **Disaster stop:** if a bar's high/low trades **2.0 ATR beyond** the current stop, exit at that disaster level
  intrabar (this is the order that would rest on the exchange). 2.0 is fixed, not tuned.
- Costs/funding as §5 decision row (12bp + 1× Binance funding on dev).

**Adopt A_CS for live/paper only if BOTH:**
1. Binance dev period (2021-01-01 → 2026-05-31): A_CS full-period Sharpe ≥ 0.90 × A's **and** MAR ≥ 0.90 × A's
   (i.e. not materially worse on the data A was validated on).
2. Coinbase prices, 2025-08-08 → 2026-05-31 (12bp, no funding): A_CS profit factor > A's (0.59).

Report-only: A_CS on Binance over the same 10-month window. No sealed-window look unless adopted; if adopted,
one logged confirmation look per §5 rules.

## 8. Spot-referenced stops: A_SR (registered 2026-10-23, before any code or results)

Motivation: `AUDIT_2026-10-23.md` W4. Coinbase nano stops trigger on the nano last trade only (no mark/index
trigger in the API), and rare thin-book nano spikes clip A's big winners (Coinbase PF 0.59 vs Binance 1.12,
§7 window). Coinbase **spot** (BTC-USD, ETH-USD) is a far deeper book. A live bot could watch spot and close the
nano position with a market IOC order when spot crosses the stop, keeping only a wide resting stop on nano.

**Contestant A_SR:** strategy A's exact rules and config (4h, k=2, ATR(14), init 1.0, trail 6.0, max_hold 120,
1% risk, max 1/symbol, 2 concurrent), except that the price series used for **signals, regime, ATR, trailing
"best" price and the stop trigger is Coinbase spot 4h** (intrabar highs/lows, as in A). Fills are on **nano**:
- Entry = nano close of the signal bar.
- Stop exit = spot stop level × (nano close ÷ spot close) of the exit bar, so the basis is carried over.
- Disaster stop: a resting nano stop **2.0 ATR beyond** the current stop (fixed, same as §7). If nano's
  high/low reaches it, exit there (or at the nano open if the bar gapped past it). If the disaster and the spot
  stop hit in the same bar, take the **worse** fill.
- Time exit = nano close.
- R uses the spot stop distance. Costs 12bp round trip.
- Known optimism: the backtest assumes the spot breach is caught instantly. Live needs ~1-minute polling;
  that latency is not modelled.

**Adopt A_SR for paper only if BOTH:**
1. **Coinbase window** 2025-08-08 → 2026-05-31 (12bp, no funding): A_SR profit factor ≥ **1.00** **and** A_SR
   PF > A's Coinbase PF (0.59), using the same harness for both.
2. **Spot keeps the edge on dev data** 2021-01-01 → 2026-05-31 (12bp, no funding): A run entirely on Coinbase
   spot 4h has Sharpe ≥ 0.90 × and MAR ≥ 0.90 × A on Binance (0× funding, same harness).

Report-only (never used to decide): A on Binance over the Coinbase window; a per-trade table of the trades
common to A and A_SR; how many nano disaster stops fired. ~70 trades means condition 1 is directional
evidence, not proof. No sealed-window look unless adopted; if adopted, one logged look per §5.

## 9. A_SR into PAPER alongside A (registered 2026-10-23, AFTER the §8 result — disclosed)

**Disclosure:** written after §8 returned "DO NOT ADOPT" (Coinbase PF 1.17 passed; spot-dev MAR 0.99 missed
the 1.23 bar, Sharpe 0.89 vs 0.90). This is a new decision, not an edit of §8, and it is weaker evidence for
having been made after seeing results. Joel's decision, 2026-10-23: the §8 90% bar (copied from §7) was set
too strict for a **paper-only** step that risks no money. §8's verdict stands as recorded.

**Decision:** A_SR runs in paper on the VM **alongside** A. A is unchanged and keeps its own state, its clock
and its kill rule. Neither is switched off or swapped because of early paper results.

**A_SR paper spec (fixed):** the §8 contestant, live.
- Signals, regime, ATR and the trailing stop come from Coinbase spot 4h (BTC-USD, ETH-USD). The trail updates
  at each 4h close from the bar's high/low.
- Stop trigger: the spot 1-minute high/low, processed hourly from 1-minute candles (what a 1-minute poller
  would see, without its latency).
- Fills on nano:
  - Entry = nano 4h close of the signal bar.
  - Stop exit = stop × (nano ÷ spot) close of that minute.
  - Disaster = resting nano stop 2.0 ATR beyond the stop, checked on nano 1-minute bars.
  - Same minute: take the worse fill.
  - Time exit after 120 bars = nano 4h close.
- Costs: 12bp round trip, plus Coinbase hourly funding at the current published rate.
- Sizing: whole contracts, same `RiskConfig` as A paper (1% risk, notional ≤ 1× equity, ≤ 2× target risk).
- Account: $1,000 start, separate state dir `paper_state_sr/`. No cycle filter (§8 had none).
- Hard halt at the same thresholds as `KILL_RULE.md` (39.8% DD or >33 consecutive R≤0), latched.

**Gate to REAL money for A_SR (fixed now, before any A_SR paper data). ALL required:**
1. ≥ 6 months of A_SR paper **and** ≥ 30 closed paper trades.
2. **Execution parity:** re-running the §8 harness on the same Coinbase data reproduces ≥ 90% of the paper
   trades (same entry bar and side), each within 0.25R. This proves the live code is the tested code.
3. No hard-halt trip, and paper average R ≥ **−0.69**. That is the 5th percentile of a 30-trade average R
   bootstrapped from A's 402 Coinbase-spot dev trades (seed 20261023; dev mean +0.48). Honest limit: 30 trades
   can only catch a *broken* strategy, not prove an edge.
4. A written, dated go decision by Joel. Live code reviewed. Auto-update **off**. Manual deploy.
