# §8: A vs A_SR (spot-referenced stops, nano fills)

Protocol: `VALIDATION_RULES.md` §8, committed in `228de57` before this script existed.

## 1. Coinbase window 2025-08-08 → 2026-05-31 (12bp, no funding)

| Run | CAGR | Max DD | MAR | Sharpe | PF | Trades | avg R | Return |
|---|---|---|---|---|---|---|---|---|
| A on nano | -28.9% | 28.8% | -1.00 | -1.49 | 0.59 | 70 | -0.365 | -24.2% |
| A_SR (spot stops, nano fills) | 1.8% | 21.1% | 0.09 | 0.33 | 1.17 | 70 | +0.158 | +1.5% |
| A on Binance (report only) | 0.7% | 21.0% | 0.03 | 0.26 | 1.12 | 72 | +0.103 | +0.6% |
| A on Coinbase spot (report only) | 10.8% | 21.3% | 0.51 | 0.54 | 1.30 | 70 | +0.265 | +8.7% |

A_SR candidate trades in window (before the portfolio's 1/symbol, 2-concurrent caps): 100 spot stops, 6 nano disaster stops, 5 time exits. Candidates common to A-on-nano and A_SR (same entry bar/side): 93.

Largest per-trade differences (report only):

| Symbol | Entry | Side | A on nano R | A_SR R | A_SR exit |
|---|---|---|---|---|---|
| BTC | 2026-01-20 04:00 | short | +2.68 | +30.43 | stop |
| BTC | 2026-01-16 12:00 | short | +3.71 | +24.39 | time |
| ETH | 2026-01-20 04:00 | short | +14.81 | +23.74 | disaster |
| ETH | 2025-10-29 16:00 | short | -1.06 | +4.81 | stop |
| ETH | 2025-08-08 16:00 | long | -1.06 | +3.21 | stop |
| BTC | 2026-01-05 12:00 | long | -1.13 | -3.13 | disaster |
| BTC | 2025-08-19 12:00 | short | -1.11 | -3.12 | disaster |
| BTC | 2025-12-29 00:00 | long | -1.14 | -3.14 | disaster |
| ETH | 2025-12-01 00:00 | short | -1.06 | -3.03 | disaster |
| BTC | 2025-08-10 00:00 | long | +0.25 | -1.12 | stop |

## 2. Dev period 2021-01-01 → 2026-05-31 (12bp, no funding)

| Run | CAGR | Max DD | MAR | Sharpe | PF | Trades | avg R | Return |
|---|---|---|---|---|---|---|---|---|
| A on Binance (0x funding) | 35.6% | 26.0% | 1.37 | 1.00 | 1.65 | 396 | +0.562 | +419.3% |
| A on Coinbase spot | 30.1% | 30.5% | 0.99 | 0.89 | 1.55 | 402 | +0.478 | +315.0% |

## Decision (§8, both required)

1. A_SR Coinbase PF 1.17 ≥ 1.00 and > A on nano 0.59 → yes
2. Spot dev Sharpe 0.89 ≥ 0.90×1.00=0.90 and MAR 0.99 ≥ 0.90×1.37=1.23 → no

**Verdict: DO NOT ADOPT A_SR**

## Interpretation (written after the results; not part of the rule)

Note: rerunning the script rewrites everything above this section, but not this section itself.

1. **The spike mechanism is now supported.** Moving the stop trigger to spot restores the winners that nano
   clipped. BTC 2026-01-16 short goes from +3.7R to +24.4R, and BTC 2026-01-20 short from +2.7R to +30.4R.
   Window PF goes from 0.59 to 1.17, slightly above Binance's 1.12. The Coinbase venue problem lies in where
   the stop triggers, not in the signals.
2. **The nano disaster stop costs real money.** 6 of 111 candidate trades hit the resting nano stop 2 ATR out,
   each at about −3R. Those are thin-book spikes that would still fill a resting order.
3. **Condition 2 failed on the dev edge, not on the fix.** On Coinbase spot's own 2021–26 history, A makes
   30.1% CAGR, MAR 0.99, Sharpe 0.89 and PF 1.55. On Binance it makes 35.6%, 1.37, 1.00 and 1.65. The main gap
   is drawdown (30.5% vs 26.0%). Part of this is likely out-of-sample decay, because trail 6.0 was chosen on
   Binance data. That makes the spot numbers the more honest estimate of A on an independent price series:
   still positive, but weaker.
4. Per §8 A_SR is **not adopted**, and there is no sealed-window look. Lowering the bar now would be choosing
   the rule after seeing the result. Any follow-up needs a new dated rule, and it must disclose that it was
   written after this run.
5. Caveats: the test assumes the spot breach is caught instantly (live needs about 1-minute polling). The window
   has only 70 trades. The dev comparison covers signals on spot only; nano did not exist before 2025-07.
