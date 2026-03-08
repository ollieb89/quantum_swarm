---
phase: 11-explainability-decision-cards
plan: "02"
subsystem: graph
tags: [langgraph, decision-card, audit, jsonl, conditional-edge, tdd]

# Dependency graph
requires:
  - phase: 11-01
    provides: "DecisionCard Pydantic model, build_decision_card(), canonical_json(), verify_decision_card(), _compute_hash()"
provides:
  - "decision_card_writer_node async LangGraph node that builds + appends decision cards to data/audit.jsonl"
  - "route_after_order_router conditional routing function (success -> decision_card_writer, failure -> trade_logger)"
  - "Three new SwarmState optional fields: decision_card_status, decision_card_error, decision_card_audit_ref"
  - "TestDecisionCardWriter integration test class (7 tests covering append, retry, double-failure, routing)"
affects:
  - "trade_logger (now receives state after decision_card_writer runs)"
  - "Any downstream node reading decision_card_status or decision_card_audit_ref"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Conditional edge pattern: route_after_order_router inserts optional node between order_router and trade_logger"
    - "Retry-once file write: for attempt in range(2) with OSError catch and compliance INCIDENT log on double failure"
    - "DB-optional prev_audit_hash: caught exception sets prev_audit_hash=None, never blocks card creation"
    - "mock_open() for write capture: patch builtins.open on mode=='a' to intercept audit.jsonl appends in tests"

key-files:
  created:
    - ".planning/phases/11-explainability-decision-cards/11-02-SUMMARY.md"
  modified:
    - "src/graph/state.py"
    - "src/graph/orchestrator.py"
    - "tests/test_decision_card.py"

key-decisions:
  - "Patching builtins.open (mode=='a') is the test isolation strategy for audit.jsonl writes — avoids Path monkeypatching which caused recursive calls"
  - "decision_card_writer placed between order_router and trade_logger via conditional edge; on failure path trade_logger is reached directly"
  - "get_pool() DB failure for prev_audit_hash is non-fatal (logged warning, card still written with prev_audit_hash=None)"
  - "Double open() failure logs COMPLIANCE INCIDENT and returns status='failed' without rolling back the executed trade"

patterns-established:
  - "TDD node test pattern: setUpClass stubs broken ccxt via sys.modules; mock_open captures writes without filesystem"
  - "Conditional edge insertion: add_node + add_conditional_edges replacing direct add_edge; original target remains reachable on failure path"

requirements-completed:
  - EXEC-04

# Metrics
duration: 4min
completed: 2026-03-08
---

# Phase 11 Plan 02: Explainability Decision Cards — Orchestrator Wiring Summary

**decision_card_writer_node wired into LangGraph between order_router and trade_logger via conditional edge; every successful trade produces a SHA-256-verified JSON line in data/audit.jsonl with retry-once and compliance INCIDENT logging**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-08T00:31:08Z
- **Completed:** 2026-03-08T00:35:18Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `decision_card_status`, `decision_card_error`, `decision_card_audit_ref` optional fields to `SwarmState` (all initialized to `None` in `run_task_async`)
- Implemented `decision_card_writer_node` async function with: async DB query for `prev_audit_hash`, `MemoryRegistry` rule loading, retry-once file append, compliance INCIDENT log on double failure
- Replaced direct `order_router -> trade_logger` edge with conditional edge via `route_after_order_router`; added `decision_card_writer -> trade_logger` edge completing the graph wiring
- Added `TestDecisionCardWriter` (7 tests: 3 routing + 4 node integration) — all 21 tests in `test_decision_card.py` pass; full 225-test suite clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Add SwarmState fields and implement decision_card_writer node** - `e0483da` (feat)
2. **Task 2: Integration tests for decision_card_writer write path** - `26a655f` (test)

**Plan metadata:** (docs commit below)

_Note: Task 2 used TDD pattern; RED confirmed before GREEN implementation._

## Files Created/Modified

- `src/graph/state.py` - Added `Literal` import; three new Phase 11 optional fields after `execution_result`
- `src/graph/orchestrator.py` - Added imports (`build_decision_card`, `canonical_json`, `verify_decision_card`, `get_pool`); implemented `route_after_order_router` and `decision_card_writer_node`; registered node; replaced direct edge with conditional edge; added three fields to `initial_state`
- `tests/test_decision_card.py` - Added `TestDecisionCardWriter` class with 7 integration tests

## Decisions Made

- Used `mock_open()` capturing `mode=='a'` calls for test isolation — avoids filesystem writes and the fragile `Path` monkeypatching approach that caused recursive `Path(p)` calls during test
- DB failure for `prev_audit_hash` is non-fatal by design; card is still created with `prev_audit_hash=None` to ensure no trade goes unlogged due to transient DB issues
- Compliance INCIDENT is logged (not raised) on double write failure so the trade execution is never rolled back

## Deviations from Plan

None — plan executed exactly as written. The test isolation approach (mock_open strategy) was selected from the plan's documented alternatives (option c: "patch builtins.open in the orchestrator module scope") and refined for correctness.

## Issues Encountered

- Initial `test_card_appended_to_audit_jsonl` test failed RED with `FileNotFoundError` because patching `src.graph.orchestrator.Path` with a lambda caused recursive `Path(p)` calls in the `else` branch. Resolved by switching to `mock_open()` interception on `mode=='a'` which is the plan's recommended option c. This was a test design issue, not a node implementation issue.

## User Setup Required

None — no external service configuration required. The `data/audit.jsonl` file is created automatically on first successful trade.

## Next Phase Readiness

- EXEC-04 fully satisfied: every successful trade execution produces a verifiable JSON decision card in `data/audit.jsonl`
- Phase 11 complete: Plan 01 (model + builder + verifier) + Plan 02 (orchestrator wiring + integration tests)
- `decision_card_status` and `decision_card_audit_ref` available in state for any downstream node that needs to reference card provenance

---
*Phase: 11-explainability-decision-cards*
*Completed: 2026-03-08*
