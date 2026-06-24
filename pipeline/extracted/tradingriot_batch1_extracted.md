# TradingRiot Batch 1 — Extracted Setups & Concepts

**Source articles:**
- tradingriot_crypto_guide_compressed.md
- tradingriot_crypto_data_compressed.md
- tradingriot_when_bitcoin_bottoms_compressed.md

**Extraction date:** 2026-06-19
**Total items:** 17

---

### ITEM 1: Funding Rate Mechanics

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_crypto_guide_compressed.md
- claim_type: concept
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: Funding Rate Mechanics
- market_regime: any
- instrument_scope: any
- zone_definition: [not mentioned]
- trigger: [not mentioned]
- entry_execution: [not mentioned]
- direction_logic: Funding positive = longs pay shorts (bearish lean); funding negative = shorts pay longs (bullish lean). Reflects crowd positioning sentiment.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: Rate = Interest Rate + Premium Index. Clamp: −0.04% to +0.06% = interest only. Exchange cap ±0.75% maintenance margin. Binance USDT base = 0.01% per 8h.
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: [not mentioned]

**D. Trade Management**
- invalidation: [not mentioned]
- stop_placement: [not mentioned]
- target_logic: [not mentioned]
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: funding
- proposed_param: funding_rate_threshold = 0.05% per 8h (elevated); funding_rate_extreme = 0.1% per 8h (blowoff)
- param_count_note: 2 params; within cap

---

### ITEM 2: Liquidation Cascade as Entry Signal

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_crypto_guide_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: Liquidation Cascade Entry
- market_regime: post-liquidation
- instrument_scope: any
- zone_definition: Zone where large liquidation cascade occurred; price wick or sharp drop into cluster of leveraged longs
- trigger: Large long liquidation event (z-score deeply negative on long liquidations). 10-day forward return slopes up after long flushes.
- entry_execution: maker
- direction_logic: Long after long liquidation cascade. "Long shakeouts = historically good entry for new longs."

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: OI falls during cascade = forced closures (not new shorting). OI fall confirms liquidation not shorting.
- funding_signal: [not mentioned]
- liquidation_signal: Large long liquidation z-score deeply negative = core trigger. 10-day fwd return positive after flush.
- volume_profile: [not mentioned]
- confluence_count: Liquidation z-score deeply negative required. OI fall confirms.

**D. Trade Management**
- invalidation: [not mentioned]
- stop_placement: [not mentioned]
- target_logic: [not mentioned]
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: 10-day forward return window implied
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: OI, tick-trades (liquidation data feed)
- proposed_param: liq_zscore_entry = -2.0 (long liquidation z-score threshold)
- param_count_note: 1 param; lightweight

---

### ITEM 3: Momentum Setup (OI + Price + Low Funding)

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_crypto_guide_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: Healthy Momentum (OI-Led Breakout)
- market_regime: trend
- instrument_scope: any
- zone_definition: Price breaking above/below significant structural level or moving average
- trigger: OI spiking + funding low or negative + price breaking significant level. Automated strategies pile in.
- entry_execution: taker
- direction_logic: Long when OI up + price up + funding muted/negative (spot-led, not leverage-chasing). Direction follows price break.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: OI exploding (e.g. PENGU 40-50M → 290M). OI rise = fresh conviction, not rotation.
- funding_signal: Funding low or negative during uptrend = healthy. Funding staying negative = spot buyers ahead. Negative spike early (e.g. −0.17%) = not crowded.
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: All three must align: OI spike + muted/negative funding + level break

**D. Trade Management**
- invalidation: Funding turns hard positive (crowd piling in, momentum exhausted)
- stop_placement: [not mentioned]
- target_logic: Trend continuation; ride until data deteriorates
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles, OI, funding
- proposed_param: oi_zscore_entry = +1.5 (OI spike threshold); funding_max = 0.03% per 8h (muted); price_break = structural level (requires pattern definition)
- param_count_note: 3 params; structural level detection adds complexity

---

