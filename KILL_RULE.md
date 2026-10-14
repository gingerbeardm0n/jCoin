# jCoin: Kill Rule for Strategy A

**Fixed on 2026-10-14. Do not edit the numbers after seeing live or paper results.**
If the rule is ever changed, the change is a new dated document, and the reason is written
down first.

Applies to: strategy A (BTC+ETH, 4h breakout, 1% risk per trade), in paper or live.

## The rule

Stop trading A if **either** of these happens:

1. **Drawdown breach:** account equity falls more than **39.8%** below its highest point
   since the paper/live clock started.
2. **Losing-streak breach:** more than **33** closed trades in a row finish at R <= 0
   (the 34th consecutive non-winner trips it).

## Where the numbers come from

`pipeline/A_HONEST_NUMBERS_2026-10.md`, section 4. A's 396 dev-period trades (2021-01-01 to
2026-05-31, Binance funding at 1x, 12bp costs) were resampled 10,000 times into one-year
paths of 73 trades, compounded at 1% risk per trade (seed 20261014). The thresholds are the
**99th percentiles**: only about 1 in 100 ordinary-bad-luck years should breach either
one. For reference, the 95th percentiles are 32.8% and 26 trades, and the median
year has an 18.7% drawdown and a 14-trade losing streak.

Caveat: resampling treats trades as independent, which understates real-life clustering
of losses. A breach is therefore a strong signal that something is wrong (the strategy,
the data, the market regime, or the code), but a pass does not prove A is fine.

## How it is measured

- **Drawdown:** (peak equity - current equity) / peak equity, using mark-to-market account
  equity (closed P&L plus open positions), peak taken since the clock start date. Checked
  at least once per 4h bar.
- **Streak:** count consecutive closed trades, in exit order, with R <= 0. Any trade with
  R > 0 resets the count to zero. Open trades do not count until they close.
- **Clock start:** the date A is (re)deployed to paper or live. Resetting paper equity
  restarts the clock. A new deployment gets a new clock; thresholds stay the same.

## What "stop" means

1. **Flatten:** close all open positions at market (paper: simulated close).
2. **Latch:** write the halt latch so the runner refuses to place any new order, even
   after a restart. No automatic resume, no cooldown timer.
3. **Human review:** Joel reviews the trade log, data feed and code before anything
   restarts. Restarting is a written, dated decision, not a flag flip, and the
   thresholds above do not move to make a restart easier.

## Implementation (wired 2026-10-14)

- `KillSwitchConfig.max_dd_pct` and `max_losing_streak` (jcoin/engine/kill_switch.py). The
  engine/backtest defaults are unchanged (0.25 and 0 = off); the LIVE runners
  (`run_paper.py`, `run_kraken.py`, `scripts/task_runner.pyw`, `run_paper_live.ps1`)
  default to `--max-dd-pct 0.398 --max-losing-streak 33`, so laptop and VM match.
- The streak counts closed trades by net R (after costs and funding), in exit order;
  `KillSwitchState.nonwin_streak` is persisted in state.json. The trade that makes it 34
  trips the halt immediately and the runner flattens in the same step.
- A hard halt flattens every position, sets `hard_halted` (persisted), and writes
  `KILLSWITCH_HALT.latch` into the state dir. While that file exists `run_paper` and
  `run_kraken` exit with code 5 before touching anything, and `reset_equity()` raises.
- **Restart = human action:** review, write the dated decision, delete
  `KILLSWITCH_HALT.latch`, then run once with `--reset-equity <amount>` (new clock).
  Deleting the latch alone does nothing useful: the persisted `hard_halted` flag
  re-latches on the next bar. The thresholds do not change.
- Mark-to-market caveat: paper `account.equity` is realized P&L only (open positions are
  not marked), so the paper drawdown check lags open-trade losses until they close.

Paper P&L also now accrues Kraken perp funding (jcoin/live/funding.py); it is part of
each trade's R, so it feeds this rule.
