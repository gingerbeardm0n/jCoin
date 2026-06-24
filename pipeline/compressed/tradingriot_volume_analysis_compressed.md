# Volume Analysis in Trading

## Volume vs Delta
**Volume** = total contracts traded (sum both sides).  
**Delta** = difference between market orders at bid vs ask (aggression indicator).

High volume candle + high positive delta = aggressive buyers (likely breakout/start of move).  
High volume + small delta = balanced participation.

Use delta for detailed analysis. For higher TF, volume alone sufficient.

## Relative Volume (rVOL)
Volume outside fair value. Calculate using standard deviation:
- **Blue bars** = volume >2 SD above fair value (high relative volume)  
- **Yellow bars** = volume <2 SD below fair value (low relative volume)

**High rVOL**: Appears at move starts (large traders initiating breakouts) + move ends (retail FOMO). Breakout confirmation.

**Low rVOL**: Market slowdown, lack of participation. Areas with LrVOL won't attract traders—become target zones.

Implementation: Use Koalafied indicator on TradingView (free) for candle coloring.

## Composite Volume Profile (CVP)
Structure market understanding via volume distribution across price levels.

**High Volume Nodes (HVN)** = large executed volume concentration  
- Fair value zones, sideways/range-bound action  
- Good targets, bad for initiating—prone to chopping  

**Point of Control (POC)** = highest volume level within HVN  
- Most "fair price"  
- Exception: fading fast rallies into old POCs (not visited long time)  

**Low Volume Nodes (LVN)** = voids, very low executed volume  
- Prices move fast through LVN—minimal resistance/liquidity  
- Best entry zones (price moves quickly your way)  

Trade Setup:
- Enter: edges of HVN or fast rallies into POC  
- Targets: next HVN or POC  
- Adjust levels as market builds volume

Example: ETH 2023 onward—CVP levels acted as S/R during entire move.

## Volume-Weighted Indicators

**VWAP** (Volume-Weighted Average Price):  
- Fixed to time period (daily, weekly, monthly, yearly)  
- Dynamic support/resistance  
- Plot 1 SD bands around VWAP = fair value zone  
- Price inside bands = balanced, outside = imbalanced/trending  
- Prior period VWAP = compare current structure vs historical

**VWMA** (200-period example shown):  
- Smoother than simple MA, weights by volume  
- Trend confirmation

Alternative: Prefer composite volume profile (CVP) for clearer full picture—VWAP bands often too wide.

## Execution Integration
rVOL + CVP + support/resistance + moving averages = complete system.  
Volume shows real participation; entry at LVN edges, exits at HVN/POC with confluence.  
Professional traders use volume in different forms—core edge tool.
