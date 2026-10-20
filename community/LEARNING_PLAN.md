# jCoin 4-week learning plan

**Goal:** be able to explain, in your own words, **who pays jCoin and why they'll keep paying**, and spot
which new ideas are worth testing. About 3–4 hours a week. Write short answers in `LEARNING_JOURNAL.md`
(create it) — a few sentences each is plenty. Bring anything confusing to Claude: "explain X using our trades".

---

## Your bot in 5 numbers (from the 2021–May 2026 backtest, 396 trades)

- **Wins only 18% of the time.** Losers usually end in **under a day**; winners run a median **~10 days**.
- **The best 10% of trades (39) made +486R. The other 90% lost −277R.** Net +209R.
- Longest losing streak: **18 trades in a row.**
- Biggest winners:

| Coin | Side | Entry | Exit | Days | Result |
|---|---|---|---|---|---|
| BTC | long | 2023-01-08 | 2023-01-14 | 5 | +43.3R |
| ETH | long | 2024-02-06 | 2024-02-26 | 20 | +27.9R |
| ETH | long | 2025-07-08 | 2025-07-22 | 13 | +25.8R |
| BTC | short | 2026-01-16 | 2026-02-05 | 20 | +24.3R |
| ETH | short | 2023-08-16 | 2023-08-18 | 1 | +21.5R |

- Typical losers: about −1 to −1.6R each (the stop doing its job).

("R" = one unit of planned risk. At $1,000 and 1% risk, 1R ≈ $10, so +43R ≈ +$430.)

---

## Week 1 — Where does trend-following profit come from?

**Read**
- Carver, *Leveraged Trading*: Part 1 (why most retail traders lose; costs) and the trend-following chapter.
- Clenow, *Following the Trend*: chapter 1 and the chapter on what a trend-following year feels like.

**Do (with our data)**
- Open a free TradingView chart (BTCUSD / ETHUSD, 4h). Look at each of the 5 biggest winners above.
  What was the market doing before entry? What news happened (search the dates)? Why did the move keep going?
- Pick 3 losers from 2021 (dates above). What did the market do right after the stop?

**Answer in your journal**
1. In one sentence: who is on the other side of a winning trend trade, and why are they wrong?
2. Why does a strategy that wins 18% of the time make money at all?
3. Why do losers end fast and winners last long — is that luck or design?

---

## Week 2 — Crypto market plumbing (perpetual futures)

**Read**
- How perpetual futures and **funding** work (search: "perpetual futures funding rate explained" — BitMEX's
  original perpetual explainer, or Kraken/Coinbase help pages on funding).
- What **basis**, **open interest**, and **liquidations** are; why prices differ between exchanges.
- Kaiko research blog: any post on **exchange liquidity / order-book depth** (search "Kaiko market depth").

**Do (with our data)**
- Read `pipeline/COINBASE_PARITY_2026-10.md`. Find the 2026-01-31 Coinbase spike (+2.8% above Binance) on a chart.
- Read `pipeline/A_HONEST_NUMBERS_2026-10.md`: funding cost ≈ 2.5% of profit. Longs paid, shorts got paid. Why?

**Answer**
4. When funding is positive, who pays whom, and what does that say about the crowd?
5. Why would a thin order book (Coinbase nano contracts) produce price spikes, and why do those hurt *stops* most?
6. Is there a way to profit *from* the crowd's leverage instead of being hurt by it?

---

## Week 3 — Costs, sizing, and small accounts

**Read**
- Carver, *Leveraged Trading*: chapters on position sizing, minimum account size, and trading costs.

**Do (with our data)**
- Read `pipeline/A_LO_SPOT_2026-10.md`: the same signals with spot fees (1% round trip) went from profitable
  to break-even. Work out roughly what one round trip costs in R when the stop is ~1.3% away.
- Read the contract-size table in `pipeline/VENUE_DECISION_2026-10.md`. With $1,000, how many contracts can
  you trade, and how close is that to 1% risk?

**Answer**
7. Why does a strategy with small stops suffer so much more from fees than one with wide stops?
8. What's the smallest account where this strategy is comfortable on Coinbase, and why?
9. Carver says breadth (many markets) matters for trend. Why did our 30-coin basket test still lose to BTC+ETH?

---

## Week 4 — Being honest with yourself (and what to test next)

**Read**
- Bailey, Borwein, López de Prado, Zhu, "Pseudo-Mathematics and Financial Charlatanism" (short, readable):
  https://www.davidhbailey.com/dhbpapers/overfitting.pdf
- Rob Carver blog: "The three kinds of (over)fitting" — https://qoppac.blogspot.com/2015/11/the-three-kinds-of-overfitting.html
- Skim `VALIDATION_RULES.md` (our looks log) — now it should make sense *why* we write rules first.

**Do**
- List **3 ideas** you now think could improve jCoin or be a different edge entirely. For each, write:
  who would pay you, why they'd keep paying, and what result would prove you wrong.

**Answer**
10. Why did the optimized config in June look amazing and then lose money on unseen data?
11. Of your 3 ideas, which is most likely to be real, and why?

**Then:** bring the 3 ideas to Claude. We'll write the best one's pass rule down first and test it honestly.

---

## Optional listening (commute/gym)
- *Flirting with Models* (Corey Hoffstein) — systematic investing, honest about what fails.
- *Top Traders Unplugged* — trend-following practitioners.
- *Chat With Traders* — individual traders' stories (good for intuition, less for rigor).
