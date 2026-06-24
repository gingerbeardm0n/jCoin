# Concept: Liquidation Cascade Reversal

> **⛔ DEPRECATED 2026-06-19 — DO NOT BUILD.** Two independent reasons:
> 1. **Data NO-GO** (see `DATA_AVAILABILITY.md`): Coinbase publishes no liquidation data; Kraken only thin own-venue. Real liquidation data lives on Binance/Bybit (untradeable for US no-VPN) → no backtest/live parity.
> 2. **Spec §3 forbids it**: listed under "Explicitly NOT building — highest blowup risk."
> Kept for reference only. Liquidation *confirmations* in other concepts are demoted to optional Kraken-only context, never a hard entry gate.

**Last updated:** 2026-06-19
**Source:** TradingRiot (Batch1 ITEM 2, ITEM 16; Batch2 ITEM 5)
**Sample size:** 0 verified fills (claimed/implied examples)
**Win rate:** "10-day forward return slopes up after long flushes" — directional claim, no win% cited

---

## Source Items Merged

| Item | Source | Name |
|------|--------|------|
| Batch1 ITEM 2 | tradingriot_crypto_guide_compressed.md | Liquidation Cascade Entry |
| Batch2 ITEM 5 | tradingriot_liquidity_compressed.md | Post-Liquidation Cascade Reversal |
| Batch1 ITEM 16 | tradingriot_when_bitcoin_bottoms_compressed.md | BTC Bottom Composite Regime |

---

## Definition

Enter after a liquidation cascade flushes leveraged positions, confirmed by open-interest drop (forced closures, not new short entries) and funding normalization. The cascade creates an overreaction — price moves beyond fair value as stop-losses and liquidation orders chain — and the reversal opportunity arises once the flush is complete and the forced-selling pressure is exhausted.

Key distinctions:
- **vs. catching falling knives:** requires OI drop confirmation — distinguishes forced liquidation (OI falls) from deliberate short positioning (OI rises); the latter is not a reversal setup
- **vs. VWAP Band Fade:** VWAP band provides the statistical location; this concept is triggered by the event (cascade) rather than a statistical extreme — both can fire simultaneously for highest conviction
- **vs. Liquidation Continuation (Batch1 ITEM 13):** that setup is for trend-following AFTER liq; this setup is the REVERSAL — opposite direction

---

## Setup Criteria

### Required

| Criterion | Target | Notes |
|-----------|--------|-------|
| Market regime | post-liquidation | Cascade must have completed; price slowing after spike |
| Liquidation signal | Sharp price spike + OI drop simultaneously | OI drop = forced closures confirmed; required |
| OI drop threshold | OI drop ≥ 3% of total OI in cascade window | Batch2 ITEM 5: `oi_drop_pct_threshold = 0.03` |
| Price spike magnitude | Spike ≥ 2.0 × ATR | Batch2 ITEM 5: `spike_atr_mult = 2.0` |
| Liq z-score | Long liquidation z-score ≤ -2.0 (for long entry) | Batch1 ITEM 2: `liq_zscore_entry = -2.0` |
| Price slowing | Price must slow (market not continuing cascade direction) | Batch2 ITEM 5: "market slows and begins accumulation" |

### Composite Regime (BTC Bottom — ITEM 16, highest conviction)

For BTC-specific bottom detection, all four components must enter "red zone":
1. OI decreasing (z-score < -1.0)
2. Funding negative (< -0.02% per 8h)
3. Put overpayment / negative risk reversal (RR z-score > +1.5) — requires options data
4. Realized vol > implied vol (`rv_iv_ratio > 1.0`)

Note: Component 3 requires Deribit options feed (BTC/ETH only). Components 1+2 are sufficient without options data for non-BTC or when options data unavailable.

### Ideal (increases conviction)

- Funding normalizing (moving toward 0) after being deeply negative
- Post-cascade price behavior: "accumulation/distribution then return" — not straight-line reversal
- 10-day forward return historically positive after long liquidation flush (Batch1 ITEM 2)
- Leviathan heatmap levels (estimated liquidation clusters) confirm cascade hit a known cluster

---

## Entry Trigger

**Primary trigger:** OI drop confirmation + price slowing after cascade spike.

