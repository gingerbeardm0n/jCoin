# TradingRiot Batch 2 — Extracted Setups & Concepts

Source articles:
1. tradingriot_auction_market_theory_compressed.md
2. tradingriot_liquidity_compressed.md
3. tradingriot_order_book_compressed.md
4. tradingriot_volume_analysis_compressed.md

---

### ITEM 1: AMT Balance-Edge Mean Reversion

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_auction_market_theory_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: AMT Balance-Edge Mean Reversion
- market_regime: range
- instrument_scope: any
- zone_definition: Edge of balance area (value area boundary); price reaches the extreme of the established value area or VWAP ± 1–2 SD bands
- trigger: Price accepts (closes) inside balance zone after touching edge, signaling rejection
- entry_execution: maker
- direction_logic: Both; long at lower edge, short at upper edge; bias = revert toward opposite edge/POC

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: POC as mean target; HVN edges as zone definition; value area (68% volume) as balance boundary
- confluence_count: [not mentioned]; implied: price action acceptance + volume profile zone

**D. Trade Management**
- invalidation: Price accepts OUTSIDE balance area (closes beyond edge with time + volume confirmation)
- stop_placement: Beyond the balance edge; if price accepts outside value area, setup is void
- target_logic: Opposite edge of balance area or POC (highest volume level = "fairest price")
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: Implied — if price builds time + volume at edge, it may break through (AMT Rule 5); exit if that occurs
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles, OI (volume profile construction)
- proposed_param: vwap_sd_entry = 2.0; value_area_pct = 0.68; require_close_inside = true
- param_count_note: 3 params; within cap

---

