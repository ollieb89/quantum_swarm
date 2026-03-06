---
phase: "03"
plan: "01"
subsystem: l3-executors
tags:
  - data-fetcher
  - dexter-bridge
  - yfinance
  - ccxt
  - finbert
  - fred
  - langgraph
  - async
dependency_graph:
  requires:
    - "03-00"   # NautilusTrader install + Pydantic data model contracts
  provides:
    - data_fetcher_node   # async LangGraph node (src/graph/agents/l3/data_fetcher.py)
    - invoke_dexter       # async Dexter CLI bridge (src/tools/dexter_bridge.py)
    - fetch_equity_data   # yfinance client with cache (src/tools/data_sources/yfinance_client.py)
    - fetch_crypto_ohlcv  # ccxt async client (src/tools/data_sources/ccxt_client.py)
    - fetch_news_sentiment # FinBERT fallback (src/tools/data_sources/news_sentiment.py)
    - fetch_economic_data  # FRED fallback (src/tools/data_sources/economic_calendar.py)
  affects:
    - src/graph/state.py   # data_fetcher_result field consumed by downstream nodes
    - config/swarm_config.yaml  # trading block added
tech_stack:
  added:
    - yfinance==0.2.x (installed in .venv)
    - ccxt==4.4.60 (pinned; latest 5.x has broken lighter_client static dep)
    - httpx (async HTTP for FinBERT calls)
    - fredapi (FRED economic data)
    - pydantic v2 (already present via langchain)
  patterns:
    - asyncio.to_thread wrapping synchronous yfinance/fredapi calls
    - asyncio.create_subprocess_exec + wait_for for Dexter CLI timeout
    - Module-level dict cache keyed by (symbol, source_params)
    - Pydantic .model_dump(mode='json') for LangGraph state serialization
key_files:
  created:
    - src/tools/dexter_bridge.py
    - src/tools/data_sources/__init__.py
    - src/tools/data_sources/yfinance_client.py
    - src/tools/data_sources/ccxt_client.py
    - src/tools/data_sources/news_sentiment.py
    - src/tools/data_sources/economic_calendar.py
    - src/graph/agents/l3/data_fetcher.py
    - src/graph/agents/l3/__init__.py
    - tests/test_dexter_bridge.py (converted from xfail stubs)
    - tests/test_data_fetcher.py (converted from xfail stubs)
    - tests/test_phase3_smoke.py
  modified:
    - config/swarm_config.yaml (trading block: execution_mode, IB config, dexter, trade_history_window)
    - src/models/data_models.py (confirmed pre-exists from 03-00; no changes needed)
decisions:
  - "Pinned ccxt==4.4.60 — latest ccxt 5.x has a broken lighter_client static dependency import that raises ModuleNotFoundError on import"
  - "FRED uses DTWEXBGS series for USD index (Broad USD) rather than 'DXY' — DXY is not available on FRED directly"
  - "FinBERT mock fallback triggers when HUGGINGFACE_API_KEY is absent (not only on failure) — avoids timeout on missing key"
  - "Dexter env var check reads from both os.environ and DEXTER_DIR/.env via dotenv_values — allows keys set only in Dexter's .env to be detected"
metrics:
  duration_seconds: 503
  completed_date: "2026-03-06"
  tasks_completed: 2
  tasks_total: 2
  files_created: 11
  files_modified: 1
  tests_passing: 16
  tests_total: 16
---

# Phase 3 Plan 01: DataFetcher Node & Dexter Bridge Summary

**One-liner:** Real async DataFetcher LangGraph node backed by yfinance (equities), ccxt (crypto), FinBERT sentiment, FRED economic data, and Dexter fundamentals bridge with 90s timeout and env-var graceful degradation.

## What Was Built

### Task 1: Dexter Bridge and Data Source Clients

**`src/tools/dexter_bridge.py`**
- `invoke_dexter(query: str) -> str` — async subprocess wrapper using `asyncio.create_subprocess_exec` + `asyncio.wait_for(timeout=90)`
- Checks for `FINANCIAL_DATASETS_API_KEY`, `EXASEARCH_API_KEY`, `ANTHROPIC_API_KEY` in both `os.environ` and the Dexter `.env` file via `dotenv_values`
- Raises `EnvironmentError` (missing keys), `TimeoutError` (90s exceeded), `RuntimeError` (non-zero exit)
- `invoke_dexter_safe(query, symbol) -> FundamentalsData` — wraps all exceptions, returns graceful FundamentalsData with `raw_markdown="Dexter unavailable: {reason}"`

