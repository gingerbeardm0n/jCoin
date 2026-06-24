# Trader Mayne — Integration Map

**Date:** 2026-06-20
**Source:** 21 extracted items (mayne_batch1 = 9, mayne_batch2 = 12)
**Purpose:** Where each Mayne concept lands in the jCoin engine. Avoids duplicate concept pages — most Mayne items enrich existing concepts or feed the new regime filter.

---

## Headline finding: TradingRiot and Mayne describe the SAME trade

| Element | TradingRiot | Trader Mayne | Synthesis |
|---|---|---|---|
| Where to fade | VWAP ±2σ, value-area edge | EQH/EQL, premium/discount of dealing range | Zone can be defined by stats (VWAP) OR structure (EQH/EQL). Cross-validating. |
| Trigger | CVD absorption candle (near-zero delta at extreme) | Swing Failure Pattern (wick past level + body close back + displacement) | Same exhaustion event. SFP is the **candle-only** version (no tick/CVD feed needed). |
| Regime gate | "range only" (vague) | HH/HL vs LL/LH classifier (concrete) | Mayne fills the gap → `concept_regime_filter.md`. |
| Target | back to VWAP / opposite band | opposing liquidity (swept EQL → target EQH) | Both = revert to the other side of the range. |

This convergence is the strongest validation signal in the project so far: two independent educators, different vocabularies, same mechanical trade.

---

## Item-by-item disposition

### → Feeds `concept_regime_filter.md` (NEW — the linchpin, audit #8)
- B2 ITEM 1 — Regime classification HH/HL vs LL/LH **(highest value)**
- B2 ITEM 2 — Break of Structure (continuation)
- B2 ITEM 3 — Market Structure Shift (reversal warning)
- B2 ITEM 5 — Internal vs external structure (trap filter)
- B2 ITEM 6 — 3-candle swing detection (building block)
- B2 ITEM 11 — Range contraction early-warning

### → Enriches `concept_vwap_band_fade.md` (adds a candle-only trigger)
- B1 ITEM 2 — **Swing Failure Pattern (SFP)** = price-action twin of CVD absorption. Add as an ALTERNATIVE trigger that works without tick data.
- B1 ITEM 3 — Break-and-Close sweep = SFP variant (body close through, then reclaim).
- B1 ITEM 1 — Liquidity sweep mechanics (BSL/SSL) = the "why" behind the fade.

### → Enriches `concept_volume_profile_fade.md` (structural zone definitions)
- B2 ITEM 10 — **Premium/Discount (dealing-range EQ)** = price-action equivalent of value-area edges. Discount = long zone, premium = short zone. Maps directly onto VAL/VAH.
- B1 ITEM 5/6 — Equal Highs / Equal Lows = structural zone (BSL/SSL pools). Alternative to volume-profile edges.

### → NEW veto rules (add to `concept_confirmation_signals.md`)
- B1 ITEM 7 — **EQH/EQL pre-sweep veto: "never sell below equal highs, never buy above equal lows."** Genuinely protective — stops the bot fading INTO an unswept liquidity pool that will likely get run. High-value, candle-only, cheap.
- B1 ITEM 4 — HTF trend weighting: never fade a sweep that opposes the higher-timeframe trend. Reinforces regime filter across timeframes.

### → New setups, but TREND-biased (defer — not mean-reversion)
- B2 ITEM 7,8 — Order Blocks + high-probability checklist (trend pullback entries; maker)
- B2 ITEM 9 — Breaker block (failed OB → SR flip; reversal-zone trade)
- B2 ITEM 12 — OB + FVG overlap (max-confluence trend entry)
- B2 ITEM 4 — HTF–LTF sync entry (trend timing)
- **These are for the future trend/continuation book, NOT the v1 mean-reversion engine.** Park them.

### → Target logic (already covered)
- B1 ITEM 8 — EQH/EQL sweep-and-reclaim full setup (the complete fade — combine zone + SFP + target)
- B1 ITEM 9 — Ping-pong target rule (swept one side → target the other)

---

## Key tension this surfaces (reinforces audit #5)

**Mayne's sweep/SFP entries are TAKER** — you enter *after* the displacement/reclaim confirms, by definition you can't rest a limit and know the sweep failed. This conflicts with the maker-first fee thesis.

Two ways to reconcile, to be tested:
1. **Maker variant:** rest a limit AT the EQH/EQL or premium/discount zone, anticipating the sweep+reclaim. Earns the spread but risks getting filled on real breakouts (adverse selection — audit #5).
2. **Taker variant:** wait for SFP/MSS confirmation, cross the spread. Pays ~9bps but only enters confirmed reversals.

Decision deferred to backtest: does the confirmed-taker win rate beat the maker-fee savings? This is a core economic question for the whole strategy and must be measured, not assumed.

---

## What this does to the param budget

New candle-only params introduced by Mayne (regime filter + SFP + EQH/EQL veto):
`swing_confirmation_candles`, `regime_lookback_swings`, `body_close_required`, `sfp_wick_min_pct`, `mss_min_bars`, `eqh_tolerance_pct`, `eqh_veto_range_pct` ≈ 7.

Good news: all candle-only (cheap data, backtestable today). They can REPLACE some of the expensive TradingRiot signals (OI/funding/CVD) for a v1 that runs on candles alone, then layer derivatives signals in v2. This is a cheaper, faster path to a first backtest.

---

## Recommended v1 reframing (post-Mayne)

A candle-only v1 is now possible and is the cheapest path to validation:
1. **Regime filter** (range gate) — candle-only
2. **Zone** = EQH/EQL or premium/discount edge — candle-only
3. **Trigger** = SFP (sweep + reclaim) — candle-only
4. **Veto** = EQH/EQL pre-sweep rule + HTF trend — candle-only
5. **Risk** = 0.5% per trade, stop beyond sweep wick, target opposite side

That's ~8–10 params, all backtestable on free candle data, no OI/funding/CVD/liquidation dependency. Derivatives signals (TradingRiot's OI/funding/CVD) become v2 conviction overlays once the candle-only core is proven. This directly addresses audit findings #1, #2, #10 (cheap data, backtestable, low param count).
