---
phase: 13-wire-institutional-guard
plan: "01"
subsystem: testing
tags: [langgraph, institutional-guard, tdd, graph-wiring, pytest]

# Dependency graph
requires:
  - phase: 08-portfolio-risk-governance
    provides: institutional_guard_node with metadata propagation (trade_risk_score, portfolio_heat)
provides:
  - TDD RED scaffold: tests/test_graph_wiring.py with two tests defining the wiring contract
  - test_institutional_guard_wired_in_graph: fails (RED) — asserts claw_guard -> institutional_guard edge missing
  - test_institutional_guard_metadata_propagation: passes — confirms node logic already correct
affects:
  - 13-02 (Plan 02 must make test_institutional_guard_wired_in_graph GREEN by wiring orchestrator)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Monkeypatch StateGraph.compile to return raw workflow for edge inspection without graph compilation"
    - "Capture StateGraph instance inside fake_compile via closure dict for post-call inspection"
    - "AsyncMock patch.object for _get_open_positions and _get_daily_pnl avoids live PostgreSQL in node tests"

key-files:
  created:
    - tests/test_graph_wiring.py
  modified: []

key-decisions:
  - "TDD RED first: write tests asserting the desired wiring before touching orchestrator.py"
  - "Use fake_compile closure pattern to capture StateGraph before compile() converts it to CompiledGraph"
  - "Edge inspection via workflow._graph.edges() (networkx DiGraph) with AttributeError fallback"
  - "test_institutional_guard_metadata_propagation intentionally passes in RED — node logic correct, wiring is the gap"

patterns-established:
  - "Graph wiring test pattern: patch StateGraph.compile -> capture raw workflow -> inspect ._graph.edges()"
  - "Both assertions (wiring + metadata propagation) in same test file so Plan 02 has a complete contract"

requirements-completed: []  # RISK-07 and RISK-08 completed at plan level in Plan 02 (GREEN phase)

# Metrics
duration: 8min
completed: 2026-03-08
---

# Phase 13 Plan 01: Wire Institutional Guard — TDD RED Scaffold Summary

**TDD RED scaffold creating two graph wiring tests: claw_guard->institutional_guard edge assertion (fails) and metadata propagation check (passes), establishing Plan 02's implementation contract.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-08T00:00:00Z
- **Completed:** 2026-03-08T00:08:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `tests/test_graph_wiring.py` with two tests defining the Phase 13 wiring contract
- `test_institutional_guard_wired_in_graph`: FAILS (RED) — confirms current gap: `claw_guard` routes to `data_fetcher` bypassing `institutional_guard`
- `test_institutional_guard_metadata_propagation`: PASSES — confirms `institutional_guard_node` correctly populates `trade_risk_score` and `portfolio_heat` in metadata
- All 7 Phase 8 tests (`test_institutional_guard.py`) still pass — no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Write RED tests — graph wiring and metadata propagation** - `999a6d0` (test)

## Files Created/Modified

- `tests/test_graph_wiring.py` — TDD RED scaffold; two tests defining the graph wiring and metadata propagation contract for Plan 02

## Decisions Made

- Used `fake_compile` closure pattern (capturing `self` inside monkeypatched `StateGraph.compile`) to get the raw `StateGraph` object without triggering LangGraph compilation — this allows edge inspection via `._graph.edges()` (networkx DiGraph)
- `test_institutional_guard_metadata_propagation` intentionally passes in RED state per plan spec: the node logic is already correct, the gap is purely in the graph wiring
- Added `AttributeError` fallback in edge inspection in case future LangGraph versions change the `_graph` attribute

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- `tests/test_graph_wiring.py` committed and RED state verified
- Plan 02 must wire `claw_guard -> institutional_guard -> data_fetcher` in `src/graph/orchestrator.py` to turn the failing test GREEN
- Phase 8 tests unaffected — safe to proceed

---
*Phase: 13-wire-institutional-guard*
*Completed: 2026-03-08*
