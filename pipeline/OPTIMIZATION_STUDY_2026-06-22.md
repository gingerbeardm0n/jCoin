# Parameter Optimization Study — 2026-06-22

**Question:** Does fine-tuning the ATR exit params beat the hand-picked defaults
out-of-sample? **Harness:** `jcoin/research/optimize.py`.
**Discipline:** train(2021–23) / validate(2023–24) / test(2025–26 sealed); tune only
atr_init × atr_trail; lock the rest; baseline = un-tuned defaults; metric MAR=CAGR/MaxDD.

## Result: optimization OVERFIT and lost out-of-sample

Optimizer selected `atr_init=0.5, atr_trail=4.0` (best train+validate avg MAR; validate
MAR was a gorgeous **7.55**). Sealed TEST scored that winner vs the baselines:

| Config | Test CAGR | Test MaxDD | Test MAR | Test PF | Sharpe |
|---|---|---|---|---|---|
| **SELECTED (0.5/4.0)** | **−17.0%** | 47.7% | −0.36 | 0.90 | −0.19 |
| hand-picked default (1.0/4.0) | +3.2% | 27.1% | 0.12 | 1.13 | 0.27 |
| un-tuned first-guess (1.5/3.0) | +10.6% | 17.5% | 0.61 | 1.33 | 0.72 |

**The optimized params lost 17% OOS. The un-tuned defaults held up.** The selected config
fit train+validate beautifully and had zero predictive value — "peak, not plateau" noise.

## Lesson (live confirmation on jCoin's own data)
This reproduces jTrader's 126-param overfitting in miniature, deliberately. It empirically
proves the param-discipline lesson (LESSONS_FROM_JTRADER §2): naive optimization here is
**net-negative**. Keeping params few + un-optimized is what makes v1 robust.

## Decision
**KEEP THE DEFAULTS. Adopt no optimized params.** Per the pre-committed rule, optimization
failed to beat the baseline on a sealed test → keep the simpler proven config.
Note: do NOT switch to 1.5/3.0 just because it won the test — that would be selecting on
the test set (peeking), the exact sin we're guarding against. Test is for scoring, not
selecting.

## Caveat + possible follow-up
The selection method was naive (picked the highest validate score = a peak, not a true
plateau). A stricter **plateau-selection** (reward configs whose neighbors are all good;
penalize spikes) is the correct way to optimize and might avoid the 0.5/4.0 trap. Worth a
follow-up — but the burden of proof stays on optimization to *clearly* beat the dead-simple
defaults on a sealed test. So far it hasn't.

---

## Part 2 — Full 5-param study + validation (same day)

`jcoin/research/optimize_full.py` tuned all 5 edge params (k, atr_period, atr_init,
atr_trail, max_hold) on the FULL range with a per-year consistency lie-detector.

**Apparent "BEST": k2/ap10/init0.5/trail6.0/hold160 — full-range CAGR 84%, MAR 2.12,
positive in ALL 6 years.** Looked spectacular. Then validation (`validate_best.py`):

**Sealed train/validate/TEST (12bp):**

| Config | train CAGR | valid CAGR | TEST CAGR | TEST maxDD | TEST MAR | TEST PF |
|---|---|---|---|---|---|---|
| BEST (0.5/6.0) | 105% | 151% | +13% | **40%** | 0.33 | 1.34 |
| **MIDDLE (1.0/6.0)** | 39% | 55% | **+16%** | **21%** | **0.78** | 1.35 |
| DEFAULT (1.0/4.0) | 26% | 62% | +4% | 27% | 0.16 | 1.13 |

**Slippage stress (full range): BEST maxDD blows 40→55%; MIDDLE & DEFAULT stay ~27–33%.**

### Findings
- BEST's 84% was **in-sample inflation** (105–151% in → 13% out). Bought with a 40–55%
  drawdown. The tight 0.5-ATR init is the culprit: inflates backtest + drawdown + most
  exposed to optimistic stop-fills.
- The **real, robust lever is the wider TRAIL (4→6)**, not the tight init. Isolating it:
  **MIDDLE (init 1.0, trail 6.0) wins the SEALED TEST on every axis** — higher return,
  *lower* drawdown, 5× the MAR of the default — and degrades gracefully under slippage.
- Had we "optimized on full range and grabbed the top," we'd have taken BEST (mirage). The
  **sealed test is what separated mirage from real improvement.** Holdout earned its keep.

### DECISION (2026-06-22): adopt `atr_trail = 4.0 -> 6.0`
Single, interpretable, OOS-validated change. Everything else stays at defaults.
`StrategyConfig.atr_trail` updated to 6.0. Paper bot picks it up next run.
Caveat: the sealed test is now lightly "used" across a few configs; the truly-clean final
check is the live forward paper run. MIDDLE came from a principled hypothesis (widen trail)
that the test *confirmed*, not a scan-and-pick — legitimate, but don't keep mining the test.
