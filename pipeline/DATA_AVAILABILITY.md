# jCoin — Market-Data Signal Availability (US-legal, Coinbase/Kraken, no VPN)

**Scope:** Trade venues = Coinbase (Advanced/CFM perps) then Kraken (Kraken Futures `PF_*` perps). US-based, no VPN, so Binance/Bybit/OKX/Hyperliquid/dYdX are off-limits **as trade venues**. Third-party aggregators that *pull* data from those venues are still legal to consume for signals — but using their data to drive trades on Coinbase/Kraken creates a **parity problem** (the signal describes a market you don't trade).

_Researched 2026-06-19. Verify pricing before purchase — it drifts._

## Verdict table

| Signal | Live source (US-legal) | Historical source | Cost | Verdict |
|---|---|---|---|---|
| 1. Open Interest | Coinbase `GetProduct` (`perpetual_details.open_interest`); Kraken Futures `tickers` WS/REST | Coinalyze (free, ~1500pt retention); Velo/Coinglass (paid, deep) | Free live; free-shallow / paid-deep hist | **Available-free** |
| 2. Funding rate | Coinbase `GetProduct.funding_rate`; Kraken `tickers` | Kraken `historical-funding-rates` (free, public, full); Coinbase = scrape/store yourself or Coinalyze/Velo | Free | **Available-free** |
| 3. Liquidations | **Coinbase: none public.** Kraken Futures: WS `trade` channel w/ liquidation flag | Kraken: Tardis (paid) since 2019. Coinbase: **none** | Tardis ~$450+/mo (Kraken only) | **Problematic** |
| 4. Tick trades / CVD | Coinbase WS `market_trades`; Kraken WS `trade` (both carry aggressor side → derive CVD yourself) | Coinbase/Kraken REST (shallow); Tardis tick archive (deep) | Free live; ~$450+/mo deep hist | **Available-free (live); paid (deep hist)** |
| 5. Order book L2 | Coinbase WS `level2`; Kraken WS `book` | Tardis incremental L2 + snapshots | Free live; ~$450+/mo hist | **Available-free (live); paid (hist)** |
| 6. Aggregated OI/funding/basis | Coinalyze (free), Velo ($199/mo), Coinglass ($29–699/mo) | same | $0–$300/mo realistic | **Available-free→paid** |

---

## Per-signal detail

### 1. Open Interest
- **Coinbase (live, free):** `GetProduct` returns `future_product_details.perpetual_details.open_interest` + `funding_rate`, `funding_time`, `index_price`. Snapshot only — poll it to build a series.
- **Kraken (live, free):** Futures `tickers` (REST + WS v2, public, ~1s throttle) includes `openInterest`.
- **Historical:** Neither exchange serves an OI *time series* natively (you'd have to log your own polls). Free third-party: **Coinalyze** API (free, 40 req/min) has OI history for Coinbase + Kraken, but only retains ~1500–2000 intraday points (rolling ~1 day at 1m). Deep history → Velo ($199/mo) or Coinglass.
- **Caveat:** For backtests you must either self-log from day one or buy deep history; free deep OI history for Coinbase/Kraken specifically is not available.

### 2. Funding rate
- **Live, free:** Coinbase `GetProduct.funding_rate` (hourly funding); Kraken `tickers.fundingRate`.
- **Historical, free:** Kraken Futures `GET /historical-funding-rates` is **public, no auth, full history** per `PF_*` market. This is the cleanest signal of the six.
- **Coinbase historical funding:** no clean native history endpoint — self-log, or use Coinalyze/Velo. Coinbase funding mechanics differ (hourly), so don't assume Binance-style 8h schedules.

### 3. Liquidation data — THE PROBLEM
- **Coinbase:** No public liquidation feed or channel exists (Advanced/Exchange WS has no liquidation channel; INTX likewise). You cannot get Coinbase liquidation events live or historically from any source, because Coinbase does not broadcast them.
- **Kraken Futures:** Does surface forced-liquidation fills on the public WS `trade` channel (flagged as liquidation type). Tardis.dev archives these historically (Kraken Futures liquidations since 2019-03-30). So Kraken liquidations are obtainable live (free, self-captured) and historically (paid, Tardis).
- **Aggregators (Coinglass/Coinalyze):** Their liquidation dashboards are overwhelmingly Binance/Bybit/OKX-sourced. Using them means your liquidation signal describes venues you can't trade — a backtest-vs-live parity mismatch and a strategy-logic risk.
- **Bottom line for the strategy:** A liquidation-driven strategy has **no Coinbase liquidation data at all**, and only Kraken-native liquidations (which are thin vs. the big offshore venues). If the edge depends on large liquidation cascades, those cascades live on Binance/Bybit — visible via aggregators but **not tradeable** here.

### 4. Tick trades / CVD
- **Live, free:** Coinbase WS `market_trades` and Kraken WS `trade` both include side/aggressor → compute CVD locally. This is fully available for the exact instruments traded.
- **Historical:** Exchange REST trade endpoints are shallow/rate-limited. Deep tick history (and ready-made CVD inputs) → Tardis.dev (Solo tier ~$450/mo) covers Coinbase + Kraken tick trades.
- **Caveat:** CVD is not served pre-computed; you derive it. Live parity is good (same venue).

### 5. Order book depth / L2
- **Live, free:** Coinbase WS `level2`; Kraken WS `book`. Full incremental L2.
- **Historical:** No native deep archive. Tardis.dev provides incremental L2 updates + periodic snapshots for both Coinbase and Kraken (~$450+/mo). Self-recording is the free alternative but storage-heavy.

### 6. Spot/perp basis & cross-venue aggregated OI/funding
Usability for US retail (data consumption is legal regardless of trade-venue restrictions):
- **Coinalyze** — **free** API (40 req/min), covers Coinbase + Kraken + offshore; OI, funding, predicted funding, liquidations, long/short, CVD. Best free option. Weakness: shallow intraday retention (~1500 pts).
- **Velo (velodata.app)** — API $199/mo (monthly = 3mo history; yearly = full). Aggregated OI/funding/volume, high-res. Good value mid-tier.
- **Coinglass** — Hobbyist $29 / Startup $79 / Standard $299 / Pro $699 per month. Broad: liquidations, OI, funding, L2/L3, heatmaps. Deep history at higher tiers.
- **Coinalyze + Velo or Coinglass-Startup** covers ~all aggregate needs for <$300/mo.
- **Kaiko / Amberdata** — institutional, quote-based, typically $1k+/mo; overkill for a retail bot. (Note: Kaiko acquired Amberdata, June 2026.)
- **CryptoQuant / Glassnode** — on-chain/exchange-flow focused, subscription dashboards; not the right tool for perp microstructure signals here.
- **Tardis.dev** — the go-to for *historical tick/L2/liquidations* (backtesting), ~$450+/mo; not a live-trading feed.

---

## Bottom line — GO / NO-GO

**OI and funding: GO.** Both are available live and free directly from Coinbase and Kraken for the exact instruments traded; Kraken even gives free full funding history, and Coinalyze (free) plus Velo/Coinglass (cheap) cover aggregate and historical gaps. A realistic data budget for everything except liquidations is **$0–$300/mo**.

**Liquidations: the gate fails as designed.** Coinbase publishes **no** liquidation data (live or historical) — full stop. Kraken Futures publishes only its own (thin) liquidations. The rich liquidation-cascade data the strategy implicitly wants lives on Binance/Bybit/OKX, which are visible through aggregators but **not tradeable** by a US no-VPN bot — so any liquidation edge backtested on aggregator data will not have a matching tradeable venue (parity break).

**Verdict:** A US-legal Coinbase/Kraken bot **can** reliably get OI, funding, trades/CVD, and L2 — both live and (with modest paid history or self-logging) historically. It **cannot** get meaningful liquidation data for its trade venues. **If the strategy "leans heavily on liquidation data," it is NO-GO as designed** and must be re-scoped to (a) Kraken-only liquidations, (b) liquidations as a non-tradeable context signal only, or (c) dropping the liquidation dependency. OI/funding/CVD/L2 portions are GO.
