# A_LO: spot long-only (VALIDATION_RULES.md §6)

Strategy A signals, long trades only, no funding, dev window 2021-01-01 → 2026-05-31.

## Full dev period

| Cost (round trip) | CAGR | Max DD | MAR | Sharpe | PF | Trades | avg R |
|---|---|---|---|---|---|---|---|
| 1.00% **(decision)** | 0.7% | 46.2% | 0.02 | 0.22 | 1.14 | 224 | +0.180 |
| 0.50% (report only) | 14.0% | 37.5% | 0.37 | 0.59 | 1.46 | 224 | +0.485 |
| 2.60% (report only) | -32.6% | 90.6% | -0.36 | -0.98 | 0.62 | 224 | -0.797 |

## By slice at 1.00% cost

| Slice | Return | Max DD | MAR | Trades | avg R |
|---|---|---|---|---|---|
| 2021 | +39.1% | 16.7% | 2.34 | 46 | +0.883 |
| 2022 | -35.3% | 35.3% | -1.00 | 36 | -1.192 |
| 2023 | +53.8% | 17.3% | 3.12 | 35 | +1.611 |
| 2024 | +10.0% | 23.0% | 0.43 | 42 | +0.386 |
| 2025 | -12.5% | 31.0% | -0.40 | 48 | -0.116 |
| 2026H1 | -22.0% | 22.0% | -2.05 | 17 | -1.444 |

## Pass rule (§6, all three required)

1. PF ≥ 1.20: **1.14** → no
2. MAR > BTC buy-and-hold (0.24) and > 0: **0.02** → no
3. Positive in ≥ 4 of 6 slices: **3 of 6** → no

**Verdict: FAIL**

Worst dev-slice max drawdown (sealed-look threshold): 35.3%
