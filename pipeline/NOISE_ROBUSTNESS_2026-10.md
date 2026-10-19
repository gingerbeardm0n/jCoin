# Noise robustness of strategy A (diagnostic)

Dev window 2021-01-01 → 2026-05-31, Binance 4h, fixed A config, 12bp, no funding.
Noise: independent multiplicative N(0, 0.075%) on every O/H/L/C; 200 runs, seed 20261019.

| Metric | Baseline | p5 | p25 | median | p75 | p95 |
|---|---|---|---|---|---|---|
| cagr | 35.6% | 22.7% | 27.8% | 31.5% | 34.8% | 40.7% |
| max_dd | 26.0% | 22.8% | 27.0% | 29.0% | 31.1% | 34.8% |
| mar | 1.37 | 0.71 | 0.94 | 1.05 | 1.26 | 1.60 |
| pf | 1.65 | 1.44 | 1.51 | 1.57 | 1.63 | 1.73 |
| sharpe | 1.00 | 0.77 | 0.87 | 0.95 | 0.99 | 1.11 |
| avg_R | +0.562 | +0.382 | +0.446 | +0.494 | +0.540 | +0.626 |
| n_trades | 396 | 386 | 396 | 401 | 408 | 417 |

- Runs with PF < 1.0 (losing): 0%
- Runs with PF < 1.15: 0%
- Runs with CAGR < 0: 0%
