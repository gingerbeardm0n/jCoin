# Trader Mayne Batch 1 — Extracted Setups & Concepts

**Source articles:**
- mayne_liquidity_sweeps_compressed.md
- mayne_equal_high_low_compressed.md

**Extraction date:** 2026-06-20
**Total items:** 9

---

### ITEM 1: Liquidity Sweep — Core Concept (Buy-Side / Sell-Side)

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_liquidity_sweeps_compressed.md — Whiteboard Series Ep. 3
- claim_type: concept
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: Liquidity Sweep (BSL/SSL Mechanics)
- market_regime: any
- instrument_scope: any
- zone_definition: Buy-side liquidity (BSL) = cluster above prior swing highs (retail long stop losses + breakout buy stops). Sell-side liquidity (SSL) = cluster below prior swing lows (retail long stop losses + breakout sell stops). Zone located by identifying the most recent significant swing high (BSL) or swing low (SSL) on the working timeframe.
- trigger: [not applicable — foundational concept, not direct entry rule]
- entry_execution: [not applicable]
- direction_logic: Market alternates BSL → SSL → BSL. Identifying which was just run tells you the next directional target. A BSL sweep = look long toward SSL. A SSL sweep = look short toward BSL.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: Stop-run itself is effectively a forced-close cascade on retail stops
- volume_profile: [not mentioned]
- confluence_count: [not mentioned]

**D. Trade Management**
- invalidation: [not mentioned]
- stop_placement: [not mentioned]
- target_logic: Opposing liquidity level (swept BSL → target SSL, and vice versa)
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: swing_lookback_bars = 20 (N-bar local high/low detection); bsl_ssl_label = prior swing high / prior swing low
- param_count_note: 1 param; foundational — feeds all sweep-entry items below

---

### ITEM 2: Swing Failure Pattern (SFP) Entry

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_liquidity_sweeps_compressed.md — Whiteboard Series Ep. 3
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: Swing Failure Pattern (SFP)
- market_regime: any
- instrument_scope: any
- zone_definition: Prior swing high (BSL) or prior swing low (SSL) as defined by N-bar lookback. Swing high: local high with lower highs on both sides. Sweep occurs when candle wick pierces the swing level but candle BODY closes back on the origin side.
- trigger: Candle wicks past prior swing high/low AND closes back on origin side (body close, not wick close). Then displacement candle fires: aggressive, fast move in opposite direction that breaks the most recent minor swing in new direction (MSS). Both conditions required — wick-close-back alone is not sufficient without displacement.
- entry_execution: taker (enter after displacement candle confirms reclaim; cannot enter on the sweep candle close alone since displacement confirmation comes next bar)
- direction_logic: SFP above BSL = short entry (fade the false breakout). SFP below SSL = long entry (fade the false breakdown). Direction is always against the sweep.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: The sweep wick itself represents stop cascade; displacement confirms institutional absorption
- volume_profile: [not mentioned]
- confluence_count: Two required: (1) SFP candle pattern (wick past level, close back) + (2) displacement candle creating MSS

**D. Trade Management**
- invalidation: Price lingers above/below swept level without displacement (= real breakout, not sweep)
- stop_placement: Beyond the sweep wick extreme (the false move high/low)
- target_logic: Opposing liquidity level (prior SSL if fading BSL sweep, prior BSL if fading SSL sweep)
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: swing_lookback_bars = 20; sfp_wick_min_pct = 0.05% (wick must pierce level by minimum threshold); mss_min_bars = 1 (displacement must close past last minor swing within N bars of sweep)
- param_count_note: 3 params; most mechanically-clean sweep entry

---

### ITEM 3: Break-and-Close Sweep Entry

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_liquidity_sweeps_compressed.md — Whiteboard Series Ep. 3
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: Break-and-Close Sweep (False Breakout)
- market_regime: any
- instrument_scope: any
- zone_definition: Prior swing high (BSL) or swing low (SSL). Sweep occurs when candle(s) close past the level, but then subsequent candle(s) close back on the origin side promptly. Key distinction from SFP: body closes through the level, not just a wick.
- trigger: Candle closes past swing level (body close through) AND within the next 1–3 candles price closes back on origin side (prompt reversion required — lingering above = real breakout). Then displacement fires creating MSS.
- entry_execution: taker (enter on close-back candle or displacement candle; not on the break candle since direction not confirmed)
- direction_logic: Close-back above BSL → short (false breakout). Close-back below SSL → long (false breakdown). Fade direction is against the break.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: Body close through level traps breakout traders who buy the break; rapid reversal traps them
- volume_profile: [not mentioned]
- confluence_count: Two required: (1) body close through + prompt close-back + (2) displacement/MSS

**D. Trade Management**
- invalidation: Price lingers above/below level after body close (>3 candles without close-back = real breakout)
- stop_placement: Beyond the extreme of the false break (high/low of the break candle)
- target_logic: Opposing liquidity level
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: close-back_max_bars = 3 (if no close-back within 3 bars of break, treat as breakout)
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: swing_lookback_bars = 20; close_back_max_bars = 3; mss_min_bars = 2
- param_count_note: 3 params; slightly more complex than SFP due to multi-candle window logic

