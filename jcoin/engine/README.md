# jCoin Execution Engine

One engine, two adapters. The Strategy and TradingEngine run **identically** in
backtest, paper, and live — only the Broker (how fills happen) and the data clock differ.
This is the parity backbone (LESSONS_FROM_JTRADER.md #1): a passing backtest is a faithful
preview of live behavior because the deciding code is the same code.

## Modules

| File | Role |
|---|---|
| `types.py` | Value types: `Bar`, `EnterIntent`, `Position`, `Fill`, `ClosedTrade`, `Account`. |
| `features.py` | `compute_features()` — regime, ATR, confirmed swing levels, breakout flags. Deterministic + causal (no lookahead). Same function in backtest (run once) and live (run on trailing window). |
| `strategy.py` | `BreakoutStrategy` — pure logic: `entry_signal()` (trend-aligned breakout) + `manage_position()` (ATR chandelier trailing stop + timeout). |
| `risk.py` | Risk-based position sizing (`risk_frac` of equity per trade) + concurrency caps. |
| `broker.py` | `Broker` ABC + `BacktestBroker` (simulated fills). Paper/Live brokers slot in here. |
| `engine.py` | `TradingEngine.step(ts, rows)` — manage exits, then consider entries. The loop, identical everywhere. |
| `kill_switch.py` | Safety layer: daily-loss / max-drawdown / consecutive-loss / equity-floor halts. Pure, unit-tested. |

## Parity status — VALIDATED 2026-06-20

`python -m jcoin.research.run_engine_backtest` reproduces the validated portfolio backtest:

| | engine | target |
|---|---|---|
| trades | 450 | ~441 |
| final equity | $39,078 | $38,576 |
| CAGR | 28.4% | 28.1% |
| max DD | 27.1% | 27.1% |
| PF / Sharpe | 1.47 / 0.98 | 1.48 / 0.98 |

Tiny trade-count diff = slot-freeing order at coincident timestamps (engine exits-then-enters
within a bar — the canonical convention). Risk metrics identical. **Architecture proven.**

## Remaining before paper trading (next phase)

1. **PaperBroker / LiveBroker** (`broker.py`) — ccxt-backed: place orders on Coinbase/Kraken,
   read real fills + fees. Paper = real live data, simulated fills tracked in a virtual account.
2. **Live runner / data loop** — poll closed 4h bars as they finalize, build the `rows` dict,
   call `engine.step()`; persist account state across restarts.
3. **Wire the kill-switch** into the live runner (flatten-all + disable on hard halt; pause
   entries on soft halt) + heartbeat + exchange position reconciliation (§4 mandate).
4. **Run paper ≥30 days** → confirm live results track the backtest → tiny live → scale.

## Usage (backtest mode)

```bash
python -m jcoin.research.run_engine_backtest            # parity run
```
