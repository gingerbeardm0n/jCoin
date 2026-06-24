# Crypto Trading Guide - Compressed

## Perpetual Futures

Perpetual = derivative contract, tracks underlying, leveraged, never expires.

Unlike classical futures (with expiry & forced convergence), perpetual needs funding rate to anchor price to spot. No settlement = no term structure.

### Funding Rate Mechanics

Funding = Interest Rate + Premium Index

- Interest rate: 0.01% per 8h (Binance USDT), flat exchange-set rate
- Premium Index: gap between perp and spot price
  
`Premium Index ≈ (Perp Price − Spot Price) / Spot Price`

Clamp prevents rate blowoff: as long as premium sits −0.04% to +0.06%, funding = 0.01% interest only.

Exchange caps final rate (Binance ±0.75% of maintenance margin ratio).

`Funding Payment = (Mark Price × Position Size) × Funding Rate`

Ex: Long 10 BTC, 0.01% funding = pay 0.001 BTC to shorts.

Funding reflects sentiment. Positive = crowded longs. Negative = shorts dominant or spot buying.

### Linear vs Inverse

- **Linear**: settle USDT. Quote = settlement. Boring payoff: $1 price move = $1 PnL.
- **Inverse**: settle coin, quote dollars. Payoff bends with price moves. Rare.

### Leverage & Margin

**Crypto**: contract tiny, you set leverage via slider (vs CME: fixed contract size).

- Initial margin: what you post to open
- Maintenance margin: floor to stay above
- Liquidation at maintenance breach

Higher leverage = less room to be wrong. At 40x, 2% move ends you.

**Isolated**: fence collateral to one position. Loss caps at that amount.
**Cross**: whole account backs all positions. Liquidation wider, but cascades entire account if breaks.

### Mark Price (Not Last Price)

Perpetuals liquidate off mark price, not last traded price. Mark = median of: spot index, index + funding basis, contract price.

Index = weighted average spot across Binance, Coinbase, Kraken, OKX + guard caps deviation.

Why: prevents single venue wick from triggering forced exits market disagrees with.

### Insurance & ADL

Insurance fund: absorbs liquidations that close worse than bankruptcy price.

Auto-deleveraging (ADL): if insurance steamrolled, exchange closes profitable traders (by profit & leverage) to cover bankrupts. You can be deep in profit and still get yanked.

Decentralized venues (Hyperliquid) use community vaults; JELLY March 2025 case: vault held 4M short that blew up, vote delisted contract at 0.0095 vs oracle 0.50. Message: backstop can act in own interest.

**Signal**: liquidations show forced exits. Cascades are opportunities for patient participants.

Long shakeouts = historically good entry for new longs. 10-day fwd return after liquidations slopes up when longs get flushed (z-score deeply negative).

### Liquidation Cascades

Chain reaction: price drops → most reckless longs liquidate → market sells → price drops further → next tier tips.

Higher leverage, 24/7 trading, thin books = worse than regulated futures. No circuit breakers or margin-call grace periods.

Oct 10 2025: 100% tariff threat = 19B liquidations (24h record), 1.6M accounts hit, 87% longs wiped. BTC fell 14% in hours.

Cascade is the mechanism, not the trigger.

### Fees

Maker-taker model: post resting limit = maker (0.02%+). Hit market = taker (0.05%+). Scales with volume tier.

Taker fee = drag if scalping. Rounding error if holding days-to-weeks.

Zero-fee venues (Lighter): no maker rebate = limit orders get picked off by faster traders (adverse fills cost more than fee saves).

Thin books: slippage > fee. Patience in thin markets pays.

### Open Interest

Total contracts open = commitment not closed yet.

For every long, always a short (definition). "More buyers than sellers" false in derivatives.

Three cases:
1. Both open new = OI rises
2. Both close = OI falls
3. One opens, one closes = OI flat

**Price moves because of market-maker hedging**, not buy/sell imbalance. When directional traders pile one side, OI climbs alongside price = fresh conviction (not rotation).

OI falls while price drops = forced closures, not new shorting.

Clusters of OI = gravity levels, defended or where forced exits happen.

**Crypto advantage**: OI live, aggregated, per-second updates on single continuous contract (vs CME daily, fragmented across expirations).

**Sentiment**: most structurally long, rarely short. OI elevated at highs, depressed at lows.

OI z-score (30-day lookback): extremes measurable.

Pattern: OI rotates to alts when euphoric, concentrates to BTC when fearful. Recent highs = alt OI. Recent lows = BTC OI.

## Trading Styles (3 Types)

Bitcoin brutal-correlated to alts. Alts = leveraged BTC bets mostly. TA secondary; derivatives data gives bias.

### Momentum

Trend following: something moves, bet it keeps moving.

**Healthy momentum**: price up, OI up (new money, not rotation), funding low/negative (spot leading, not crowded longs).

Perp at/below spot = spot buyers out front.

PENGU H2 2025: OI 40-50M for months → exploded to 290M as coin rallied. Funding stayed muted, spiked negative in early July (−0.17%). Spot demand, no long froth.

**Simple system**: find spiking OI + muted funding, breaking above/below significant level aligned with moving averages. Automated strategies pile in.

Momentum: long string small losses + occasional big win.

### Mean Reversion

Fade moves, but trends run longer/hotter than expected. Blown-out reversions quick (sharp snap, done), not new trends.

**Rules**:
1. Fade extreme = short-lived (not weeks). Get in, catch snap, get out.
2. Define target level: prior level, MA, something real. Fade toward mean, cover there.

