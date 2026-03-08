---
phase: 22-failure-path-kami-memory-logging
plan: 02
subsystem: trading
tags: [orchestrator, routing, decision-card, failure-path, graph-topology]

# Dependency graph
requires:
  - phase: 22-failure-path-kami-memory-logging
    plan: 01
    provides: "failure_cause classification, _SELF_INDUCED_CAUSES, CYCLE_STATUS in MEMORY.md"
  - phase: 16-kami-merit-index
    provides: "decision_card_writer, merit_updater, build_decision_card"
provides:
  - "Direct edge order_router -> decision_card_writer (unconditional)"
  - "Failure cards with same audit hash-chain treatment as success cards"
  - "Single failure path: order_router -> decision_card_writer -> merit_updater -> memory_writer -> trade_logger"
affects: [22-03, phase-23]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-path graph topology: all order_router outcomes traverse same node chain"
    - "Outcome-aware nodes: behavior varies by execution_result.success, not by graph routing"

key-files:
  created: []
  modified:
    - src/graph/orchestrator.py
    - tests/core/test_failure_path.py
    - tests/test_decision_card.py
    - tests/test_l3_integration.py

key-decisions:
  - "route_after_order_router deleted entirely (clean removal, not dead code)"
  - "No changes needed to build_decision_card or decision_card_writer_node — already handle failure cases generically"
  - "No changes needed to merit_updater — execution_result is truthy dict when success=False, passes aborted-cycle guard"

patterns-established:
  - "Graph topology encodes structure, not business logic — nodes inspect state to vary behavior"

requirements-completed: [KAMI-03, EVOL-01]

# Metrics
duration: 6min
completed: 2026-03-08
---

# Phase 22 Plan 02: Failure Path Routing Rewiring Summary

**Direct edge order_router -> decision_card_writer replacing conditional routing, with failure cards and full regression verification**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-08T20:45:24Z
- **Completed:** 2026-03-08T20:51:20Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Removed conditional routing (route_after_order_router) — all order_router outcomes now traverse single chain
- Confirmed decision_card_writer produces valid failure cards with same hash-chain audit treatment
- Confirmed merit_updater processes failed execution_results (not skipped by aborted-cycle guard)
- 508 tests passing with 0 regressions from orchestrator rewiring

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewire orchestrator + failure-aware decision_card_writer** - `f074704` (feat)
2. **Task 2: Full regression and end-to-end verification** - `87ee186` (test)

_Note: TDD tasks had RED/GREEN phases within each commit._

## Files Created/Modified
- `src/graph/orchestrator.py` - Deleted route_after_order_router, replaced conditional edges with direct edge
- `tests/core/test_failure_path.py` - 7 new tests: graph topology, failure card, merit_updater failure, end-to-end chain
- `tests/test_decision_card.py` - Removed stale routing tests, added failure card production test
- `tests/test_l3_integration.py` - Updated edge assertions to reflect new direct edge topology

## Decisions Made
- route_after_order_router deleted entirely (clean removal) — no deprecation comment, function is dead code after direct edge
- No changes needed to build_decision_card — already reads execution_result generically and handles Optional fields
- No changes needed to decision_card_writer_node — already produces full cards regardless of execution_result.success value
- No changes needed to merit_updater — execution_result dict is truthy even when success=False, passes the aborted-cycle guard correctly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated stale test_l3_integration.py edge assertions**
- **Found during:** Task 2
- **Issue:** test_l3_chain_order asserted ("order_router", "trade_logger") edge which no longer exists after rewiring
- **Fix:** Updated to assert full chain: order_router -> decision_card_writer -> merit_updater -> memory_writer -> trade_logger
- **Files modified:** tests/test_l3_integration.py
- **Committed in:** 87ee186

**2. [Rule 1 - Bug] Removed stale route_after_order_router tests in test_decision_card.py**
- **Found during:** Task 2
- **Issue:** 4 tests imported and tested the deleted route_after_order_router function
- **Fix:** Removed 3 routing tests, replaced 1 with failure card production test
- **Files modified:** tests/test_decision_card.py
- **Committed in:** 87ee186

---

**Total deviations:** 2 auto-fixed (2 bugs — stale test references)
**Impact on plan:** Both fixes necessary for test suite to pass after routing change. No scope creep.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- INT-03 gap fully closed: all order_router outcomes traverse decision_card_writer -> merit_updater -> memory_writer -> trade_logger
- Ready for Plan 03 (if any) or Phase 23
- Full graph topology verified via compiled graph introspection

---
*Phase: 22-failure-path-kami-memory-logging*
*Completed: 2026-03-08*
