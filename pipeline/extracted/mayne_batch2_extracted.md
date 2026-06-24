# Trader Mayne Batch 2 — Extracted Setups & Concepts

**Source files:**
- mayne_market_structure_ep2_compressed.md
- mayne_market_structure_pro_compressed.md
- mayne_order_blocks_compressed.md

**Extraction date:** 2026-06-20
**Total items:** 12

---

### ITEM 1: Market Regime Classification — HH/HL vs LL/LH

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_market_structure_ep2 + mayne_market_structure_pro
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: Market Regime Filter (Trend vs Range)
- market_regime: any (this rule DEFINES the regime)
- instrument_scope: any
- zone_definition: [not applicable — this is the regime classifier]
- trigger: [not applicable — this is the regime classifier]
- entry_execution: [not applicable]
- direction_logic: Uptrend = sequence of HH + HL (candle body closes). Downtrend = sequence of LL + LH (candle body closes). Range = no clear HH-HL or LL-LH chain; equal highs/equal lows or ambiguous. "If it's not obvious, we're probably sideways." Only trade uptrend buys and downtrend sells. Stand aside in ranges — but range is the ONLY valid regime for mean-reversion fading.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: Candle body close required to confirm each new HH, HL, LL, LH. Wicks do not qualify.

**D. Trade Management**
- invalidation: Regime shift (MSS): uptrend → body close below most recent validated HL; downtrend → body close above most recent validated LH.
- stop_placement: [not applicable — regime filter only]
- target_logic: [not applicable]
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: regime_lookback_swings = 3 (minimum swing count to confirm trend); body_close_required = true (wick-only breaks ignored); regime_labels = {uptrend, downtrend, range}
- param_count_note: 2 params; HIGHEST PRIORITY — this is the mean-reversion bot's primary on/off switch. Bot fades extremes ONLY when regime = range. Bot stands aside when regime = uptrend or downtrend.

---

### ITEM 2: Break of Structure (BOS) — Continuation Signal

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_market_structure_ep2 + mayne_market_structure_pro
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: Break of Structure (BOS) — Trend Continuation
- market_regime: trend (uptrend or downtrend)
- instrument_scope: any
- zone_definition: Prior validated swing high (in uptrend) or prior validated swing low (in downtrend).
- trigger: Candle body closes above prior swing high (bullish BOS) or below prior swing low (bearish BOS).
- entry_execution: maker (enter on corrective pullback after BOS)
- direction_logic: BOS = confirmation that current trend continues. Signals to look for next corrective pullback entry in trend direction. Pro version calls this MSB (Market Structure Break); ep2 calls it BOS. Same concept.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: Body close required. Wick-only = liquidity sweep / SFP, not a valid BOS.

**D. Trade Management**
- invalidation: Next corrective move closes past the new HL (uptrend) or LH (downtrend) → MSS → potential reversal.
- stop_placement: Below the new validated HL (long) or above the new validated LH (short).
- target_logic: Next structural high (long) or structural low (short).
- r_multiple: [not mentioned explicitly]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: bos_close_confirmation = body_close (not wick); swing_lookback_candles = 5 (to identify prior swing point)
- param_count_note: 2 params; supports the regime filter in Item 1.

---

### ITEM 3: Market Structure Shift (MSS) — Potential Reversal Signal

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_market_structure_pro + mayne_market_structure_ep2
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: Market Structure Shift (MSS) — Regime Change Warning
- market_regime: trend (fires at transition)
- instrument_scope: any
- zone_definition: Most recent validated higher low (uptrend) or most recent validated lower high (downtrend).
- trigger: Candle body closes below the most recent validated HL (bearish MSS, uptrend may be ending) or above the most recent validated LH (bullish MSS, downtrend may be ending).
- entry_execution: maker (on subsequent corrective move after MSS confirms with next opposing swing)
- direction_logic: MSS = potential reversal. Not guaranteed. Uptrend MSS → expect lower high on bounce → bearish MSB down confirms new downtrend. Downtrend MSS → expect higher low on pullback → bullish MSB up confirms new uptrend.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: MSS alone insufficient for trade; need subsequent opposing swing + MSB in new direction to confirm.

**D. Trade Management**
- invalidation: Price resumes original direction and breaks new HH (uptrend resumes) or new LL (downtrend resumes) after MSS — false MSS.
- stop_placement: Beyond the most recent structural point (above prior HH for short; below prior LL for long).
- target_logic: First structural level in new trend direction.
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: mss_close_confirmation = body_close; confirmation_required = subsequent_opposing_swing (wait for next LH after bearish MSS before classifying regime as downtrend)
- param_count_note: 2 params; MSS output feeds regime classifier in Item 1.

---

