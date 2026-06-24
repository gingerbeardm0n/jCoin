# Concept: Volume Profile Fade

**Last updated:** 2026-06-19
**Source:** TradingRiot (Batch2 ITEM 1, ITEM 3, ITEM 8, ITEM 9, ITEM 13)
**Sample size:** 0 verified fills (framework/concept level)
**Win rate:** not stated

---

## Source Items Merged

| Item | Source | Name |
|------|--------|------|
| Batch2 ITEM 1 | tradingriot_auction_market_theory_compressed.md | AMT Balance-Edge Mean Reversion |
| Batch2 ITEM 3 | tradingriot_auction_market_theory_compressed.md | POC Rejection Fade |
| Batch2 ITEM 8 | tradingriot_volume_analysis_compressed.md | LVN Entry — Low Volume Node Fade |
| Batch2 ITEM 9 | tradingriot_volume_analysis_compressed.md | HVN Edge Entry — Fade Fast Rally into Old POC |
| Batch2 ITEM 13 | tradingriot_auction_market_theory_compressed.md | AMT Framework — Market Profile / Volume Profile |

---

## Definition

Fade price at volume profile extremes — value area edges, low-volume nodes (LVN), high-volume node (HVN) boundaries, and point-of-control (POC) rejections — where structural volume imbalances create predictable mean-reversion tendencies. Auction Market Theory (AMT) provides the theoretical spine: markets balance around fair value (POC), and price deviations to low-volume areas are temporary.

Key distinctions:
- **vs. VWAP Band Fade:** This concept uses historical volume profile structure (composite profile) rather than a real-time VWAP calculation; zones persist from prior sessions
- **vs. arbitrary S/R levels:** Zones are anchored to actual volume-weighted structure — HVNs are where participants agreed on price, LVNs are voids the market skipped through
- **vs. LVN entry (trend-following):** LVN entries in this concept are fade-mode — entering at the LVN edge expecting fast travel BACK through the LVN to the next HVN/POC

---

## Setup Criteria

### Required

