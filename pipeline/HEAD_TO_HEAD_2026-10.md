# Head-to-head: A (current bot) vs B (daily basket) — 2026-10-14

Protocol: `VALIDATION_RULES.md` §5, committed in `4d123d8` before any results existed.
Data: dev period 2021-01-01 → 2026-05-31 only. Detail: `A_HONEST_NUMBERS_2026-10.md`, `B_BASKET_RESULTS_2026-10.md`.

## Full dev period

| Row | CAGR | Max DD | MAR | Sharpe | Notes |
|---|---|---|---|---|---|
| **A** (1× funding, decision row) | 32.4% | 26.3% | 1.24 | **0.95** | 396 trades, avg R 0.53, PF 1.60 |
| A (0× funding) | 35.6% | 26.0% | 1.37 | 1.00 | regression = old harness exactly |
| A (2× funding) | 29.3% | 26.5% | 1.10 | 0.89 | funding ≈ 2.5% of gross profit at 1× |
| **B main** (EMA 20/100, 1/30 slots) | 18.2% | 65.0% | 0.28 | **0.58** | 6.3× turnover/yr, ~3.1%/yr cost drag, 53% avg cash |
| B sens (EMA 50/200) — report only | 10.7% | 79.4% | 0.13 | 0.47 | |
| B alt (1/N_long) — report only, not pre-registered | −27.8% | 99.1% | −0.28 | 0.26 | |
| BTC buy-and-hold | 18.7% | 76.7% | 0.24 | 0.59 | |
| EW top-30 buy-and-hold | −10.3% | 94.6% | −0.11 | 0.32 | |

Note: Sharpe for A is per-trade annualized; for B it is daily-return annualized. Not identical
methods; the gap (0.95 vs 0.58) is large relative to that difference.

## MAR by slice

| Row | 2021 | 2022 | 2023 | 2024 | 2025 | 2026H1 |
|---|---|---|---|---|---|---|
| A (1×) | 1.81 | **0.34** | **4.22** | **3.77** | **0.20** | 1.90 |
| B main | **7.33** | −0.96 | 0.84 | −0.19 | −0.81 | **5.14** |
| BTC B&H | 1.11 | −0.96 | 7.79 | 4.59 | −0.20 | −0.98 |
| EW top-30 B&H | 8.16 | −0.99 | 1.67 | −0.14 | −0.89 | −0.44 |

## Decision (applied mechanically)
1. B full-period Sharpe > A? **No** (0.58 vs 0.95).
2. B MAR beats A in ≥ 4 of 6 slices? **No** (2 of 6: 2021, 2026H1).

**A stays.** B is roughly "BTC buy-and-hold with smaller drawdowns", strong only in broad alt
rallies (2021, early 2026) and losing in 2022/2024/2025.

## Caveats (honest)
- A's ATR trail 6.0 was originally picked using 2025–26 data (pre-audit contamination), so A's
  2025/2026H1 slices are flattered. A still wins 2022–2024, which predate that choice.
- B uses Binance perp prices as a spot proxy and Binance volume for ranking; delisting exits assume
  a sale at the last close (optimistic for collapses).
- No significance testing; 396 trades for A, 142 rebalances for B.

## Next
One logged confirmation look at 2026-06-01 → present for both (§5). It confirms, it does not select.
