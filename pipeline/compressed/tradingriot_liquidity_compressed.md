# Liquidity in Trading

Liquidity = resting limit orders in order book, not stop-losses (stops are market orders, invisible to DOM).

## Order Book Basics
- Bid/Ask = passive limit orders visible to all participants  
- Cannot see: stop orders, liquidation prices (executed as market orders)
- Large visible orders often spoofed—fake supply/demand pulled when price nears them
- Iceberg orders: large position split into small limit orders across price levels

## Market Liquidity & Volatility
- Thicker market (more liquidity) = lower volatility  
- Thinner market = higher volatility  
- ES vs NQ: Both track S&P, but NQ thinner → higher % moves  
- Post-COVID: ES +120%, NQ +150%; ES corrected 27%, NQ 37%

## Price Action & Liquidity Pools
Liquidity hunting ≠ real mechanism. Markets are two-sided auctions:
- Moves past swing points trigger stops but also attract larger retail participation  
- Mean-revert traders vs trend-followers both step in  
- Markets range more than trend—FOMO on sharp moves creates reversal opportunities

Example: Gold spike held for 24hr before selling off on macro release—not pure stop-hunt, two-sided auction resolution.

## Market Makers
- Delta-neutral strategy: quote bid+ask simultaneously  
- Make money on spread, not direction  
- Sharp "stop-hunts" unfavorable to market makers—they hate having directional exposure  
- Ideal scenario: low vol, continuous liquidity on both sides

## Crypto-Specific
Liquidation cascades visible post-facto via:
- Sharp price moves + open interest drops = forced closures  
- Liquidation heatmaps (free via Leviathan) estimate liquidation levels from OI changes  
- BUT: Most estimated levels sit at logical S/R zones—not predictive edge  

Better approach: Watch OI + order flow + relative volume behavior at these zones rather than pre-fade every liquidation.

## Post-Event Behavior
After large spikes trigger stops/liquidations, markets slow, accumulate/distribute—don't move in straight lines.

## Order Book Analysis by Market
- **Forex/CFDs**: OTC, no visible DOM—pure speculation  
- **CME Futures**: Visible DOM but packed with HFT; developing edge requires massive time/focus  
- **Crypto**: Thin + fast, DOM single-price worthless. Useful: order book skew (bid/ask imbalance), check if multiple participants pushing same side (genuine vs spoofed)
