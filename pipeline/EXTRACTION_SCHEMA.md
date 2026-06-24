# jCoin — Educator Extraction Schema

**Status:** Draft v0.1 — approval gate before any pipeline agent runs
**Date:** 2026-06-19
**Purpose:** The fixed field set every educator clip/article gets compressed into. One row = one tradeable rule or one reusable concept. If a source can't fill the mandatory fields, it's noise — drop it.

> Scope of this pass: feed **Strategy 1 (maker mean-reversion)** first. Breakout/funding fields exist but are tagged `[later]` — capture if seen, don't chase.

---

## A. Source provenance (every extracted item carries these)

| Field | What | Example |
|---|---|---|
| `educator` | TradingRiot / Trader Mayne / CanteringClark | `TradingRiot` |
| `source_id` | video URL / title / timestamp | `yt:abc123 @ 14:32` |
| `claim_type` | `rule` \| `concept` \| `anecdote` \| `opinion` | `rule` |
| `confidence` | did they state it as a system, or muse? `stated` \| `implied` \| `vibe` | `stated` |
| `verified_track_record` | do they show fills/PnL for this, or just talk? `shown` \| `claimed` \| `none` | `claimed` |

`anecdote`/`opinion`/`vibe` items get logged but never become engine rules without corroboration. (jTrader lesson: don't encode an educator's vibe as a parameter.)

---

## B. Setup definition (the core — mean-reversion entry)

| Field | What | Mandatory? |
|---|---|---|
| `setup_name` | their label | yes |
| `market_regime` | when valid: `range` / `trend` / `post-liquidation` / `any` | yes |
| `instrument_scope` | BTC / ETH / alts / any | yes |
| `zone_definition` | HOW they locate the extreme: VWAP band, prior S/R, demand block, liquidity sweep level, Bollinger/Keltner, round number, prior session high/low | yes |
| `trigger` | what fires entry once price reaches zone (e.g. "wick rejection + CVD divergence") | yes |
| `entry_execution` | `maker` (resting limit at zone) / `taker` (confirmation then cross) | yes — flags fee cost |
| `direction_logic` | long-only / short-only / both, and the bias rule | yes |

---

## C. Confirmation / veto signals (the order-flow overlay)

Maps to jCoin's CVD-veto + regime-filter guards. Capture each as present/absent + the threshold they cite.

| Field | What |
|---|---|
| `cvd_signal` | cumulative volume delta use — divergence, absorption, exhaustion |
| `oi_signal` | open-interest behavior at the zone (rising into top = trapped longs, etc.) |
| `funding_signal` | funding extreme as a contrarian tell |
| `liquidation_signal` | liq cascade / wick as entry context |
| `volume_profile` | POC, value-area edge, HVN/LVN reference |
| `confluence_count` | how many must align before they take it |

---

## D. Trade management (turns a setup into a closed loop)

| Field | What | Mandatory? |
|---|---|---|
| `invalidation` | exact price/condition that voids the idea (→ becomes the hard stop) | yes |
| `stop_placement` | where + why (beyond sweep wick, beyond block, ATR mult) | yes |
| `target_logic` | mean / VWAP / opposing zone / fixed R | yes |
| `r_multiple` | typical risk:reward they cite | if stated |
| `scale_rules` | partial-take / add rules | if stated |
| `time_stop` | bail if no move in N bars? | if stated |
| `funding_avoidance` | do they flatten before funding stamp? | if stated |

---

## E. Quantify-ability (the bridge to code)

The whole point. Each item scored for whether jCoin can actually implement it.

| Field | Values |
|---|---|
| `codeable` | `yes` (objective threshold) / `partial` (needs proxy) / `no` (discretionary "feel") |
| `data_need` | `candles` / `tick-trades` / `orderbook` / `funding` / `OI` — what feed it requires |
| `proposed_param` | if codeable: the param + a starting value (e.g. `zscore_entry = 2.0`) |
| `param_count_note` | flag toward the ~13–15 cap (jTrader lesson) |

Items marked `codeable: no` go to a "discretionary" bucket — studied, not coded.

---

## F. `[later]` fields (capture-if-seen, don't chase this pass)

- `breakout_*` — range-break trigger, expansion volume, retest logic (Strategy 2)
- `funding_carry_*` — basis, APR, delta-neutral construction (Strategy 3, >$15k)

---

## Output shape

Pipeline produces one **concept page** per distinct setup (not one per video), aggregating all sources that describe it, ending in a **Decision Rule** pseudo-code block:

```
IF regime == range
   AND price in zone (VWAP - 2σ)
   AND cvd_divergence == true
   AND funding not extreme-same-direction
THEN post maker bid at zone
     stop = zone_low - 0.3·ATR
     target = VWAP
     risk = 0.5% equity
```

That block is the only thing the engine consumes. Everything above is the audit trail behind it.

---

## Approval gate

Schema locked? → next: Haiku agent adapts jTrader's 4 pipeline prompts (compression / extraction / enrichment / concept-template) to emit THIS schema. Then real corpus run (fresh session).