### ITEM 4: Mean Reversion — OI + Funding Froth Fade

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_crypto_guide_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: Froth Fade (OI Spike + Hard Positive Funding)
- market_regime: range
- instrument_scope: any
- zone_definition: Price at extreme after OI exploded + funding hard positive. Short liquidation cluster at high = last bears squeezed.
- trigger: OI spike z-score extreme + funding hard positive + short liquidations hit (last bears squeezed = buying disappears). "Data confirms, one side flushed, level to aim at."
- entry_execution: maker
- direction_logic: Short (fade crowded longs). "Little fuel left. Snap brutal."

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: OI spikes extreme (z-score +2 or beyond). OI elevated at highs.
- funding_signal: Funding hard positive = crowded longs stretched. Core confirmation signal.
- liquidation_signal: Short liquidations hitting at highs = last bears flushed = buying exhausted. Required.
- volume_profile: [not mentioned]
- confluence_count: All three required: OI spike + hard positive funding + short liquidation flush

**D. Trade Management**
- invalidation: OI continues rising without funding retreat (trend resumes)
- stop_placement: [not mentioned]
- target_logic: Prior structural level (mean). ZEC example: snap −25% into prior mid-level.
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: Fade is "short-lived, not weeks." Implied exit within days.
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: OI, funding, tick-trades (liquidation data)
- proposed_param: oi_zscore_fade = +2.0; funding_extreme_positive = 0.1% per 8h; liq_short_zscore = +2.0
- param_count_note: 3 params; high priority for Strategy 1

---

### ITEM 5: Mean Reversion — Target = Prior Structural Level

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_crypto_guide_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: Mean Reversion Target Rule
- market_regime: range
- instrument_scope: any
- zone_definition: Prior structural level, moving average, or "something real" as defined target before entry
- trigger: Defined before entering fade trade (not reactive)
- entry_execution: maker
- direction_logic: Fade toward mean; cover at prior structural level. Must have target before entry.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: Target definition is prerequisite, not confirmation

**D. Trade Management**
- invalidation: No defined target = no trade (discipline rule)
- stop_placement: [not mentioned]
- target_logic: Prior structural level, MA, or opposing zone. Must be defined pre-entry.
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: Snap is short-lived; if no move quickly, concept invalidated
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles
- proposed_param: target_type = prior_swing_high_low | VWAP | MA_period (e.g. 20-period)
- param_count_note: 1-2 params depending on target type chosen

---

### ITEM 6: Delta Neutral — Funding Rate Arbitrage (Long Spot / Short Perp)

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_crypto_guide_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: Funding Rate Arb (Long Spot, Short Perp)
- market_regime: any
- instrument_scope: any
- zone_definition: [not applicable — direction neutral]
- trigger: Persistent positive funding rate (longs paying). Buy spot, short equal size perp. Collect funding 3x/day.
- entry_execution: maker
- direction_logic: Delta neutral. Net direction ~zero. Earn yield from funding differential. Example: 0.05% per 8h ≈ 55% annualized.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: Positive funding required. Collect 0.05% per 8h × 3 = 55% annualized. Strategy collapses if funding flips.
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: Positive funding = entry; neutral to negative = exit

**D. Trade Management**
- invalidation: Funding flips mid-trade. Short leg needs margin; spike up liquidates it.
- stop_placement: Monitor funding rate continuity
- target_logic: Collect funding indefinitely; exit when funding flips or approaches zero
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: Flipping risk is the core risk; monitor each 8h stamp

**E. Quantify-ability**
- codeable: yes
- data_need: funding, candles
- proposed_param: funding_arb_min = 0.03% per 8h; funding_exit = 0.0% per 8h
- param_count_note: 2 params; [later] Strategy 3 tag

---

### ITEM 7: Negative Funding + OI Spike = Early Long Signal

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_crypto_guide_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: OI Spike + Negative Funding Early Long
- market_regime: any
- instrument_scope: alts (especially low-float)
- zone_definition: Price action muted / chart boring. OI spiking while price flat = early positioning.
- trigger: OI z-score spiking + funding deeply negative + price barely moved. "Data unusual, chart boring." Possible insider accumulation or maker hedging.
- entry_execution: maker
- direction_logic: Long. Perp traders opening, shorts aggressive while spot buying elsewhere. Setup fires before pump obvious.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: OI spiked while price muted. Core signal. Rise + negative funding = unique combo.
- funding_signal: Deeply negative despite OI spike = shorts paying longs = structural imbalance. Core confirmation.
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: Both required: OI spike + deeply negative funding simultaneously

