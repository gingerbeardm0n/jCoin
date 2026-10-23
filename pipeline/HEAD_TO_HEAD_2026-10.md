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
  2025/2026H1 slices are flattered. ~~A still wins 2022–2024, which predate that choice.~~
  **Correction 2026-10-23 (`AUDIT_2026-10-23.md` W3):** that is wrong. Trail 6.0 came from a
  full-range 2021–26 grid of 432 configs (`VALIDATION_RULES.md` §2 Looks Log), so 2022–24 were
  part of the selection too. On the dev data A's edge is thin and tail-dependent: t ≈ 2.2, and
  the top 10 trades are ~109% of total R. The sealed confirmation below also had only ~3 truly
  blind trades.
- B uses Binance perp prices as a spot proxy and Binance volume for ranking; delisting exits assume
  a sale at the last close (optimistic for collapses).
- No significance testing; 396 trades for A, 142 rebalances for B.

## Next
One logged confirmation look at 2026-06-01 → present for both (§5). It confirms, it does not select.

## Sealed-window confirmation (run once, 2026-10-14)

Window 2026-06-01 00:00 UTC → 2026-09-30 23:59 UTC (four complete months), both contestants run once with
their fixed configs by `jcoin/research/sealed_confirmation.py` (`splits.check_window(..., allow_sealed=True)`).
This confirms; it does not select. Data: Binance USD-M, same source as dev, fetched into a scratch dir
(repo `data/` untouched); dev data supplies warm-up. Equity starts at 10,000.

| Row | Return | Max DD | Trades / rebalances | Avg R (A) | Win% (A) |
|---|---|---|---|---|---|
| **A, 1× funding** (decision row) | **+30.7%** | **6.4%** | 18 trades | 1.638 | 33.3% |
| A, 0× funding | +31.1% | 6.4% | 18 trades | 1.661 | 33.3% |
| A, 2× funding | +30.3% | 6.5% | 18 trades | 1.615 | 33.3% |
| **B main** (EMA 20/100, 1/30 slots) | +10.5% | 16.9% | 8 rebalances (112 orders) | n/a | n/a |
| BTC buy-and-hold (from 06-01) | +12.9% | 20.8% | 1 entry | n/a | n/a |

Notes:
- A: 42 candidate signals, 18 taken (slots full for the rest); 0 trades open at the 09-30 close (none needed
  mark-to-market). 6 winners / 12 losers; the 6 winners are 3 ETH + 3 BTC multi-day trends (Jun, Jul, Aug).
  Funding cost -0.41 R in total at 1×. Max DD is on the realized (exit-time) equity curve, same as the dev tables.
  Only 4 months, 18 trades: the +30.7% is not an annualizable CAGR and is dominated by a few large winners.
- B: first rebalance on the dev 14-day grid (every 14 days from 2021-01-01) at or after 06-01 is 2026-06-12, cash
  before, equity 10,000 there; later rebalances 06-26, 07-10, 07-24, 08-07, 08-21, 09-04, 09-18; 24 coins held at the end.
  Return and DD are measured over the whole 06-01 → 09-30 window (flat 06-01 → 06-11).
- BTC buy-and-hold uses the same simulator as dev (0.5% entry cost): raw open(06-01) → close(09-30) is +13.5%.
  For reference only, buy-and-hold started 06-12 instead (B's first rebalance) is +30.8%.
- Cross-check vs the 2026-09-18 audit replay (Kraken data, BTC+ETH, 18 trades, 5W/13L, +$254 on $1k, DD 4.9%): this Binance run has
  15 trades entered by 09-18, and is likewise driven by a handful of large ETH/BTC trend winners with a long string of ~-1R stops; the trade
  count matching the audit's 18 is coincidence (this window runs 12 days longer), so the data sources agree in character, not trade by trade.

**Drawdown check (mechanical, §5):** A's worst dev-slice max drawdown at 1× funding is 21.8% (2022 slice,
`A_HONEST_NUMBERS_2026-10.md`). A's sealed max drawdown is 6.4%. 6.4% does not exceed 21.8%.

**CONFIRMED.** (A stays; no STOP AND REASSESS.) Disclosure from §5 still applies: A's behaviour on 06-01 → 09-18 had already
been seen once in the 2026-09-18 audit, so this look is not fully blind for A; it is blind for B.
