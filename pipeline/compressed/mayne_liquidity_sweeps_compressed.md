# Trader Mayne — Liquidity Sweeps (Compressed)

**Source:** Whiteboard Series Ep. 3 — Liquidity & Liquidity Sweeps

---

## Core Definition

**Liquidity** (for trading purposes) = resting orders = retail stop losses clustered at obvious levels. Two types:
- **Buy-side liquidity (BSL):** above the market — buy orders / long stop losses. Triggers buys.
- **Sell-side liquidity (SSL):** below the market — sell orders / long stops trigger as sells.

Market structure: price moves from BSL → SSL → BSL repeatedly (ping-pong). Identifying which was just run tells you the next target.

---

## Why Stop Hunts Happen (Mechanism)

Institutions need opposing orders to fill large positions without chasing price (e.g. a $500M buy order market-bought would drive price up, worsening avg fill). Solution: drive price into clusters of retail stops (= opposing orders) to fill at a desired price. Retail long stops = sell orders → institution buys them. Retail short stops = buy orders → institution sells into them.

Engineering: market forms higher lows repeatedly, building retail confidence and stop-stacking below obvious swings. Once sufficient stops accumulate, the sweep fires.

---

## Liquidity Sweep Definition (The Pattern)

A **liquidity sweep** = price moves through a level (swing point, equal highs/lows) → then **rejects back** → then **displaces**. NOT a breakout. Confirmation requires both:
1. Move through level + rejection (close back)
2. **Displacement** afterward = aggressive, fast move in opposite direction creating a market structure shift (MSS)

Displacement = confirmation that the sweep was genuine (big money filled, not breakout).

---

## Two Sweep Patterns

### 1. Swing Failure Pattern (SFP)
- Swing high defined: 3 candles (lower-high, peak, lower-high)
- Price wicks above swing high but **closes back below** → SFP. Strong signal.
- Also fires as SFP when wick pierces level but candle body closes below

### 2. Break and Close
- Price breaks **and closes** above/below the level
- But then **immediately** closes back on the other side on the next candle(s)
- Key: must get back below/above quickly — lingering above = real breakout

Both patterns require displacement to confirm.

---

## Codeable Sweep Identification Rules

```
SWEEP DETECTED when:
  (a) SFP: candle wicks past prior swing high/low; candle CLOSES back on origin side
  (b) Break-and-Close: candle(s) close past level; subsequent candle(s) close back on origin side promptly
  
CONFIRMATION: displacement candle(s) after — fast, aggressive move creating MSS
  MSS = price moves far enough opposite to break the most recent minor swing in that direction

NOT a sweep if: price lingers above/below level (breakout candidate instead)
```

---

## Timeframe Weighting

- Higher timeframe sweep > lower timeframe sweep (weekly SSL sweep >> 4H SSL sweep in weight)
- HTF trend always dominates: a 4H bearish sweep during a weekly bull trend ≠ short signal; it's a potential long entry after 4H realigns bullish
- Rule: sweep weight proportional to timeframe of the level swept

---

## Entry Context (What To Do)

When sweep fires:
1. Ears perk up — institutions just showed hand (filled positions)
2. Don't panic — this is opportunity not bad luck
3. Wait for displacement to confirm
4. Subsequent entry is **after** reclaim + displacement (taker — enter after confirmation candle)
5. Old stop location → becomes your entry zone in the trade direction of the displacement

Stop placement post-sweep: beyond the sweep wick (the extreme of the false move)

---

## Takeaways

1. Liquidity = retail stops. Stop placement at obvious levels = being the liquidity.
2. The sweep itself is not the entry — displacement confirmation is.
3. BSL above highs; SSL below lows. Market alternates between them.
4. SFP (wick + close back) or Break-and-Close (close through, then immediately back) are the two visual patterns.
5. High-time-frame sweeps > low-time-frame sweeps.