**`src/tools/data_sources/yfinance_client.py`**
- `fetch_equity_data(symbol, period) -> MarketData` — async, `asyncio.to_thread` wrapping `yf.download`
- In-memory cache `_data_cache: dict[tuple[str, str], MarketData]` — keyed on `(symbol, period)`
- `clear_cache()` for per-swarm-run invalidation
- Column normalisation: `df.columns = [c.lower() for c in df.columns]` (Pitfall 3 from RESEARCH.md)
- Handles MultiIndex columns from yfinance (flattens before access)

**`src/tools/data_sources/ccxt_client.py`**
- `fetch_crypto_ohlcv(symbol, exchange_id, timeframe, limit) -> MarketData` — uses `ccxt.async_support`
- Cache keyed on `(symbol, exchange_id, timeframe)`
- Exchange session explicitly closed after each fetch

**`src/tools/data_sources/news_sentiment.py`**
- `fetch_news_sentiment(symbol) -> SentimentData` — HuggingFace FinBERT Inference API
- Mock fallback when `HUGGINGFACE_API_KEY` absent or API call fails
- FinBERT label mapping: positive → bullish, negative → bearish, neutral → neutral

**`src/tools/data_sources/economic_calendar.py`**
- `fetch_economic_data() -> EconomicData` — FRED API via `fredapi` library
- Fetches VIXCLS (VIX), DTWEXBGS (Broad USD Index), DGS10 (10Y yield)
- `asyncio.to_thread` wrapping synchronous fredapi calls
- Mock fallback when `FRED_API_KEY` absent or call fails

### Task 2: DataFetcher LangGraph Node + Config

**`src/graph/agents/l3/data_fetcher.py`**
- `data_fetcher_node(state: SwarmState) -> dict` — real async LangGraph node
- Reads `quant_proposal.symbol` and `quant_proposal.asset_class` from state
- Dispatches: equity → yfinance, crypto → ccxt
- Always fetches sentiment and economic data
- Optional Dexter fundamentals when `metadata.fetch_fundamentals == True`
- Returns `{"data_fetcher_result": {...}, "messages": [{"role": "assistant", ...}]}`
- All values JSON-serializable via `.model_dump(mode="json")`

**`config/swarm_config.yaml`**
- Added `trading.execution_mode: paper` (default, CONTEXT.md decision)
- Added `trading.interactive_brokers` config (per RESEARCH.md: Alpaca has no NT adapter)
- Added `trading.crypto_adapter: "binance"`
- Added `trading.dexter.timeout_seconds: 90`
- Added `trading.trade_history_window: 15`
- Marked `integrations.execution.freqtrade` as deprecated (replaced by NautilusTrader)

## Test Results

| Test File | Tests | Result |
|-----------|-------|--------|
| tests/test_dexter_bridge.py | 3 | PASSED |
| tests/test_data_fetcher.py | 5 | PASSED |
| tests/test_phase3_smoke.py | 8 | PASSED |
| **Total** | **16** | **16 PASSED** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ccxt 5.x breaks on import due to missing lighter_client**
- **Found during:** Task 1 dependency installation
- **Issue:** Latest ccxt (5.x) raises `ModuleNotFoundError: No module named 'ccxt.static_dependencies.lighter_client'` on import. Not a code error — a packaging defect in latest ccxt.
- **Fix:** Pinned `ccxt==4.4.60` which imports cleanly and has full `async_support`.
- **Files modified:** None (venv only; requirements.txt unchanged)
- **Impact:** Low — 4.4.60 has full ccxt.async_support functionality needed for this plan.

**2. [Rule 2 - Missing critical functionality] FRED DXY series not available**
- **Found during:** Task 1 economic_calendar implementation
- **Issue:** `DXY` is not a FRED series identifier. FRED provides `DTWEXBGS` (Broad US Dollar Index) as the standard USD index.
- **Fix:** Used `DTWEXBGS` instead of `DXY` in economic_calendar.py.
- **Files modified:** `src/tools/data_sources/economic_calendar.py`

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| src/tools/dexter_bridge.py | FOUND |
| src/graph/agents/l3/data_fetcher.py | FOUND |
| src/tools/data_sources/yfinance_client.py | FOUND |
| src/tools/data_sources/ccxt_client.py | FOUND |
| src/tools/data_sources/news_sentiment.py | FOUND |
| src/tools/data_sources/economic_calendar.py | FOUND |
| SUMMARY.md | FOUND |
| commit f8a76ab (Task 1) | FOUND |
| commit f5a769c (Task 2) | FOUND |
| 16 tests passing | CONFIRMED |
