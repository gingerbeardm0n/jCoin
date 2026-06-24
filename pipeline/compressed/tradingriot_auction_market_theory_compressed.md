# Auction Market Theory - Compressed

## Orderflow & Price Movement

Prices move via aggressive **market orders** hitting **passive limit orders**, not "more buyers than sellers" (always equal in derivatives).

Market order = buy/sell at best available price NOW. Takes resting orders, moves price.
Limit order = resting on book at specific level. Advertises intent, waits.

Large players use limit orders to avoid slippage. Market orders are aggressive, move price.

Dynamic: aggressive vs passive is the mechanic.

## What is Auction Market Theory (AMT)?

AMT = market is continuous two-way auction seeking fair value.

Two purposes:
1. Facilitate trade (two-way auction)
2. Seek fair value

Two-way auction: "up" auction end → "down" auction start, vice versa.

## Practical Example

Samsung $100 → phone fails → drops to $50 (new buyers) → new value area at $50 → repairs happen → price rises to prior $100 value area (equilibrium level).

**Market does**: facilitate trade, negotiate prices between balanced and imbalanced values.

## Three Key AMT Components

1. **Price advertises opportunity**: moves away from value = opportunity signal. Drop below fair value = bargain signal.
2. **Time regulates opportunity**: longer at price level = more accepted. Time validates/invalidates discovery.
3. **Volume measures success**: where participants wanted to do business. Volume most important in electronic age.

## Balance vs Imbalance

**Balanced market**: buyers/sellers agree price fair. Lower volatility, ranging. Bell-curve distribution.

**Imbalanced market**: new info, fundamental/technical driver, disagreement on fair value. One side aggressive. Market trends.

Fact: markets mostly balanced (proven by options: IV > realized vol). Selling straddles/strangles profitable until not (market imbalanced, get rekt).

## AMT Rules (Framework, Not Strategy)

1. **Price accepts inside balance** → likely revert to other side. Often retests edge before opposite travel.
2. **Price inside balance** → reject edges, choppier behavior. This is where breakout traders get chopped.
3. **Price accepts outside balance** → likely imbalanced, seek new value (often prior balance POC).
4. **Strong POC rejection** → can break Rule 1. Strong reaction from POC prevents full rotation.
5. **Time + volume build at balance edge** → price pushes through. Genuine breakout vs failed auction.

## Market Profile (Time-Based AMT Tool)

Created 1980s CBOT by Peter Steidlmayer.

**TPO** (Time Price Opportunity) = 30-min intervals. Instead of candles, strings of letters. Each string = one 30-min bar.

**Value Area** = 68% of data within one std dev of mean. 68% of trades that session. Buyers/sellers agreed prices here.

**Point of Control (POC)** = most TPOs printed (most time at level).

Advantage: market-generated info, not subjective hand-drawn levels.

## Volume Profile (Volume-Based AMT Tool)

Same concept as Market Profile, but measures **volume** at each level, not time.

**Key diff**: Market Profile = time spent. Volume Profile = contracts/shares traded.

Both create bell-curve shape but levels differ.

Volume more important now (electronic), but can be skewed (most futures volume last hour = forced closes, not fair value discovery).

Choice personal; both work if understood.

## Composite Values

Overlay multiple days where value areas overlap = composite value. Days, weeks, months.

Composite reveal bigger ranges (Volume) or day-trade ranges (Market Profile).

Manual (eye-ball overlaps) or fixed lookback (weekly, monthly, quarterly, yearly).

## VWAP (Volume-Weighted Average Price)

`VWAP = (Σ Price × Volume) / (Σ Volume)`

Average price weighted by volume traded at each level.

Diff from simple MA: VWAP emphasizes price points with higher volume.

30-min chart: 24-hr MA vs VWAP can differ by $0.30 (volume weighting).

Plotted fixed horizons (daily, weekly, monthly, yearly) or anchored/rolling.

### VWAP Myth vs Reality

Common claim: institutions use VWAP for support/resistance, "defend" it.

Reality: institutions benchmark execution quality against VWAP. Algos designed execute large orders at/near VWAP to minimize impact.

Does NOT mean VWAP acts as magic support; just execution benchmark, not directional signal.

Useless to assume huge things based on VWAP alone. Never know what other side doing.

## VWAP Standard Deviation Bands = AMT Connection

Add bands around VWAP: direct AMT mirror.

- VWAP = fair value
- Bands = price statistically extended from fair value

Canadian dollar futures example (yearly VWAP = one trading year):

Price dips → re-accepted prior year value area → traveled to prior year VWAP (POC) → broke down → −1 std dev served resistance → rotation through current value area.

Levels never perfect, but follow AMT rules loosely.

Expect ranging when price hits key POC/VWAP. Strong reaction breaks rule.

Prefer trending once price breaks outside value: less volume resistance to desired direction.

## Putting It Together (AMT Framework)

AMT = framework (not strategy): market = continuous two-way auction, participants negotiate prices between balance/imbalance.

Tools:
- **Market Profile**: time-based auction structure
- **Volume Profile**: volume-based auction structure
- **VWAP + std dev bands**: dynamic fair-value representation, boundaries

Tools work together, not alone. No magic.

What matters:
- Inside value area vs outside?
- Market balanced or imbalanced?
- Prices accepted or rejected?

Tech analysis (price action) beneficial as confluence to spot acceptance into value or breaks outside.

Fair value + balance/imbalance understanding = significant edge whether trading directional or non-directional (selling options premium, etc.).

No single tool answers all. Understanding auction process behind markets makes everything else more effective.

---

## Summary

AMT rules:
1. Accept inside balance → revert opposite
2. Inside balance → reject edges, choppy
3. Accept outside balance → imbalanced, seek new value
4. Strong POC rejection → may break Rule 1
5. Time + volume at edge → breakout

Value Area = 68% vol (fair value agreed area)
POC = most time/volume (fairest price)

Market Profile (time) vs Volume Profile (volume) = choose preference.

VWAP + bands = fair value ± extension.

Confluence: combine market-generated levels (profiles, VWAP) with simple price action (acceptance/rejection patterns) for edge.
