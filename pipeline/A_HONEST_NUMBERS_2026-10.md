# Strategy A: honest numbers (with Binance perp funding)

Generated 2026-10-14 by `jcoin/research/phase1_honest_a.py`. Dev window only: 2021-01-01 to 2026-05-31 (sealed window untouched). Config is fixed, nothing was tuned.

**A config:** BTC+ETH, 4h trend-aligned breakout (k=2), ATR period 14, init stop 1.0 ATR, chandelier trail 6.0 ATR, max hold 120 bars, 1% risk per trade, max 1 per symbol / 2 concurrent, 12bp round-trip cost. Funding: Binance USD-M history, long pays / short receives when the rate is positive, charged on entry notional for prints in (entry bar open, exit bar open], converted to R by dividing by the stop distance (same conversion as cost). Multiplier 1x = historical, 2x = double.

Conventions: a window's trades are those entered in it; CAGR and Sharpe use the calendar length of the window; each window starts at 10,000 equity; trades that start but do not finish a slice are kept whole (sequential, risk-sized). The 2026H1 slice is only 5 months, so its CAGR is an annualized short sample.

## 1. Regression check (funding_mult = 0 must equal the unchanged harness)

Trade list from a call with no funding arguments vs `funding_mult=0`: IDENTICAL (662 candidate trades).

| metric | baseline (pre-change harness) | funding_mult=0 | match |
|---|---|---|---|
| cagr | 0.3557181366348321 | 0.3557181366348321 | OK |
| max_dd | 0.2595839414218871 | 0.2595839414218871 | OK |
| pf | 1.6506706122497947 | 1.6506706122497947 | OK |
| sharpe | 1.0014039877260577 | 1.0014039877260577 | OK |
| n_trades | 396 | 396 | OK |
| avg_R | 0.5623097715430554 | 0.5623097715430554 | OK |
| final_equity | 51927.50330915668 | 51927.50330915668 | OK |

**Regression result: PASS (exact)**

## 2. Full dev period

| window | CAGR | maxDD | MAR | Sharpe | PF | n_trades | avg_R | win% |
|---|---|---|---|---|---|---|---|---|
| funding 0x | 35.6% | 26.0% | 1.37 | 1.00 | 1.65 | 396 | 0.562 | 18.2% |
| funding 1x | 32.4% | 26.3% | 1.24 | 0.95 | 1.60 | 396 | 0.527 | 17.9% |
| funding 2x | 29.3% | 26.5% | 1.10 | 0.89 | 1.55 | 396 | 0.492 | 17.7% |

### Funding paid vs gross profit (taken trades, R units)

Gross profit = sum of R over winning taken trades (after costs and funding, the PF numerator). Funding paid = minus the sum of per-trade funding R (negative share = net funding received).

| funding | total funding R | avg funding R/trade | funding paid / gross profit | long funding R | short funding R | n long / short |
|---|---|---|---|---|---|---|
| 0x | +0.00 | +0.0000 | 0.0% | +0.00 | +0.00 | 205 / 191 |
| 1x | -13.98 | -0.0353 | 2.5% | -17.76 | +3.77 | 205 / 191 |
| 2x | -27.97 | -0.0706 | 5.1% | -35.51 | +7.55 | 205 / 191 |

## 3. Per slice (DEV_SLICES)

### funding 0x

| window | CAGR | maxDD | MAR | Sharpe | PF | n_trades | avg_R | win% |
|---|---|---|---|---|---|---|---|---|
| 2021 | 40.5% | 16.1% | 2.52 | 1.09 | 1.68 | 74 | 0.568 | 17.6% |
| 2022 | 8.3% | 21.4% | 0.39 | 0.49 | 1.22 | 69 | 0.192 | 18.8% |
| 2023 | 78.1% | 17.9% | 4.36 | 1.40 | 2.29 | 68 | 1.133 | 19.1% |
| 2024 | 60.0% | 14.8% | 4.05 | 1.43 | 2.01 | 69 | 0.834 | 23.2% |
| 2025 | 4.7% | 19.3% | 0.24 | 0.36 | 1.18 | 84 | 0.159 | 14.3% |
| 2026H1 | 38.4% | 21.0% | 1.82 | 1.03 | 1.67 | 32 | 0.609 | 15.6% |

### funding 1x

| window | CAGR | maxDD | MAR | Sharpe | PF | n_trades | avg_R | win% |
|---|---|---|---|---|---|---|---|---|
| 2021 | 29.2% | 16.2% | 1.81 | 0.89 | 1.51 | 74 | 0.446 | 16.2% |
| 2022 | 7.4% | 21.8% | 0.34 | 0.46 | 1.21 | 69 | 0.180 | 18.8% |
| 2023 | 76.0% | 18.0% | 4.22 | 1.38 | 2.27 | 68 | 1.112 | 19.1% |
| 2024 | 56.7% | 15.0% | 3.77 | 1.39 | 1.96 | 69 | 0.799 | 23.2% |
| 2025 | 4.0% | 19.5% | 0.20 | 0.34 | 1.16 | 84 | 0.149 | 14.3% |
| 2026H1 | 39.8% | 21.0% | 1.90 | 1.04 | 1.69 | 32 | 0.625 | 15.6% |

### funding 2x

| window | CAGR | maxDD | MAR | Sharpe | PF | n_trades | avg_R | win% |
|---|---|---|---|---|---|---|---|---|
| 2021 | 18.7% | 16.3% | 1.14 | 0.67 | 1.35 | 74 | 0.324 | 16.2% |
| 2022 | 6.6% | 22.1% | 0.30 | 0.43 | 1.19 | 69 | 0.168 | 18.8% |
| 2023 | 74.0% | 18.1% | 4.08 | 1.36 | 2.25 | 68 | 1.092 | 19.1% |
| 2024 | 53.4% | 15.3% | 3.50 | 1.35 | 1.91 | 69 | 0.764 | 23.2% |
| 2025 | 3.2% | 19.7% | 0.16 | 0.32 | 1.15 | 84 | 0.139 | 13.1% |
| 2026H1 | 41.3% | 20.9% | 1.97 | 1.06 | 1.71 | 32 | 0.641 | 15.6% |

Funding paid / gross profit by slice (funding 1x):

| slice | 2021 | 2022 | 2023 | 2024 | 2025 | 2026H1 |
|---|---|---|---|---|---|---|
| funding / gross profit | 9.2% | 1.1% | 1.0% | 2.2% | 0.9% | -1.0% |

## 4. Monte Carlo (funding 1x)

Bootstrap with replacement of A's 396 dev-period per-trade R values (funding 1x) into 10,000 one-year paths of 73 trades each (the dev average per year), compounded at 1% risk per trade from 1.0 equity. Seed 20261014. Trades are resampled independently, so real-life clustering of losses (chop regimes) is NOT captured: treat these as a floor on how bad ordinary bad luck looks, not a ceiling.

| percentile | max drawdown | longest losing streak (trades) |
|---|---|---|
| p50 | 18.7% | 14 |
| p90 | 29.2% | 23 |
| p95 | 32.8% | 26 |
| p99 | 39.8% | 33 |

A losing trade is R <= 0 (same definition as the profit-factor split). Streak percentiles are rounded up to a whole trade.

These p99 values feed `KILL_RULE.md`.
