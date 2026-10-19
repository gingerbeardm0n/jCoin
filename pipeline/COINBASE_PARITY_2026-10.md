# Coinbase nano perps vs Binance (backtest data) — price & signal parity

Run 2026-10-18. Overlap ends 2026-05-31 (dev window only).

## BTC (BIP-20DEC30-CDE)

- Coinbase history starts 2025-07-18 20:00 UTC; compared 1775 overlapping 4h bars from 2025-08-08.
- Close difference: median 0.064%, 95th pct 0.154%, max 0.399%.
- Basis (Coinbase vs Binance): mean +0.040%, median +0.046%.
- ATR ratio (Coinbase / Binance), median: 1.020.
- Regime label agreement: 85.9%.
- Any breakout flag: both 160, Coinbase only 17, Binance only 21.
- **A's trade-able entries (breakout aligned with regime): both 46, Coinbase only 8, Binance only 10.**

## ETH (ETP-20DEC30-CDE)

- Coinbase history starts 2025-07-18 20:00 UTC; compared 1775 overlapping 4h bars from 2025-08-08.
- Close difference: median 0.071%, 95th pct 0.186%, max 0.438%.
- Basis (Coinbase vs Binance): mean +0.054%, median +0.058%.
- ATR ratio (Coinbase / Binance), median: 1.000.
- Regime label agreement: 88.8%.
- Any breakout flag: both 146, Coinbase only 12, Binance only 12.
- **A's trade-able entries (breakout aligned with regime): both 45, Coinbase only 5, Binance only 8.**


## Strategy A on Coinbase vs Binance prices (2025-08-08 → 2026-05-31, 12bp, no funding) — RED FLAG

| Prices | Taken trades | Total return | Max DD | PF | avg R |
|---|---|---|---|---|---|
| Binance (backtest source) | 72 | +0.6% | 21.0% | 1.12 | +0.10 |
| **Coinbase (live venue)** | 70 | **−24.2%** | 28.8% | **0.59** | **−0.37** |

- Warm-up ruled out: Binance-vs-Binance with the same short start agrees 100%.
- 51 of ~70 trades share entry bar and side, yet those common trades sum to **+16.8R on Binance vs −17.0R on
  Coinbase** — the difference is mostly in **exits** (trailing stops), not entries.
- Example: BTC short entered 01-16 12:00 → +24.1R on Binance, +3.7R on Coinbase. ETH long 08-08 → +3.3R vs −1.1R.
- Likely cause (unverified): Coinbase nano candles have different/larger wicks (thinner market), so the
  trailing stop is hit earlier; plus tiny price differences move swing points (~20% of entries differ).
- Meaning: A's results depend on a few large winners, and catching them is sensitive to exact highs/lows.
  The edge may not transfer to Coinbase's own price series. **Do not go live on Coinbase until this is
  understood** (next: compare wick sizes; re-run with stop/trailing evaluated on closes; check longer history).

## Diagnosis (2026-10-19)

1. **Not general wickiness.** Median 4h range: BTC 1.11% Coinbase vs 1.08% Binance; ETH 1.64% vs 1.64%.
2. **Not fragility to small noise in general.** `noise_robustness.py` (200 runs, N(0, 0.075%) on every price,
   full dev window): all runs profitable, PF p5–p95 1.44–1.73 (baseline 1.65 sits ~p70 → fairer CAGR ≈ 31%,
   not 35.6%). See `NOISE_ROBUSTNESS_2026-10.md`.
3. **Worse than noise explains.** Over the same 10-month window, only 0.5% of noisy Binance runs lost as much as
   Coinbase (−24.2%); noise-only PF p5–p95 0.86–1.49.
4. **Cause: rare extreme Coinbase spikes** (thin nano order book). Highs/lows beyond Binance by >1%: BTC 13/8,
   ETH 11/12 bars in 1,780; >2%: BTC 4/3, ETH 3/2. Example during the BTC 01-16 short: 01-31 16:00 high 84,500
   vs 82,200 (+2.8%), 02-08 08:00 +2.4% → trailing stop hit early, +24.1R became +3.7R.
   One 12h data gap (2025-10-25, maintenance).
5. **This is real execution risk,** not bad data: a resting stop on Coinbase would trigger on these prints.
   Candidate mitigation: evaluate stops on 4h **closes** + a wide resting "disaster" stop. Must be pre-registered
   and tested (VALIDATION_RULES.md §7) before any change.
