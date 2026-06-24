# Concept: VWAP Band Fade

**Last updated:** 2026-06-19
**Source:** TradingRiot (Batch1 ITEM 4, ITEM 14; Batch2 ITEM 4, ITEM 12)
**Sample size:** 0 verified fills (claimed examples only)
**Win rate:** not stated

---

## Source Items Merged

| Item | Source | Name |
|------|--------|------|
| Batch2 ITEM 4 | tradingriot_auction_market_theory_compressed.md | VWAP + SD Band Mean Reversion |
| Batch1 ITEM 4 | tradingriot_crypto_guide_compressed.md | Froth Fade (OI Spike + Hard Positive Funding) |
| Batch1 ITEM 14 | tradingriot_crypto_data_compressed.md | ETH Multi-Signal Mean Reversion Short |
| Batch2 ITEM 12 | tradingriot_volume_analysis_compressed.md | Volume Delta Divergence — Absorption at Extreme |

---

## Definition

Fade price when it reaches a statistically extreme deviation from VWAP (±2 standard deviations), confirmed by OI/funding froth (crowded positioning) and CVD absorption (sellers/buyers being soaked up at the extreme). The zone provides the location, the froth signals provide the "why it will snap back," and the absorption signal provides the "now" trigger.

Key distinctions:
- **vs. blind VWAP band touch:** requires OI/funding confirmation — price can extend at bands in trending markets; froth/absorption filter suppresses trend-day failures
- **vs. OI/funding fade alone:** requires a structural price zone (VWAP ±2σ) — filters entries that occur in the middle of nowhere

---

## Setup Criteria

### Required

| Criterion | Target | Notes |
|-----------|--------|-------|
| Market regime | range | AMT: price inside value area = range expected; trending days invalidate |
| Price zone | VWAP ±2σ (standard deviation bands) | Daily VWAP preferred; entry at the band, target = VWAP |
| OI signal | OI z-score elevated ≥ +2.0 at highs (short fade) OR OI falling z-score ≤ -1.5 at lows (long fade) | Elevated OI at highs = trapped longs; falling OI at lows = forced exits |
| Funding signal | Hard positive ≥ +0.10% per 8h (short fade) OR negative ≤ -0.05% per 8h (long fade) | Crowded positioning in fade direction = fuel for snap |
| Absorption signal | High rVOL candle (≥ 2.0 SD above mean) at zone with near-zero delta (delta < 10% of volume) | Absorption = opposing side soaking up aggression; mean-reversion likely |

### Ideal (increases conviction)

- Short liquidations spiking at highs (last bears squeezed = buying exhausted) — z-score ≥ +2.0 (Batch1 ITEM 4)
- Long liquidations rising into lows (longs flushed) — z-score ≥ +2.0 (Batch1 ITEM 14)
- Sell-off + falling OI (forced exits, not fresh shorts) — not new shorts entering (Batch1 ITEM 14)
- All four ETH signals: sell-off + falling OI + negative funding + rising long liquidations ("very strong mean-reversion signal")

---

## Entry Trigger

**Primary trigger:** Absorption candle at VWAP ±2σ band confirmed by OI/funding froth.

**Mechanism:**
1. Identify VWAP ±2σ zone on daily VWAP (recalculates intraday)
2. Confirm OI z-score ≥ +2.0 (shorts) or falling OI at lows (longs); confirm funding extreme in fade direction
3. Wait for high-rVOL candle at the zone with near-zero delta (delta < 10% of volume on that candle)
4. Post maker limit at zone; fill before price turns

**Time of entry:** After absorption candle prints at VWAP band extreme; requires patience — do not anticipate, wait for the candle to close

---

## Add-On Mechanics

| Mechanic | Frequency | Description |
|----------|-----------|-------------|
| Single entry at zone | Primary | Post maker at VWAP ±2σ level, no scale-in |
| Scale-in on confirmation | Secondary | Only if short liquidations (or long liq) confirm after initial fill |

