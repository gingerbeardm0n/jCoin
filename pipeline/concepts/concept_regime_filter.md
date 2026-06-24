# Concept: Market Regime Filter (Trend vs Range)

**Last updated:** 2026-06-20
**Source:** Trader Mayne (Batch2 ITEM 1, 2, 3, 5, 6, 11) + TradingRiot (AMT value-area context)
**Sample size:** 0 verified fills — classifier rule, validate against data before trusting
**Status:** HIGHEST PRIORITY. This is the mean-reversion bot's master on/off switch.

> **Why this concept matters most:** Every fade setup (VWAP band fade, volume profile fade, EQH/EQL sweep) is only valid in a RANGE. In a trend, fading = selling more of a position as the trend runs you over (the spec calls this "the strategy's killer"). The audit (2026-06-19, finding #8) flagged that this filter was the linchpin and the least-specified piece in the plan. Trader Mayne supplies a concrete, candle-only, mechanically-codeable classifier. This page closes that gap.

---

## Definition

Classify the market into one of three regimes from swing-point structure, using **candle body closes** (not wicks):

- **Uptrend** = sequence of Higher Highs + Higher Lows (HH/HL)
- **Downtrend** = sequence of Lower Lows + Lower Highs (LL/LH)
- **Range** = no clean HH/HL or LL/LH chain; equal highs/lows or ambiguous. "If it's not obvious, we're probably sideways."

**The bot fades extremes ONLY when regime == range. It stands aside in uptrend and downtrend.** This single gate is what separates survivable mean-reversion from account death.

---

## Building Blocks (in dependency order)

### 1. Swing detection (3-candle confirmation) — Batch2 ITEM 6
A swing is not valid until confirmed by 3 candles:
```
swing_high at N:  candle[N-1].high < candle[N].high AND candle[N+1].high < candle[N].high
swing_low  at N:  candle[N-1].low  > candle[N].low  AND candle[N+1].low  > candle[N].low
```
Param: `swing_confirmation_candles = 3` (Mayne hardcodes this).
Note: 3-candle (fractal) is the simplest definition; `swing_lookback_bars` (e.g. 20) is a stronger/looser alternative used in the sweep concepts. Decide one canonical swing definition for the engine — do NOT run two.

### 2. Trend classification — Batch2 ITEM 1
From the confirmed swing series:
- ≥ `regime_lookback_swings` (start = 3) consecutive HH+HL → uptrend
- ≥ 3 consecutive LL+LH → downtrend
- else → range

### 3. Break of Structure (BOS) = continuation — Batch2 ITEM 2
Body close past prior swing high (bull BOS) / swing low (bear BOS) → trend continues. Wick-only past the level is NOT a BOS — it's a liquidity sweep / SFP (see EQH/EQL concept).

### 4. Market Structure Shift (MSS) = possible reversal — Batch2 ITEM 3
Body close below most-recent validated HL (bearish MSS) / above most-recent validated LH (bullish MSS) → trend MAY be ending. MSS alone is NOT confirmation; wait for the next opposing swing + a BOS in the new direction before flipping the regime label.

### 5. Internal vs external structure (trap filter) — Batch2 ITEM 5
A BOS *inside* the range of a prior impulse is **internal structure = noise**. Only an **external** BOS (close past the macro swing high/low) is a valid structural signal. This prevents false regime flips that would wrongly switch the fade engine on during a trend. **Critical safety rule.**

### 6. Range contraction (soft early-warning) — Batch2 ITEM 11
Successive impulse legs shrinking (each < ~70% of prior, over ≥3 impulses) often precedes a reversal. Use only as soft confirmation that an MSS is genuine, never standalone.

---

## How it gates the fade engine

```
regime = classify(swing_series)

IF regime == range:
    fade engine ENABLED (VWAP band fade, volume profile fade, EQH/EQL sweep all live)
IF regime == uptrend OR downtrend:
    fade engine DISABLED — stand aside
    (optional v2: trend-continuation pullback entries — NOT mean-reversion, separate book)

ON regime transition (MSS confirmed by opposing swing + new-direction BOS):
    flatten any open fade positions that the new regime invalidates
    re-evaluate
```

---

## Codeable Assessment

**Codeable: YES** — pure candle data, no tick/CVD/OI/funding feed required. This is the cheapest-data, highest-leverage component in the entire system. It can and should be backtested first, before any setup that depends on it.

Friction: "swing" definition has two candidate forms (3-candle fractal vs N-bar lookback). Must pick one canonical definition engine-wide. The HH/HL chain logic and internal/external boundary tracking need careful state management but are deterministic.

---

## Parameter Inventory

| Parameter | Source | Proposed Start | Notes |
|-----------|--------|----------------|-------|
| `swing_confirmation_candles` | B2 ITEM 6 | `3` | canonical swing detector |
| `regime_lookback_swings` | B2 ITEM 1 | `3` | swings needed to confirm a trend |
| `body_close_required` | B2 ITEM 1,2,3 | `true` | wick-only breaks ignored everywhere |
| `impulse_range_decay_pct` | B2 ITEM 11 | `0.70` | soft reversal early-warning (v2) |

**Param count: 4 (3 for v1; decay is v2).** Cheap. Leaves room under the 13–15 cap.

---

## jCoin Decision Rules

```
REGIME_FILTER — runs before every fade-setup evaluation

  swings = detect_swings(candles, swing_confirmation_candles=3)

  CLASSIFY:
    IF last >=3 swings form HH & HL (body-close confirmed):  regime = UPTREND
    ELIF last >=3 swings form LL & LH (body-close confirmed): regime = DOWNTREND
    ELSE: regime = RANGE

  VALID STRUCTURE BREAKS (body close only):
    BOS  = close past prior swing extreme in trend direction (continuation)
    MSS  = close past most-recent counter-swing (possible reversal)
    internal BOS (inside prior impulse range) = IGNORE (noise)

  REVERSAL CONFIRMATION (to flip regime):
    MSS  AND  next opposing swing forms  AND  BOS in new direction
    (optional) impulse legs contracting < impulse_range_decay_pct

  GATE:
    fade_engine_enabled = (regime == RANGE)

  ON confirmed regime flip:
    flatten fades invalidated by new regime; recompute zones
```

---

## Cross-source consensus & cautions

- **Convergence with TradingRiot:** Mayne's "range = no clean HH/HL chain" maps onto AMT's "price balancing inside value area." Two independent framings of the same regime gate — raises confidence.
- **ICT/SMC caveat:** Mayne's vocabulary (BOS/MSS/order blocks/FVG) comes from ICT/Smart-Money-Concepts, which the spec flags as unverified. The *mechanics* extracted here are objective and codeable; the "smart money intent" narrative is discarded. **These rules get NO free pass — validate the regime classifier against historical data (does range-labeled time actually mean-revert, trend-labeled time actually trend?) before it gates real capital** (audit finding #3).
- **Next pass:** Backtest the classifier standalone. Measure: in range-labeled periods, do fades have positive expectancy? In trend-labeled periods, would fades have lost? That test validates the entire mean-reversion thesis.

---

*End of concept_regime_filter.md*