### ITEM 4: Two-Timeframe Congruence — Entry Timing Rule

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_market_structure_pro
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: HTF–LTF Sync Entry
- market_regime: any (applies across regime)
- instrument_scope: any
- zone_definition: The LTF chart will be counter-trend during HTF pullback phases. Entry zone = the moment LTF structure turns congruent with HTF.
- trigger: HTF is in trend direction. LTF is counter-trend (pullback). LTF then produces MSS (breaks counter-trend HL or LH) + MSB in HTF direction. That MSB on LTF = entry trigger.
- entry_execution: maker (limit at LTF OB or FVG within HTF zone at sync moment)
- direction_logic: Long when HTF bullish + LTF flips bullish (MSS + MSB). Short when HTF bearish + LTF flips bearish. Never trade LTF against HTF.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: Both conditions required: HTF trend direction + LTF sync MSB in same direction.

**D. Trade Management**
- invalidation: LTF resumes counter-trend before reaching HTF target (counter-trend MSS on LTF after entry).
- stop_placement: Below LTF entry structure (below LTF HL for long, above LTF LH for short).
- target_logic: HTF structural target (next HTF HH or LL).
- r_multiple: [not mentioned explicitly; implied much larger than LTF-only entries]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles (two timeframe feeds)
- proposed_param: htf_timeframe = daily (or 4h); ltf_timeframe = 1h (or 15m); sync_signal = ltf_msb_in_htf_direction
- param_count_note: 3 params; requires dual-timeframe candle feed; the "sync moment" is the highest-conviction entry point per Mayne.

---

### ITEM 5: Internal Structure Trap — Do Not Trade

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_market_structure_ep2
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: Internal Structure Non-Signal (Trap Avoidance)
- market_regime: trend
- instrument_scope: any
- zone_definition: Within the range of a prior impulse move (between impulse start and end), price may form apparent sub-trends with local BOS signals.
- trigger: [not a trade — this is a VETO rule]
- entry_execution: [not applicable]
- direction_logic: Any BOS that occurs WITHIN the boundaries of a prior impulse is internal structure. It does NOT signal trend reversal. It is noise inside a corrective move. Do NOT fade the trend based on internal BOS.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: For a BOS to be valid, it must break OUTSIDE the boundaries of the prior impulse (close past prior swing HH or LL at the macro level).

**D. Trade Management**
- invalidation: Only an external BOS (close past macro swing high/low) is a valid structural signal.
- stop_placement: [not applicable]
- target_logic: [not applicable]
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: impulse_boundary_high = most recent macro swing high; impulse_boundary_low = most recent macro swing low; internal_bos_ignore = true (any BOS within this range is non-actionable)
- param_count_note: 2 bounding params per impulse; prevents false regime-change signals that would incorrectly enable mean-reversion during trends.

---

### ITEM 6: Swing High/Low — 3-Candle Confirmation System

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_market_structure_pro
- claim_type: rule
- confidence: stated
- verified_track_record: stated

**B. Setup Definition**
- setup_name: 3-Candle Swing Detection
- market_regime: any
- instrument_scope: any
- zone_definition: A confirmed swing high requires: candle N-1 lower than candle N (the high), candle N+1 lower than candle N. A confirmed swing low requires: candle N-1 higher than candle N (the low), candle N+1 higher than candle N.
- trigger: [not a trade setup — structural building block for regime classifier]
- entry_execution: [not applicable]
- direction_logic: Swing highs and lows are the raw inputs to trend classification and BOS/MSS detection. Nothing is a valid structural level until confirmed by 3 candles.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: 3 candles required. Third candle close confirms the swing.

**D. Trade Management**
- invalidation: [not applicable — detection rule]
- stop_placement: [not applicable]
- target_logic: [not applicable]
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: swing_confirmation_candles = 3 (hardcoded per Mayne)
- param_count_note: 1 param; foundational for Items 1–5.

```
IF candle[N-1].high < candle[N].high AND candle[N+1].high < candle[N].high
THEN swing_high confirmed at candle[N]

IF candle[N-1].low > candle[N].low AND candle[N+1].low > candle[N].low
THEN swing_low confirmed at candle[N]
```

---

### ITEM 7: Order Block (OB) — Zone Definition

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_order_blocks
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: Order Block Zone (Demand / Supply Zone)
- market_regime: trend (OBs form within trends)
- instrument_scope: any
- zone_definition: Bullish OB = last bearish candle(s) immediately before a large displacement move higher. Bearish OB = last bullish candle(s) immediately before a large displacement move lower. Box drawn from high to low of the OB candle(s). Extended forward in time.
- trigger: Price returns to the OB zone after displacement. Entry at top → 50% of OB (bullish) or bottom → 50% of OB (bearish).
- entry_execution: maker (resting limit orders at OB zone)
- direction_logic: Bullish OB = long at zone. Bearish OB = short at zone. Must align with HTF trend direction.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: High probability requires: large displacement + FVG created + MSB achieved + liquidity taken before OB. Minimum: displacement + OB candle identifiable. HTF context must be aligned.

