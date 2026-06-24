"""Execution engine — one engine, two adapters (backtest / live).

The Strategy and TradingEngine are IDENTICAL across backtest, paper, and live. Only
the Broker adapter (how fills happen) and the data clock differ. This is the parity
backbone (LESSONS_FROM_JTRADER.md #1): the code that decides and manages trades runs
unchanged everywhere, so a passing backtest is a faithful preview of live behavior.
"""
