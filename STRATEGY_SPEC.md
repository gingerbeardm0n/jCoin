# jCoin — Strategy & Risk Specification

**Status:** Draft v0.1 — pre-build blueprint
**Date:** 2026-06-19
**Owner:** Joel
**Mandate:** A 24/7 automated crypto perpetual-futures trader. Constant monitoring, momentum scalping — many small profitable trades that compound. US-based, no VPN, capital band $5k–25k.

> Sibling project to **jTrader** (mid-cap momentum equities, 9:30–11:30am only). jCoin removes the time-of-day constraint by moving to a market that never closes.

---

## 0. The First Principle (read this before anything else)

> **UPDATED 2026-06-20 — superseded for the v1 strategy.** The maker-first rule below was
> written for the original **mean-reversion scalping** plan, which was tested and rejected
> (no edge — see §3 and `pipeline/THESIS_RESULTS_2026-06-20.md`). The validated v1 strategy
> is **trend breakout, and it is correctly a TAKER** (see "Why taker is correct for v1"
> below). Keep this section for the underlying fee math, but the maker mandate no longer
> binds — fees are not the constraint for v1.

**Fees matter in proportion to your profit-per-trade.** The maker edge is not alpha — it is
fee-avoidance, and how much it matters depends entirely on target size vs fee:

- A taker→taker round trip costs ~9 basis points (0.09%) before spread and slippage.
- For **small-target scalping**, that fee is a huge fraction of profit → break-even needs
  ~92% win rate → maker (post-only, ~0% fee) was **mandatory**. This drove the original plan.
- For **large-target setups**, the fee is a rounding error → taker is fine.

### Why taker is correct for v1 (trend breakout)
1. **Targets dwarf the fee.** Winners run for hundreds of bps via the trailing stop; net
   edge is **+59 bps/trade after fees**. A 9 bp fee is minor against that.
2. **Breakouts are taker by nature.** To catch the impulse you must cross the spread and
   enter NOW on confirmation. A resting maker limit at the level either won't fill (price
   runs away) or fills mainly on *false* breakouts that reverse — adverse selection.
3. **Proven fee-insensitive.** Cost-stress test: the strategy still beats buy & hold even
   at a 30 bp round-trip cost (5× normal taker). Fees are not the binding constraint.

**Design rule (v1):** signal + risk management dominate; fee optimization is secondary.
A maker-entry variant of breakout ("buy the retest") is a possible future fee-shave — see
§3 v2 experiments — but it is not required and is not a priority.

---

## 1. Venue Plan

US-legal, no-VPN venues only (Hyperliquid, dYdX, GMX, Binance, Bybit, OKX are all US-blocked and excluded).

| Phase | Venue | Why |
|---|---|---|
| **Build & validate** | **Coinbase Financial Markets** | Official Python/TS/Go/Java SDKs, post-only + reduce-only supported, 0.00% maker / 0.03% taker, BTC-PERP + ETH-PERP. Best place to write and prove the code. Limitation: only 2 markets, 10x leverage cap. |
| **Primary (scale)** | **Kraken / Bitnomial** | 16 perp markets (more momentum signals), 8-hour funding (friendlier for intraday than hourly), full order types incl. trailing stop. Brand new (Jun 2026) — **must measure real spread/depth live before trusting**. |
| **Hedge only** | CME Micro BTC/ETH | Institutional clearing, un-geofenceable. NOT for high-frequency scalping — flat ~$5–7/round-turn = 2–10% of capital/day at 100 trades. |

**Action items / unknowns to confirm:**
- [ ] Verify Coinbase + Kraken perp trading is allowed in Joel's state (Kraken bans NY + ME).
- [ ] Confirm Coinbase US perp post-only fee/rebate (international rate may differ).
- [ ] Measure live bid/ask spread + book depth on both venues before sizing.

---

## 2. Instruments

Ranked for this capital band:

1. **BTC-PERP** — mandatory core. Tightest spread (0.5–3 bp), deepest US-legal book, predictable funding.
2. **ETH-PERP** — run alongside BTC. Higher ATR (3–5% vs 2–4%) → 30–50% more setups.
3. **SOL-PERP** (Kraken only) — add after BTC/ETH proven. 5–8% ATR. New book is thin → trade at 25–50% size until depth confirmed.
4. *Opportunistic:* XRP-PERP (event-driven only).
- **Excluded:** DOGE, LINK, AVAX, ADA — spread + slippage exceed scalp targets at this capital.