**Key principle:** TradingRiot: "Little fuel left. Snap brutal." — size the initial entry; the snap is fast, scale-in may miss it.

---

## Stop Criteria

| Stop Type | When to Use |
|-----------|-------------|
| Hard stop beyond band | Always; price accepting outside VWAP ±2σ invalidates range assumption |
| OI continuation stop | If OI continues rising with price (trend resuming, not reversal) — exit immediately |

**Stop placement:** Band level extreme − 0.3 × ATR (or beyond absorption candle extreme for tight stops)

**Critical rule:** If price closes and holds beyond the SD band (AMT Rule: acceptance outside = breakout), exit. The setup is a range-regime trade; acceptance outside = regime change.

---

## Profit Targets

| Target Type | How Determined | Notes |
|-------------|---|---|
| T1 | VWAP (daily mean) | Primary target; "fairest price" per AMT |
| T2 | Opposite VWAP band (±1σ or ±2σ) | If momentum carries through VWAP |

**Observed behavior:** ZEC example from Batch1 ITEM 4 — snap −25% into prior mid-level. Target defined BEFORE entry ("must have target before entering fade" — Batch1 ITEM 5).

---

## Hold Duration

| Duration | Notes |
|----------|-------|
| Intraday (hours) | "Fade is short-lived, not weeks" (Batch1 ITEM 4) |
| Days (maximum) | Only if OI/funding remain extreme — reassess each 8h funding stamp |

---

## Market Condition Dependency

- **Ranging day (AMT inside value area):** Full setup valid; highest win probability
- **Trending day:** Skip — VWAP bands can stretch without reverting; OI/funding signals may not fire
- **Post-liquidation environment:** Combine with Concept 3 (liquidation cascade reversal) for higher conviction

---

## Red Flags (When to Skip)

- OI rising with no retreat after touch (trend continuation, not exhaustion)
- Funding extreme in same direction as move with no absorption candle (blowoff not complete)
- Price accepts (closes) outside VWAP ±2σ band — setup is invalid, don't re-enter immediately
- High rVOL + high same-direction delta at band = genuine breakout, NOT absorption — skip
- Trending market structure (AMT: price outside value area consistently)

---

## Example Trades (from extraction)

**Batch1 ITEM 4 — ZEC (Froth Fade):**
OI spiked to z-score extreme + funding hard positive + short liquidations hit at highs (last bears squeezed). Entered short. Snapped −25% into prior mid-level. Lesson: "When data confirms, one side flushed, level to aim at."

**Batch1 ITEM 14 — ETH (Multi-Signal Short Fade):**
Sell-off with falling OI (forced closures, not new shorts) + negative funding (fear extreme) + rising long liquidations. All four signals aligned. "Very strong mean-reversion signal." Long entry after exhaustion confirmed.

---

## Codeable Assessment

**Codeable: PARTIAL → HIGH**

All components have objective thresholds:
- VWAP + SD bands: standard calculation, yes
- OI z-score: yes (requires OI feed)
- Funding rate threshold: yes (requires funding feed)
- Absorption candle (high rVOL + near-zero delta): yes (requires tick-trades for delta; candles for rVOL)
- Liquidation z-score: partial (requires liquidation data feed — Binance/Bybit liquidation websocket)

Primary friction: liquidation feed for highest-conviction confirmation. Core logic (VWAP band + OI + funding + absorption) is fully codeable without it.

---

## Parameter Inventory

