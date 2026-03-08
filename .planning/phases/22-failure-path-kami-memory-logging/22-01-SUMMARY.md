---
phase: 22-failure-path-kami-memory-logging
plan: 01
subsystem: trading
tags: [kami, merit, recovery, failure-cause, memory-writer, order-router]

# Dependency graph
requires:
  - phase: 16-kami-merit-index
    provides: "_extract_recovery_signal, _SELF_INDUCED_ERRORS, compute_merit, apply_ema"
  - phase: 17-memory-evolution-agent-church
    provides: "_build_entry, _process_agent, MEMORY.md structured format"
provides:
  - "failure_cause classification in order_router execution_result"
  - "_SELF_INDUCED_CAUSES and _EXTERNAL_CAUSES taxonomy in kami.py"
  - "[CYCLE_STATUS:] field in MEMORY.md entries"
  - "cycle_status determination in memory_writer _process_agent"
affects: [22-02, 22-03, phase-23]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "failure_cause taxonomy as frozenset constants (kami.py + memory_writer.py)"
    - "fail-open for unknown failure_cause values in _extract_recovery_signal"
    - "CYCLE_STATUS field between DRIFT_FLAGS and THESIS_SUMMARY in MEMORY.md"

key-files:
  created:
    - tests/core/test_failure_path.py
  modified:
    - src/core/kami.py
    - src/graph/agents/l3/order_router.py
    - src/graph/nodes/memory_writer.py

key-decisions:
  - "failure_cause field checked BEFORE legacy error_type path for backward compatibility"
  - "Unknown failure_cause values get 1.0 (fail-open) rather than 0.0 (penalise)"
  - "_EXTERNAL_CAUSES duplicated in memory_writer.py to avoid cross-layer coupling"
  - "EXECUTION_FAILURE (generic exception) treated as external — cannot classify without more context"

patterns-established:
  - "failure_cause taxonomy: frozenset constants with explicit self-induced vs external classification"
  - "cycle_status derivation: success/failed/external_failure based on execution_result.success + failure_cause"

requirements-completed: [KAMI-03, EVOL-01]

# Metrics
duration: 3min
completed: 2026-03-08
---

# Phase 22 Plan 01: Failure Path KAMI + Memory Logging Summary

**failure_cause classification in order_router with KAMI recovery signal awareness and CYCLE_STATUS in MEMORY.md entries**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-08T20:39:21Z
- **Completed:** 2026-03-08T20:42:53Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- order_router returns failure_cause in all execution_result dicts (RISK_RULE_VIOLATION, EXECUTION_FAILURE, or None)
- _extract_recovery_signal penalises self-induced causes (0.0) and spares external/unknown causes (1.0, fail-open)
- MEMORY.md entries include [CYCLE_STATUS:] field between DRIFT_FLAGS and THESIS_SUMMARY
- 25 tests covering failure_cause taxonomy, recovery signal, _build_entry, and _process_agent cycle_status

## Task Commits

Each task was committed atomically:

1. **Task 1: Add failure_cause to order_router + update KAMI recovery signal** - `51d9f3c` (feat)
2. **Task 2: Add [CYCLE_STATUS:] field to MEMORY.md entries** - `dda732b` (feat)

_Note: TDD tasks had RED/GREEN phases within each commit._

## Files Created/Modified
- `tests/core/test_failure_path.py` - 25 tests covering failure_cause taxonomy and CYCLE_STATUS behavior
- `src/core/kami.py` - _SELF_INDUCED_CAUSES, _EXTERNAL_CAUSES frozensets; updated _extract_recovery_signal
- `src/graph/agents/l3/order_router.py` - failure_cause field in all execution_result return dicts
- `src/graph/nodes/memory_writer.py` - cycle_status param in _build_entry, _EXTERNAL_CAUSES constant, cycle_status derivation in _process_agent

## Decisions Made
- failure_cause field checked BEFORE legacy error_type path — new taxonomy takes precedence but old path preserved for backward compatibility with pre-Phase 22 execution results
- Unknown failure_cause values get 1.0 (fail-open) — penalising unclassified causes would violate the user's "Unknown: neutral/no penalty" decision
- _EXTERNAL_CAUSES duplicated in memory_writer.py — memory_writer is graph layer, kami is core layer; local constant avoids coupling
- EXECUTION_FAILURE (generic exception in order_router) treated as external — cannot classify without more context, so fail-open applies

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- failure_cause and CYCLE_STATUS infrastructure ready for Plan 02 (routing topology changes) and Plan 03 (decision card failure handling)
- All existing tests pass (merit_updater: 5/5, memory_writer: 27/27, failure_path: 25/25)

---
*Phase: 22-failure-path-kami-memory-logging*
*Completed: 2026-03-08*
