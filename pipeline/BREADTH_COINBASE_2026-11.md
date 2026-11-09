# §10 breadth: A on other Coinbase US perp coins

Protocol: `VALIDATION_RULES.md` §10, committed in `a5f8698` before this script existed. Binance USD-M 4h,
dev window 2021-01-01 → 2026-05-31, 12bp, funding 0x, A's fixed config. **Unseen coins are marked \***; the rest were evaluated before (see §10 disclosure).

| Coin | Data | Trades | PF | avg R | Win % | CAGR | Max DD | MAR | +R slices | Pass |
|---|---|---|---|---|---|---|---|---|---|---|
| ADA | 5.2y from 2021-03 | 215 | 1.48 | +0.403 | 19.5% | 14.4% | 17.6% | 0.82 | 5/6 | **yes** |
| AAVE | 5.4y from 2021-01 | 231 | 0.89 | -0.091 | 15.2% | -5.5% | 46.3% | -0.12 | 4/6 | no |
| AVAX | 5.2y from 2021-03 | 214 | 1.15 | +0.132 | 16.8% | 3.2% | 27.9% | 0.11 | 3/6 | no |
| BCH | 5.2y from 2021-03 | 214 | 0.95 | -0.045 | 15.0% | -3.4% | 52.2% | -0.06 | 3/6 | no |
| BNB | 5.2y from 2021-03 | 230 | 0.82 | -0.159 | 14.8% | -8.1% | 49.8% | -0.16 | 2/6 | no |
| DOGE | 5.2y from 2021-03 | 207 | 0.95 | -0.043 | 16.4% | -3.5% | 51.5% | -0.07 | 2/6 | no |
| ENA \* | 2.0y from 2024-06 | 73 | 2.34 | +1.003 | 27.4% | 39.9% | 15.0% | 2.66 | 3/3 | **yes** |
| HBAR | 5.0y from 2021-05 | 222 | 1.25 | +0.224 | 14.9% | 6.8% | 34.4% | 0.20 | 4/6 | **yes** |
| HYPE \* | insufficient data (0.8y from 2025-07) | — | — | — | — | — | — | — | — | no |
| LTC | 5.2y from 2021-03 | 215 | 0.74 | -0.227 | 15.8% | -9.9% | 54.2% | -0.18 | 1/6 | no |
| LINK | 5.2y from 2021-03 | 214 | 1.24 | +0.204 | 19.2% | 6.3% | 24.8% | 0.26 | 5/6 | **yes** |
| NEAR | 5.2y from 2021-03 | 226 | 1.37 | +0.309 | 17.7% | 11.1% | 26.8% | 0.41 | 4/6 | **yes** |
| ONDO \* | 2.2y from 2024-03 | 91 | 1.06 | +0.055 | 11.0% | -0.3% | 27.2% | -0.01 | 1/3 | no |
| PEPE \* | 2.9y from 2023-07 | 123 | 1.00 | +0.003 | 14.6% | -2.0% | 34.9% | -0.06 | 3/4 | no |
| DOT | 5.2y from 2021-03 | 230 | 1.02 | +0.016 | 15.2% | -1.9% | 40.4% | -0.05 | 2/6 | no |
| SHIB \* | 4.9y from 2021-07 | 192 | 1.31 | +0.254 | 20.8% | 8.1% | 21.5% | 0.38 | 4/6 | **yes** |
| SOL | 5.2y from 2021-03 | 204 | 1.02 | +0.018 | 15.2% | -1.0% | 27.2% | -0.04 | 3/6 | no |
| SUI | 2.9y from 2023-07 | 111 | 1.57 | +0.482 | 17.1% | 15.8% | 23.6% | 0.67 | 3/4 | **yes** |
| XLM | 5.4y from 2021-01 | 222 | 0.92 | -0.067 | 14.9% | -4.6% | 38.0% | -0.12 | 2/6 | no |
| XRP | 5.2y from 2021-03 | 204 | 1.39 | +0.337 | 17.2% | 10.7% | 28.6% | 0.38 | 4/6 | **yes** |
| ZEC \* | 5.2y from 2021-03 | 219 | 1.10 | +0.085 | 15.5% | 1.6% | 48.6% | 0.03 | 5/6 | no |

## Portfolio (dev window)

| Portfolio | CAGR | Max DD | MAR | Sharpe | PF | Trades | avg R |
|---|---|---|---|---|---|---|---|
| BTC+ETH (max 2 concurrent) | 35.6% | 26.0% | 1.37 | 1.00 | 1.65 | 396 | +0.562 |
| BTC+ETH+ADA+ENA+HBAR+LINK+NEAR+SHIB+SUI+XRP (max 4 concurrent) | 81.7% | 53.3% | 1.53 | 1.49 | 1.44 | 1429 | +0.377 |

## Decision (§10, both required)

1. Coins passing: 8 (ADA, ENA, HBAR, LINK, NEAR, SHIB, SUI, XRP) ≥ 3 → yes
2. Combined Sharpe 1.49 ≥ 1.00 and MAR 1.53 ≥ 1.37 → yes

**Verdict: BREADTH ADOPTED (paper decision next)**