**D. Trade Management**
- invalidation: Funding turns positive (crowd normalizes, edge gone)
- stop_placement: [not mentioned]
- target_logic: Multi-hundred percent rally possible (RIVER example). Hold until data shifts.
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: "Funding stays negative at tops; too late by several multiples of daily ATR." — exit when funding flips.
- funding_avoidance: Monitor: if funding goes positive at elevated price, exit signal

**E. Quantify-ability**
- codeable: partial
- data_need: OI, funding
- proposed_param: oi_zscore_threshold = +1.5; funding_negative_extreme = -0.05% per 8h; price_move_gate = <1% (chart boring filter)
- param_count_note: 3 params

---

### ITEM 8: Order Book Skew as Confluence Filter

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_crypto_guide_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: Spot Order Book Skew Confluence
- market_regime: range
- instrument_scope: any (spot market)
- zone_definition: Bid/ask imbalance within a band around current price. Heavy bid skew below = hard to push down.
- trigger: Skew z-score extreme in direction of trade + same-side positioning as large spot players
- entry_execution: maker
- direction_logic: Not standalone. Raises conviction when spot book aligns with derivatives signals. Heavy bids below = long bias. Heavy asks above = short bias.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: Not standalone entry. Must combine with other signals.

**D. Trade Management**
- invalidation: Strong trend = skew meaningless (price chews through levels). Valid in ranges only.
- stop_placement: [not mentioned]
- target_logic: [not mentioned]
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: orderbook
- proposed_param: skew_zscore_threshold = +2.0 or -2.0; band_pct = 0.5% around mid
- param_count_note: 2 params; orderbook feed required (expensive data)

---

### ITEM 9: Options 25-Delta Risk Reversal Fade

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_crypto_guide_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: 25-Delta Risk Reversal Fade
- market_regime: any
- instrument_scope: BTC | ETH
- zone_definition: 25Δ RR = IV(25Δ Call) − IV(25Δ Put). Extreme positive = crowded calls. Extreme negative = crowded puts.
- trigger: RR z-score extreme. Z < -2 = crowded calls (upside priced in, fade). Z > +2 = crowded puts (fear extreme, fade).
- entry_execution: [not mentioned]
- direction_logic: Fade extremes. Crowded calls = short or avoid longs. Crowded puts = long or fade fear.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: Combine with OI + funding for full alignment

**D. Trade Management**
- invalidation: RR continues in same direction (sentiment not reversing)
- stop_placement: [not mentioned]
- target_logic: Fade toward neutral RR (0 or mean)
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: funding (options IV data from Deribit)
- proposed_param: rr_zscore_fade = +2.0 or -2.0
- param_count_note: 1 param; requires Deribit options data feed (BTC/ETH only)

---

### ITEM 10: Full Alignment Trade (All Signals Convergent)

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_crypto_guide_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: Full Signal Alignment Trade
- market_regime: any
- instrument_scope: any
- zone_definition: Derivatives data (OI, funding, liquidations) + spot book skew + options RR all pointing same direction
- trigger: All signals convergent in same direction. Rare setup.
- entry_execution: maker
- direction_logic: Direction dictated by convergent signals. Long or short depending on alignment.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: OI signal required in alignment
- funding_signal: Funding signal required in alignment
- liquidation_signal: Liquidation signal required in alignment
- volume_profile: [not mentioned]
- confluence_count: All five signal types must align: OI + funding + liquidations + spot skew + options RR

**D. Trade Management**
- invalidation: Any signal breaks alignment
- stop_placement: [not mentioned]
- target_logic: [not mentioned]
- r_multiple: [not mentioned]
- scale_rules: Size up on convergence ("trade with conviction")
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: OI, funding, tick-trades, orderbook, funding (options)
- proposed_param: min_aligned_signals = 4 (out of 5); all individual signal z-scores >= 1.5
- param_count_note: Composite of 5 sub-signals; important meta-rule, not standalone strategy

---

