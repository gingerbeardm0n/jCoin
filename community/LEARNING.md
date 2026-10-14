# What we've learned from the community

Each entry: the takeaway, who said it, and whether it changes anything we do.

## 2026-10-13 — first replies (r/algotradingcrypto, 8 replies; raw text in replies_2026-10-13.md)

| Takeaway | Who | Changes for jCoin? |
|---|---|---|
| 4 losses in 4 trades at a 25% win rate happens ~30% of the time. Normal. | 3 separate people | No — confirms paper results aren't alarming |
| Write the kill rule now from the backtest (e.g. losing streak or drawdown past its 99th percentile) and never change it after | Huge_Position890, QuanTradin | **Yes** — TODO item, do before live |
| Expected streaks for ~60 trades/yr at 25%: longest losing run typically 10, 1-in-10 years 16, 1% of years 24 | Huge_Position890 (own simulation) | Use as kill-rule input; re-derive from our backtest |
| Paper needs 6-12 months at ~5 trades/month before it means much | 3 people | Sets expectations; nothing to build |
| Track things that accumulate faster than P&L: do live entries match what the backtest would do, and fill vs modelled price | Huge_Position890 | **Yes** — fits the "does this look right" check + parity ledger |
| Judge by average R per trade, not win rate | Huge_Position890 | Add avg-R to the paper summary |
| Test the backtest in ~5 separate time slices; trend systems can flip sign between periods | Huge_Position890 | **Yes** — cheap check, pre-June data only |
| Look at how funding behaved over time, not just the fee table | Huge_Position890 | Confirms TODO #1 (funding model) |
| BTC+ETH ≈ one bet. Trend needs a basket (e.g. top ~30 coins by market cap), equal-weighted | iSnake37, Hot_Heart_86, Huge_Position890 | **Big open question** — clashes with US venue (Coinbase lists few coins) and our alt results; see below |
| Use daily bars for trend; below daily, mean reversion dominates and costs bite | iSnake37 (also someone else uses 8h minimum) | Possible test, must use pre-June data only |
| Simplest version: MA crossover across the basket, equal weight, rebalance every few weeks, exit on opposite signal, no stops | iSnake37 | Interesting baseline to compare against |
| Do walk-forward + Monte Carlo before trusting anything; ~40 trades per tunable parameter | PepMar000 | Partly done; Monte Carlo not yet |
| Read Carver's "Leveraged Trading" (small accounts) and "Systematic Trading" | iSnake37 | Reading list |

Ignore / be careful: QuanTradin (promoting own site), Appropriate-Talk-735 ("PM me" — don't take trading DMs).

### The basket question
Strongest pushback was "two coins is pointless." Tension:
- Our own fresh-data replay: alts (IMX, SAND, AVAX, ADA…) lost money. But those were mid-caps picked with contaminated selection, on 4h bars, with tight stops — not a top-30 equal-weight daily basket.
- US venue: Coinbase US futures lists only a handful of coins. A basket might mean **spot, long-only** (Coinbase/Kraken spot list many coins), which also removes funding costs and leverage risk.
- A daily-bar, top-30, long-only spot basket is a genuinely different strategy. Worth one honest test on pre-2026-06 data before deciding anything.
