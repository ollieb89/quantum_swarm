---
phase: "03"
plan: "02"
subsystem: l3-executors
tags:
  - backtester
  - nautilus-trader
  - backtest-engine
  - yfinance
  - bar-data-wrangler
  - asyncio-to-thread
  - langgraph
  - tdd
dependency_graph:
  requires:
    - "03-01"  # DataFetcher node + NautilusTrader install verified
  provides:
    - backtester_node      # async LangGraph node (src/graph/agents/l3/backtester.py)
    - _run_nautilus_backtest  # sync worker (called via asyncio.to_thread)
  affects:
    - src/graph/state.py   # backtest_result field consumed by downstream nodes
tech_stack:
  added: []
  patterns:
    - asyncio.to_thread wrapping synchronous BacktestEngine.run()
    - Deferred NautilusTrader imports inside _run_nautilus_backtest function body
    - _extract_backtest_metrics helper for plain-Python dict extraction (no NT objects)
    - Fallback dict with fallback=True on any engine failure
key_files:
  created:
    - src/graph/agents/l3/backtester.py
  modified:
    - tests/test_backtester.py (converted from 3 xfail stubs to 5 real tests)
decisions:
  - "NT 1.223.0 Equity constructor uses raw_symbol (not symbol) and requires ts_event/ts_init — RESEARCH.md documented the old API; corrected in implementation and tests"
  - "NautilusTrader imports deferred inside _run_nautilus_backtest body — module remains importable even if NT has install issues"
  - "BacktestEngine metrics extracted from result.stats_returns['Sharpe Ratio (252 days)'] and result.stats_pnls[ccy] — safe_float() normalises nan/inf to 0.0 for JSON safety"
  - "LoggingConfig(log_level='OFF', bypass_logging=True) used in BacktestEngineConfig to suppress NT banner during tests"
metrics:
  duration_seconds: 480
  completed_date: "2026-03-06"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 1
  tests_passing: 5
  tests_total: 5
---

# Phase 3 Plan 02: NautilusTrader Backtester Node Summary

**One-liner:** Real NautilusTrader BacktestEngine LangGraph node with asyncio.to_thread wrapping, yfinance BarDataWrangler pipeline, plain-dict metric extraction, and fallback path on engine failure.

## What Was Built

### Task 1: Implement NautilusTrader backtester node (TDD)

**`src/graph/agents/l3/backtester.py`**

**`async def backtester_node(state: SwarmState) -> dict`** — LangGraph async node:
- Reads `quant_proposal.symbol` (default "AAPL") and `quant_proposal.strategy` from state
- Calls `await asyncio.to_thread(_run_nautilus_backtest, symbol, strategy)` — never blocks event loop
- On any exception from `asyncio.to_thread`, catches and returns structured fallback dict with `fallback=True` and `error=str(e)`
- Returns `{"backtest_result": dict, "messages": [{"role": "assistant", ...}]}`

**`def _run_nautilus_backtest(symbol: str, strategy: dict) -> dict`** — sync NT worker:
- Fetches 6 months daily OHLCV from `yf.download(symbol, period="6mo", interval="1d", auto_adjust=True)`
- Lowercases DataFrame columns: `df.columns = [c.lower() for c in df.columns]` (Pitfall 3 prevention)
- Handles yfinance MultiIndex columns (flattens to single level)
- Builds `Equity` instrument with NT 1.223.0 API (`raw_symbol`, `ts_event`, `ts_init`)
- Processes bars with `BarDataWrangler.process(df)`
- Creates `BacktestEngine` with `LoggingConfig(bypass_logging=True)` (silent output)
- Adds venue (SIM, CASH, $100k), instrument, and data; calls `engine.run()`
- Extracts metrics via `_extract_backtest_metrics(engine)`, calls `engine.dispose()`

**`def _extract_backtest_metrics(engine, period_days) -> dict`**:
- Reads `result.stats_returns["Sharpe Ratio (252 days)"]` for sharpe
- Reads `result.stats_pnls[first_currency]["PnL% (total)"]` for total_return
- Reads `result.stats_pnls[first_currency]["Win Rate"]` for win_rate
- Uses `safe_float()` helper: NautilusTrader Decimal/nan/inf → Python float (default 0.0)
- Returns plain Python dict (sharpe_ratio, total_return, max_drawdown, total_trades, win_rate, period_days)

**`def _build_equity_instrument(symbol, venue_name) -> Equity`**:
- Uses NT 1.223.0 constructor: `raw_symbol=Symbol(symbol)`, `ts_event=0`, `ts_init=0`
- Note: old RESEARCH.md pattern used `symbol=`, `venue=`, `size_precision=`, `size_increment=` — not valid in 1.223.0

## Test Results

| Test File | Tests | Result |
|-----------|-------|--------|
| tests/test_backtester.py | 5 | PASSED |
| Full suite | 32 passed, 6 xfailed | PASSED |

### Tests Implemented

| Test | What It Verifies |
|------|-----------------|
| test_backtester_node_returns_sharpe | Mocked to_thread → result["backtest_result"]["sharpe_ratio"] == 1.5 |
| test_bar_data_wrangler_processes_dataframe | UPPERCASE→lowercase, 10-row DataFrame → non-empty bar list |
| test_backtester_result_is_json_serializable | json.dumps(result["backtest_result"]) does not raise |
| test_asyncio_to_thread_used | asyncio.to_thread called exactly once with a callable |
| test_backtester_fallback | RuntimeError from to_thread → {fallback: True, error: ..., sharpe_ratio: 0.0} |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RESEARCH.md Equity constructor uses pre-1.220 API**
- **Found during:** Task 1 GREEN implementation
- **Issue:** RESEARCH.md Pattern 2 documented `Equity(symbol=Symbol(…), venue=Venue(…), size_precision=0, size_increment=Quantity(1,0), …)`. In NT 1.223.0 the constructor signature is `Equity(raw_symbol=Symbol(…), ts_event=int, ts_init=int, …)` — the old kwargs raise `TypeError: unexpected keyword argument 'symbol'`.
- **Fix:** Used correct NT 1.223.0 constructor in both `_build_equity_instrument` (implementation) and `test_bar_data_wrangler_processes_dataframe` (test). The test originally used the RESEARCH.md pattern and was fixed after the first failing run.
- **Files modified:** `src/graph/agents/l3/backtester.py`, `tests/test_backtester.py`
- **Commit:** ca87089

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| src/graph/agents/l3/backtester.py | FOUND |
| tests/test_backtester.py (5 tests) | FOUND |
| commit fe95620 (RED — failing tests) | FOUND |
| commit ca87089 (GREEN — implementation) | FOUND |
| 5/5 backtester tests passing | CONFIRMED |
| 32 total tests passing | CONFIRMED |
| python -c "from src.graph.agents.l3.backtester import backtester_node; print('ok')" | ok |
| json.dumps(backtest_result) does not raise | CONFIRMED |