### ITEM 11: Z-Score Standardization Framework

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_crypto_guide_compressed.md
- claim_type: concept
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: Z-Score Extremes Framework
- market_regime: any
- instrument_scope: any
- zone_definition: Z = (Current − Average) / StdDev over rolling window. +2 = top 2.5%. -2 = bottom 2.5%.
- trigger: Z-score crossing ±2 threshold for any metric (OI, funding, liquidations, skew, RR)
- entry_execution: [not mentioned]
- direction_logic: +2 = stretched long / overbought. -2 = stretched short / oversold. Direction depends on metric.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: OI z-score tracked (30-day lookback mentioned)
- funding_signal: Funding z-score tracked
- liquidation_signal: Liquidation z-score tracked
- volume_profile: [not mentioned]
- confluence_count: [not mentioned]

**D. Trade Management**
- invalidation: [not mentioned]
- stop_placement: [not mentioned]
- target_logic: Reversion toward z-score = 0 (mean)
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: Rolling window keeps comparison vs recent behavior only
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles, OI, funding, tick-trades
- proposed_param: zscore_window = 30 days; zscore_entry = 2.0; zscore_exit = 0.5
- param_count_note: 3 params; core infrastructure for all other setups

---

### ITEM 12: OI Spike at Breakout (Momentum Confirmation)

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_crypto_data_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: OI Surge at Structural Break
- market_regime: trend
- instrument_scope: any
- zone_definition: Structural resistance level. AVAX example: broke resistance + significant OI surge.
- trigger: Price breaks structural level + OI surges significantly simultaneously. Major participants involved.
- entry_execution: taker
- direction_logic: Long at break + OI surge = major participants confirm. Direction = direction of break.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: OI surge at breakout = core signal. OI alone insufficient (Solana caveat: OI up + sell-off).
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: OI surge required; additional signals needed per Solana caveat

**D. Trade Management**
- invalidation: OI rises but price fails to follow through / reverses (Solana case)
- stop_placement: Below structural level broken
- target_logic: Trend continuation
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles, OI
- proposed_param: oi_surge_zscore = +1.5; structural_break = prior swing high (requires pattern detection)
- param_count_note: 2 params; structural level detection is the hard part

---

### ITEM 13: Liquidation Continuation Signal (Trend Strength)

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_crypto_data_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: Post-Liquidation Continuation
- market_regime: trend
- instrument_scope: any
- zone_definition: Large liquidation event occurs in trend direction
- trigger: Price continues same direction after large liquidation event (not reversal). "Uncommon angle."
- entry_execution: taker
- direction_logic: Enter in trend direction after large liquidation fires in that direction. Trend confirmed stronger than expected.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: Large liquidation fires; price fails to reverse. Continuation = trend strength.
- volume_profile: [not mentioned]
- confluence_count: Liquidation magnitude + price continuation required

**D. Trade Management**
- invalidation: Price reverses immediately after liquidation (standard mean-reversion)
- stop_placement: [not mentioned]
- target_logic: Trend continuation
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: tick-trades (liquidation feed), candles
- proposed_param: liq_size_zscore = +2.0; continuation_bars = 3 (price holds above/below liq level for N candles)
- param_count_note: 2 params

---

### ITEM 14: ETH Mean Reversion — Multi-Signal Confluence Short

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_crypto_data_compressed.md
- claim_type: anecdote
- confidence: implied
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: ETH Multi-Signal Mean Reversion Short
- market_regime: range
- instrument_scope: ETH
- zone_definition: Sell-off into extreme with falling OI + negative funding + rising long liquidations
- trigger: Sell-off + falling OI (forced exits, not new shorts) + negative funding + rising long liquidations simultaneously. "Very strong mean-reversion signal."
- entry_execution: maker
- direction_logic: Long (fade the sell-off when all bearish signals stack = exhaustion bottom)

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: Falling OI = forced closures, not fresh shorts. Key distinction.
- funding_signal: Negative funding during sell-off = shorts paying longs = fear extreme.
- liquidation_signal: Rising long liquidations = longs being flushed. Core confirmation.
- volume_profile: [not mentioned]
- confluence_count: All four required: sell-off + falling OI + negative funding + rising long liquidations

