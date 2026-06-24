# Breadth Study — 2026-06-22

**Question:** Does the breakout edge hold across many coins on ONE shared config (no
per-coin tuning)? **Harness:** `jcoin/research/breadth_study.py`. 17 liquid USDT-perp
majors, 4h, shared config (breakout, atr_init=1.0, atr_trail=6.0, k=2, atr_period=14),
risk 1%, cost 12bp, each coin run SOLO (single-symbol portfolio).

## Result: edge is REAL but NARROW — 4 of 17 coins

| Coin | CAGR | maxDD | MAR | PF | Sharpe | yrs+ | verdict |
|---|---|---|---|---|---|---|---|
| BTC | 19% | 18% | 1.05 | 1.65 | 0.69 | 5/6 | KEEP |
| ETH | 18% | 22% | 0.84 | 1.65 | 0.74 | 6/6 | KEEP |
| ADA | 13% | 18% | 0.74 | 1.44 | 0.60 | 5/6 | KEEP |
| NEAR | 14% | 27% | 0.51 | 1.43 | 0.61 | 4/6 | KEEP (borderline) |
| FIL | 13% | 34% | 0.37 | 1.44 | 0.60 | 3/6 | weak |
| XRP | 10% | 29% | 0.37 | 1.37 | 0.51 | 4/6 | weak |
| LINK | 6% | 25% | 0.23 | 1.23 | 0.36 | 5/6 | weak |
| AVAX | 6% | 28% | 0.21 | 1.23 | 0.35 | 4/6 | weak |
| ETC | 3% | 43% | 0.07 | 1.16 | — | 2/6 | flat |
| DOT | ~0% | 40% | -0.01 | 1.06 | — | 2/6 | flat |
| BCH/UNI/DOGE/SOL/LTC/BNB/ATOM | negative | up to 74% | <0 | <1.0 | <0 | poor | LOSE |

**Keepers (PF≥1.2 AND MAR≥0.5): BTC, ETH, ADA, NEAR.**

## Findings
- The edge is **selective, not universal** — 4/17 clearly work, 7 are outright negative.
  It lives in liquid majors that trend cleanly, not "crypto" broadly. More coins ≠ more edge.
- **BTC + ETH independently confirmed** (PF 1.65 each; ETH 6/6 years). **ADA + NEAR add
  robust diversification on the SAME config** (no tuning) — genuine cross-sectional evidence.
- **SOL correctly dropped** (PF 0.97, negative — matches prior finding).
- Confirms the case AGAINST per-coin custom configs: the 13 failing coins genuinely lack
  this edge; tuning each would manufacture fake in-sample edges.
- Win rates ~15–20% across all coins (trend-following profile). Keepers differ by having
  big-enough winners (PF), not higher hit rate.

## Decisions / next
- **Add ADA** to the tradeable universe (BTC + ETH + ADA). NEAR = watch (borderline).
- Skip weak (FIL/XRP/LINK/AVAX) and negative coins.
- **Before ADA/NEAR go live:** run sealed train/validate/test (full-range pass may be luck).
- **Live check:** confirm Kraken lists liquid perps for ADA/NEAR (BTC/ETH confirmed).
- Method note: each coin run solo (max_concurrent=1); combined multi-coin portfolio
  compounds higher (e.g. BTC+ETH together ~36% vs ~19% solo).
