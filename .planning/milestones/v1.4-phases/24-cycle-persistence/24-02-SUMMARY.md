---
phase: 24-cycle-persistence
plan: 02
subsystem: core
tags: [async, cycle-runner, persistence, postgresql, filesystem, pydantic]

requires:
  - phase: 24-cycle-persistence
    provides: "CycleSnapshot Pydantic model and cycle_snapshots DDL"
provides:
  - "CycleRunner async wrapper class for graph execution + persistence"
  - "Filesystem snapshot writer (data/cycles/{padded_id}/snapshot.json)"
  - "PostgreSQL cycle_id allocation and row updates"
affects: [24-03, 24-04, 25-pipeline-runner]

tech-stack:
  added: []
  patterns: ["CycleRunner external wrapper pattern (graph via DI, no graph imports)", "Hybrid persistence (PostgreSQL metadata + filesystem full snapshot)"]

key-files:
  created:
    - src/core/cycle_runner.py
  modified:
    - tests/core/test_cycle_runner.py
    - tests/core/test_import_boundaries.py

key-decisions:
  - "decision_card built from decision_card_audit_ref + decision_card_status fields (inline dict, no FK)"
  - "Fallback cycle_id uses timestamp-based integer when db_pool is None"

patterns-established:
  - "CycleRunner DI pattern: graph injected via constructor, never imported"
  - "Three-status extraction: completed (all fields), rejected (agent memos only), failed (error_context)"
  - "base_dir parameter for testable filesystem writes"

requirements-completed: [CYCL-01, CYCL-04]

duration: 3min
completed: 2026-03-09
---

# Phase 24 Plan 02: CycleRunner Wrapper Summary

**Async CycleRunner wrapper executing graph pipeline with three-status persistence to filesystem JSON and PostgreSQL, 14 unit tests, import boundary enforcement**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-09T02:32:35Z
- **Completed:** 2026-03-09T02:35:15Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- CycleRunner class handling completed/rejected/failed status paths with CycleSnapshot extraction
- Filesystem writes producing valid JSON in data/cycles/{padded_id}/snapshot.json
- PostgreSQL cycle_id allocation via INSERT RETURNING with fallback for no-DB mode
- 14 CycleRunner tests + 4 new import boundary tests (34 total passing)
- Zero graph imports in cycle_runner.py (enforced by boundary tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: CycleRunner wrapper + tests** - `aa43908` (test: RED) + `b2d23e9` (feat: GREEN)
2. **Task 2: Register cycle modules in import boundary tests** - `bb30d74` (test)

## Files Created/Modified
- `src/core/cycle_runner.py` - CycleRunner class with run_cycle(), _build_initial_state(), _extract_snapshot(), _write_snapshot_file(), _allocate_cycle_id(), _update_cycle_row()
- `tests/core/test_cycle_runner.py` - 14 unit tests covering all three status paths, state isolation, DB mocks, filesystem writes
- `tests/core/test_import_boundaries.py` - 4 new tests for cycle_snapshot and cycle_runner (leaf import + no-graph-import)

## Decisions Made
- decision_card constructed as inline dict from decision_card_audit_ref and decision_card_status SwarmState fields (no FK, per research recommendation)
- Fallback cycle_id uses timestamp-based integer modulo 10^9 when db_pool is None (enables testing without PostgreSQL)
- base_dir constructor parameter enables tmp_path injection for deterministic filesystem tests

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CycleRunner ready for pipeline runner integration (Phase 25)
- Snapshot query layer (Plan 03/04) can build on top of filesystem + DB writes
- Import boundary law enforced for both cycle modules

---
*Phase: 24-cycle-persistence*
*Completed: 2026-03-09*
