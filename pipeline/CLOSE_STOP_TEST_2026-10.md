# §7: A vs A_CS (close-based stops + 2 ATR disaster stop)

## 1. Binance, full dev period (12bp + 1x funding)

| Run | CAGR | Max DD | MAR | Sharpe | PF | Trades | avg R | Return |
|---|---|---|---|---|---|---|---|---|
| A (intrabar stops) | 32.4% | 26.3% | 1.24 | 0.95 | 1.60 | 396 | +0.527 | +357.4% |
| A_CS (close stops) | 30.3% | 35.7% | 0.85 | 0.90 | 1.53 | 311 | +0.687 | +319.7% |

MAR by slice (1x funding):

| Slice | 2021 | 2022 | 2023 | 2024 | 2025 | 2026H1 |
|---|---|---|---|---|---|---|
| A | 1.81 | 0.34 | 4.22 | 3.77 | 0.20 | 1.90 |
| A_CS | 0.71 | 3.22 | 3.58 | 2.57 | -0.19 | 2.00 |

## 2. Coinbase prices, 2025-08-08 → 2026-05-31 (12bp, no funding)

| Run | CAGR | Max DD | MAR | Sharpe | PF | Trades | avg R | Return |
|---|---|---|---|---|---|---|---|---|
| A on Coinbase | -28.9% | 28.8% | -1.00 | -1.49 | 0.59 | 70 | -0.365 | -24.2% |
| A_CS on Coinbase | -13.9% | 28.7% | -0.49 | -0.05 | 0.98 | 59 | -0.033 | -11.5% |

Report only — same window on Binance prices:

| Run | CAGR | Max DD | MAR | Sharpe | PF | Trades | avg R | Return |
|---|---|---|---|---|---|---|---|---|
| A on Binance | 0.7% | 21.0% | 0.03 | 0.26 | 1.12 | 72 | +0.103 | +0.6% |
| A_CS on Binance | 2.4% | 25.0% | 0.10 | 0.35 | 1.16 | 56 | +0.222 | +2.0% |

## Decision (§7, both required)

1. Dev Sharpe 0.90 ≥ 0.90×0.95=0.85 and MAR 0.85 ≥ 0.90×1.24=1.11 → no
2. Coinbase PF 0.98 > 0.59 → yes

**Verdict: KEEP A (intrabar stops)**
