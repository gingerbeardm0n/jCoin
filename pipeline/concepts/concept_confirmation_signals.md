# Concept: Confirmation Signals (Veto / Overlay Layer)

**Last updated:** 2026-06-19
**Source:** TradingRiot (Batch1 ITEM 1, ITEM 7, ITEM 8, ITEM 11; Batch2 ITEM 6, ITEM 7)
**Sample size:** N/A — these are filters, not standalone setups
**Win rate:** N/A — impact measured via reduction of false signals on other concepts

---

## Source Items Merged

| Item | Source | Name |
|------|--------|------|
| Batch1 ITEM 1 | tradingriot_crypto_guide_compressed.md | Funding Rate Mechanics |
| Batch1 ITEM 7 | tradingriot_crypto_guide_compressed.md | OI Spike + Negative Funding Early Long |
| Batch1 ITEM 8 | tradingriot_crypto_guide_compressed.md | Spot Order Book Skew Confluence |
| Batch1 ITEM 11 | tradingriot_crypto_guide_compressed.md | Z-Score Extremes Framework |
| Batch2 ITEM 6 | tradingriot_order_book_compressed.md | Order Book Delta Imbalance Confluence |
| Batch2 ITEM 7 | tradingriot_order_book_compressed.md | Spot vs Futures Book Divergence Signal |

---

## Definition

This concept is NOT a standalone trading setup. It is the veto/confirmation overlay that gates entry on Concepts 1, 2, and 3. These signals operate as additional filters: they either confirm a setup (increasing conviction) or veto it (blocking entry despite a valid zone/trigger). Applying these filters reduces false signals and improves the signal-to-noise ratio of the engine.

Key distinctions:
- **vs. setup concepts (1, 2, 3):** Those concepts define WHERE and WHEN. This concept defines WHETHER — the additional confirmation or veto layer.
- **Confirmation signals:** increase position conviction when aligned with setup direction
- **Veto signals:** block entry when contradicting setup direction (even if zone and trigger are valid)

---

## Signal Inventory

### Signal A — Funding Rate State (Batch1 ITEM 1)

**What it measures:** Crowd positioning sentiment; whether longs or shorts are paying funding.

**Thresholds:**
- Normal range: -0.04% to +0.06% per 8h (interest-only zone, no signal)
- Elevated (signal): > +0.05% per 8h (longs crowded) OR < -0.05% per 8h (shorts crowded)
- Extreme (strong signal): > +0.10% per 8h OR < -0.10% per 8h

**Veto rule for fades:**
- Fading UP (short): funding must be elevated-to-extreme positive — confirms crowded longs; if funding is negative or neutral, skip the fade
- Fading DOWN (long): funding must be elevated-to-extreme negative — confirms crowded shorts; if funding is positive or neutral, skip the fade

**Veto rule for early positioning (ITEM 7):**
- OI spiking + funding deeply negative (< -0.05%) = early long signal — shorts crowded while spot buyers accumulate
- If funding turns positive at elevated price = exit signal (crowd normalized, edge gone)

**Params:**
- `funding_rate_threshold` = 0.05% per 8h (elevated signal)
- `funding_rate_extreme` = 0.10% per 8h (blowoff / maximum conviction)
- `funding_normal_band` = [-0.04%, +0.06%] (no signal zone)

---

### Signal B — Z-Score Standardization (Batch1 ITEM 11)

**What it measures:** Statistical extremeness of any metric (OI, funding, liquidations) relative to recent history.

**Framework:**
- Z = (Current − 30-day rolling average) / 30-day rolling StdDev
- Z ≥ +2.0 = top 2.5% (extreme; fade signal for contrarian setups)
- Z ≤ -2.0 = bottom 2.5% (extreme; fade signal for contrarian setups)
- Z between -0.5 and +0.5 = mean (exit target zone)

**Application across concepts:**
- OI z-score used in: Concept 1 (froth fade), Concept 3 (cascade detection)
- Funding z-score used in: Concept 1 (confirmation), all concepts (veto gate)
- Liquidation z-score used in: Concept 3 (cascade entry trigger)

**Params:**
- `zscore_window` = 30 days (rolling lookback)
- `zscore_entry` = 2.0 (extreme threshold — entry/veto trigger)
- `zscore_exit` = 0.5 (mean reversion target in z-score units)

---

### Signal C — Order Book Delta Imbalance (Batch2 ITEM 6)

**What it measures:** Bid/ask volume imbalance in the spot order book within a defined depth around current price.

**Thresholds (BTC example):**
- Intraday depth: 2.5% from mid-price (`ob_depth_pct_scalp = 0.025`)
- Swing depth: 5% from mid-price (`ob_depth_pct_swing = 0.05`)
- Signal threshold: bid-ask delta > $50M (BTC; `ob_delta_threshold_intraday = 50000000`)

**Usage rule:** NOT standalone. Combine with price action + moving averages. SOL example: 7% rally despite sell-skew — book skew alone insufficient. Can stay skewed 1+ hours (patience required).

