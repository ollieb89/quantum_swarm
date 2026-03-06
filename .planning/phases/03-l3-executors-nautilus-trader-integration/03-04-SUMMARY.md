---
phase: 03-l3-executors-nautilus-trader-integration
plan: "04"
subsystem: L3 Stateless Executors / Self-Improvement Loop
tags:
  - trade-logger
  - swarm-state
  - orchestrator-wiring
  - self-improvement
  - feedback-loop
dependency_graph:
  requires:
    - 03-03 (OrderRouter node)
    - 03-02 (Backtester node)
    - 03-01 (DataFetcher node)
    - 03-00 (Data models, TradeRecord Pydantic model)
  provides:
    - trade_logger_node (LangGraph node, synchronous)
    - get_recent_trades helper (sliding window N=15)
    - Full orchestrator chain: risk_manager→data_fetcher→backtester→order_router→trade_logger→synthesize
    - Self-improvement loop: trade_history fed back to L2 researchers on every invocation
  affects:
    - src/graph/orchestrator.py (L3 chain wiring, LangGraphOrchestrator YAML config loading)
    - src/graph/agents/researchers.py (trade_history context injection)
    - src/graph/state.py (Phase 3 state fields added)
tech_stack:
  added:
    - pyyaml (yaml.safe_load for swarm_config.yaml in LangGraphOrchestrator.__init__)
  patterns:
    - LangGraph operator.add reducer — list-append semantics for trade_history accumulation
    - Read-time sliding window (trim at read, accumulate unbounded) for trade_history[-15:]
    - patch.object pattern for mocking orchestrator module-level functions in integration tests
    - asyncio.run(graph.ainvoke(...)) for e2e tests with async L3 nodes
key_files:
  created:
    - src/graph/agents/l3/trade_logger.py
  modified:
    - src/graph/state.py
    - src/graph/orchestrator.py
    - src/graph/agents/researchers.py
    - tests/test_trade_logger.py
    - tests/test_l3_integration.py
decisions:
  - "List-wrapped TradeRecord ([record_dict] not record_dict) required for operator.add reducer to append rather than replace trade_history"
  - "patch.object(orch_module, ...) required for integration test mocking — not patch('src.graph.orchestrator.X', ...) — because patch.object affects the actual module attribute at graph compile time"
  - "asyncio.run(graph.ainvoke()) used in e2e test (not graph.invoke()) because L3 nodes (data_fetcher, backtester, order_router) are async coroutines"
  - "YAML config merged into orchestrator config at LangGraphOrchestrator.__init__ so create_orchestrator_graph has access to intent_patterns for classify_intent"
metrics:
  duration: 10min
  completed: "2026-03-06"
  tasks: 2
  files: 5
---

# Phase 3 Plan 04: TradeLogger, Orchestrator Wiring, and Self-Improvement Loop Summary

One-liner: TradeLogger node appends Pydantic-serialized TradeRecord to operator.add reducer in SwarmState, orchestrator wired with full L3 chain (risk_manager→data_fetcher→backtester→order_router→trade_logger→synthesize), and L2 researchers inject sliding-window trade_history as context for self-improvement.

## What Was Built

### Task 1: TradeLogger Node and SwarmState Phase 3 Fields

**src/graph/agents/l3/trade_logger.py** — New synchronous LangGraph node:
- `trade_logger_node(state)` reads `quant_proposal` + `execution_result`, constructs `TradeRecord` (Pydantic v2), serializes via `model_dump(mode="json")`, returns `{"trade_history": [record_dict], "messages": [...]}`.
- Returns list-wrapped record dict so `operator.add` reducer correctly appends to `trade_history`.
- `get_recent_trades(state)` helper returns `state.get("trade_history", [])[-TRADE_HISTORY_WINDOW:]` — read-time trim, unbounded accumulation.
- `TRADE_HISTORY_WINDOW = 15` (within discretion range 10-20 per RESEARCH.md).

**src/graph/state.py** — Added 5 Phase 3 fields:
- `trade_history: Annotated[List[dict], operator.add]` — append-only reducer
- `execution_mode: str` — "paper" | "live"
- `data_fetcher_result: Optional[dict]`
- `backtest_result: Optional[dict]`
- `execution_result: Optional[dict]`

### Task 2: Orchestrator Wiring and Researcher Feedback Loop

**src/graph/orchestrator.py** — L3 chain wiring:
- Added imports for all 4 L3 executor nodes
- Registered `data_fetcher`, `backtester`, `order_router`, `trade_logger` nodes in `create_orchestrator_graph`
- Replaced `risk_manager → synthesize` direct edge with the full 5-hop chain
- `LangGraphOrchestrator.__init__` now loads `config/swarm_config.yaml` via `yaml.safe_load`, stores as `self._yaml_config`, merges into graph config
- `run_task()` initializes Phase 3 state fields including `execution_mode` from YAML

