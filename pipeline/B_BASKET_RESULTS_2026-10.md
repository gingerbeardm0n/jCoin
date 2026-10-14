# Strategy B results: daily basket trend, long-only (dev window only)

Generated 2026-10-14 by `python -m jcoin.research.basket_trend_backtest`. Protocol: `VALIDATION_RULES.md` section 5.
Config is fixed (EMA 20/100, top 30, 14-day rebalance, 0.50% per side); nothing was tuned.
The EMA 50/200, 1/N_long and equal-weight rows are sensitivities/benchmarks, reported only. Sealed window (2026-06-01 on) was never downloaded, loaded or evaluated.
No interpretation or decision is made in this file. The decision rule is applied in Phase 3.

## Data

- Source: data.binance.vision USD-M futures **monthly daily-klines** (`data/futures/um/monthly/klines/<SYM>/1d/<SYM>-1d-YYYY-MM.zip`), months 2020-01 to 2026-05 only.
- Symbol list from the bucket listing (includes delisted contracts): **895** USDT-quoted symbols (dated quarterly contracts and USDC-quoted pairs dropped).
  **729** have data in 2020-01..2026-05; 166 have none in range (listed only from 2026-06 on, mostly TradFi/new-token perps).
  **28** of the 729 stop before 2026-05-31 (delisted; e.g. LUNA 2022-05-13, ANC 2022-05-13, BTT 2022-01-26, MATIC 2024-09-11, EOS 2025-05-21).
  Stored at `data/ohlcv/binance_daily/<SYM>/1d.parquet` (ts UTC, open, high, low, close, volume, quote_volume).
- Download: about 47 min wall time total (first run at 16 workers was too slow and was killed after about 8 min; main run at 48 workers took 36 min; 8 symbols that hit transient DNS errors were re-fetched in 92 s).
- Panel: 2020-01-01 to 2026-05-31 (2,343 days) x 729 symbols. 52 symbols have small internal gaps in daily bars (max 29 missing days: TLM, BNX, ICP; typically 5); closes are forward-filled for marking only, and a coin cannot be traded on a day with no bar.
- These are **perp prices used as a spot proxy** (Binance spot vs perp differ about 0.05% on majors; small caps can differ more). Volume ranking is **Binance perp quote volume**, which can differ from US-venue (Kraken/Coinbase) spot ranking.

## Methodology (as implemented)