| Parameter | Source | Proposed Start Value |
|-----------|--------|---------------------|
| `vwap_period` | Batch2 ITEM 4 | `daily` (reset each session) |
| `vwap_sd_entry` | Batch2 ITEM 4, ITEM 1 | `2.0` (standard deviations) |
| `oi_zscore_fade_high` | Batch1 ITEM 4 | `2.0` (OI extreme at highs for short) |
| `oi_falling_zscore` | Batch1 ITEM 14 | `-1.5` (falling OI at lows for long) |
| `funding_extreme_positive` | Batch1 ITEM 4 | `0.10%` per 8h |
| `funding_extreme_negative` | Batch1 ITEM 14 | `-0.05%` per 8h |
| `absorption_rvol_sd` | Batch2 ITEM 12 | `2.0` (rVOL spike threshold) |
| `absorption_delta_pct` | Batch2 ITEM 12 | `0.10` (delta < 10% of volume = absorbed) |
| `stop_atr_mult` | inferred | `0.3` (stop = band − 0.3×ATR) |
| `risk_per_trade` | schema default | `0.5%` equity |

**Param count: 10**
**Toward 13–15 cap: 10 used here; 3–5 remaining for shared infrastructure (zscore_window, etc.)**

---

## jCoin Decision Rules

```
VWAP_BAND_FADE entry conditions:

  PRE-FILTER (regime gate):
    market_regime == range
    (price inside value area 68% OR price oscillating between VWAP bands)

  ZONE (where):
    price >= VWAP + (vwap_sd_entry * daily_sd)    → SHORT setup
    price <= VWAP - (vwap_sd_entry * daily_sd)    → LONG setup

  FROTH CONFIRMATION (why it will snap):
    SHORT: oi_zscore >= oi_zscore_fade_high (2.0)
           AND funding_rate >= funding_extreme_positive (0.10% per 8h)
    LONG:  oi_zscore <= oi_falling_zscore (-1.5)
           AND funding_rate <= funding_extreme_negative (-0.05% per 8h)

  ABSORPTION TRIGGER (when to enter):
    candle.rvol >= VWAP_band + absorption_rvol_sd (2.0 SD above mean)
    AND abs(candle.delta) / candle.volume <= absorption_delta_pct (0.10)

  IDEAL (add conviction, not required):
    SHORT: liq_short_zscore >= 2.0 (last bears squeezed)
    LONG:  liq_long_zscore >= 2.0 (longs flushed)

IF all required conditions met:
  THEN post maker limit at VWAP ±2σ band level
       stop = band_level - (0.3 * ATR)           [short: band + 0.3*ATR]
       target_T1 = VWAP
       target_T2 = opposite_vwap_band
       risk = 0.5% equity

INVALIDATION (exit immediately if triggered after entry):
  price accepts (closes) outside VWAP ±2σ band
  OR oi_zscore continues rising with no absorption (trend resuming)
  OR high_rvol_candle with high_same_direction_delta at band (breakout, not fade)
```

---

## Data Coverage & Confidence

| Field | Coverage | Confidence | Notes |
|-------|----------|-----------|-------|
| Zone definition | 4 items | High | VWAP ±2σ consistent across all |
| OI signal | 3 items | High | Thresholds explicitly stated |
| Funding signal | 3 items | High | Thresholds explicitly stated |
| Absorption trigger | 1 item | Medium | Batch2 ITEM 12 only; logical complement |
| Liquidation confirmation | 2 items | Medium | Enhances but not required |
| Stop placement | 1 item (inferred) | Low | 0.3×ATR not explicitly stated; derived from AMT "beyond the band" |

**Next pass:** Verify absorption delta threshold (10%) against more examples; confirm daily vs. anchored VWAP preference.

---

## Aggregated Educator Consensus

- TradingRiot (all 4 sources): Consistent framing — VWAP bands are the zone, OI/funding are the "why," absorption is the timing trigger
- **Conflicts:** None material; ITEM 4 (Batch1) is short-focused, ITEM 14 (Batch1) is long-focused — both are the same concept applied symmetrically
- **Highest confidence elements:** `vwap_sd_entry = 2.0`, `funding_extreme_positive = 0.10%`, `absorption_delta_pct = 0.10`, target = VWAP

---

*End of concept_vwap_band_fade.md*
