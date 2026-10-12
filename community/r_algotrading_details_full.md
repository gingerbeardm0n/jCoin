# r/algotrading — FULL details (send to people who ask for more)

Notes for Joel before posting:
- r/algotrading rules: no self-promo, no links to paid stuff, be specific. This draft follows that.
- Flair: probably "Strategy" or "Infrastructure" (check what the sub offers that day).
- Posting the numbers is the point. People there respond to real data, and they are blunt. That's what we want.
- Edit anything that doesn't sound like you. The [brackets] are spots to check before posting.

---

**Title:** First crypto trend bot, hobbyist, ran an audit on my own setup and found I'd basically contaminated my test set ~1000 times.. looking for a sanity check before I put real money in

**Body:**

Hey all, long time lurker, first real post. I've been building a crypto trend-following bot for about 4 months as a side project (I'm a dev, not a quant, and I'll be upfront that I've built most of it with heavy AI help). I'm in the US (Ohio) and I'd like to eventually run it with something like $1-2k of real money, but I just did a full audit of the whole thing and I think I've been fooling myself in a couple of ways, so I'd really like some outside eyes before I go any further.

**The strategy (pretty plain):**
- BTC + ETH only, 4h candles
- Enter on a breakout past a prior swing high/low, only in the direction of the trend (simple swing-structure trend filter, sits out ranging markets)
- ATR initial stop (1.0x), ATR trailing stop (6.0x), no profit target
- 1% risk per trade, 0.75% when a long-term cycle filter says "bear"
- ~6 parameters total, I tried really hard not to over-optimize (an earlier optimizer run looked amazing in-sample and lost money out of sample, which was a good lesson)

**What the backtests said:** train 2021-23 / validate 2023-25 / test 2025-26, on Binance perp data, flat 12bp round-trip cost. BTC+ETH looked decent, profit factor somewhere around 1.3-1.5, ~25% win rate, wins come from a few big trend rides. [check: quote whichever numbers you're comfortable sharing]

**What the audit found (the embarrassing part):**
1. My "sealed" test window wasn't sealed at all. Between parameter sweeps and screening ~20 coins for which ones to add, I estimate 1000+ config-by-coin evaluations touched it. I was literally using test pass/fail to decide what to trade. The coins I added (XRP, HBAR, SAND, IMX etc.) mostly lost money when I re-ran them on fresh data.
2. Each coin only had ~50-60 trades in the test window, which I now think is way too few to tell PF 1.15 from 1.0 anyway.
3. No funding costs modeled at all (it's perps, holds for days).
4. The venue I'd built for (Kraken Futures) isn't actually available to US residents, which I somehow missed for months lol. The US Kraken perps product has no API as far as I can tell.

**What I've done since:**
- Cut back to BTC+ETH only
- Declared everything from 2026-06-01 onward a fresh holdout and I'm keeping a log of every time I look at it
- Clean replay on that window ($1k start, Jun 1 - Sep 18): BTC+ETH +$254 over 18 trades, 5 wins / 13 losses, max drawdown ~5%. But one ETH trade was 63% of the profit, so.. I don't really trust it either way
- Paper trading since Sep 18: 4 trades, 4 losses, about -1R each, account down ~4%. Which I think is normal for a 25% win rate system but it's hard to tell

**Where I'd love input:**
1. For a ~25% win rate trend system that only trades ~5 times a month, what's your actual rule for when to trust paper/live results, and what's your pre-set rule for when to kill it? I've read the "4+ years to tell Sharpe 1 from luck" math and honestly it's a bit deflating lol.
2. US folks shorting crypto via API: is Coinbase's US futures (nano BTC/ETH, Advanced Trade API) really the only realistic option? If you've run a bot on it, how bad were fees, fills, and funding in practice? I've seen people mention ~25%/yr funding on longs at times, which would eat a multi-day hold strategy alive.
3. Is trend following on just BTC+ETH reasonable, or does it only really work with breadth (Carver-style, lots of markets)? The US venues only list a handful of coins, so I'm kind of stuck there.

I'm aware this is a lot and I'm possibly overthinking parts of it, but I'd rather get roasted here than find out with real money. Thanks in advance, I'll stop rambling now.