### ITEM 2: AMT Breakout — Accept Outside Balance

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_auction_market_theory_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: AMT Breakout — Accept Outside Balance
- market_regime: trend
- instrument_scope: any
- zone_definition: Price breaks outside established value area / VWAP band; confirmed by time + volume build at the edge (AMT Rule 5)
- trigger: Price closes outside balance AND builds time + volume at that level (acceptance, not fake-out)
- entry_execution: taker
- direction_logic: Both; direction of breakout; target = prior balance POC (prior value area's highest-volume level)

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: Time + volume build at edge is the confirmation; prior balance POC = target
- confluence_count: 2 (acceptance outside + volume/time confirmation)

**D. Trade Management**
- invalidation: Price returns inside prior balance area (failed auction)
- stop_placement: Back inside balance edge
- target_logic: Prior balance POC (often next HVN from composite volume profile)
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles, OI (volume profile)
- proposed_param: min_bars_outside = 3; breakout_volume_sd = 1.5
- param_count_note: 2 params; within cap; note this is Strategy 2 (breakout) territory per schema

---

### ITEM 3: POC Rejection Fade

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_auction_market_theory_compressed.md
- claim_type: rule
- confidence: implied
- verified_track_record: none

**B. Setup Definition**
- setup_name: POC Rejection Fade
- market_regime: range
- instrument_scope: any
- zone_definition: Prior (unvisited for extended period) Point of Control (POC) — highest volume level from a prior session's profile
- trigger: Strong rejection at POC (price reaches old POC, shows clear rejection candle/pattern — prevents full rotation per AMT Rule 4)
- entry_execution: taker
- direction_logic: Both; fade the move into old POC when strong rejection observed; exception to full rotation expectation

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: Old POC = the zone; "strong reaction" at POC = veto for continued rotation
- confluence_count: 1 (strong POC rejection candle)

**D. Trade Management**
- invalidation: Price trades through and accepts beyond POC
- stop_placement: Beyond POC level
- target_logic: Mean of current value area / VWAP
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles, OI (volume profile for POC identification)
- proposed_param: poc_lookback_days = 30; poc_rejection_wick_ratio = 0.6
- param_count_note: 2 params; within cap

---

### ITEM 4: VWAP + SD Band Mean Reversion

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_auction_market_theory_compressed.md
- claim_type: concept
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: VWAP + SD Band Mean Reversion
- market_regime: range
- instrument_scope: any
- zone_definition: VWAP ± 1–2 standard deviation bands; price statistically extended from fair value
- trigger: Price reaches VWAP ± 2 SD; look for acceptance (close inside band after touch) or rejection candle
- entry_execution: maker
- direction_logic: Both; long at -2 SD, short at +2 SD; target = VWAP (fair value)

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: VWAP = fair value proxy; bands represent AMT balance boundaries
- confluence_count: [not mentioned]

**D. Trade Management**
- invalidation: Price accepts and closes beyond the SD band (imbalance confirmed)
- stop_placement: Beyond the SD band level
- target_logic: VWAP (mean); secondary target = opposite SD band
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles, OI (for VWAP calculation)
- proposed_param: vwap_period = daily; vwap_sd_entry = 2.0; vwap_sd_target = 0.0
- param_count_note: 3 params; core to Strategy 1 mean-reversion

---

### ITEM 5: Post-Liquidation Cascade Reversal

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_liquidity_compressed.md
- claim_type: rule
- confidence: implied
- verified_track_record: none

**B. Setup Definition**
- setup_name: Post-Liquidation Cascade Reversal
- market_regime: post-liquidation
- instrument_scope: any (crypto-specific context)
- zone_definition: Level where price spikes sharply triggering stop-losses/liquidations; identified post-facto by sharp price move + OI drop
- trigger: Sharp price spike + visible open interest drop (forced closures confirmed); then market slows and begins accumulation/distribution
- entry_execution: maker
- direction_logic: Both; fade the spike direction after cascade completes; market does not move in straight lines after large liquidation events

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: OI drop = forced closure confirmation; required for setup validation
- funding_signal: [not mentioned]
- liquidation_signal: Sharp price move + OI drop = liquidation cascade confirmation; liquidation heatmaps (Leviathan) for estimated levels
- volume_profile: [not mentioned]
- confluence_count: 2 (sharp move + OI drop)

**D. Trade Management**
- invalidation: Price continues moving in cascade direction without slowing
- stop_placement: Beyond cascade spike extreme
- target_logic: Mean-revert to pre-spike level; market accumulates/distributes then returns
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles, OI, tick-trades
- proposed_param: oi_drop_pct_threshold = 0.03; spike_atr_mult = 2.0
- param_count_note: 2 params; OI feed required

---

### ITEM 6: Order Book Delta Imbalance Confluence

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_order_book_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: Order Book Delta Imbalance Confluence
- market_regime: any
- instrument_scope: BTC (example: $50M threshold); any crypto with sufficient spot book depth
- zone_definition: Not a zone per se — used as confluence overlay; significant bid/ask delta imbalance in spot order book within 10% depth of market price
- trigger: Order book delta (bid volume − ask volume) exceeds threshold at a price level; use as confluence, NOT standalone entry
- entry_execution: maker
- direction_logic: Both; skewed to buy side → long bias; skewed to sell side → short bias; note: SOL example showed 7% rally despite sell-skew — not directional alone

**C. Confirmation/Veto**
- cvd_signal: Implied — delta tracking is related; order book delta distinct from trade delta but complementary
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: Must combine with price action + moving averages; explicitly stated as confluence, not standalone

**D. Trade Management**
- invalidation: Delta imbalance reverses or disappears before price moves
- stop_placement: [not mentioned]
- target_logic: Mean reversion after imbalance resolves; spot traders patient (1+ hours before mean-revert)
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: Can stay skewed 1+ hours — patience required
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: orderbook
- proposed_param: ob_delta_threshold_intraday = 50000000 (BTC); ob_depth_pct_scalp = 0.025; ob_depth_pct_swing = 0.05
- param_count_note: 3 params; requires aggregated spot order book feed (Trdr.io recommended)

---

### ITEM 7: Spot vs Futures Book Divergence Signal

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_order_book_compressed.md
- claim_type: concept
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: Spot vs Futures Book Divergence Signal
- market_regime: any
- instrument_scope: BTC, ETH, alts (crypto only; concept: futures book = noise, spot book = signal)
- zone_definition: Price levels where large spot orders cluster (visible as meaningful turns); futures book at same level shows distributed MM orders everywhere
- trigger: Large spot limit orders visible at a key price level while futures book shows normal MM noise; meaningful turns confirmed by spot-only book analysis
- entry_execution: maker
- direction_logic: Both; align with direction implied by large spot orders (real capital, directional intent)

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: 1 (large spot order at key level); combine with price action per article

**D. Trade Management**
- invalidation: Spot orders pulled (spoofed) before price reaches them
- stop_placement: [not mentioned]
- target_logic: [not mentioned]
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: orderbook (spot-specific feed required, separate from perp)
- proposed_param: spot_order_size_threshold = [asset-specific]; spoof_check = monitor if order persists as price approaches
- param_count_note: 1–2 params; requires separate spot book feed; partial because spoofing detection is hard to code robustly

---

### ITEM 8: LVN Entry — Low Volume Node Fade

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_volume_analysis_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: LVN Entry — Low Volume Node Fade
- market_regime: any
- instrument_scope: any
- zone_definition: Low Volume Node (LVN) = void in composite volume profile where very little volume was executed; price moves fast through LVN with minimal resistance
- trigger: Price enters an LVN; enter at the near edge of the LVN expecting fast travel through it
- entry_execution: taker (price moves quickly; maker risk of not filling)
- direction_logic: Both; enter in the direction price is already moving through LVN; best entry zone because price moves quickly your way

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: LVN identification from composite volume profile required; HVN = target
- confluence_count: Implied 2+ (LVN location + price action direction + support/resistance confluence per article)

**D. Trade Management**
- invalidation: Price stalls inside LVN or reverses back through entry
- stop_placement: Back at the LVN boundary edge (where LVN begins)
- target_logic: Next HVN or POC
- r_multiple: [not mentioned]
- scale_rules: Adjust levels as market builds volume
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles, OI (composite volume profile construction)
- proposed_param: lvn_volume_threshold_pct = 0.20 (below 20% of average volume at level); hvn_target_volume_pct = 1.5
- param_count_note: 2 params; within cap

---

### ITEM 9: HVN Edge Entry (Fade Fast Rally into POC)

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_volume_analysis_compressed.md
- claim_type: rule
- confidence: implied
- verified_track_record: none

**B. Setup Definition**
- setup_name: HVN Edge Entry — Fade Fast Rally into Old POC
- market_regime: range
- instrument_scope: any
- zone_definition: Edge of a High Volume Node (HVN) or old unvisited POC (most executed volume = fair value zone); fast rally into this zone
- trigger: Fast (high-momentum) rally into old POC that hasn't been visited in a long time; enter fade at HVN edge or POC level
- entry_execution: maker
- direction_logic: Short (fade fast rally); the exception noted is POC as resistance, not support, on fast rallies

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: POC identification from composite volume profile; "old" POC = not visited for extended time
- confluence_count: 2 (fast rally velocity + old unvisited POC)

**D. Trade Management**
- invalidation: Price accepts above POC (closes and holds above with volume)
- stop_placement: Above POC / HVN boundary
- target_logic: Back to recent value area mean / VWAP
- r_multiple: [not mentioned]
- scale_rules: Adjust levels as market builds new volume at levels
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles, OI (composite volume profile)
- proposed_param: poc_lookback_bars = 200; fast_rally_atr_mult = 1.5 (velocity check); poc_unvisited_bars = 50
- param_count_note: 3 params; within cap

---

### ITEM 10: rVOL Breakout Confirmation

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_volume_analysis_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: rVOL Breakout Confirmation
- market_regime: trend
- instrument_scope: any
- zone_definition: Breakout from range or key level; identified by price + relative volume spike
- trigger: Volume bar exceeds 2 standard deviations above rolling mean (rVOL "blue bar"); at breakout level = confirmation of large trader initiation
- entry_execution: taker
- direction_logic: Both; direction of the breakout; high rVOL at move start = institutional initiation signal

**C. Confirmation/Veto**
- cvd_signal: Delta complements — high positive delta + high rVOL = aggressive buyers; high rVOL + small delta = balanced/suspect
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: rVOL calculation relative to fair value volume baseline; LVN/HVN context for the breakout level
- confluence_count: 2 (rVOL spike + price action breakout); optionally add delta direction

**D. Trade Management**
- invalidation: rVOL spike accompanied by small delta (retail FOMO at move end, not institutional initiation)
- stop_placement: Back inside broken level / value area
- target_logic: Next HVN or POC on composite volume profile
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles, tick-trades (for delta)
- proposed_param: rvol_threshold_sd = 2.0; rvol_lookback_bars = 50; delta_direction_match = true
- param_count_note: 3 params; within cap; note this is Strategy 2 (breakout) territory per schema

---

### ITEM 11: Low rVOL Zone as Target

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_volume_analysis_compressed.md
- claim_type: concept
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: Low rVOL Zone as Target / Magnet
- market_regime: any
- instrument_scope: any
- zone_definition: Price areas where rVOL is consistently below 2 SD below mean (yellow bars) = low participation zones; these areas won't attract traders and become magnet targets for incoming price
- trigger: [not a direct entry setup]; used as target zone selection — when price is heading toward a low rVOL zone, expect fast travel
- entry_execution: [not applicable — this is target logic, not entry]
- direction_logic: Both; direction of incoming move; low rVOL zones function like LVNs — minimal resistance

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: rVOL coloring (yellow = low participation = void/target); correlates with LVN concept
- confluence_count: [not mentioned]

**D. Trade Management**
- invalidation: [not applicable]
- stop_placement: [not mentioned]
- target_logic: Low rVOL zone = fast-travel target; extend targets to next HVN/POC beyond the LrVOL area
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: rvol_low_threshold_sd = -2.0; rvol_lookback_bars = 50
- param_count_note: 2 params; primarily affects target selection logic

---

### ITEM 12: Volume Delta Divergence — Absorption at Extreme

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_volume_analysis_compressed.md
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: Volume Delta Divergence — Absorption at Extreme
- market_regime: range
- instrument_scope: any
- zone_definition: Key support/resistance level, VWAP band extreme, or HVN edge; where high volume candle occurs but delta is small (balanced participation)
- trigger: High volume candle (rVOL spike) at zone BUT delta is small/near-zero = absorption signal; aggressive sellers/buyers absorbed by opposite side; mean-reversion likely
- entry_execution: maker
- direction_logic: Both; if at lower zone with high volume + near-zero delta → long (sellers absorbed); if at upper zone → short (buyers absorbed)

**C. Confirmation/Veto**
- cvd_signal: Delta reading required; near-zero delta on high-volume candle = absorption/balanced; positive delta on high-volume = genuine breakout (veto for fade)
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: HVN/LVN context; absorption most meaningful at HVN edges or VWAP SD bands
- confluence_count: 2 (high rVOL + near-zero delta at key zone)

**D. Trade Management**
- invalidation: High volume + high same-direction delta (genuine breakout, not absorption)
- stop_placement: Beyond the absorption candle's extreme
- target_logic: Mean reversion to VWAP / POC
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles, tick-trades (for delta)
- proposed_param: absorption_rvol_sd = 2.0; absorption_delta_pct = 0.10 (delta < 10% of volume = absorbed); zone_proximity_atr = 0.5
- param_count_note: 3 params; core to Strategy 1; highly relevant to CVD-veto in jCoin

---

### ITEM 13: AMT — Concept: Market Profile / Volume Profile Framework

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_auction_market_theory_compressed.md
- claim_type: concept
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: AMT Framework — Market Profile / Volume Profile
- market_regime: any
- instrument_scope: any
- zone_definition: Value Area = 68% of volume traded (fair value agreed area); POC = most time/volume (fairest price); these become S/R zones for other setups
- trigger: [concept — not a standalone entry; provides the zone-definition layer for other setups]
- entry_execution: [not applicable]
- direction_logic: Context: inside value area = range/chop expected; outside value area = trend expected

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: Core concept — volume profile IS the tool (HVN, LVN, POC, Value Area)
- confluence_count: [not applicable]

**D. Trade Management**
- invalidation: [not applicable — this is the framework]
- stop_placement: [not applicable]
- target_logic: Always toward POC/mean; POC = highest probability target
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles, OI
- proposed_param: value_area_pct = 0.68; profile_lookback_period = session/week/month (configurable)
- param_count_note: 2 params; this is the zone-generation layer for other setups

---

### ITEM 14: Liquidity — Concept: Liquidation Heatmap Approach

**A. Provenance**
- educator: TradingRiot
- source_id: tradingriot_liquidity_compressed.md
- claim_type: concept
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: Liquidation Heatmap — OI-Based Level Estimation
- market_regime: any
- instrument_scope: any (crypto-specific)
- zone_definition: Estimated liquidation levels derived from OI change analysis (via Leviathan heatmaps); most estimated levels sit at logical S/R zones — warns against pre-fading every level
- trigger: NOT a standalone entry; watch OI + order flow + relative volume behavior AT liquidation levels rather than blindly pre-fading them
- entry_execution: maker (if used at all)
- direction_logic: Both; but explicitly: do NOT pre-fade every liquidation level; combine with OI + order flow + rVOL behavior AT the level

**C. Confirmation/Veto**
- cvd_signal: Order flow confirmation required
- oi_signal: OI drop at level = cascade confirmation; OI + order flow = required confluence
- funding_signal: [not mentioned]
- liquidation_signal: Heatmap provides estimated level; actual trigger requires OI drop + price behavior
- volume_profile: Relative volume at level required as confluence
- confluence_count: 3 (estimated liq level + OI behavior + order flow + rVOL)

**D. Trade Management**
- invalidation: Price passes through liquidation level without OI drop or order flow confirmation
- stop_placement: [not mentioned]
- target_logic: [not mentioned]
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: OI, candles, tick-trades
- proposed_param: oi_drop_threshold = 0.03; liq_level_source = Leviathan API (or internal OI-change model)
- param_count_note: 2 params; requires external heatmap data or OI-change-based level estimation

---
