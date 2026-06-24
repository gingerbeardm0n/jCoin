# Finding Data-Driven Crypto Trades - Compressed

## Derivatives Data Overview

OI, funding, liquidations = positioning tools, not direct buy/sell signals.

## Open Interest (OI)

Total outstanding contracts not yet closed = commitment in market.

`OI = (Net Long Positions + Net Short Positions) / 2`

**Three cases**:
1. Both open new → OI rises
2. Both close → OI falls
3. One opens, one closes → OI flat

Sharp OI rise = robust positional demand, potential momentum.
Sharp OI fall = liquidation wave, forced exits.

**Example**: AVAX broke structural resistance + significant OI surge = major participants involved, upward move likely.

**Caveat**: Solana big OI increase = no continued uptrend, instead sell-off. OI alone insufficient; need other tools.

## Funding Rates

Mechanism keeps perpetual anchored to spot.

**Positive**: perp above spot, longs pay shorts.
**Negative**: perp below spot, shorts pay longs.

**Misconception**: extreme funding ≠ guaranteed reversal. Funding can stay elevated extended periods in trends.

### Recent Evolution

Carry trades now common = rare see drastic blowoffs. Extreme funding mostly "crime" coins now. But significant *changes* in funding still valuable.

### SUI Example (Positive Funding)

Price +30%, OI nearly doubled, May 8 funding spiked hard positive = froth.

Combined with huge short liquidations at highs (last bears squeezed) = buying disappears, blow-off marked.

ZEC follow-up: rolled −25%, snapped into prior mid-500s level (mean). Fading froth works.

### PENGU Example (Negative Funding)

Price rallied, OI rose, funding **stayed negative**.

Negative during uptrend = spot buying outpacing perp buying (spot traders ahead, not leverage chasing). Healthy start to trend.

## Liquidations

When leveraged, position has liquidation price; exchange force-closes at that level.

Liquidations cluster in specific areas = signal potential move end; many algos/traders provide liquidity there.

**Uncommon angle**: price continues same direction *after* large liquidation = strong trend.

**ETH example**: sell-off + falling OI + negative funding + rising long liquidations = very strong mean-reversion signal.

## Putting Together: Z-Scores

Problem: hard to quantify if OI spike significant. Is 50M jump big? Is −0.05% funding extreme? Depends on coin.

**Solution**: z-score.

`Z = (Current Value − Average) / Std Dev`

Z = 0: average. Z = +2: two std dev above (top 2.5%). Z = −2: bottom 2.5%.

Makes everything comparable. PENGU +2 OI = BTC +2 OI = same stretched positioning despite different $ sizes.

Rolling window = judges current vs recent coin behavior (not ancient history).

### Engine: TradingRiot Analytics

Each metric z-score + percentile rank:
- OI z-score, funding z-score, liquidations z-score
- Spot order book skew z-score
- Options risk reversal z-score

Screener ranks entire market by extremes daily. Instead of flipping 150 charts, get handful where positioning stretched.

Deep-dive per market: raw data, z-scores, forward returns.

Proprietary regime indicator combines metrics into strength gauge for each move.

## Spot Market Data (Order Book Skew)

Perpetuals have noise. Spot has real money moving size; spot buyers push price.

Spot skew = bid/ask imbalance around current price.

**Logic**: many bids below = hard to push down. Many asks above = hard to push up.

High skew = range-bound or nascent trend where one side absorbs silently.

**Spoofing risk**: less on spot (need coins/cash behind big order = real signal vs futures with cheap leverage).

**Limit**: skew works ranges. Strong trend: price chews through bids/asks, skew says little. Spot patient; book stays lopsided longer before snap.

Use as confluence: spot players aligned same direction = higher conviction. Not standalone entry.

Order book skew z-score available (Kiyotaka, community tab, search "abetrade").

## Options Data (25-Delta Risk Reversal)

Only viable BTC/ETH (Deribit >90% ETH, contested BTC with ETFs).

**25-delta**: moderate OTM, liquid, reflects real positioning (midpoint between 50-delta ATM and 0-delta far OTM).

Implied volatility (IV) = market's forward estimate volatility, baked into option price.

Delta = how much option price moves per $1 underlying move (calls 0-1, puts 0-−1).

`25Δ RR = IV(25Δ Call) − IV(25Δ Put)`

**Positive RR**: calls bid up, upside priced, reward thin. Fade = sell calls.
**Negative RR**: puts bid, fear in, closer to reversal. Fade = buy puts.

**Crypto edge**: fade extremes.
- High call skew (Z < −2) = crowded calls = upside priced, reward fades
- High put skew (Z > +2) = crowded puts = fear in = closer snap

Risk Reversal Z-score indicator available (Kiyotaka).

## Full Trade Alignment

**Most favorable**: all indicators point same way (derivatives + spot book + options skew).

Rare convergence. Size up, trade with conviction.

Most days = data keeps you out of bad trades. Wait for rare alignment.

---

## Summary

**OI**: new commitment. Spike = potential momentum. Fall = forced exits.

**Funding**: sentiment. Positive = longs crowded. Negative = shorts/spot dominant.

**Liquidations**: forced exit clusters. Continuation after big liquidation = trend strength.

**Z-scores**: standardize extremes. +2/−2 = stretched. Comparable across coins.

**Spot skew**: real money imbalance. High = range or early trend. Works best ranges.

**Options RR**: sentiment z-score. Fade extremes (crowded calls/puts).

**Confluence rule**: wait for alignment. Rare. All signals pointing same direction = high conviction trade.

Trade early in setup (data unusual, chart boring) > trade obvious tops/bottoms.
