# Carver-style continuous trend follower: BTC + ETH

Generated 2026-10-21 by `jcoin/research/carver_trend.py`. Dev window only (2021-01-01 to 2026-05-31). All configs are fixed and pre-declared — nothing was tuned. This is a research comparison, not a selection.

**How it works:** instead of binary breakout signals with tight ATR stops, this strategy computes a continuous forecast from an EMA crossover, normalized by ATR. Position size scales with forecast strength — stronger trend = bigger position. No stops: positions shrink gradually as the trend weakens. Cost: Coinbase spot taker 0.60% per side, charged on the trade delta only. Rebalance threshold 10%.

**Why test this:** strategy A's biggest problem on Coinbase is that tight stops get knocked out by exchange-specific price spikes (~2/month/coin). A continuous strategy has no stop to hit. Costs are higher (spot taker vs perp maker), but no funding.

## Vol target 25% — daily bars

Position sizes scale with 1/volatility. At 25% target, BTC's ~100% annual vol means only ~2-5% equity exposure. At 50%, double that. Neither is leveraged — max exposure stays well under 1x equity.

| config | CAGR | maxDD | MAR | Sharpe | turnover | final equity |
|---|---|---|---|---|---|---|
| EMA 8/32 | 0.5% | 2.9% | 0.16 | 0.25 | 1.1x | $10,252 |
| EMA 16/64 | 0.4% | 4.9% | 0.08 | 0.16 | 0.9x | $10,201 |
| EMA 32/128 | -0.7% | 9.4% | -0.07 | -0.18 | 0.8x | $9,626 |

## Vol target 50% — daily bars

Position sizes scale with 1/volatility. At 25% target, BTC's ~100% annual vol means only ~2-5% equity exposure. At 50%, double that. Neither is leveraged — max exposure stays well under 1x equity.

| config | CAGR | maxDD | MAR | Sharpe | turnover | final equity |
|---|---|---|---|---|---|---|
| EMA 8/32 | 0.9% | 5.8% | 0.16 | 0.25 | 2.1x | $10,500 |
| EMA 16/64 | 0.6% | 9.6% | 0.07 | 0.15 | 1.7x | $10,355 |
| EMA 32/128 | -1.5% | 18.1% | -0.09 | -0.18 | 1.6x | $9,190 |

### Benchmarks

| benchmark | CAGR | maxDD | MAR |
|---|---|---|---|
| BTC buy-hold | 18.5% | 76.7% | 0.24 |
| BTC+ETH equal-weight | 19.6% | 77.4% | 0.25 |

## Per slice (daily, EMA 16/64, vol target 25%)

| config | CAGR | maxDD | MAR | Sharpe | turnover | final equity |
|---|---|---|---|---|---|---|
| 2021 | -0.1% | 1.8% | -0.05 | -0.04 | 0.5x | $9,990 |
| 2022 | -0.6% | 3.3% | -0.19 | -0.30 | 0.6x | $9,939 |
| 2023 | 0.6% | 2.4% | 0.25 | 0.30 | 0.9x | $10,060 |
| 2024 | -1.5% | 2.9% | -0.52 | -0.72 | 0.8x | $9,850 |
| 2025 | 0.3% | 1.8% | 0.15 | 0.14 | 0.7x | $10,028 |
| 2026H1 | -0.6% | 0.7% | -0.85 | -1.05 | 0.5x | $9,976 |

## Per slice (daily, EMA 16/64, vol target 50%)

| config | CAGR | maxDD | MAR | Sharpe | turnover | final equity |
|---|---|---|---|---|---|---|
| 2021 | -0.2% | 3.5% | -0.05 | -0.02 | 1.0x | $9,982 |
| 2022 | -1.2% | 6.5% | -0.18 | -0.28 | 1.1x | $9,881 |
| 2023 | 1.0% | 4.7% | 0.22 | 0.27 | 1.9x | $10,102 |
| 2024 | -2.9% | 5.7% | -0.51 | -0.70 | 1.7x | $9,704 |
| 2025 | 0.4% | 3.7% | 0.11 | 0.12 | 1.5x | $10,041 |
| 2026H1 | -1.2% | 1.4% | -0.85 | -1.05 | 1.1x | $9,951 |

## 4h bars (for comparison with A, vol target 25%)

| config | CAGR | maxDD | MAR | Sharpe | turnover | final equity |
|---|---|---|---|---|---|---|
| EMA 8/32 (4h) | -2.2% | 11.6% | -0.19 | -0.46 | 6.9x | $8,853 |
| EMA 16/64 (4h) | -1.5% | 8.8% | -0.17 | -0.22 | 5.5x | $9,233 |
| EMA 32/128 (4h) | -1.4% | 11.8% | -0.12 | -0.15 | 5.3x | $9,242 |

## Interpretation

The Carver approach trades cost for robustness: no tight stops to get spiked out, but higher round-trip costs (spot taker) and continuous position adjustment. Compare Sharpe and MAR to strategy A's honest numbers (A_HONEST_NUMBERS_2026-10.md). If Carver's MAR is competitive with A's, it may be more robust on Coinbase where A's PF collapsed from 1.12 to 0.59 due to stop-hunting spikes.
