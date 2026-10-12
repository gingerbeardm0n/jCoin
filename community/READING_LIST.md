# jCoin reading list (research sweep 2026-10-12)

Ten best items found across four questions, ranked by how much each one should change what we do.
Reddit blocks automated fetching, so Reddit threads were read via archives or search snippets.

## Read these first

1. **Rob Carver: "The three kinds of (over)fitting"**
   https://qoppac.blogspot.com/2015/11/the-three-kinds-of-overfitting.html
   - Any decision made after seeing test results is "implicit fitting". That's exactly what our ~1,000 test-window looks were.
   - His fix is the one we adopted: log every idea you try (our `VALIDATION_RULES.md` looks log) and use fresh data.

2. **Bailey, Borwein, López de Prado, Zhu: "Pseudo-Mathematics and Financial Charlatanism" (2014, peer-reviewed)**
   https://www.davidhbailey.com/dhbpapers/overfitting.pdf
   - With 5 years of daily data, trying more than ~45 variants is enough to produce a fake Sharpe of 1 that goes to 0 live.
   - Why our pre-September "validated" results can't be trusted.

3. **Wiecki et al. (Quantopian): "All that Glitters Is Not Gold" (2016)**
   https://quantpedia.com/quantopians-academic-paper-about-in-vs-out-of-sample-performance-of-trading-alg/
   - 888 real live algos: backtest Sharpe predicted live Sharpe with R² ≈ 0.02. The more backtests run, the worse.

4. **Rob Carver: "Diversification and small account size"**
   https://qoppac.blogspot.com/2016/03/diversification-and-small-account-size.html
   - Trend following earns its keep through breadth across many uncorrelated markets. BTC + ETH is roughly one bet.
   - Small accounts lose a lot to rounding whole contracts (about 20% of Sharpe at 1 contract). This matters for Coinbase nano contracts.

5. **r/algotrading: "US Crypto Perpetual Futures API" (2026-07-30)**
   https://www.reddit.com/r/algotrading/comments/1vbeqqm/
   - Someone with our exact problem. Kraken US issues spot and margin API keys only. Coinbase is the only US option people name, and they complain about fees.

## Worth reading

6. **r/algotrading: "Best crypto futures exchange" (2025-12-18)**
   https://www.reddit.com/r/algotrading/comments/1ppvpvq/
   - A US user says Coinbase futures was the only US way to short with leverage, and that funding on longs ran about 25% a year at times. Our backtests model zero funding.

7. **Zarattini, Pagani, Barbon: "Catching Crypto Trends" (Swiss Finance Institute, 2025)**
   https://concretumgroup.com/catching-crypto-trends-a-tactical-approach-for-bitcoin-and-altcoins/
   - Trend following on a rotating set of the top 20 coins showed a net Sharpe above 1.5 in backtest. The authors sell research, and the counter-study (item 9) disagrees.

8. **HackerNoon: "Your trading bot needs limits before it needs an edge" (2026-08)**
   https://hackernoon.com/your-trading-bot-needs-limits-before-it-needs-an-edge
   - A bot read an API error as "position = 0" and doubled up. Rule: an API error means "unknown", never "flat".

9. **Sun & Krištoufek: "Diversification among cryptoassets" (2021)**
   https://ies.fsv.cuni.cz/veda-vyzkum/working-papers/6476
   - Once you correct for survivorship bias, active multi-coin strategies mostly don't beat holding BTC.

10. **Quantpedia: "Revisiting Trend-following and Mean-reversion in Bitcoin" (2024)**
    https://quantpedia.com/revisiting-trend-following-and-mean-reversion-strategies-in-bitcoin/
    - Bitcoin trend rules kept working out of sample from 2022 to 2024 (daily data). It's thin evidence, but it is post-2022.

## Also useful
- Freqtrade stoploss-on-exchange docs: https://www.freqtrade.io/en/stable/stoploss/ (same design as our resting stop)
- Freqtrade supported exchanges: https://www.freqtrade.io/en/stable/exchanges/ (no Coinbase futures, so a custom bot is the realistic route)
- ccxt Coinbase futures bug #26218: https://github.com/ccxt/ccxt/issues/26218 (ccxt support for Coinbase futures has been shaky; use the official SDK)
- healthchecks.io: https://healthchecks.io/docs/ (the alert service we planned)
- Elite Trader, "When to stop a trading system": https://elitetrader.com/et/threads/when-to-stop-a-trading-system.371089/

## What this changes for jCoin
1. **Funding cost is a real gap.** Reports of ~25% a year on longs at times would eat a multi-day trend strategy. We need to model it before trusting any number.
2. **Coinbase is the venue, if any.** Use the official `coinbase-advanced-py` SDK, not ccxt. Expect complaints about fees and fills, and measure them with a tiny live test.
3. **Two coins is thin.** Breadth is what makes trend following work, but the US venue only lists a handful of coins. Any alt we add must be re-tested on fresh data only.
4. **Patience math.** Telling a Sharpe-1 strategy apart from luck takes about 4 years of results. Paper results alone won't validate this, so decide what level of evidence is good enough to risk $1-2k.
5. **Write the kill rule now**, before live: for example, stop if drawdown exceeds 1.5–2x the backtest's worst. Ten losses in a row is about a 6% event at a 25% win rate, so a streak alone shouldn't trigger it.
6. **Reconcile code check.** Confirm an exchange error never gets read as "no position".
