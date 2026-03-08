---
phase: 20-wire-drift-flags-pipeline
plan: 02
subsystem: core
tags: [drift-detection, memory-writer, drift-eval, soul-loader, integration]

# Dependency graph
requires:
  - phase: 20-wire-drift-flags-pipeline
    plan: 01
    provides: "DriftRule dataclass, evaluate_drift(), AgentSoul.drift_rules"
  - phase: 17-memory-evolution
    provides: "memory_writer_node with _build_entry, _process_agent, _check_triggers"
provides:
  - "Drift-evaluated _build_entry replacing hardcoded 'none'"
  - "_evaluate_drift_flags helper: three-state model (none/flags/evaluation_failed)"
  - "Non-blocking drift evaluation wired into _process_agent"
  - "DRIFT_STREAK trigger works with real drift flags"
  - "ARS drift_flag_frequency confirmed functional with real data"
affects: [ars-auditor, agent-church, evolution-triggers]

# Tech tracking
tech-stack:
  added: []
  patterns: [three-state-drift-flags, fail-soft-drift-eval, module-level-monkeypatch]

key-files:
  created: []
  modified:
    - src/graph/nodes/memory_writer.py
    - tests/core/test_memory_writer.py

key-decisions:
  - "Module-level monkeypatch (mw_mod, 'load_soul') instead of string-based path to avoid AttributeError when src.graph.nodes not loaded as submodule attribute"
  - "Canonical text extraction reuses same key priority as _extract_thesis_summary but takes FULL text instead of first sentence"

patterns-established:
  - "Three-state drift flags: 'none' (clean), 'flag1,flag2' (detected), 'evaluation_failed' (error sentinel)"
  - "Non-blocking drift eval: exception -> WARNING log + evaluation_failed sentinel, never blocks memory write"

requirements-completed: [EVOL-02, ARS-01]

# Metrics
duration: 7min
completed: 2026-03-08
---

# Phase 20 Plan 02: Wire Drift Flags Pipeline Summary

**Drift evaluation wired into memory_writer _build_entry/_process_agent with three-state model (none/flags/evaluation_failed), replacing hardcoded 'none' -- DRIFT_STREAK and ARS drift_flag_frequency confirmed end-to-end**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-08T17:47:41Z
- **Completed:** 2026-03-08T17:54:32Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- _build_entry accepts drift_flags parameter (default "none"), replacing hardcoded value
- _evaluate_drift_flags helper: load_soul().drift_rules + evaluate_drift() with fail-soft exception handling
- _process_agent extracts canonical text and evaluates drift before building entry
- DRIFT_STREAK trigger confirmed working with real non-"none" drift flags
- ARS _compute_drift_flag_frequency confirmed to count "evaluation_failed" as flagged (no code change needed)
- _extract_drift_flags treats "evaluation_failed" as non-empty (conservative safety behavior)
- 477 tests passing in full suite (1 pre-existing PostgreSQL failure, 2 pre-existing DB errors)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing drift flag tests** - `16c5d1b` (test)
2. **Task 1 GREEN: Wire drift eval into memory_writer** - `54d1275` (feat)
3. **Task 2: Fix monkeypatch targets for full suite regression** - `a985cbb` (fix)

_Note: Task 1 followed TDD (RED then GREEN commits). Task 2 discovered and fixed test isolation issue._

## Files Created/Modified
- `src/graph/nodes/memory_writer.py` - Added drift_eval/soul_loader imports, drift_flags param to _build_entry, _evaluate_drift_flags helper, canonical text extraction + drift eval in _process_agent
- `tests/core/test_memory_writer.py` - 15 new tests: _build_entry drift_flags, _evaluate_drift_flags unit tests, _process_agent integration tests, DRIFT_STREAK with real flags, _extract_drift_flags evaluation_failed sentinel

## Decisions Made
- Module-level monkeypatch (mw_mod, 'load_soul') instead of string-based path -- avoids AttributeError when src.graph.nodes not loaded as submodule attribute in full suite
- Canonical text extraction reuses same key priority order as _extract_thesis_summary but takes full text (not first sentence) for drift evaluation accuracy

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed monkeypatch target for drift tests in full suite**
- **Found during:** Task 2 (full regression)
- **Issue:** String-based monkeypatch.setattr("src.graph.nodes.memory_writer.load_soul", ...) fails when src.graph module doesn't have nodes as an attribute (module not imported as submodule)
- **Fix:** Changed to monkeypatch.setattr(mw_mod, "load_soul", ...) using the already-imported module reference
- **Files modified:** tests/core/test_memory_writer.py
- **Verification:** Full suite passes 477/478 (1 pre-existing PG failure)
- **Committed in:** a985cbb

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential for test correctness in full suite. No scope creep.

## Issues Encountered
None beyond the monkeypatch fix documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 20 complete: drift flags pipeline fully wired end-to-end
- INT-01 closure: hardcoded "none" replaced with evaluated drift flags
- EVOL-02: DRIFT_STREAK trigger works with real flags from soul drift rules
- ARS-01: drift_flag_frequency confirmed to count real flags and evaluation_failed
- Ready for Phase 21 (next gap closure phase per ROADMAP)

## Self-Check: PASSED

- src/graph/nodes/memory_writer.py exists and contains evaluate_drift import
- tests/core/test_memory_writer.py exists with 27 tests
- All 3 commits verified in git log

---
*Phase: 20-wire-drift-flags-pipeline*
*Completed: 2026-03-08*