**D. Trade Management**
- invalidation: OI continues falling with price (capitulation extends)
- stop_placement: [not mentioned]
- target_logic: Mean reversion bounce to prior level
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles, OI, funding, tick-trades
- proposed_param: oi_falling_zscore = -1.5; funding_negative = -0.05% per 8h; liq_long_zscore = +2.0
- param_count_note: 3 params; ETH-specific example but generalizable

---

### ITEM 15: Trade Early When Data Unusual, Chart Boring

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_crypto_data_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: claimed

**B. Setup Definition**
- setup_name: Early Positioning (Data Leads Price)
- market_regime: any
- instrument_scope: any
- zone_definition: Derivatives data showing extreme positioning while price action is quiet/muted
- trigger: Derivatives extreme (OI spike + negative funding, or other combo) while price barely moves. Spot chart boring.
- entry_execution: maker
- direction_logic: Enter direction implied by derivatives signal before price confirms. "Trade early in setup > trade obvious tops/bottoms."

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: OI spiking while price flat = early positioning
- funding_signal: Funding extreme while price muted = signal before pump/dump
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: Derivatives extreme + price muted (both conditions)

**D. Trade Management**
- invalidation: Derivatives normalize without price move (signal was noise)
- stop_placement: [not mentioned]
- target_logic: Wait for price to follow derivatives positioning
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: If no price follow-through within reasonable window, exit
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles, OI, funding
- proposed_param: price_range_pct = 1.0% (muted price threshold over lookback); derivatives_zscore_min = +2.0
- param_count_note: 2 params; requires defining "boring" quantitatively

---

### ITEM 16: BTC Bottom Detection via Composite Regime Indicator

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_when_bitcoin_bottoms_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: BTC Bottom Composite Regime
- market_regime: post-liquidation
- instrument_scope: BTC
- zone_definition: Composite indicator depressed = OI decreasing + negative funding + put overpayment (negative RR) + realized vol > implied vol
- trigger: All four components enter "red zone" simultaneously. "Sentiment exhausted — everyone given up."
- entry_execution: maker
- direction_logic: Long BTC. Zone-based entry on regime confirmation, not point prediction.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: Decreasing OI = required. Forced exits, not fresh shorts.
- funding_signal: Negative funding = required. Shorts paying longs = fear extreme.
- liquidation_signal: Large derivative cascades = bottoms characterized by overreactions
- volume_profile: [not mentioned]
- confluence_count: All four: decreasing OI + negative funding + put overpayment + realized vol > implied vol

**D. Trade Management**
- invalidation: Regime components don't all align; one or more absent
- stop_placement: [not mentioned]
- target_logic: Recovery from bottom; trend following once regime exits red zone
- r_multiple: [not mentioned]
- scale_rules: Avoid exact bottom catching; use zone-based entries
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: OI, funding, funding (options/RR), candles (realized vol vs implied vol)
- proposed_param: oi_falling = OI z-score < -1.0; funding_negative_gate = < -0.02% per 8h; rr_put_skew = RR z-score > +1.5; rv_iv_ratio = realized_vol / implied_vol > 1.0
- param_count_note: 4 params; requires options data (BTC-specific)

---

### ITEM 17: Gold/BTC Cointegration Debunked (Do Not Trade)

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_when_bitcoin_bottoms_compressed.md
- claim_type: concept
- confidence: stated
- verified_track_record: shown

**B. Setup Definition**
- setup_name: Gold-BTC Pairs Trade (REJECTED)
- market_regime: any
- instrument_scope: BTC
- zone_definition: BTC/Gold ratio mean-reversion
- trigger: [not applicable — setup rejected]
- entry_execution: [not applicable]
- direction_logic: Do NOT trade. No cointegration (Engle-Granger p = 0.44, need <0.05). Half-life ~216 days = too slow. Spread non-stationary. Only 3 data points for gold tops.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: [not applicable]

**D. Trade Management**
- invalidation: Entire concept invalidated statistically
- stop_placement: [not applicable]
- target_logic: [not applicable]
- r_multiple: [not applicable]
- scale_rules: [not applicable]
- time_stop: [not applicable]
- funding_avoidance: [not applicable]

**E. Quantify-ability**
- codeable: no
- data_need: candles
- proposed_param: [not applicable — do not implement]
- param_count_note: Excluded from jCoin pipeline

---

*End of extraction. Total: 17 items.*