---

### ITEM 4: Timeframe Weighting for Sweeps

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_liquidity_sweeps_compressed.md — Whiteboard Series Ep. 3
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: HTF Sweep Weighting Rule
- market_regime: any
- instrument_scope: any
- zone_definition: Swing high/low identified on multiple timeframes. Higher-timeframe swing levels carry more weight (more stops cluster there, more institutional significance).
- trigger: Sweep detected on any timeframe. Weight = proportional to timeframe of the swept level (weekly SSL > 4H SSL > 1H SSL).
- entry_execution: [not directly an entry — a filter/weight rule]
- direction_logic: HTF trend dominates. A 4H bearish sweep during a weekly bull trend is NOT a short signal — it is a potential long entry after 4H structure realigns bullish. Never fade a sweep that opposes the HTF trend.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: HTF trend alignment required as veto gate before any sweep entry

**D. Trade Management**
- invalidation: Sweep on LTF that contradicts HTF trend = do not trade
- stop_placement: [not mentioned]
- target_logic: [not mentioned]
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles
- proposed_param: htf_timeframe = 1D or 1W (define the "higher" timeframe for trend filter); ltf_timeframe = 4H or 1H (execution timeframe); trend_filter_method = higher_high_higher_low sequence on HTF
- param_count_note: 2 params; HTF trend definition requires its own detection logic (adds complexity)

---

### ITEM 5: Equal Highs (EQH) Zone Definition

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_equal_high_low_compressed.md — Technical Bootcamp Ep. 6
- claim_type: concept
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: Equal Highs (EQH) Zone
- market_regime: range
- instrument_scope: any
- zone_definition: 2+ swing highs within a price tolerance of each other (suggested ~0.1–0.5%). Each swing high defined as local high with lower highs on both sides (N-bar lookback). "Relative" EQH: highs within ~1–2% tolerance — treated the same but with reduced confidence. EQH mechanically = BSL pool (short stops + breakout buy stops stacked above).
- trigger: [not an entry trigger — zone identification only]
- entry_execution: [not applicable]
- direction_logic: EQH above current price = DO NOT enter shorts from below. Wait for sweep of EQH first. Zone above EQH (post-sweep) = valid entry zone. Zone below EQH (pre-sweep) = filtered out.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: [not mentioned — zone definition, not entry]

**D. Trade Management**
- invalidation: EQH exists above → veto all short entries from below until swept
- stop_placement: [not mentioned]
- target_logic: After EQL sweep, target = EQH. After EQH sweep, target = EQL.
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: swing_lookback_bars = 20; eqh_tolerance_pct = 0.3% (tight) or eqh_tolerance_pct_relative = 1.5% (wide); eqh_min_count = 2 (minimum swing highs to form EQH)
- param_count_note: 3 params; tolerance threshold is the key tunable — start tight, widen to validate

---

### ITEM 6: Equal Lows (EQL) Zone Definition

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_equal_high_low_compressed.md — Technical Bootcamp Ep. 6
- claim_type: concept
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: Equal Lows (EQL) Zone
- market_regime: range
- instrument_scope: any
- zone_definition: 2+ swing lows within a price tolerance of each other (~0.1–0.5% tight, ~1–2% relative). Each swing low = local low with higher lows on both sides (N-bar lookback). EQL mechanically = SSL pool (long stops + breakout sell stops stacked below).
- trigger: [not an entry trigger — zone identification only]
- entry_execution: [not applicable]
- direction_logic: EQL below current price = DO NOT enter longs from above. Wait for sweep of EQL first. Zone below EQL (post-sweep entry) = valid. Zone above EQL (pre-sweep) = filtered out.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: [not mentioned — zone definition, not entry]

**D. Trade Management**
- invalidation: EQL exists below → veto all long entries from above until swept
- stop_placement: [not mentioned]
- target_logic: After EQL sweep, target = EQH. After EQH sweep, target = EQL.
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: swing_lookback_bars = 20; eql_tolerance_pct = 0.3%; eql_min_count = 2
- param_count_note: 3 params (shared logic with EQH — same detection engine, different direction)

---

### ITEM 7: EQH/EQL Pre-Entry Veto Rule

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_equal_high_low_compressed.md — Technical Bootcamp Ep. 6
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: EQH/EQL Pre-Sweep Veto
- market_regime: any
- instrument_scope: any
- zone_definition: Any live unswept EQH above price or EQL below price. "Live" = not yet swept (wick has not exceeded the level and closed back).
- trigger: Veto fires when: (1) EQH live above AND trade direction = short from below EQH, OR (2) EQL live below AND trade direction = long from above EQL. Trade is suppressed until liquidity is swept.
- entry_execution: [not applicable — veto rule]
- direction_logic: "If you don't see the liquidity, you will be the liquidity." — never enter in a direction where unswept opposing liquidity exists at a nearby level. "Never sell below equal highs. Never buy above equal lows."

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: Single-condition veto: unswept EQH/EQL in path of trade = block trade

