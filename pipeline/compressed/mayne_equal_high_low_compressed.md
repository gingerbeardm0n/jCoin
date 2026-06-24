# Trader Mayne — Equal High & Equal Low Liquidity (Compressed)

**Source:** Technical Bootcamp Ep. 6 — Equal High and Equal Low Liquidity

---

## Core Definitions

**Equal Highs (EQH):** 2+ swing highs at approximately the same price level. Visually = resistance. Mechanically = stop-loss cluster above (shorts' stops + breakout buy stops). Creates BSL pool.

**Equal Lows (EQL):** 2+ swing lows at approximately the same price level. Visually = support. Mechanically = stop-loss cluster below (longs' stops + breakout sell stops). Creates SSL pool.

**Relative equal highs/lows:** not perfectly aligned but close enough to create a liquidity zone — treated the same way.

---

## Why EQH/EQL Form (Order Mechanics)

Above a swing high, two order types accumulate:
- **Stop losses** of shorts who entered near the high (stops above = buy orders)
- **Buy stops** of breakout traders who trigger long on high break (also buy orders)

Below a swing low:
- **Stop losses** of longs who entered near the low (stops below = sell orders)
- **Sell stops** of breakout traders (also sell orders)

Result: EQH = massive buy order pool above; EQL = massive sell order pool below. Both act as **price magnets** because within the range there aren't enough orders to create a large directional move — price drifts toward the larger order cluster.

---

## Institutional Execution Mechanism

Large participant (institution) needs to build a short position: can't market-sell into thin ranging liquidity (worsens fill, drives price against them). Optimal: wait for price to drift to EQH where thousands of buy orders enter simultaneously. Then:
1. All those buy orders = opposing sell liquidity for the institution
2. Institution sells massive contracts against the incoming buys
3. Absorption of buys → price rapidly reverses downward
4. Buyers (stop hunters + breakout longs) are now trapped long at the high

Same logic flipped for building long positions at EQL.

---

## Key Rules (Codeable)

**Rule 1 — Never sell below equal highs:**
If EQH is live above current price, DO NOT enter shorts from below. Wait for sweep of EQH first. Zone below EQH is a bad zone.

**Rule 2 — Never buy above equal lows:**
If EQL is live below current price, DO NOT enter longs from above. Wait for sweep of EQL first. Zone above EQL is a bad zone.

**Rule 3 — Whichever liquidity gets swept first → other becomes the target:**
- Sweep EQL → target EQH (buy after sweep)
- Sweep EQH → target EQL (sell after sweep)

**Rule 4 — Entry timing:**
After sweep, look for: (a) absorption evidence (large wicks, aggressive reversal candles), (b) structural shift (MSS / BOS in new direction), (c) demand/supply zone + imbalance in new direction. Then enter with stop below/above sweep wick.

---

## EQH/EQL Identification (Codeable)

```
EQH: 2+ swing highs within X% of each other (price tolerance TBD, ~0.1–0.5% suggested)
EQL: 2+ swing lows within X% of each other

Swing high: local high with lower highs on both sides (N-bar lookback)
Swing low: local low with higher lows on both sides

"Relative" EQH/EQL: highs/lows within ~1–2% tolerance (discretionary threshold — flag as param)
```

---

## Absorption Evidence (Entry Confirmation)

After sweep below EQL:
- Large wicks lower with closes back inside range
- Aggressive bullish candle body closing higher than prior candle
- BOS/MSS to the upside on internal structure

Combined with: demand zone present from prior impulsive move + open imbalance (FVG) in direction of trade.

---

## EQH/EQL in Trend Context

In a downtrend:
- EQH above = magnet / trap zone before continuation lower
- Good short zone = supply above EQH (combined: supply zone + EQH sweep entry)
- Do NOT sell from supply below EQH; wait for EQH sweep, THEN enter from the supply above

Example: downtrend has EQH. Supply zone below EQH = filtered out (bad). Supply zone above EQH (after sweep) = valid entry. Sell after sweep into premium supply → target new low.

---

## Confluence Framework for Entry

After EQL/EQH sweep, a full entry setup requires:
1. Liquidity swept (EQH or EQL taken)
2. Demand/supply zone present in new direction
3. Imbalance (FVG) present and open
4. BOS/structural shift in new direction
5. Target = opposing liquidity level (EQH or EQL on the other side)

All 5 present = highest-quality setup. Fewer = reduced confidence.

---

## Key Phrase / Filter Rule

"If you don't see the liquidity, you will be the liquidity."

Translation: if you enter from support/resistance without checking for unfilled EQH/EQL above/below, you are the stop that will get swept.
