---
phase: 30-kami-weight-rebalance-token-tracking
plan: 02
subsystem: observability
tags: [token-tracking, budget-manager, cycle-snapshot, replay-cli]

# Dependency graph
requires:
  - phase: 25-end-to-end-pipeline-runner
    provides: CycleRunner, CycleSnapshot, replay CLI
  - phase: 29-persona-score-core
    provides: persona_scores pattern on CycleSnapshot
provides:
  - Per-agent token tracking in BudgetManager (record_usage agent_id, per_agent_summary)
  - token_usage field on CycleSnapshot persisted to filesystem/DB
  - Token usage rendering in replay CLI handle_show
affects: [31-pipeline-hardening, observability-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns: [per-agent cost attribution via BudgetManager, infrastructure fields excluded from audit hash]

key-files:
  created: []
  modified:
    - src/core/budget_manager.py
    - src/core/cycle_snapshot.py
    - src/core/audit_logger.py
    - src/core/cycle_runner.py
    - src/graph/agents/analysts.py
    - src/graph/agents/researchers.py
    - src/graph/nodes/l1.py
    - src/cli/replay.py
    - tests/test_budget_tracking.py
    - tests/core/test_cycle_snapshot.py
    - tests/cli/test_replay.py

key-decisions:
  - "agent_id parameter is Optional[str]=None for full backward compatibility"
  - "token_usage excluded from audit hash chain (infrastructure metadata, not MiFID II trade data)"
  - "BudgetManager remains single authoritative source -- no SwarmState token reducer (OBS-05)"
  - "Per-agent data cleared on reset_session to prevent cross-cycle leakage"

patterns-established:
  - "Per-agent tracking: pass agent_id= to record_usage at each call site"
  - "Infrastructure fields on CycleSnapshot: add to AUDIT_EXCLUDED_FIELDS, do NOT add to _COMPLETED_REQUIRED_FIELDS"

requirements-completed: [OBS-02, OBS-04, OBS-05]

# Metrics
duration: 7min
completed: 2026-03-10
---

# Phase 30 Plan 02: Token Usage Tracking Summary

**Per-agent per-cycle token cost tracking from BudgetManager through CycleSnapshot to replay CLI display**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-09T23:38:46Z
- **Completed:** 2026-03-09T23:45:45Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Extended BudgetManager with per-agent token tracking (agent_id parameter + per_agent_summary method)
- Added token_usage field to CycleSnapshot, excluded from audit hash, populated in CycleRunner before persist
- Wired agent_id to all 4 call sites (macro_analyst, quant_modeler, bullish/bearish_research, classify_intent)
- Added compact inline token usage rendering in replay CLI handle_show
- 35 tests passing across budget, snapshot, and replay test suites

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend BudgetManager with per-agent tracking** - `ff0f23c` (feat, TDD)
2. **Task 2: Wire agent_id, CycleSnapshot, audit, CycleRunner, replay CLI** - `8a117ce` (feat)

## Files Created/Modified
- `src/core/budget_manager.py` - Added _per_agent dict, agent_id param, per_agent_summary(), clear in reset_session
- `src/core/cycle_snapshot.py` - Added token_usage: Optional[dict] field
- `src/core/audit_logger.py` - Added "token_usage" to AUDIT_EXCLUDED_FIELDS
- `src/core/cycle_runner.py` - Populate snapshot.token_usage from budget.per_agent_summary() before persist
- `src/graph/agents/analysts.py` - Added agent_id="macro_analyst" and "quant_modeler" to record_usage calls
- `src/graph/agents/researchers.py` - Added agent_id param to _run_researcher_agent, passed "bullish_research"/"bearish_research"
- `src/graph/nodes/l1.py` - Added agent_id="classify_intent" to record_usage call
- `src/cli/replay.py` - Token usage inline rendering after Merit Weights section
- `tests/test_budget_tracking.py` - 4 new per-agent tracking tests
- `tests/core/test_cycle_snapshot.py` - 2 new token_usage field tests
- `tests/cli/test_replay.py` - 1 new token usage rendering test

## Decisions Made
- agent_id is Optional[str]=None for full backward compatibility -- existing call sites work unchanged
- token_usage excluded from audit hash chain (same pattern as persona_scores, soft_failed_nodes)
- BudgetManager is single authoritative source -- no SwarmState token reducer to avoid double-counting
- Per-agent data clears on reset_session() to prevent cross-cycle leakage

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Token tracking fully operational from agent nodes through persistence to CLI display
- Ready for Phase 30 Plan 01 (KAMI weight rebalance) or Phase 31

---
*Phase: 30-kami-weight-rebalance-token-tracking*
*Completed: 2026-03-10*
