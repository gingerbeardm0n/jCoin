# Venue decision — 2026-10-18

Question: where can strategy A (BTC+ETH 4h breakout, **long and short**, multi-day holds, ~5 trades/month)
run unattended, US-legal, with a $1–2k account at ~1% risk per trade?
Spot long-only is ruled out (§6 test failed: shorts carry the strategy, spot fees ~8× too high).

## Recommendation: Coinbase US perpetual-style nano futures (BIP = 0.01 BTC, ETP = 0.1 ETH)

## Side by side

| | **Coinbase nano perps** | **CME micros via IBKR** |
|---|---|---|
| BTC contract that fits $1–2k | BIP 0.01 BTC (~$810) | QBTC spot-quoted 0.01 BTC (~$820); MBT 0.1 BTC is far too big |
| ETH contract | ETP 0.1 ETH (~$237) | MET 0.1 ETH (~$240) |
| Round-trip fees | BTC ~$0.30 (0.04%), ETH ~$0.30 (0.13%) (fee tier partly unverified; worst case 0.10% / 0.17%) | QBTC $0.92 (0.11%), MET $0.62 (0.26%) |
| Holding cost | Hourly funding (Binance history: ~2.5% of gross profit) | No funding; roll/basis ~3–5%/yr; spot-quoted has daily financing adjustment |
| Hours | ~24/7 (1h Friday break, occasional Saturday maintenance) | Micros 24/7 since 2026-05-29; spot-quoted still 5 days/week |
| API for a bot | REST (Advanced Trade API) with a key; official Python SDK | Java IB Gateway must run 24/7; **human 2FA login every week**; ~1GB RAM (too much for the e2-micro) |
| Resting stop | Stop-**limit** only at the exchange (can be gapped through) | IBKR-simulated stops on IBKR servers, regular hours only unless flagged |
| Margin per contract (overnight) | BTC $170 long / $208 short; ETH $57 / $72 | MET ~$115; QBTC ~$100+ (unverified) |
| Paper sandbox | None (our own paper sim covers it) | IBKR paper account (yes) |
| Data | Free public candles (~15 months of 4h) | ~$1.55+/month CME data |

**Why Coinbase:** cheaper per trade for our contract sizes, no weekly human login (dealbreaker for an unattended bot),
light enough for the free server, 24/7, contract sizes fit $1k (BTC: 1 contract ≈ 1.1% risk at the median stop;
ETH: 2 contracts ≈ 0.9%). Funding was already measured as small.

## Risks to manage (Coinbase)
1. **Stop-limit only** — a fast gap can jump the limit and leave the position open. Mitigation: set the limit well
   beyond the trigger (e.g. 3% past it) and have the bot check every hour that a stop exists and the position is
   still within its stop; if not, close at market (the existing stop-failure → flatten → latch path).
2. **4pm ET overnight margin jump** (≈10% → 21–30% of notional) — Coinbase's own #1 cause of surprise
   liquidations. At our sizing (≈1.3× notional on $1k across both coins) overnight margin ≈ $300 of $1,000: OK,
   but the bot should check available margin before entries and keep ≥50% of the account free.
3. **No sandbox** — first live step is a single tiny order placed and cancelled by hand-approved script.
4. **Funding history not downloadable** — keep Binance funding as the backtest proxy; record live funding as it accrues.
5. **SDK bug** — `get_futures_position` crashes with no open position (issue #108); wrap or use list endpoint.
6. **Short history (≈15 months of 4h candles)** — use it for a price/signal parity check vs the Binance data we backtest on.

## Not chosen and why
- **CME via IBKR:** weekly 2FA re-login breaks unattended running; gateway too heavy for the free server;
  ETH micro fees ~2× Coinbase. Revisit only if Coinbase becomes unavailable.
- **Kraken Derivatives US:** no trading API. **Offshore perps / Hyperliquid:** not US-legal for Joel (no VPN rule).

## Next steps
1. **Joel:** in Coinbase, enable US derivatives/futures (eligibility questionnaire). Fund nothing yet.
2. **Claude:** parity check — Coinbase BIP/ETP 4h candles vs Binance for the overlapping ~15 months
   (do the breakout signals agree?). Log in the Looks Log (signal comparison only, not selection).
3. **Claude:** Coinbase broker adapter (official SDK, not ccxt): place/cancel, stop-limit with wide limit,
   position + margin checks, funding recorded. Paper path unchanged.
4. **Then:** one tiny live order, placed and cancelled, before any real trading — and the paper clock keeps running.