**Mechanism:**
1. Detect cascade: price moves ≥ 2.0×ATR in one direction within a short window
2. Confirm OI drop ≥ 3% simultaneously (forced closures, not new shorts entering)
3. Confirm long liquidation z-score ≤ -2.0 (longs being flushed, not shorts piling in)
4. Wait for price to slow (not continuing cascade direction) — 3+ bars without new extreme
5. Post maker limit at or near cascade level; target pre-spike level

**Time of entry:** After cascade completes and price shows first signs of slowing; maker pre-load at cascade low/high; do not chase

---

## Add-On Mechanics

| Mechanic | Frequency | Description |
|----------|-----------|-------------|
| Zone-based entry | Primary | "Use zone-based entries" (ITEM 16) — not exact bottom catching |
| Scale in on accumulation | Secondary | If price shows accumulation signals (volume declining, range compressing post-cascade) |

**Key principle:** TradingRiot ITEM 16: "Avoid exact bottom catching; use zone-based entries." The cascade creates a zone, not a point. Size conservatively; fade into the zone.

---

## Stop Criteria

| Stop Type | When to Use |
|-----------|-------------|
| Beyond cascade spike extreme | Always — beyond the wick/spike low (for long) or high (for short) |
| Continuation signal | If price resumes cascade direction without slowing → exit; "price continues in cascade direction without slowing" = invalidation |

**Stop placement:** Beyond cascade spike extreme (Batch2 ITEM 5: "stop beyond cascade spike extreme")

**Critical rule:** If OI is not dropping during the price spike, the move is driven by fresh shorts/longs entering — NOT a liquidation cascade. Do not enter.

---

## Profit Targets

| Target Type | How Determined | Notes |
|-------------|---|---|
| T1 | Pre-spike level / prior value area mean | "Mean-revert to pre-spike level" (Batch2 ITEM 5) |
| T2 | Recovery trend target (if regime exits red zone) | ITEM 16: "trend following once regime exits red zone" |

**Observed behavior:** ITEM 2: "10-day forward return slopes up after long flushes" — not a scalp, a swing entry.

---

## Hold Duration

| Duration | Notes |
|----------|-------|
| Swing (days) | "10-day forward return" context (Batch1 ITEM 2) suggests this is not a scalp |
| Medium (hours–days) | Batch2 ITEM 5: "market accumulates then returns" — takes time after cascade |

---

## Market Condition Dependency

- **Isolated cascade (not macro downtrend):** Best results — cascade is event-driven overreaction in otherwise balanced market
- **BTC cascade at composite regime red zone:** Highest conviction (all 4 ITEM 16 components)
- **Cascade in ongoing trend:** Lower confidence — forced closures may be first wave of larger capitulation; reduce size or skip
- **Multiple cascades in sequence:** Capitulation may be multi-wave; wait for OI + funding to stabilize before entering

---

## Red Flags (When to Skip)

- OI rising during price spike (new short entries, not forced liquidations — NOT a cascade reversal)
- Price continues cascade direction without slowing (capitulation extending — no entry)
- Funding remains deeply negative without normalizing after cascade (fear not exhausted)
- Cascade in trending market (may be wave 1 of larger deleveraging)
- No OI data available — cannot distinguish liquidation from directional short campaign

---

## Example Trades (from extraction)

**Batch1 ITEM 2 — Any (Long Liquidation Cascade Entry):**
Large long liquidation z-score deeply negative (≤ -2.0). OI fell during cascade (forced closures, not new shorts). "Long shakeouts = historically good entry for new longs." 10-day forward return positive. Lesson: OI fall is the distinguishing signal — it's not more shorts entering, it's longs getting forced out.

**Batch2 ITEM 5 — Any (Post-Liquidation Cascade Reversal):**
Sharp price spike + visible OI drop. Market slows, begins accumulation. Enter maker at cascade level. Target: mean-revert to pre-spike level. Stop: beyond spike extreme. "Market does not move in straight lines after large liquidation events."

**Batch1 ITEM 16 — BTC (Composite Bottom Regime):**
All four components in red zone: OI decreasing + negative funding + put overpayment + realized vol > implied vol. "Sentiment exhausted — everyone given up." Zone-based long entry. Target: recovery trend. Lesson: use composite indicator for bottoms, not any single signal alone.

---

## Codeable Assessment

**Codeable: PARTIAL**

Core components codeable:
- OI drop ≥ 3%: yes (OI feed required)
- Spike ≥ 2.0×ATR: yes (candle data)
- Liquidation z-score: partial (liquidation feed — Binance/Bybit liquidation websocket)
- Funding normalization: yes (funding feed)