**Data signal**: OI spikes + funding hard positive together = crowded longs stretched. Little fuel left. Snap brutal.

Liquidations matter: huge short liquidations into highs = last bears squeezed, buying disappears. Blow-off marks itself.

ZEC early May 2026: OI exploded toward 1B, May 8 funding spiked positive (froth). Shortest liquidations hit, final legs gone. ZEC rolled −25% into prior mid-500s level (mean). Trader fades froth back to mean.

**Discipline**: fade extremes when data confirms (not guessing), when one side flushed (no shorts left to squeeze), level to aim at. Miss any = guess.

### Delta Neutral

Long + short cancel directionally, collect spread/yield instead. Opinion on direction not needed.

**Classic**: cash and carry. Buy spot, short dated quarterly future at premium. Legs cancel, collect basis as converges to expiry.

**Pairs**: ETHBTC long equal dollar size. Shared beta cancels, only spread left. Make money if ETH beats BTC regardless market moves.

**Funding rate arb**: positive funding = longs bleed, shorts earn.

Buy 10 ETH spot, short 10 ETH perp. Net delta ~zero. 3x/day collect 0.05% per 8h = ~55% annualized on direction-neutral position.

Cross-exchange arb: same coin, different funding. Single-digit one exchange, hundreds/thousands on illiquid one. Long cheap perp, short rich one, pocket difference. Widest gaps on thin alts (nobody moves size to close).

Deep negative funding (shorts pay longs): spot overloaded by market makers, unlocks, weak long demand, downtrends.

**Not free**: funding flips mid-trade. Short leg still needs margin; spike up liquidates it even though spot up same. Cross-exchange adds counterparty risk, capital split, transfer delays. Exit breaks these; thin venue unwinding costs > weeks funding collected.

### Extreme Funding Drivers

Euphoric rallies: longs want in > short supply, longs pay premium. Double-digit positive.

Altcoins negative:
- Makers hedge spot sales by shorting perps = selling pressure on perp side
- Unlock front-run: traders short before selling = deeply negative before event
- No leveraged longs demand: shorts hedgers/bears, longs thin = structural imbalance
- Spot premium (low float, listing diffs, withdrawal issues) vs perp fair value = persistent negative

Altcoins: −0.1% to −0.5% per 8h (−100% to −500% annualized). Market pays you long, but token drops 80% anyway. Funding ≠ compensation.

**Edge**: OI rise + negative funding together. Perp traders opening, discount persists. Shorts aggressive while spot buying elsewhere = makers hedging accumulation or insiders pre-move.

Early: price action muted, OI spiked, funding deeply negative = setup early, before pump obvious.

RIVER: OI spiked, funding −, price barely moved → multi-hundred % rally after.

Funding stays negative at tops; too late by several multiples of daily ATR. Edge = spotting early when data unusual, chart boring.

Shorting tops hard to time: crowded trade at highs, paying funding on short, can stay silly longer than solvent.

## Order Book (Spot)

Full order book public standard on crypto (vs forex OTC, futures limited depth paid).

**Spoofing rampant**: place orders never intending fill. Spot > futures (need coins/cash behind big bid = real info).

**Don't read single levels, read shape: skew**.

Skew = bid/ask imbalance within band around price. Far more bids below = hard to push down. Reverse = hard to push up.

Heavy skew = range-bound or early trend where one side absorbs silently.

**Limit**: skew works best in ranges. Strong trend: price chews through bids/asks, skew says little. Spot patient; book stays lopsided longer than expected before mean-revert snap.

Confluence: same side as large spot players, raises conviction. Not standalone entry.

## Options Skew (BTC/ETH Only)

Only liquid on Deribit (>90% ETH options, contested BTC now with ETFs).

**25-delta risk reversal**: moderate OTM, liquid, reflects real positioning.

`25Δ RR = IV(25Δ Call) − IV(25Δ Put)`

Positive RR = calls bid up, upside priced, reward thin. Negative RR = puts bid, fear in, closer to reversal.

Edge: **fade extremes**. All crowded calls = upside priced out. All crowded puts = fear in.

## Z-Scores: Standardizing Extremes

Raw numbers hard to judge. Z-score = (Current − Average) / Std Dev.

+2 = two std dev above normal = top 2.5%. −2 = bottom 2.5%.

Makes everything comparable. PENGU +2 OI vs BTC +2 OI = same stretched positioning despite different dollar sizes.

Rolling window = judges current vs recent coin behavior (not ancient history).

Engine: TradingRiot Analytics. OI, funding, liquidations each get z-score + percentile rank. Spot skew z-score. Options RR z-score. Screener ranks entire market by extremes daily.

## Trade Alignment Rule

**Wait for alignment**: derivatives data + spot book + options skew all point same way.

Rare setup. Size up, trade with conviction. Most days = data keeps you out of bad trades.

---

## Summary

Crypto advantage:
- 24/7 trading, leverage, no circuit breakers
- Public order book depth standard
- Free, live, real-time OI aggregated per second
- Positioned via funding, OI, liquidations, spot skew, options RR
- Z-scores standardize extremes across coins

Trend-following: OI + price up, funding low (spot-led momentum).
Mean-reversion: OI spike + funding hard positive + short flush = snap snap back to prior level.
Delta neutral: funding arb (long spot, short perp), cross-exchange arb, pairs.

Data flags moment when chart aligns with positioning. Most power = all signals convergent.