**Veto application:**
- Book heavily bid-skewed at lower zone → supports long fade (aligned with Concepts 1, 2)
- Book heavily ask-skewed at upper zone → supports short fade
- Book skew contradicts trade direction → lower conviction; do not veto alone but reduce size

**Limitation:** Requires aggregated spot order book feed (Trdr.io recommended). Expensive data; deprioritize for v1.

**Params:**
- `ob_delta_threshold_intraday` = 50,000,000 (BTC; asset-specific)
- `ob_depth_pct_scalp` = 0.025
- `ob_depth_pct_swing` = 0.05

---

### Signal D — Spot vs. Futures Book Divergence (Batch2 ITEM 7)

**What it measures:** Whether large orders in the spot book (real directional capital) align with or contradict the trade direction. Futures book = market-maker noise; spot book = signal.

**Usage rule:** Large spot limit orders at a key price level indicate real directional intent. Futures book at same level shows distributed MM orders everywhere (meaningless). Use SPOT book only.

**Veto application:**
- Large spot orders on BID at key level → long confirmation
- Large spot orders on ASK at key level → short confirmation
- No large spot orders at level → neutral (neither confirms nor vetoes)
- Caveat: spoofing risk — orders pulled before price arrives. Monitor: order must persist as price approaches.

**Limitation:** Requires separate spot book feed (not perp book). Asset-specific size threshold needed. Hard to code robustly due to spoofing risk. Deprioritize for v1.

**Params:**
- `spot_order_size_threshold` = [asset-specific; BTC: TBD]
- `spoof_check_bars` = 3 (order must persist as price approaches for N bars)

---

### Signal E — Spot Order Book Skew (Batch1 ITEM 8)

**What it measures:** Bid/ask imbalance z-score within a narrow band around current price (spot market).

**Thresholds:**
- Skew z-score ≥ +2.0 or ≤ -2.0 = extreme imbalance
- Band: 0.5% around mid-price (`band_pct = 0.005`)

**Veto rule:** Valid in ranges only. In strong trends, price chews through skew levels — skew signal is meaningless in trend. Gate: only apply in `market_regime == range`.

**Params:**
- `skew_zscore_threshold` = 2.0 (or -2.0)
- `band_pct` = 0.005 (0.5% around mid)

---

## Signal Priority Hierarchy

For jCoin v1, implement in this order (cost and complexity):

| Priority | Signal | Data Required | v1? |
|----------|--------|---------------|-----|
| 1 | Z-Score Framework (Signal B) | candles, OI, funding | YES — core infrastructure |
| 2 | Funding Rate State (Signal A) | funding feed | YES — feeds into all concepts |
| 3 | Order Book Delta Imbalance (Signal C) | aggregated spot orderbook | LATER (expensive) |
| 4 | Spot vs Futures Divergence (Signal D) | separate spot orderbook | LATER (spoofing complexity) |
| 5 | Spot Book Skew (Signal E) | spot orderbook | LATER (overlaps Signal C) |

---

## How These Gate the Other Concepts

### Concept 1 (VWAP Band Fade) — confirmation/veto checks:
- **Required:** funding_rate in fade direction at elevated threshold (Signal A)
- **Required:** oi_zscore ≥ +2.0 or ≤ -1.5 (Signal B)
- **Ideal:** ob_delta aligned with fade direction (Signal C — v2)

### Concept 2 (Volume Profile Fade) — confirmation/veto checks:
- **Veto:** if funding extreme AGAINST fade direction → skip (Signal A)
- **Ideal:** ob_delta aligned at volume profile zone (Signal C — v2)
- **Note:** Concept 2 can fire without Signal A confirmation; Signal A adds conviction, absent = reduced size

### Concept 3 (Liquidation Cascade Reversal) — confirmation/veto checks:
- **Required:** liq_zscore extreme via Signal B framework
- **Confirmation:** funding normalizing post-cascade (Signal A moving toward zero)
- **Veto:** OI not dropping during spike → skip (OI rising = new positions, not liquidations)

---

## Codeable Assessment

**Codeable: YES (Signals A + B), PARTIAL (Signals C, D, E)**

- Signal A (funding): fully codeable — threshold comparison, 8h timestamp aware
- Signal B (z-score): fully codeable — rolling window statistics on any metric
- Signal C (ob delta): codeable with aggregated spot book feed; data cost is the barrier
- Signal D (spot/futures divergence): partial — spoofing detection reduces robustness
- Signal E (skew): codeable but overlaps Signal C; deprioritize

---

## Parameter Inventory

| Parameter | Signal | Source | Proposed Start Value |
|-----------|--------|--------|---------------------|
| `funding_rate_threshold` | A | Batch1 ITEM 1 | `0.05%` per 8h |
| `funding_rate_extreme` | A | Batch1 ITEM 1 | `0.10%` per 8h |
| `funding_normal_band_low` | A | Batch1 ITEM 1 | `-0.04%` per 8h |
| `funding_normal_band_high` | A | Batch1 ITEM 1 | `+0.06%` per 8h |
| `zscore_window` | B | Batch1 ITEM 11 | `30` days |
| `zscore_entry` | B | Batch1 ITEM 11 | `2.0` |
| `zscore_exit` | B | Batch1 ITEM 11 | `0.5` |
| `ob_delta_threshold_intraday` | C | Batch2 ITEM 6 | `50,000,000` (BTC; asset-specific) |
| `ob_depth_pct_scalp` | C | Batch2 ITEM 6 | `0.025` |
| `ob_depth_pct_swing` | C | Batch2 ITEM 6 | `0.05` |
| `skew_zscore_threshold` | E | Batch1 ITEM 8 | `2.0` |
| `band_pct` | E | Batch1 ITEM 8 | `0.005` |

