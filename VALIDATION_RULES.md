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