**Session handling — Adaptive 24/7 (decided):**
Trade around the clock, but scale behavior by liquidity:
- **Prime (UTC 08:00–11:00, 13:00–17:00):** full size, normal filters. 16:00–17:00 = peak volume.
- **Thin hours (esp. UTC 03:00–06:00) + weekends:** auto-shrink position size and tighten entry filters (require stronger signal, wider edge over cost). Volume drops 15–40% off-hours; flash-wick risk up.
- Implementation: a liquidity/volatility gate that reads live spread + depth and modulates size + signal thresholds, rather than a hard on/off clock.

---

## 3. Strategy Stack (build in this order)

> **Build decision:** Mean-reversion engine FIRST, alone. Build + paper-test + prove it before adding breakout. One engine at a time.

---

### v1 — Trend-Aligned Breakout *(VALIDATED 2026-06-20, replaces dead mean-reversion plan)*

> **History:** The original v1 was candle-only **mean-reversion** (fade extremes in ranges,
> from TradingRiot + Trader Mayne). It was **tested against 5.5y of BTC/ETH/SOL data and
> REJECTED** — no edge in any regime, timeframe, or trigger (naive z-score fade AND the real
> Swing Failure Pattern). See `pipeline/THESIS_RESULTS_2026-06-20.md`. The mean-reversion
> concept pages in `pipeline/concepts/` are kept as historical reference only.
> The data instead pointed to **momentum**, which validated. This is the new v1.

**The validated edge:** Trade WITH a break of structure (body close past a prior confirmed
swing), only when ALIGNED with the prevailing trend regime, on the 4h timeframe, BTC + ETH,
with an ATR trailing stop. Backtest (5.5y, 671 trades): **profit factor 1.36, +59 bps net
avg/trade, 5 of 6 years positive.** This is a modest, drawdown-prone trend-following edge —
not a jackpot — but it is real, consistent across years/symbols, and stable across the
parameter grid.

**v1 components:**

| Layer | Rule | Module |
|---|---|---|
| **Regime gate** | Regime classifier (HH/HL vs LL/LH, body-close confirmed). Trade ONLY in trend; stand aside in range. (Inverse of the fade gate — this is the on-switch.) | `jcoin/strategy/regime.py` |
| **Trigger** | Break of Structure: candle body closes past the most recent confirmed swing high (long) / low (short). Fresh cross only. | `jcoin/strategy/breakout.py` |
| **Alignment** | Long breakouts only in uptrend regime; short breakouts only in downtrend. Skip range entirely. | (regime ∩ breakout) |
| **Entry** | Taker at the breakout candle close (targets dwarf the ~9 bp fee). | — |
| **Stop** | ATR initial stop (1.0×ATR) + chandelier trailing stop (**6.0×ATR**, widened from 4.0 on 2026-06-22 — OOS-validated, see `pipeline/OPTIMIZATION_STUDY_2026-06-22.md`) → cut losers fast, let winners run far. | `jcoin/engine/strategy.py` |
| **Instruments** | BTC + ETH only (SOL tested and excluded — too whippy, loses money). | — |
| **Horizon** | Swing (multi-day holds). NOT scalping — mandate followed the edge. | — |

**Param set (~6, all candle-derived):** `swing_k`, `atr_period`, `atr_init`, `atr_trail`,
`max_hold`, regime `lookback_swings`. Low overfit surface; sensitivity grid is stable.

**Known caveats (carry into the build):** ~25% win rate (trend-following: many small losses,
few big wins → long losing streaks are normal); slippage not yet modeled (live net < +59 bps);
2026 YTD soft (watch for decay); 2-symbol concentration; backtest evaluates trades
independently (the live engine must serialize / cap concurrent positions + size by risk).

**v2 (later, after v1 paper-proven):** layer derivatives signals (OI, funding — both
US-legal-gettable) as conviction filters; broaden instruments if liquidity allows.

