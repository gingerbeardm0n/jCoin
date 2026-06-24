# Crypto Educator Source List — Strategy-Extraction Pipeline

**Purpose:** Curated cornerstone teaching content feeding the jCoin mean-reversion (fade-the-extreme) perp bot strategy-extraction pipeline.
**Curated:** 2026-06-19. Cornerstone/"start here" content only — recurring market-recap content deliberately excluded.

**Extraction topic codes:** zone-definition · entry-trigger · CVD/order-flow · open-interest · funding · liquidations · volume-profile · trade-management/stops · risk-sizing

**Difficulty:** easy = blog text · medium = YT w/ captions · hard = X thread or audio

**Verification note:** `tradingriot.com` article pages return 404/403 to automated fetchers (bot protection), but every URL below appears consistently across independent search indexes and is treated as resolving. `blog.tradingriot.com` (Substack) archive was fetched successfully. Trader Mayne Bootcamp episode URLs verified via the official playlist. CanteringClark long-form is genuinely thin (see flag).

---

## 1. TradingRiot (Penko / Adam) — order flow, volume profile, CVD, perps

Two properties: **tradingriot.com** (long-form evergreen guides — preferred, dense clean text) and **blog.tradingriot.com** (Substack, more macro/concept essays). Ranked for mean-reversion signal value.

| # | Title | URL | Format | Length | Topics | Difficulty |
|---|-------|-----|--------|--------|--------|------------|
| 1 | Orderflow Trading: Delta vs Liquidity — Complete Strategy & Indicators Guide | https://tradingriot.com/orderflow-trading | blog-post | long (~5k+ words) | CVD/order-flow, entry-trigger, liquidations, trade-management/stops | easy |
| 2 | Trading with Volume Profile: Everything You Need to Know | https://tradingriot.com/volume-profile/ | blog-post | long | volume-profile, zone-definition, entry-trigger | easy |
| 3 | Understanding Liquidity in Trading — Is Someone Hunting Your Stops? | https://tradingriot.com/liquidity-in-trading/ | blog-post | long | liquidations, entry-trigger, trade-management/stops | easy |
| 4 | Understanding Volume Analysis in Trading — Complete Guide | https://tradingriot.com/volume-trading-analysis/ | blog-post | long | CVD/order-flow, volume-profile | easy |
| 5 | Auction Market Theory | https://blog.tradingriot.com/p/auction-market-theory | blog-post | medium-long | volume-profile, zone-definition | easy |
| 6 | How To Trade Cryptocurrencies | https://blog.tradingriot.com/p/how-to-trade-cryptocurrencies | blog-post | medium | funding, open-interest, CVD/order-flow, risk-sizing | easy |
| 7 | When Bitcoin Bottoms | https://blog.tradingriot.com/p/when-bitcoin-bottoms | blog-post | medium | open-interest, funding, liquidations | easy |
| 8 | The Empirical Evidence for Technical Analysis | https://blog.tradingriot.com/p/the-empirical-evidence-for-technical | blog-post | medium | risk-sizing (mental model / edge validation) | easy |
| 9 | Tradingriot Bootcamp Flow (free overview / module map) | https://tradingriot.com/tradingriot-bootcamp-flow/ | blog-post | short | index of order-flow, volume-profile, perps modules | easy |

**Notes:** #1–#4 are the load-bearing cornerstones for a fade strategy — delta/CVD exhaustion, value-area edges, and stop-hunt liquidity are exactly the mean-reversion triggers. #5 (Auction Market Theory) supplies the conceptual frame (price rejecting away from value → revert to value). Substack also carries options/earnings essays — excluded as off-domain.

---

## 2. Trader Mayne (John Gregory) — crypto price action, S/R, demand/supply zones, liquidity sweeps

Channel: https://www.youtube.com/@TraderMayne · Site: https://www.tradermayne.com/home · X: https://x.com/Tradermayne
The **Trader Mayne Trading Bootcamp** playlist is the canonical "start here": https://www.youtube.com/playlist?list=PLKItFyoma4GeQSNjY7LM5qtEgTFUidxYI