**Param count: 12**
**Note: Signals A + B = 7 params needed for v1. Signals C + E add 5 more (v2).**

---

## jCoin Decision Rules

```
CONFIRMATION_SIGNALS — apply as overlay on Concepts 1, 2, 3

=== SIGNAL A: FUNDING GATE ===

  funding_direction_check(trade_direction):
    IF trade_direction == SHORT:
      REQUIRE funding_rate >= funding_rate_threshold (0.05% per 8h)
      IDEAL:   funding_rate >= funding_rate_extreme (0.10% per 8h)
      VETO:    funding_rate <= 0.0% (funding neutral or negative = crowd not stretched long)

    IF trade_direction == LONG:
      REQUIRE funding_rate <= -funding_rate_threshold (-0.05% per 8h)
      IDEAL:   funding_rate <= -funding_rate_extreme (-0.10% per 8h)
      VETO:    funding_rate >= 0.0% (funding neutral or positive = crowd not stretched short)

  EXCEPTION (Concept 2 — volume profile fades only):
    funding gate is ADVISORY not hard veto; absent = reduce position size 50%

=== SIGNAL B: Z-SCORE FRAMEWORK ===

  zscore(metric, window=30):
    return (metric.current - metric.rolling_mean(window)) / metric.rolling_std(window)

  signal_extreme(metric):
    return abs(zscore(metric)) >= zscore_entry (2.0)

  signal_mean(metric):
    return abs(zscore(metric)) <= zscore_exit (0.5)

  apply to: OI, funding_rate, liq_long, liq_short, rVOL (each metric has its own z-score)

=== SIGNAL C: ORDER BOOK DELTA (v2 only) ===

  ob_delta = sum(bid_volume, depth=ob_depth_pct_scalp) - sum(ask_volume, depth=ob_depth_pct_scalp)

  IF ob_delta >= ob_delta_threshold_intraday:
    ob_signal = LONG_BIAS
  ELIF ob_delta <= -ob_delta_threshold_intraday:
    ob_signal = SHORT_BIAS
  ELSE:
    ob_signal = NEUTRAL

  use as: confirmation (aligned = +conviction), not standalone entry, not hard veto

=== COMBINED GATE (apply per concept entry) ===

  FOR any setup entry:
    IF signal_A (funding) VETOES trade direction:
      BLOCK entry
    ELIF signal_A confirms AND signal_B confirms:
      ALLOW entry at full size (risk = 0.5% equity)
    ELIF signal_A confirms AND signal_B neutral:
      ALLOW entry at half size (risk = 0.25% equity)
    ELIF signal_A neutral AND signal_B confirms:
      ALLOW entry at half size — Concept 2 only
      BLOCK entry — Concepts 1 and 3
    ELSE:
      BLOCK entry

  EARLY LONG SIGNAL (Batch1 ITEM 7 — pre-positioning):
    IF oi_zscore >= 1.5
       AND funding_rate <= -funding_rate_threshold (-0.05%)
       AND price_range_pct_recent <= 0.01 (price barely moved = "boring chart"):
      FLAG as early long candidate; watch for catalyst
      entry_size = 50% (early positioning, before confirmation)
      exit_signal = funding_rate turns positive at elevated price
```

---

## Data Coverage & Confidence

| Field | Coverage | Confidence | Notes |
|-------|----------|-----------|-------|
| Funding mechanics | 2 items | High | Thresholds stated explicitly in ITEM 1 |
| Z-score framework | 1 item | High | ITEM 11: 30-day window, ±2.0 threshold |
| OB delta imbalance | 1 item | Medium | BTC $50M threshold; asset-specific scaling unclear |
| Spot/futures divergence | 1 item | Low | Concept-level; spoofing makes it hard to code robustly |
| Book skew | 1 item | Medium | Overlaps Signal C; deprioritize |

**Next pass:** Validate funding thresholds against real funding distributions; determine if 0.05%/0.10% cutoffs are appropriate for alt coins (vs. BTC/ETH where these were stated).

---

## Aggregated Educator Consensus

- TradingRiot (6 items): consistent that derivatives signals (OI, funding, liq) are the primary edge; order book is secondary confluence
- **Conflicts:** ITEM 8 (book skew) and ITEM 6 (ob delta) overlap significantly — likely the same concept described from different angles; implement Signal C only and skip Signal E for v1
- **Highest confidence elements:** funding threshold 0.05%/0.10%, z-score window 30 days, z-score threshold ±2.0, target z-score 0.5

---

*End of concept_confirmation_signals.md*