**v2 experiments (test, don't assume):**
- **Maker buy-the-retest A/B.** Hypothesis: instead of taker entry at the breakout close,
  rest a post-only limit at the broken level on the pullback (maker, ~0% fee). Measure head
  to head vs the taker breakout on the same data. *Trade-offs to quantify:* fee saved per
  trade vs trades MISSED (many breakouts never retest, and momentum's best moves often don't
  look back) and worse fills on retests that fail. Decision rule: adopt only if maker net
  expectancy > taker net expectancy after accounting for missed trades. **Not a priority —
  v1 is proven fee-insensitive (cost-stress survives 30 bp); this is a marginal optimization,
  not a fix.**
- ~~Cross-sectional momentum across a wider alt basket (rank + trade top movers).~~ **TESTED
  2026-07-01, DEAD** — `jcoin/research/cross_sectional_momentum_backtest.py`. Looked good
  in-sample (train Sharpe 0.66) but fully inverted out-of-sample (TEST Sharpe -1.15). Overfit
  to the training window.
- Volatility/consolidation pre-filter (breakout from a tight range = higher quality).
- **Funding-rate-extreme reversal — a genuine lead, parked pending better data.** Tested
  2026-07-01 (`jcoin/research/funding_extreme_reversal_backtest.py`): fade a coin when its
  funding rate is a z-score extreme vs its own rolling history (crowd unusually one-sided ->
  bet it unwinds). This is a downgraded, funding-only version of TradingRiot's documented
  3-leg signal (OI spike + funding spike + liquidation flush) — the other 2 legs have no free
  historical data (Kraken has zero historical OI, confirmed via direct API test 2026-06-30;
  liquidation history needs paid Tardis, ~$450+/mo).
  **Result: XRP and ADA show a real, consistent edge** — win% 63-65%, positive in both
  halves of the available window (not a one-window fluke like RUNE/SUI were), ~6% CAGR at a
  10%-of-equity per-trade sizing, low drawdown (<1.5%). SAND and AVAX are noise-level, not
  worth trading. Honest caveats: (1) only ~10 months of data exist (Kraken's funding-history
  ceiling) — no multi-regime test possible yet; (2) missing the OI/liquidation confirmation
  legs that make the full signal credible; (3) best framed as a **confirmation filter on top
  of breakout signals**, not a standalone strategy — matches the v2 plan above.
  **Decision: do NOT wire into live/paper trading yet** — same rigor bar as everything else
  (this is thinner evidence than the breakout coin gate). Revisit with real OI/liquidation
  history (Coinglass ~$29-699/mo or Velo) once the account is live and profitable enough to
  justify the recurring data cost — not before.

### Strategy 3 — Funding Carry *(ballast only, capital > $15k)*
- Delta-neutral long-spot / short-perp (or cross-venue) to harvest funding. ~10–30% APR, low drawdown, near-uncorrelated with the momentum books.
- **Not the core mandate** (it's carry, not scalping). Role: smooth the equity curve so the momentum strategies can size up. Marginal capital efficiency below $15k.

### Signal overlay (not a standalone strategy)
- **CVD / order flow / footprint** — built as a *confirmation feature* feeding Strategies 1 & 2. Needs trade-level (tick) data, not candles. Never run as a standalone tick-scalp system (you lose the latency race to HFT).

### Explicitly NOT building
- **Liquidation-cascade hunting** — slippage destroys the modeled edge exactly when you trade it; highest blowup risk.
- **Momentum-ignition / microstructure HFT** — latency-loser for retail + a compliance hazard (ignition/spoofing is prohibited).

---

## 4. Risk Framework (non-negotiable before live capital)

> **Capital decision:** Design around **~$10k** account (likely fund $5k+ early, scale on proof). Capital is a **config parameter**, not hardcoded — sizing scales automatically. Funding-carry (Strategy 3) skipped until capital > $15k.

**Sizing & leverage**
- Venue leverage cap set to **5x max**; *effective* leverage from risk-first sizing will usually be **1–2x**.
- At $10k: per-trade risk ~$50–75 (0.5–0.75%).
- Position size = `(equity × per-trade-risk%) / stop-distance%`.
- **Per-trade risk: 0.5–0.75% of equity.**
- **Isolated margin**, with liquidation price **≥ 5× the stop distance** away (a flash wick must never reach liquidation).
- Max total open notional ≤ 2× equity.

**Loss limits**
- **Daily: 3% of equity → auto-flatten + halt until next day.**
- Weekly: 6–8% → halt + manual review.
- Every position carries a resting on-exchange stop.

**Cost discipline**
- Maker (post-only) wherever possible. Require net edge > 2× round-trip cost.
- Avoid holding across funding stamps unless carry is favorable; flatten before thin windows.

**Collateral & counterparty**
- Collateral in **USDC** (not USDT — depeg risk).
- **Sweep profits weekly** to self-custody / bank.
- Cap exposure per venue (≤40% of trading capital on any single venue).

**Mandatory safety mechanisms (no live trading without ALL of these):**
1. Daily-loss auto-halt + flatten
2. Feed-staleness watchdog (halt on stale market data)
3. Heartbeat watchdog process (flatten if the bot dies)
4. Position reconciliation from the exchange as source of truth (never trust local state)
5. Idempotent orders (client order IDs)
6. Consecutive-error circuit breaker
7. Resting on-exchange stop for every position
8. API keys: **trade-only, withdrawals disabled, IP-whitelisted**
9. Manual "flatten-all + disable" reachable from phone

**Go-live ramp:**
`Paper / testnet ≥ 30 days → live at minimum size (~$500–1k risk capital) ≥ 30 days → scale into the $5k–25k band.`

---

## 5. Learning Plan (educators — selection deferred)

**Selected (decided):**
- **Primary — TradingRiot** — order-flow / footprint / volume-profile, crypto perps explicitly. Feeds the entry logic + CVD veto for the mean-reversion engine.
- **Primary — Trader Mayne** — crypto-native price action (S/R, demand blocks, liquidity sweeps). Where the reversal/extreme zones are.
- **Secondary — CanteringClark** — crypto-native, only source that explicitly covers perp mechanics (OI, funding, liquidations, crowd positioning). Light third for perp intuition.
- **Reserve — Adam Mancini** — ES futures, "failed breakdown" setup. Maps to the breakout engine (Strategy #2, built later). Not crypto.
- **Dropped — Axia Futures** — futures (not crypto) + DOM/price-ladder style is mostly *taker* execution, opposite our maker-first edge.
- **Avoid — ICT** — no verified track record.

> Plan: mine TradingRiot + Trader Mayne (+ CanteringClark) for documented rules, synthesize into the concrete signal logic for the mean-reversion engine first.

---

## 6. Open Decisions / Next Steps

- [x] ~~Choose 2–3 educators to study.~~ → TradingRiot (primary) + Trader Mayne (primary) + CanteringClark (secondary). See §5.
- [x] ~~Decide build vs deeper-study order.~~ → Learn educators BEFORE building code.
- [x] ~~Lock project name.~~ → **jCoin**.
- [x] ~~TradingRiot educator pipeline.~~ → Complete. 7 articles → 31 extractions → 4 concept pages.
- [x] ~~Trader Mayne pipeline.~~ → Complete. 5 videos → 21 items → `concept_regime_filter.md` (NEW) + `MAYNE_INTEGRATION.md`.
- [x] ~~Plan audit.~~ → `pipeline/AUDIT_2026-06-19.md` (11 findings).
- [x] ~~Data-availability gate.~~ → `pipeline/DATA_AVAILABILITY.md`. Liquidations NO-GO; OI/funding/CVD/candles OK.
- [x] ~~Lock v1 strategy.~~ → **Candle-only mean-reversion** (see §3 v1 block). ~8–10 params, no derivatives feeds.
- [x] ~~CanteringClark.~~ → **Dropped.** Light third; his edge was liquidations (now deprecated). Not worth the effort.
- [ ] Confirm state eligibility (Coinbase + Kraken) — Joel is in Ohio, both should be available but verify.
- [ ] **Source candle data** (Coinbase/Kraken historical OHLCV) for backtesting.
- [ ] **Backtest the regime filter standalone** — does range-labeled time mean-revert / trend-labeled time trend? Validates the whole thesis.
- [ ] Resolve open decisions: maker-vs-taker entry (§3 v1), scalp-vs-swing horizon, validate-before-live discipline.
- [ ] Scaffold repo + execution layer (venue-agnostic engine, one-engine-two-adapters, parity ledger, kill-switch stack).