**src/graph/agents/researchers.py** — Self-improvement context injection:
- Added import of `get_recent_trades`, `TRADE_HISTORY_WINDOW` from `trade_logger`
- Both `BullishResearcher` and `BearishResearcher` now prepend `[Trade History — last N trades]` block to their query before calling the LLM
- Zero changes to core debate logic, tool budget, hypothesis tagging

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] asyncio.run() required for e2e test with async L3 nodes**
- **Found during:** Task 2 — test_end_to_end_paper_graph
- **Issue:** Plan specified `graph.invoke()` but L3 nodes are `async def` coroutines; LangGraph sync `invoke()` cannot run async nodes — raises `TypeError: No synchronous function provided`
- **Fix:** Changed integration test to use `asyncio.run(graph.ainvoke(initial_state, config=config))`
- **Files modified:** tests/test_l3_integration.py

**2. [Rule 1 - Bug] patch.object() required instead of patch() for e2e test mocking**
- **Found during:** Task 2 — test_end_to_end_paper_graph
- **Issue:** `patch("src.graph.orchestrator.data_fetcher_node", ...)` patched the string path but `create_orchestrator_graph()` captures module-level name references; `patch.object(orch_module, ...)` correctly patches the attribute on the already-imported module object before the graph is compiled
- **Fix:** Switched all e2e test patches to `patch.object(orch_module, ...)`
- **Files modified:** tests/test_l3_integration.py

**3. [Rule 2 - Missing functionality] Intent patterns required in graph config for e2e test**
- **Found during:** Task 2 — graph routing in test
- **Issue:** Empty config `{}` passed to `create_orchestrator_graph` caused `classify_intent` to always return `intent="unknown"` → graph exited at END without running any L3 nodes
- **Fix:** Added `graph_config = {"orchestrator": {"intent_patterns": {...}}}` to the e2e test so "trade AAPL" correctly routes to `quant_modeler`
- **Files modified:** tests/test_l3_integration.py

### Deferred Items (Out of Scope)

**Pre-existing test isolation issue:** `test_order_router.py` uses deprecated `asyncio.get_event_loop().run_until_complete()`. When run after other async test files that call `asyncio.run()` (which closes the event loop), 6 tests fail with `RuntimeError: There is no current event loop`. These tests pass in isolation and were failing before Plan 03-04 started. Documented in `.planning/phases/03-l3-executors-nautilus-trader-integration/deferred-items.md`.

## Verification Results

```
pytest tests/ -q
  40 passed (all new tests + all previous Phase 3 tests)
  6 pre-existing failures in test_order_router.py (event loop issue, out-of-scope)

python -c "from src.graph.state import SwarmState; fields = list(SwarmState.__annotations__); assert 'trade_history' in fields and 'execution_mode' in fields; print('state fields ok')"
  state fields ok

python -c "from src.graph.orchestrator import create_orchestrator_graph; g = create_orchestrator_graph({}); print(list(g.get_graph().nodes.keys()))"
  ['__start__', 'classify_intent', 'macro_analyst', 'quant_modeler', 'bullish_researcher', 'bearish_researcher', 'debate_synthesizer', 'risk_manager', 'data_fetcher', 'backtester', 'order_router', 'trade_logger', 'synthesize', '__end__']

grep -r "adapters.alpaca" src/  →  OK: no alpaca references
```

## Commits

| Hash | Description |
|------|-------------|
| 52fb727 | test(03-04): add failing tests for TradeLogger node and Phase 3 SwarmState fields |
| 72b403e | feat(03-04): implement TradeLogger node and extend SwarmState with Phase 3 fields |
| d04d575 | test(03-04): add failing integration tests for L3 orchestrator wiring |
| 12ed67f | feat(03-04): wire L3 nodes into orchestrator and inject trade_history into L2 researchers |

## Human Verification (Task 3 Checkpoint) — APPROVED

The human smoke run confirmed:
- Test suite: 40 passed, 6 pre-existing failures (test_order_router event loop issue, pre-existing)
- State fields confirmed: trade_history, execution_mode, data_fetcher_result, backtest_result, execution_result all present
- Graph nodes confirmed: data_fetcher, backtester, order_router, trade_logger wired in correct order after risk_manager
- No Alpaca references in src/

**Phase 3 plan 03-04 is complete. Human approved.**

## Self-Check: PASSED

- SUMMARY.md: present at `.planning/phases/03-l3-executors-nautilus-trader-integration/03-04-SUMMARY.md`
- Commit 52fb727: test(03-04) add failing tests for TradeLogger
- Commit 72b403e: feat(03-04) implement TradeLogger node
- Commit d04d575: test(03-04) add failing integration tests for L3 orchestrator wiring
- Commit 12ed67f: feat(03-04) wire L3 nodes into orchestrator