| # | Title | URL | Format | Length | Topics | Difficulty |
|---|-------|-----|--------|--------|--------|------------|
| 1 | The Real Reason Smart Money Traders Use Liquidity Sweeps | https://www.youtube.com/watch?v=8lhYu10v0NQ | youtube-video | ~15-25 min | liquidations, entry-trigger, zone-definition | medium |
| 2 | Equal High & Equal Low Liquidity — Bootcamp Ep.6 | https://www.youtube.com/watch?v=-UIrmQ3y0nI | youtube-video | ~15-25 min | liquidations, entry-trigger | medium |
| 3 | Market Structure: The Skill That Separates Winners — Bootcamp Ep.2 | https://www.youtube.com/watch?v=YxMMov8roBQ | youtube-video | ~15-25 min | zone-definition, entry-trigger | medium |
| 4 | How To Trade Market Structure Like a Pro | https://www.youtube.com/watch?v=jt5ncnNoCTQ | youtube-video | ~15-30 min | zone-definition, entry-trigger, trade-management/stops | medium |
| 5 | How Smart Money Traders Use Order Blocks To Enter Perfectly | https://www.youtube.com/watch?v=NSTmMdnQg7Y | youtube-video | ~15-25 min | zone-definition, entry-trigger | medium |
| 6 | Trend Liquidity — Bootcamp Ep.7 | https://www.youtube.com/watch?v=qErVtn3NBbQ | youtube-video | ~15-25 min | liquidations, trade-management/stops | medium |
| 7 | Bootcamp Ep.1 — ICT / Smart Money Concepts for Beginners | (via Bootcamp playlist, link above) | youtube-video | ~20 min | zone-definition (foundations) | medium |
| 8 | Bootcamp Ep.3 — Liquidity (what it is / where it sits) | (via Bootcamp playlist, link above) | youtube-video | ~20 min | liquidations, zone-definition | medium |
| 9 | Price Action Trading & Intro to Demand Blocks (Crypto Entrepreneurs pod) | https://creators.spotify.com/pod/profile/cryptoentrepreneurs/episodes/Price-Action-Trading-and-an-Introduction-to-Demand-Blocks-with-Trader-Mayne-e93fl6 | podcast | ~45-60 min | zone-definition, entry-trigger | hard |
| 10 | Highlights (curated educational threads) | https://x.com/Tradermayne/highlights | x-thread | varies | zone-definition, entry-trigger | hard |

**Notes:** Liquidity-sweep + equal-high/low content (#1, #2) is the single highest-value cluster for a fade strategy — sweep-and-reclaim IS the mean-reversion entry. Captions present → medium difficulty; prefer caption scrape over Whisper. Episode IDs for #7/#8 to be pulled from the playlist on ingest.

---

## 3. CanteringClark (Ryan) — perp mechanics: OI, funding, liquidations, crowd positioning

Linktree: https://linktr.ee/canteringclark · X: https://x.com/canteringclark · Substack: https://blockroots.substack.com · Co-founder of Blockroots.
**⚠ THIN FREE STRUCTURED CONTENT — see flag at bottom.** Most teaching is live X Spaces, streams, and X threads (ephemeral / hard to scrape). Long-form is the numbered "Crypto Market Insights" Substack series (recurring market recaps, not evergreen lessons) — only the conceptually-dense early volumes are worth extracting.

| # | Title | URL | Format | Length | Topics | Difficulty |
|---|-------|-----|--------|--------|--------|------------|
| 1 | Crypto Market Insights — Vol. 1 (basis, funding, contango/backwardation, vol compression) | https://blockroots.substack.com/p/crypto-market-insights-vol-1 | blog-post | medium | funding, open-interest | easy |
| 2 | Crypto Market Insights — Vol. 12 (CVD, running delta) | https://blockroots.substack.com/p/crypto-market-insights-vol-12 | blog-post | medium | CVD/order-flow, open-interest | easy |
| 3 | Crypto Market Insights — Vol. 2 | https://blockroots.substack.com/p/crypto-market-insights-vol-2 | blog-post | medium | funding, open-interest, liquidations | easy |
| 4 | Crypto Market Insights — Vol. 23 (crowding / offside / poor positioning) | https://blockroots.substack.com/p/crypto-market-insights-vol23 | blog-post | medium | open-interest, funding, liquidations | easy |
| 5 | Market Meditations #15 — Crypto Trading: Lessons from a Market Veteran | https://www.buzzsprout.com/1280444/episodes/5871679-15-cantering-clark-crypto-trading-through-the-eyes-of-a-market-veteran | podcast | ~45-60 min | open-interest, funding, risk-sizing | hard |
| 6 | blocmates — Cantering Clark on Life and Trading (order flow / discipline) | https://creators.spotify.com/pod/profile/blocmates/episodes/Cantering-Clark-on-Life-and-Trading--Crypto-vs-Traditional-Markets--Trading-Psychology-e23onrh | podcast | ~60 min | CVD/order-flow, risk-sizing | hard |
| 7 | blocmates — Interview: Discipline in Trading Equals Freedom | https://www.youtube.com/watch?v=-nPgMVqgOOE | youtube-video | ~60 min | open-interest, funding, risk-sizing | medium |
| 8 | Cantering Clark Stream Summaries (3rd-party notes, e.g. 17bidding) | https://medium.com/@17Bidding/cantering-clark-6-14-stream-summary-48db6a7ded31 | blog-post | short | open-interest, funding, liquidations | easy |

**Notes:** For mean-reversion, CanteringClark's positioning/crowding framework (Vol.23, Vol.1) is the most relevant — "extreme funding + crowded OI → fade the unwind" maps directly onto the bot's thesis. But signal is diluted across recap volumes; ingest selectively, don't crawl all 23+. Podcasts (#5, #6) carry his richest mental models but require audio transcription.

---

## Cross-educator summary

- **TradingRiot** = best signal-to-effort: dense, free, written, on-topic. Primary source.
- **Trader Mayne** = best for entry-trigger / zone mechanics (sweep-and-reclaim). Captioned video.
- **CanteringClark** = best conceptual fit (crowd-positioning fade) but thinnest/hardest free content; lean on Substack early vols + podcast transcripts.