Composite regime (ITEM 16 full version):
- Components 1+2: yes
- Component 3 (options RR): partial — requires Deribit options feed (BTC/ETH only); deprioritize for v1
- Component 4 (rv/iv ratio): partial — realized vol from candles yes; implied vol requires options feed

**v1 recommendation:** Implement components 1+2+liq_zscore only; add options components in v2.

---

## Parameter Inventory

| Parameter | Source | Proposed Start Value |
|-----------|--------|---------------------|
| `oi_drop_pct_threshold` | Batch2 ITEM 5 | `0.03` (3% OI drop in cascade window) |
| `spike_atr_mult` | Batch2 ITEM 5 | `2.0` (spike ≥ 2×ATR = cascade) |
| `liq_zscore_entry` | Batch1 ITEM 2 | `-2.0` (long liquidation z-score threshold) |
| `cascade_slow_bars` | Batch2 ITEM 5 (inferred) | `3` (price doesn't make new extreme for 3 bars = slowing) |
| `funding_normalization_gate` | Batch1 ITEM 16 | `> -0.02%` per 8h (funding moving toward zero) |
| `oi_falling_zscore_regime` | Batch1 ITEM 16 | `-1.0` (composite regime component) |
| `rv_iv_ratio` | Batch1 ITEM 16 | `1.0` (realized vol / implied vol > 1.0; v2 only) |

**Param count: 7 (5 for v1 without options components)**
**Toward 13–15 cap: 7 used here (5 primary)**

---

## jCoin Decision Rules

```
LIQUIDATION_CASCADE_REVERSAL entry conditions:

  DETECT CASCADE:
    price_move_bars = 1–3 bars with total move >= spike_atr_mult (2.0) * ATR
    oi_drop_pct = (OI_before - OI_after) / OI_before >= oi_drop_pct_threshold (0.03)
    liq_long_zscore <= liq_zscore_entry (-2.0)       [for long entry]
    liq_short_zscore >= abs(liq_zscore_entry) (2.0)  [for short entry — inverted]

  CONFIRM CASCADE COMPLETE:
    price_slow = bars_since_new_extreme >= cascade_slow_bars (3)
    (price is not making new lows/highs after cascade)

  OPTIONAL REGIME GATE (BTC — highest conviction):
    oi_zscore < oi_falling_zscore_regime (-1.0)
    AND funding_rate < -0.02% per 8h  (funding_normalization_gate)
    [+ options components for v2]

IF cascade confirmed AND price slowing:
  THEN post maker limit at cascade zone (spike level ± 0.5*ATR)
       stop = cascade_spike_extreme (beyond the wick)
       target_T1 = pre_spike_level (prior value area mean)
       target_T2 = recovery trend target (if regime exits red zone)
       risk = 0.5% equity
       hold = swing (up to 10 days; exit if OI/funding re-deteriorate)

INVALIDATION:
  oi RISING during price spike (not liquidation — new shorts entering → skip)
  OR price resumes cascade direction after entry (cascade continuing)
  OR funding remains deeply negative without normalization
```

---

## Data Coverage & Confidence

| Field | Coverage | Confidence | Notes |
|-------|----------|-----------|-------|
| OI drop trigger | 2 items | High | Consistent across ITEM 2 and ITEM 5 |
| Spike magnitude | 1 item | Medium | 2×ATR from ITEM 5 only |
| Liq z-score threshold | 1 item | Medium | -2.0 from ITEM 2; single source |
| Target logic | 2 items | Medium | Pre-spike level consistent |
| Composite regime | 1 item | Low | ITEM 16 is BTC-specific; partial options dependency |
| Stop placement | 1 item | Medium | "Beyond spike extreme" — not a specific distance |

**Next pass:** Validate OI drop % threshold against real cascade events; confirm whether 3% drop is too low/high for different market conditions.

---

## Aggregated Educator Consensus

- TradingRiot (3 items): consistent "OI drop = forced liquidation = reversal signal" thesis
- **Conflicts:** ITEM 16 (BTC composite) adds options components (RR, IV); other items don't use options — treat composite as enhanced version, not required for basic setup
- **Highest confidence elements:** OI drop during spike = forced liquidation (not new shorts), target = pre-spike level

---

*End of concept_liquidation_cascade_reversal.md*
