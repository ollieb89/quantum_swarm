---
phase: 28-gemini-api-circuit-breaker
plan: 02
subsystem: infra
tags: [circuit-breaker, resilience, orchestrator, state-machine, degraded-mode]

requires:
  - phase: 28-gemini-api-circuit-breaker-01
    provides: CircuitBreaker class with check/record_success/record_failure API
provides:
  - Circuit breaker integrated into with_audit_logging (single integration point for all LLM nodes)
  - SwarmState soft_failed_nodes field with operator.add reducer
  - CycleSnapshot degraded and soft_failed_nodes fields for downstream visibility
  - Kill switch via CIRCUIT_BREAKER_ENABLED env var
affects: [cycle-replay, alerting, dashboard, monitoring]

tech-stack:
  added: []
  patterns: [single-point circuit breaker integration via wrapper, degraded cycle handling]

key-files:
  created:
    - tests/test_circuit_breaker_integration.py
  modified:
    - src/graph/orchestrator.py
    - src/graph/state.py
    - src/core/cycle_snapshot.py
    - src/core/cycle_runner.py
    - src/core/audit_logger.py

key-decisions:
  - "Single integration point: with_audit_logging wraps all LLM nodes with circuit breaker -- no per-node wiring"
  - "LLM_NODES is a frozenset of 4 nodes (macro_analyst, quant_modeler, bullish_researcher, bearish_researcher); debate_synthesizer excluded (pure aggregation)"
  - "Degraded cycles skip validate_completed() to avoid false-positive ValueError on missing fields"
  - "soft_failed_nodes excluded from audit hash chain (infrastructure metadata, not trade data)"

patterns-established:
  - "Lazy _get_circuit_breaker singleton follows existing _get_llm pattern"
  - "_is_circuit_breaker_enabled() reads env var per-call (not cached) for runtime toggling"
  - "Soft-fail returns {soft_failed_nodes: [node_id]} instead of raising -- graph continues"

requirements-completed: [SEC-05, SEC-04, SEC-03]

duration: 8min
completed: 2026-03-09
---

# Phase 28 Plan 02: Orchestrator Circuit Breaker Integration Summary

**Circuit breaker wired into with_audit_logging single point, with soft_failed_nodes state propagation, degraded CycleSnapshot tracking, and 21 integration tests**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-09T18:13:32Z
- **Completed:** 2026-03-09T18:21:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- All LLM nodes (macro_analyst, quant_modeler, bullish_researcher, bearish_researcher) gain circuit breaker protection through single with_audit_logging wrapper
- Transient errors (429, 503, timeout) trigger soft-fail returning {soft_failed_nodes: [node_id]} instead of crashing
- Non-LLM nodes completely unaffected by circuit breaker
- SwarmState accumulates soft_failed_nodes via operator.add reducer across graph run
- CycleSnapshot records degraded=True and soft_failed_nodes list for downstream visibility
- Audit hash chain continuous -- soft-failed nodes log with output={} for chain integrity
- 21 integration tests covering all behaviors

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for circuit breaker integration** - `60134f5` (test)
2. **Task 1 GREEN: Wire circuit breaker and extend state models** - `60d8309` (feat)
3. **Task 2: End-to-end integration tests** - `ba3c9d1` (test)

_TDD tasks: test-first then implementation._

## Files Created/Modified
- `src/graph/orchestrator.py` - LLM_NODES frozenset, lazy CircuitBreaker singleton, enhanced with_audit_logging with circuit breaker checks
- `src/graph/state.py` - soft_failed_nodes field with operator.add reducer
- `src/core/cycle_snapshot.py` - degraded bool and soft_failed_nodes list fields
- `src/core/cycle_runner.py` - Propagates degraded state to snapshot, skips validate_completed for degraded cycles
- `src/core/audit_logger.py` - soft_failed_nodes added to AUDIT_EXCLUDED_FIELDS
- `tests/test_circuit_breaker_integration.py` - 21 integration tests

## Decisions Made
- Single integration point via with_audit_logging -- no per-node wiring needed
- debate_synthesizer excluded from LLM_NODES (pure aggregation, no API call)
- Degraded cycles skip validate_completed() to avoid ValueError on partial runs
- soft_failed_nodes excluded from audit hash chain (infrastructure metadata)
- _is_circuit_breaker_enabled() reads env var per call for runtime flexibility

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing duckdb failures in test_knowledge_base and test_l3_integration (unrelated to changes, not regressions)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Circuit breaker fully integrated into orchestrator
- Ready for Phase 29 (if applicable) or monitoring/alerting integration
- CycleSnapshot degraded field available for replay CLI and dashboard consumption

---
*Phase: 28-gemini-api-circuit-breaker*
*Completed: 2026-03-09*