- **Rebalance**: every 14 days from 2021-01-01 (142 rebalances), executed at the **open of day d**. All inputs use bars strictly before d.
- **Universe (point-in-time)**: eligible = not excluded, a bar on d-1, and >= 100 bars of history before d (sensitivity EMA 50/200 requires >= 200 so its slow EMA is warm). Rank by mean daily `quote_volume` over the 90 bars before d. Top 30. At the first rebalance 30+ coins qualified; the universe was full (30) at every rebalance.
- **Signal**: EMA(20) > EMA(100) on closes up to d-1 (EMA seeded at each coin's first close, `adjust=False`), else flat.
- **Weights**: main line: each long coin gets **1/30 of equity** (exposure <= 1x, rest cash; average cash about 53%). Alt line: 1/N_long (fully invested across longs, 0 longs = cash). Between rebalances positions drift (no daily rebalancing). Every held coin is reset to target at each rebalance, so trims and top-ups are traded and costed.
- **Costs**: 0.40% taker + 0.10% slippage = **0.50% per side** on all traded notional (buys, sells, trims, and forced delist exits). Targets are sized on equity **net of that rebalance's cost**, so cash never goes negative when fully invested.
- **Delisting**: a held coin whose data ends is sold at its last available close (cost charged). 2 such exits occurred in B main: LUNA (2022-05-13) and EOS (2025-05-21). This assumes the delisting is known in time to exit at the last close (optimistic; see limitations).
- **Benchmarks**: BTC buy-and-hold pays one 0.5% entry cost at 2021-01-01 and never sells. EW top-30 B&H uses the same universe, 14-day rebalance and costs, with no EMA filter (1/30 per coin).
- **Metrics**: daily equity at close (UTC). CAGR = growth^(365/days)-1. MaxDD on the daily curve. MAR = CAGR / MaxDD. Sharpe = mean/std (ddof 1) of daily returns x sqrt(365), rf = 0. **Turnover/yr** = (buys + sells notional) / average equity / years (one-way turnover is half of this; cost drag for B main is about 3.1% of equity per year). Orders = individual buy/sell orders. Avg cash = mean cash share of equity; Flat days = share of days with no position.
- **Slices** are sub-curves of the single continuous full-window run (positions carry across slice boundaries; each slice's return, drawdown and Sharpe start from the prior day's close). 2026H1 is only 151 days, so its annualized CAGR/MAR are noisy.
- **Excluded bases** (explicit list in `basket_trend_backtest.py`):
  - Stablecoin/fiat-like: AEUR, BFUSD, BUSD, DAI, EUR, FDUSD, FRAX, GBP, GUSD, PAX, RLUSD, SUSD, TUSD, USD1, USDBRL, USDC, USDD, USDE, USDP, USDS, UST, XUSD.
  - Wrapped/staking/tokenized gold/index/pre-IPO: ANTHROPIC, BETH, BLUEBIRD, BTCDOM, CBETH, DEFI, FOOTBALL, OPENAI, PAXG, RETH, STETH, WBETH, WBTC, WSTETH, XAUT.
  - TradFi-underlying perps (equities, ETFs, metals, energy; 166 tickers, e.g. AAPL, TSLA, NVDA, SPY, XAU, XAG, COPPER).
  - Audit: with the exclusion switched off, only PAXG (13 rebalances), XAU (5) and XAG (4) would have entered a top-30; no other excluded name would have. No leveraged tokens exist as USD-M perps.
  - 182 distinct coins appeared in at least one top-30.

## Full dev window (2021-01-01 to 2026-05-31)

| Strategy | CAGR | MaxDD | MAR | Sharpe | Turnover/yr | Orders | Avg coins held | Flat days | Avg cash |
|---|---|---|---|---|---|---|---|---|---|
| B main (EMA 20/100, 1/30 slots) | 18.2% | 65.0% | 0.28 | 0.58 | 6.3x | 2391 | 14.0 | 0% | 53% |
| B sens (EMA 50/200) | 10.7% | 79.4% | 0.13 | 0.47 | 5.1x | 2366 | 14.7 | 3% | 51% |
| B alt weighting (1/N_long) | -27.8% | 99.1% | -0.28 | 0.26 | 18.4x | 2389 | 14.0 | 0% | 0% |
| BM: BTC buy-and-hold | 18.7% | 76.7% | 0.24 | 0.59 | 0.1x | 1 | 1.0 | 0% | 0% |
| BM: EW top-30 B&H (no filter) | -10.3% | 94.6% | -0.11 | 0.32 | 6.3x | 4571 | 30.0 | 0% | 0% |

### MAR by slice

| Strategy | Full | 2021 | 2022 | 2023 | 2024 | 2025 | 2026H1 |
|---|---|---|---|---|---|---|---|
| B main (EMA 20/100, 1/30 slots) | 0.28 | 7.33 | -0.96 | 0.84 | -0.19 | -0.81 | 5.14 |
| B sens (EMA 50/200) | 0.13 | 4.30 | -0.95 | 1.51 | -0.09 | -0.86 | 3.74 |
| B alt weighting (1/N_long) | -0.28 | 7.25 | -0.99 | 2.92 | -0.24 | -0.86 | -0.99 |
| BM: BTC buy-and-hold | 0.24 | 1.11 | -0.96 | 7.79 | 4.59 | -0.20 | -0.98 |
| BM: EW top-30 B&H (no filter) | -0.11 | 8.16 | -0.99 | 1.67 | -0.14 | -0.89 | -0.44 |

### Sharpe by slice

| Strategy | Full | 2021 | 2022 | 2023 | 2024 | 2025 | 2026H1 |
|---|---|---|---|---|---|---|---|
| B main (EMA 20/100, 1/30 slots) | 0.58 | 2.12 | -2.54 | 0.81 | 0.12 | -0.89 | 1.27 |
| B sens (EMA 50/200) | 0.47 | 1.79 | -2.08 | 1.16 | 0.21 | -1.27 | 1.30 |
| B alt weighting (1/N_long) | 0.26 | 2.09 | -1.57 | 1.58 | 0.22 | -0.76 | 0.23 |
| BM: BTC buy-and-hold | 0.59 | 0.97 | -1.28 | 2.35 | 1.75 | 0.05 | -0.59 |
| BM: EW top-30 B&H (no filter) | 0.32 | 2.20 | -1.51 | 1.29 | 0.28 | -0.72 | 0.08 |

### CAGR by slice

| Strategy | Full | 2021 | 2022 | 2023 | 2024 | 2025 | 2026H1 |
|---|---|---|---|---|---|---|---|
| B main (EMA 20/100, 1/30 slots) | 18.2% | 374.9% | -41.2% | 28.3% | -8.3% | -36.2% | 49.2% |
| B sens (EMA 50/200) | 10.7% | 271.0% | -41.4% | 31.3% | -4.1% | -47.5% | 57.5% |
| B alt weighting (1/N_long) | -27.8% | 513.9% | -91.6% | 126.5% | -14.1% | -64.7% | -83.1% |
| BM: BTC buy-and-hold | 18.7% | 58.8% | -64.2% | 155.9% | 120.6% | -6.4% | -34.3% |
| BM: EW top-30 B&H (no filter) | -10.3% | 518.4% | -84.5% | 83.1% | -8.6% | -62.3% | -18.7% |

### Max drawdown by slice

| Strategy | Full | 2021 | 2022 | 2023 | 2024 | 2025 | 2026H1 |
|---|---|---|---|---|---|---|---|
| B main (EMA 20/100, 1/30 slots) | 65.0% | 51.1% | 43.0% | 33.9% | 43.0% | 44.4% | 9.6% |
| B sens (EMA 50/200) | 79.4% | 63.1% | 43.6% | 20.7% | 46.3% | 55.2% | 15.4% |
| B alt weighting (1/N_long) | 99.1% | 70.9% | 92.2% | 43.3% | 58.8% | 75.6% | 84.2% |
| BM: BTC buy-and-hold | 76.7% | 53.2% | 66.9% | 20.0% | 26.3% | 32.0% | 35.1% |
| BM: EW top-30 B&H (no filter) | 94.6% | 63.5% | 85.4% | 49.8% | 60.6% | 69.6% | 42.6% |

## Per-slice detail

### Slice 2021 (365 days)

| Strategy | CAGR | MaxDD | MAR | Sharpe | Turnover/yr | Orders | Avg coins held | Flat days | Avg cash |
|---|---|---|---|---|---|---|---|---|---|
| B main (EMA 20/100, 1/30 slots) | 374.9% | 51.1% | 7.33 | 2.12 | 8.5x | 664 | 21.6 | 0% | 28% |
| B sens (EMA 50/200) | 271.0% | 63.1% | 4.30 | 1.79 | 8.2x | 764 | 25.7 | 0% | 14% |
| B alt weighting (1/N_long) | 513.9% | 70.9% | 7.25 | 2.09 | 15.6x | 664 | 21.6 | 0% | 0% |
| BM: BTC buy-and-hold | 58.8% | 53.2% | 1.11 | 0.97 | 0.6x | 1 | 1.0 | 0% | 0% |
| BM: EW top-30 B&H (no filter) | 518.4% | 63.5% | 8.16 | 2.20 | 6.9x | 858 | 30.0 | 0% | 0% |

### Slice 2022 (365 days)

| Strategy | CAGR | MaxDD | MAR | Sharpe | Turnover/yr | Orders | Avg coins held | Flat days | Avg cash |
|---|---|---|---|---|---|---|---|---|---|
| B main (EMA 20/100, 1/30 slots) | -41.2% | 43.0% | -0.96 | -2.54 | 3.2x | 166 | 4.9 | 0% | 85% |
| B sens (EMA 50/200) | -41.4% | 43.6% | -0.95 | -2.08 | 2.0x | 145 | 5.0 | 12% | 84% |
| B alt weighting (1/N_long) | -91.6% | 92.2% | -0.99 | -1.57 | 26.1x | 164 | 4.9 | 0% | 0% |
| BM: BTC buy-and-hold | -64.2% | 66.9% | -0.96 | -1.28 | 0.0x | 0 | 1.0 | 0% | 0% |
| BM: EW top-30 B&H (no filter) | -84.5% | 85.4% | -0.99 | -1.51 | 5.0x | 826 | 30.0 | 0% | 0% |

### Slice 2023 (365 days)

| Strategy | CAGR | MaxDD | MAR | Sharpe | Turnover/yr | Orders | Avg coins held | Flat days | Avg cash |
|---|---|---|---|---|---|---|---|---|---|
| B main (EMA 20/100, 1/30 slots) | 28.3% | 33.9% | 0.84 | 0.81 | 7.2x | 534 | 16.7 | 0% | 44% |
| B sens (EMA 50/200) | 31.3% | 20.7% | 1.51 | 1.16 | 4.5x | 373 | 12.1 | 3% | 59% |
| B alt weighting (1/N_long) | 126.5% | 43.3% | 2.92 | 1.58 | 15.8x | 534 | 16.7 | 0% | 0% |
| BM: BTC buy-and-hold | 155.9% | 20.0% | 7.79 | 2.35 | 0.0x | 0 | 1.0 | 0% | 0% |
| BM: EW top-30 B&H (no filter) | 83.1% | 49.8% | 1.67 | 1.29 | 6.0x | 842 | 30.0 | 0% | 0% |

### Slice 2024 (366 days)

| Strategy | CAGR | MaxDD | MAR | Sharpe | Turnover/yr | Orders | Avg coins held | Flat days | Avg cash |
|---|---|---|---|---|---|---|---|---|---|
| B main (EMA 20/100, 1/30 slots) | -8.3% | 43.0% | -0.19 | 0.12 | 7.2x | 555 | 18.0 | 0% | 40% |
| B sens (EMA 50/200) | -4.1% | 46.3% | -0.09 | 0.21 | 5.5x | 590 | 20.5 | 0% | 31% |
| B alt weighting (1/N_long) | -14.1% | 58.8% | -0.24 | 0.22 | 15.7x | 555 | 18.0 | 0% | 0% |
| BM: BTC buy-and-hold | 120.6% | 26.3% | 4.59 | 1.75 | 0.0x | 0 | 1.0 | 0% | 0% |
| BM: EW top-30 B&H (no filter) | -8.6% | 60.6% | -0.14 | 0.28 | 6.4x | 843 | 30.0 | 0% | 0% |

### Slice 2025 (365 days)

| Strategy | CAGR | MaxDD | MAR | Sharpe | Turnover/yr | Orders | Avg coins held | Flat days | Avg cash |
|---|---|---|---|---|---|---|---|---|---|
| B main (EMA 20/100, 1/30 slots) | -36.2% | 44.4% | -0.81 | -0.89 | 5.9x | 405 | 12.6 | 0% | 58% |
| B sens (EMA 50/200) | -47.5% | 55.2% | -0.86 | -1.27 | 4.7x | 436 | 14.5 | 0% | 52% |
| B alt weighting (1/N_long) | -64.7% | 75.6% | -0.86 | -0.76 | 22.4x | 405 | 12.6 | 0% | 0% |
| BM: BTC buy-and-hold | -6.4% | 32.0% | -0.20 | 0.05 | 0.0x | 0 | 1.0 | 0% | 0% |
| BM: EW top-30 B&H (no filter) | -62.3% | 69.6% | -0.89 | -0.72 | 6.4x | 845 | 30.0 | 0% | 0% |

### Slice 2026H1 (151 days)

| Strategy | CAGR | MaxDD | MAR | Sharpe | Turnover/yr | Orders | Avg coins held | Flat days | Avg cash |
|---|---|---|---|---|---|---|---|---|---|
| B main (EMA 20/100, 1/30 slots) | 49.2% | 9.6% | 5.14 | 1.27 | 4.1x | 67 | 4.5 | 0% | 85% |
| B sens (EMA 50/200) | 57.5% | 15.4% | 3.74 | 1.30 | 2.9x | 58 | 4.4 | 0% | 84% |
| B alt weighting (1/N_long) | -83.1% | 84.2% | -0.99 | 0.23 | 25.0x | 67 | 4.5 | 0% | 0% |
| BM: BTC buy-and-hold | -34.3% | 35.1% | -0.98 | -0.59 | 0.0x | 0 | 1.0 | 0% | 0% |
| BM: EW top-30 B&H (no filter) | -18.7% | 42.6% | -0.44 | 0.08 | 8.0x | 357 | 30.0 | 0% | 0% |

## Limitations

- **Perp prices as a spot proxy**, Binance volume as the liquidity ranking; a US spot venue would have a different (smaller) tradable list and different fills. Slippage of 0.10% is a flat assumption, optimistic for small caps in stress.
- **Survivorship is only as complete as the bucket**: delisted contracts present in the listing are included (28 delisted, LUNA among them; FTT stays listed in the archive), but any contract Binance removed from the archive is absent. Also, a *spot* delisting is not the same event as a perp delisting.
- **Delist exit uses knowledge of the last bar** (exit at last available close with normal 0.5% cost). Real exits during a collapse would be worse.
- Several coins trade under both `X` and `1000X` tickers at different times (e.g. SHIB); they are treated as separate symbols.
- 52 symbols have small bar gaps; marked at the last close, not tradable on missing days.
- Universe of TradFi tickers to exclude was built by hand; it affects only 2025-26 and the audit above shows it only mattered for PAXG/XAU/XAG.
- 1/30 slots means the main line holds on average about 53% cash; compare against buy-and-hold with that in mind. The 1/N_long line is concentrated (often 4-5 coins) and drives much larger drawdowns.
- Short samples: 6 slices, one 151-day, regime-dependent (2021 bull, 2022 bear). No significance testing or deflated-Sharpe adjustment.
- No funding, borrow or tax effects (spot long-only: none expected apart from taxes).
- Sealed window untouched. Phase 3 will make the single logged look at 2026-06-01 on.
