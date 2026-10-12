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
