---
phase: 03-l3-executors-nautilus-trader-integration
plan: "02"
subsystem: backtester
tags: [nautilus_trader, backtest, langgraph, yfinance]

requires:
  - phase: 03-l3-executors-nautilus-trader-integration
    plan: "01"
    provides: DataFetcher and Dexter bridge foundations

provides:
  - src/graph/agents/l3/backtester.py: NautilusTrader BacktestEngine LangGraph node
  - Full NautilusTrader integration for event-driven backtesting of quant proposals

affects:
  - src/graph/orchestrator.py: (Future) Will be wired to use this node
  - src/graph/agents/l2/adversarial_debate.py: (Future) Will consume backtest signal

tech-stack:
  added:
    - nautilus-trader==1.224.0 (installed via uv)
    - pyarrow==23.0.1
  patterns:
    - BacktestEngine.run() wrapped in asyncio.to_thread() to prevent event loop blocking
    - Manual column lowercasing for yfinance DataFrames before NT wrangling
    - Explicit casting of NautilusTrader Decimal types to Python float/int for JSON serializability
    - Graceful fallback to zeroed metrics on engine failure

key-files:
  modified:
    - src/graph/agents/l3/backtester.py

key-decisions:
  - "Pinned NautilusTrader to 1.223.0/1.224.0 (NT 1.223+ requires Python 3.12+)."
  - "Standardized on 'uv' for environment management to ensure correct dependency resolution between NT, pyarrow, and fredapi."
  - "Suppressed NautilusTrader internal logging in the backtest engine to keep LangGraph output clean."

duration: 20min
completed: 2026-03-06
---

# Phase 03 Plan 02: Backtester Implementation & NautilusTrader Integration Summary

**Replaced the stub Backtester with a real NautilusTrader-backed event-driven backtesting engine node.**

## Performance
- **Duration:** 20 min
- **Tasks:** 1
- **Files modified:** 1
- **Tests passing:** 21 (5 backtest tests + 5 data fetcher tests + 3 dexter tests + 8 smoke tests)

## Accomplishments
- **Nautilus Integration:** Successfully installed and integrated `nautilus_trader` into the L3 executor layer.
- **Backtester Node:** Implemented `backtester_node` in `src/graph/agents/l3/backtester.py` as an async LangGraph node.
- **Async Safety:** Wrapped the synchronous `engine.run()` in `asyncio.to_thread` to ensure the orchestrator remains responsive.
- **Data Wrangling:** Implemented a robust data pipeline that fetches `yfinance` data, normalizes columns, and wrangles them into NT `Bar` objects.
- **Metric Extraction:** Created a serialization-safe extraction layer that converts complex NT objects into plain Python dictionaries.

## Next Steps
- **Plan 03-03:** Implement the Order Router node for trade execution.
- **Integration:** Wire the `backtester_node` into the LangGraph to provide empirical signal for the adversarial debate.