| Criterion | Target | Notes |
|-----------|--------|-------|
| Market regime | range | AMT: inside value area = range mode; outside = trend mode (don't fade) |
| Price zone | Value area edge, HVN edge, old unvisited POC, or LVN boundary | See sub-setups below |
| Value area | 68% of volume traded (standard profile definition) | Defines "fair" range; edges = fade zones |
| POC | Highest volume level in profile window | Primary mean-reversion target; also functions as rejection zone |
| Rejection signal | Rejection candle / wick at POC or HVN edge; OR close back inside value area after touching edge | Prevents accepting outside (which = breakout) |

### Sub-Setup Zones (choose one per trade)

**Sub-1 — Value Area Edge (AMT Balance-Edge):**
- Price reaches upper value area edge (VAH) → short; lower value area edge (VAL) → long
- Require: close back inside value area after touch (`require_close_inside = true`)
- Target: POC or opposite edge

**Sub-2 — POC Rejection:**
- Old unvisited POC (from `poc_lookback_days = 30` window) acts as resistance/support
- Require: strong rejection candle (wick ratio ≥ 0.6 — wick is ≥ 60% of total candle range)
- Target: mean of current value area / VWAP

**Sub-3 — LVN Entry (fast travel):**
- Price enters LVN (volume < `lvn_volume_threshold_pct = 20%` of average volume at that level)
- Expect fast travel THROUGH the LVN; enter at LVN near edge in direction of move
- Target: next HVN or POC
- Note: this is directional, not strictly a fade — use with caution in range context

**Sub-4 — HVN Edge / Old POC Fade:**
- Fast (high-momentum) rally into old unvisited POC (`poc_unvisited_bars ≥ 50`)
- Enter fade short at POC; price acted as resistance not support on fast moves
- Require: fast rally velocity check (`fast_rally_atr_mult ≥ 1.5` — price moved ≥ 1.5×ATR into the POC)
- Target: back to recent value area mean / VWAP

### Ideal (increases conviction)
- Combine with Concept 1 (VWAP Band Fade) signals — OI/funding froth at the volume profile zone elevates confidence
- Volume profile zone aligns with VWAP ±1–2σ band (double-confirmed zone)
- AMT Rule 5 context: if price has built TIME at current edge → breakout risk; exit or skip

---

## Entry Trigger

**Primary trigger:** Rejection at value area edge or POC confirmed by candlestick structure.

**Mechanism:**
1. Build composite volume profile over `profile_lookback_period` (session / week / month — configurable)
2. Identify value area (68% of volume), POC, HVN edges, and LVN voids
3. Wait for price to reach an extreme zone (VAH, VAL, old POC, HVN edge)
4. Confirm rejection: close back inside value area (Sub-1), wick ratio ≥ 0.6 (Sub-2), or fast-rally velocity check (Sub-4)
5. Post maker limit at zone; stop beyond the zone

**Time of entry:** On close of rejection candle at the zone; maker entry pre-loads at zone before confirmation for best fill

---

## Add-On Mechanics

| Mechanic | Frequency | Description |
|----------|-----------|-------------|
| Single entry at zone | Primary | Post maker at profile level |
| Adjust on new profile | Ongoing | As market builds volume, levels shift — update profile and adjust positions |

**Key principle:** TradingRiot (ITEM 8, ITEM 9): "Adjust levels as market builds volume" — the profile is dynamic, not static.

---

## Stop Criteria

| Stop Type | When to Use |
|-----------|-------------|
| Beyond zone | Always — beyond the value area edge, beyond POC, beyond HVN boundary |
| Acceptance outside | AMT Rule 5: if price builds TIME + VOLUME outside zone, setup fails — exit |

**Stop placement:** Beyond the zone level (e.g., for VAH fade: stop above VAH; for POC rejection: stop beyond POC)

**Critical rule (AMT):** Acceptance outside the balance area (price closes + holds beyond zone with time + volume) = market is transitioning to trend — do not hold, do not re-enter immediately.

---

## Profit Targets

| Target Type | How Determined | Notes |
|-------------|---|---|
| T1 | POC (highest volume level) | "Fairest price" — highest probability target |
| T2 | Opposite value area edge | If momentum carries through POC |
| LVN fast-travel | Next HVN / POC beyond LVN | LVN sub-setup only |

---

## Hold Duration

| Duration | Notes |
|----------|-------|
| Intraday | Value area edges resolve intraday in most sessions |
| Multi-session | If profile is weekly/monthly; old POC rejections may take longer |

---

## Market Condition Dependency

- **Inside value area:** Full setup valid; all sub-setups applicable
- **Outside value area consistently:** AMT signals trend; do NOT fade — switch to breakout/continuation
- **After large liquidation:** Volume profile may reprice; rebuild profile before re-entering
- **Low liquidity periods:** Volume profile construction unreliable; skip

---

## Red Flags (When to Skip)

- Price builds time + volume outside value area edge (AMT Rule 5 — acceptance = breakout, not fade)
- Price accepts beyond old POC (trades through + holds above/below) — Sub-2 invalidated
- LVN stalls: price enters LVN but stops, doesn't travel — means the void is filling (exit)
- Fast rally into POC but OI spiking + positive delta (institutional breakout, not retail FOMO fade)
- No clear volume profile structure (flat profile, no distinct POC or HVN/LVN)

---

## Example Trades (from extraction)

**Batch2 ITEM 3 — POC Rejection Fade (any):**
Price reaches old POC that hasn't been visited for extended period. Shows "strong rejection candle" (wick ratio ≥ 0.6). AMT Rule 4 says full rotation expected, but Rule 4 exception applies — strong reaction prevents completion. Fade back to value area mean. Lesson: strong POC rejection overrides the "always rotates to POC" default.

**Batch2 ITEM 9 — HVN Edge / Fast Rally Fade (any):**
Fast (high-momentum) rally into old unvisited POC (not visited for ≥ 50 bars). Enter fade short at POC. Stop above POC. Target back to recent value area. The "old" POC acts as resistance on fast moves; price needs TIME to digest before accepting above.

**Batch2 ITEM 8 — LVN Fast Travel (directional):**
Price enters void (LVN, < 20% average volume at level). Travel is fast with minimal resistance. Enter at near edge in direction of travel. Target next HVN. Stop: back at LVN boundary. Lesson: LVN = least resistance, but can fill if market starts transacting there — exit if stall.

---

## Codeable Assessment

**Codeable: PARTIAL**

Volume profile construction from candle data is doable (bin candles by price level, sum volume). Key parameters are well-defined:
- Value area (68% of volume): yes
- POC identification: yes
- LVN/HVN threshold: yes (relative volume at price level)
- Rejection candle wick ratio: yes (candle math)
- Fast rally velocity: yes (ATR multiple)

Primary friction: "old unvisited POC" requires tracking profile history across sessions. Manageable with a persistent volume profile object updated each session.

---

## Parameter Inventory

| Parameter | Source | Proposed Start Value |
|-----------|--------|---------------------|
| `value_area_pct` | Batch2 ITEM 1, ITEM 13 | `0.68` (68% of volume = value area) |
| `profile_lookback_period` | Batch2 ITEM 13 | `session` (default; configurable to week/month) |
| `require_close_inside` | Batch2 ITEM 1 | `true` (must close back inside for edge fade) |
| `poc_lookback_days` | Batch2 ITEM 3 | `30` days |
| `poc_rejection_wick_ratio` | Batch2 ITEM 3 | `0.6` (wick ≥ 60% of candle range) |
| `poc_unvisited_bars` | Batch2 ITEM 9 | `50` bars (POC not visited for N bars = "old") |
| `fast_rally_atr_mult` | Batch2 ITEM 9 | `1.5` (rally velocity check) |
| `lvn_volume_threshold_pct` | Batch2 ITEM 8 | `0.20` (< 20% avg volume at level = LVN) |
| `hvn_target_volume_pct` | Batch2 ITEM 8 | `1.5` (> 1.5× avg volume at level = HVN) |

**Param count: 9**
**Toward 13–15 cap: 9 used here (some shared with other concepts, e.g., value_area_pct)**

---

## jCoin Decision Rules

```
VOLUME_PROFILE_FADE entry conditions:

  PRE-FILTER (regime gate):
    market_regime == range
    (price inside value area OR at value area edge returning inside)

  BUILD PROFILE:
    composite_profile = volume_by_price(lookback = profile_lookback_period)
    value_area = {VAL, POC, VAH} from composite_profile (value_area_pct = 0.68)
    hvn_levels = price_bins where volume > hvn_target_volume_pct * avg_volume
    lvn_levels = price_bins where volume < lvn_volume_threshold_pct * avg_volume

  --- SUB-SETUP 1: Value Area Edge Fade ---
  IF price >= VAH:
    wait for candle.close < VAH  (acceptance back inside)
    IF require_close_inside == true AND candle.close < VAH:
      THEN post maker short at VAH
           stop = VAH + 0.5*ATR
           target_T1 = POC
           target_T2 = VAL
           risk = 0.5% equity

  IF price <= VAL:
    wait for candle.close > VAL  (acceptance back inside)
    IF require_close_inside == true AND candle.close > VAL:
      THEN post maker long at VAL
           stop = VAL - 0.5*ATR
           target_T1 = POC
           target_T2 = VAH
           risk = 0.5% equity

  --- SUB-SETUP 2: POC Rejection Fade ---
  IF price reaches old_poc (not visited for poc_unvisited_bars = 50):
    IF rejection_candle_wick_ratio >= poc_rejection_wick_ratio (0.6):
      IF approaching_from_below:
        THEN post maker short at old_poc
             stop = old_poc + 0.3*ATR
             target = current_value_area_mean / VWAP
      IF approaching_from_above:
        THEN post maker long at old_poc
             stop = old_poc - 0.3*ATR
             target = current_value_area_mean / VWAP
      risk = 0.5% equity

  --- SUB-SETUP 4: Fast Rally into Old POC (HVN Edge) ---
  IF price rallies into old_poc at velocity > fast_rally_atr_mult (1.5) * ATR_per_bar:
    THEN post maker short at old_poc
         stop = old_poc + 0.5*ATR
         target = recent_value_area_mean
         risk = 0.5% equity

  INVALIDATION (exit all sub-setups if):
    price accepts outside value area (time + volume build beyond edge)
    OR price trades through old_poc with close + hold above/below
    OR LVN stalls (price stops inside LVN for > 3 bars without traveling)
```

---

## Data Coverage & Confidence

| Field | Coverage | Confidence | Notes |
|-------|----------|-----------|-------|
| Value area definition | 3 items | High | 68% consistent; POC as target consistent |
| POC rejection rules | 1 item | Medium | Wick ratio 0.6 is inferred threshold, not explicitly stated |
| LVN/HVN thresholds | 2 items | Medium | 20%/150% relative volume — reasonable starting values |
| Fast rally velocity | 1 item | Low | 1.5×ATR — inferred; educator said "fast rally" without metric |
| Stop placement | 2 items (inferred) | Low | "Beyond zone" stated; specific ATR mult derived here |

**Next pass:** Quantify "strong rejection candle" precisely; test wick ratio threshold; validate profile lookback period for crypto (session vs. rolling 24h).

---

## Aggregated Educator Consensus

- TradingRiot: consistent framework across all 5 items; AMT is the spine, volume profile provides zone structure
- **Conflicts:** None material; LVN sub-setup is directional not pure fade, so use only when regime is clear
- **Highest confidence elements:** `value_area_pct = 0.68`, target = POC, invalidation = acceptance outside zone

---

*End of concept_volume_profile_fade.md*