**D. Trade Management**
- invalidation: Price closes beyond the full OB (below for bullish, above for bearish). Also: price closes beyond the 50% mark of OB = weakness signal (may still work but lower confidence).
- stop_placement: Beyond the full OB + small buffer for fees/slippage/wicks. For high-probability OBs that took liquidity: stop just outside OB is sufficient (liq sweep already happened).
- target_logic: External range liquidity — prior swing high (bullish OB) or prior swing low (bearish OB).
- r_multiple: [not stated explicitly; implied 2:1 minimum by example]
- scale_rules: Can layer entries from top → 50% of OB.
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: ob_entry_top_pct = 1.0 (top of OB); ob_entry_50_pct = 0.5 (mean threshold); ob_stop_buffer = 0.2% beyond OB low; displacement_required = true; fvg_bonus = true (FVG overlap increases confidence but not required)
- param_count_note: 4 params; OBs are mechanically definable — last opposite candle before displacement + MSB. FVG detection adds 0 params (already defined from prior work).

```
OB_bullish = last bearish candle before impulse_bullish (impulse = closes above prior swing high with large body)
OB_bearish = last bullish candle before impulse_bearish (impulse = closes below prior swing low with large body)

Entry_bullish: limit at OB_high down to OB_midpoint
Stop_bullish: OB_low - buffer
Target_bullish: nearest external swing high above current price
```

---

### ITEM 8: Order Block — High-Probability Checklist

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_order_blocks
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: High-Probability OB Filter
- market_regime: any (filter applies in both trend and range OB contexts)
- instrument_scope: any
- zone_definition: Same as Item 7.
- trigger: Triggered when OB meets 3+ of 4 high-probability criteria before entry.
- entry_execution: maker
- direction_logic: Do not enter OB that meets < 2 criteria. Each criterion increases win probability incrementally.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: Ranked criteria: (1) Large displacement / big body candle after OB. (2) FVG created in displacement. (3) MSB achieved by displacement. (4) Liquidity taken before OB forms (prior high/low swept). All four = maximum probability. Fewer = lower probability but not automatically bad.

**D. Trade Management**
- invalidation: If OB fails (price closes through it), reassess as potential breaker (Item 9).
- stop_placement: Same as Item 7.
- target_logic: Same as Item 7.
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles
- proposed_param: ob_min_displacement = 1.5 * ATR (large body threshold); ob_fvg_required = false (bonus); ob_msb_required = false (bonus); ob_liq_sweep_required = false (bonus); ob_score_min = 2 (out of 4 criteria to take trade)
- param_count_note: 3 new params (displacement threshold, score min); adds scoring layer to OB detection.

---

### ITEM 9: Breaker Block — Failed OB → SR Flip

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_order_blocks
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: Breaker Block (Failed OB, SR Flip)
- market_regime: transition (trend reversal zone)
- instrument_scope: any
- zone_definition: A previously identified OB zone that price has now closed THROUGH in the opposing direction. Zone flips: bullish OB that fails → bearish breaker (now resistance). Bearish OB that fails → bullish breaker (now support).
- trigger: Price returns to the failed OB zone and retests from the other side. Entry at the zone on the retest.
- entry_execution: maker (limit at breaker zone on retest)
- direction_logic: Bullish breaker (was bearish OB): long on retest. Bearish breaker (was bullish OB): short on retest. Breakers most commonly at MSS points (trend reversals).

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: Breaker context: MSS occurred at or near the zone + displacement through the OB + often a liquidity sweep (the reversal takes a prior high or low first). FVG created in the reversal move = bonus high-probability signal.

**D. Trade Management**
- invalidation: Price closes back through the breaker zone in the original direction (SR flip failed).
- stop_placement: Two options:
  - Option A (tight, better RR): just beyond the breaker zone edge + small buffer.
  - Option B (wide, better win rate): beyond the liquidity sweep high/low that triggered the reversal.
  - Mayne's preference in crypto: Option B (above the sweep), because crypto frequently wicks just past the breaker. Accept worse RR for higher win rate.
