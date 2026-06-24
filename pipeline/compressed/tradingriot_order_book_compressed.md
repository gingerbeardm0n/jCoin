# Order Book Data in Crypto Trading

## Order Book Basics
Order book (DOM, depth of market) = visible resting limit orders.
- Bid (blue) = orders to buy  
- Ask/Offer (red) = orders to sell  
- Heatmaps = same data visualized on chart with colors by order intensity  

Spoofing: orders placed without intent to fill—fake supply/demand to confuse traders.

## Spot vs Futures Order Books
**Spot orders** = real capital, actual directional intent  
**Futures orders** = market-maker liquidity, no directional bias  

Spot book shows large orders at meaningful price turns. Futures book packed with MMs on both sides = noise.

Example: BTCUSDT spot vs perpetual—spot shows large orders at turning points; perpetual swarmed with orders everywhere (classic market-making).

## Delta Imbalance Strategy
Ignore single price levels. Use **delta = bid volume − ask volume** across depth.

Setup: Monitor order book delta + calculate 10% depth (orders within 10% of market price).

Example: BTC shows price reactions when delta exceeds ±$50m on intraday. On daily: reactions at ±$150m with <10% depth.

Key: Spot traders patient—books can stay skewed 1+ hours before mean-revert. Use as confluence, not standalone signal.

## Order Book Depth Settings by Timeframe
Use depth platforms (Trdr.io, Mobchart, Coinglass):
- **Scalping (1m–15m)**: 1%–2.5% depth filter  
- **Intraday/Swing (1h–4h)**: 5% depth  
- **Higher TF swing**: 10% depth  

Example setup: SOL skewed heavy to sell side, still rallied 7% before reversing—entry confluence signal, not entry trigger.

## Order Book Depth Platforms
**Trdr.io**: Aggregates multiple exchanges (best for full picture). Slow adding new altcoins. Recommended settings: Market Type = Spot, Smaller than = 1–2.5% (scalping) / 5% (intra-week) / 10% (higher TF).

**Mobchart**: Binance + Bybit only (not aggregated). Wider coin selection. Screener shows large limit orders across all markets.

**Coinglass**: Free. Aggregated feed but only shows nearest 1% from price—useful only for fast scalping.

## Confluence Edge
Order book depth NOT entry signal—shows what spot traders (often heavier hands) are interested in.  
Use as confluence indicator: validates conviction, keeps you on same side as large players.  
Spot traders patient vs futures traders—use this patience for longer-hold confluences.

Combined approach: price action + moving averages + order book delta imbalance = validation system.