**D. Trade Management**
- invalidation: EQH/EQL gets swept → veto lifted, entry conditions reassessed
- stop_placement: [not applicable]
- target_logic: [not applicable]
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: eqh_veto_range_pct = 2.0% (only veto if EQH is within N% of entry price — avoids vetoing distant zones); eql_veto_range_pct = 2.0%
- param_count_note: 2 params; critical filter for mean-reversion entries — suppresses false longs/shorts into liquidity

---

### ITEM 8: EQH/EQL Sweep Entry (Full Confluence)

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_equal_high_low_compressed.md — Technical Bootcamp Ep. 6
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: EQH/EQL Sweep-and-Reclaim Entry
- market_regime: range
- instrument_scope: any
- zone_definition: EQH or EQL level as defined above. Entry zone = the level itself (post-sweep). Price must sweep the EQL/EQH (wick or close past it, per SFP or Break-and-Close pattern) then show absorption evidence.
- trigger: All of the following required: (1) EQH or EQL swept (price moves past level), (2) absorption evidence — large wicks lower with closes back inside range, or aggressive reversal candle body closing in opposite direction, (3) BOS/MSS in new direction on internal structure, (4) demand/supply zone present in new direction, (5) open FVG (imbalance) in direction of trade. Fewer conditions = reduced confidence, not a veto; all 5 = highest quality.
- entry_execution: taker (enter after BOS/MSS confirms in new direction — cannot place resting limit without structural confirmation)
- direction_logic: EQL swept → long (fade the false breakdown, target EQH). EQH swept → short (fade the false breakout, target EQL).

**C. Confirmation/Veto**
- cvd_signal: Absorption evidence (large wicks + closes back) aligns with CVD divergence conceptually [not explicitly named by Mayne but structurally equivalent]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: Stop cascade at EQL/EQH is the sweep event itself
- volume_profile: [not mentioned]
- confluence_count: 5-factor framework: sweep + absorption + BOS/MSS + demand/supply zone + open FVG. All 5 = max confidence. Minimum 3 to consider entry.

**D. Trade Management**
- invalidation: Price sweeps EQL/EQH but fails to show absorption — continues past level = real breakout, not a sweep
- stop_placement: Beyond the sweep wick extreme (high/low of the false move)
- target_logic: Opposing liquidity level — swept EQL → target EQH; swept EQH → target EQL
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: partial
- data_need: candles
- proposed_param: eqh_tolerance_pct = 0.3%; swing_lookback_bars = 20; absorption_wick_ratio = 0.6 (wick must be >60% of candle range); mss_confirmation_bars = 3; fvg_min_size_pct = 0.1% (open gap threshold); confluence_min_count = 3
- param_count_note: 6 params; FVG and demand/supply zone detection adds complexity — partial codeable due to FVG discretion in defining "open" imbalance

---

### ITEM 9: EQH/EQL Target Logic (Ping-Pong Rule)

**A. Provenance**
- educator: Trader Mayne
- source_id: mayne_equal_high_low_compressed.md — Technical Bootcamp Ep. 6
- claim_type: rule
- confidence: stated
- verified_track_record: none

**B. Setup Definition**
- setup_name: EQH/EQL Opposing Target Rule
- market_regime: range
- instrument_scope: any
- zone_definition: After a sweep fires, the unswept liquidity on the opposite side of the range becomes the trade target. Mechanically: track the nearest live EQH and nearest live EQL at all times.
- trigger: Sweep of one side confirmed (per SFP or Break-and-Close) → the other side becomes the target. Whichever swept first: EQL swept → EQH is target; EQH swept → EQL is target.
- entry_execution: taker
- direction_logic: Direction dictated by which side was swept. Always trading away from the swept level toward the unswept level.

**C. Confirmation/Veto**
- cvd_signal: [not mentioned]
- oi_signal: [not mentioned]
- funding_signal: [not mentioned]
- liquidation_signal: [not mentioned]
- volume_profile: [not mentioned]
- confluence_count: Requires sweep confirmation first; this rule only governs target selection

**D. Trade Management**
- invalidation: Target EQH/EQL gets swept before price reaches it — reassess; new opposing level becomes the next target
- stop_placement: Beyond the sweep wick of the original sweep
- target_logic: Opposing EQH (if came from EQL sweep) or opposing EQL (if came from EQH sweep). Fixed price level — not VWAP or MA.
- r_multiple: [not mentioned]
- scale_rules: [not mentioned]
- time_stop: [not mentioned]
- funding_avoidance: [not mentioned]

**E. Quantify-ability**
- codeable: yes
- data_need: candles
- proposed_param: eqh_tolerance_pct = 0.3%; eql_tolerance_pct = 0.3%; swing_lookback_bars = 20 (shared with EQH/EQL detection)
- param_count_note: 0 new params (reuses EQH/EQL detection params); target selection is deterministic once zones identified

---

*End of extraction. Total: 9 items.*