- target_logic: External range liquidity in the new direction.
- r_multiple: Option A better RR (can be 5:1+); Option B lower RR but fewer false stops.
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: breaker_close_through = body_close_required (same as BOS logic); stop_mode = sweep_high_low (Option B default per Mayne's crypto preference); breaker_buffer = 0.2%
- param_count_note: 3 params; breaker detection is fully mechanical once OB zones are tracked and price closes through them.

```
IF ob_zone identified AND price closes THROUGH ob_zone (body close)
THEN ob_zone becomes breaker_zone (flipped polarity)
IF price retests breaker_zone from new side
THEN entry in flipped direction
Stop: beyond liquidity sweep + buffer
Target: external range liquidity
```

---

### ITEM 10: OB in Dealing Range Context (Premium / Discount Filter)

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_order_blocks
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: OB Location Filter (Discount/Premium)
- market_regime: range (and within trends)
- instrument_scope: any
- zone_definition: Dealing range = most significant high to most significant low. Midpoint = equilibrium (EQ). Discount = below EQ (lower 50%). Premium = above EQ (upper 50%). External range liquidity = swing highs/lows outside the range. Internal range liquidity = OBs, FVGs inside the range.
- trigger: Bullish OB in discount = trade it. Bullish OB in premium = avoid. Bearish OB in premium = trade it. Bearish OB in discount = avoid.
- entry_execution: maker
- direction_logic: "Longing some random OB in the middle of nowhere is not going to be as much of a high probability or quality setup as longing an OB that's in the discount of a range."

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: OB location (discount/premium) + HTF alignment together = minimum requirement for high-probability entry.

**D. Trade Management**
- invalidation: OB in neutral zone (near EQ): lower priority, apply additional filters.
- stop_placement: Same as Item 7.
- target_logic: External range liquidity = swing high (from discount long) or swing low (from premium short).
- r_multiple: [not stated]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: range_high = most recent significant swing high; range_low = most recent significant swing low; eq_midpoint = (range_high + range_low) / 2; bullish_ob_max_price = eq_midpoint (OB top must be below EQ); bearish_ob_min_price = eq_midpoint (OB bottom must be above EQ)
- param_count_note: 3 structural params (range high, range low, EQ); this is the price-action equivalent of VWAP-based mean-reversion zone selection.

---

### ITEM 11: ATR Contraction at Trend End (Regime Shift Precursor)

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_market_structure_pro
- claim_type: rule
- confidence: implied
- verified_track_record: none

**B. Setup Definition**
- setup_name: Range Contraction → Trend Exhaustion
- market_regime: trend (late-stage)
- instrument_scope: any (BTC weekly example cited)
- zone_definition: The size of each successive impulse wave contracts as the trend matures. "The range is big here; it gets a little smaller, a little smaller, a little smaller. Very common as the trend goes on and we're approaching a reversal."
- trigger: Successive impulse ranges (from swing low to swing high) are decreasing in size. Combined with eventual MSS = high-confidence regime change.
- entry_execution: [not specified for this signal alone]
- direction_logic: Contraction precedes reversal. Use as additional confirmation that MSS is a genuine reversal rather than a noise event.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: Not standalone. Combine with MSS for confirmation.

**D. Trade Management**
- invalidation: Impulse range expands again (trend resumes with new momentum).
- stop_placement: [not specified for this signal]
- target_logic: [not specified]
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles
- proposed_param: impulse_range_decay_pct = 0.7 (each successive impulse < 70% of prior impulse size, for N>=3 impulses); impulse_lookback = 3
- param_count_note: 2 params; useful as a soft regime-change early-warning filter before MSS fires.

---

### ITEM 12: OB + FVG Overlap — Maximum Confluence Setup

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_order_blocks
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: OB + FVG Overlap (Double Confluence)
- market_regime: trend or range (zone applies in both)
- instrument_scope: any
- zone_definition: An OB zone that also contains or overlaps with an FVG (3-candle displacement gap). The overlapping price region = the highest-priority entry zone.
- trigger: Price enters the overlap zone of OB + FVG simultaneously.
- entry_execution: maker
- direction_logic: Same direction as OB (bullish OB + FVG overlap = long; bearish OB + FVG overlap = short). "Double the reason, double the confidence."

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: OB zone + FVG zone must overlap. FVG signals displacement (institutional involvement). Combined = 2 independent structural confluences at same price.

**D. Trade Management**
- invalidation: Price closes through both the OB and FVG without reaction.
- stop_placement: Below the OB low (bullish) or above the OB high (bearish). Tighter if FVG gives a clean lower boundary.
- target_logic: External range liquidity (same as OB targets).
- r_multiple: [not stated; implied better than OB-alone due to tighter entry band]
- scale_rules: Can enter in two tranches: first at FVG fill, second at OB midpoint.
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: ob_fvg_overlap_required = false (bonus, not mandatory); overlap_zone = intersection of [ob_low, ob_high] and [fvg_low, fvg_high]; entry = top of overlap_zone; stop = below OB_low
- param_count_note: 0 new params (OB already in Item 7; FVG from prior extraction); just the intersection logic.

```
overlap_zone = MAX(ob_low, fvg_low) to MIN(ob_high, fvg_high)
IF overlap_zone is non-empty:
    entry = overlap_zone top (bullish) or bottom (bearish)
    stop = ob_low - buffer (bullish)
    target = external_range_liquidity
    confidence = high
```

---

*End of extraction. Total: 12 items.*
