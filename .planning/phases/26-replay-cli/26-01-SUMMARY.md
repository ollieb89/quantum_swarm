---
phase: 26-replay-cli
plan: 01
subsystem: core
tags: [cycle-store, pydantic, postgresql, filesystem, read-only]

# Dependency graph
requires:
  - phase: 24-cycle-persistence
    provides: CycleSnapshot model and cycle_snapshots DB table
provides:
  - "load_cycle() — load CycleSnapshot from filesystem JSON"
  - "list_cycles() — unified DB/filesystem cycle metadata listing"
  - "list_cycles_filesystem() — scan cycle directories for metadata"
  - "list_cycles_db() — query PostgreSQL cycle_snapshots table"
affects: [26-replay-cli]

# Tech tracking
tech-stack:
  added: [rich, structlog]
  patterns: [core-leaf-module, db-with-filesystem-fallback]

key-files:
  created: [src/core/cycle_store.py, tests/core/test_cycle_store.py]
  modified: [tests/core/test_import_boundaries.py, pyproject.toml]

key-decisions:
  - "ISO 8601 lexicographic sort for timestamp ordering (no datetime parse needed)"
  - "Lightweight JSON key extraction for list_cycles_filesystem (no full CycleSnapshot parse)"

patterns-established:
  - "DB-with-filesystem-fallback: try async DB query, catch any exception, fall back to sync filesystem scan"

requirements-completed: [REPL-01, REPL-02, REPL-03, REPL-05]

# Metrics
duration: 4min
completed: 2026-03-09
---

# Phase 26 Plan 01: Cycle Store Summary

**Read-only cycle data access layer with load_cycle, filesystem scanning, PostgreSQL query, and DB-to-filesystem fallback**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-09T07:17:40Z
- **Completed:** 2026-03-09T07:21:42Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created cycle_store.py as a core leaf module with 4 exported functions
- 14 unit tests covering load, list, filters, error cases, and DB fallback
- Registered import boundary tests (23 total import boundary tests pass)
- Added rich and structlog to pyproject.toml dependencies

## Task Commits

Each task was committed atomically:

1. **Task 1: Create cycle_store.py and unit tests** - `fc87ff9` (feat)
2. **Task 2: Register import boundary and add rich dependency** - `3f36cc2` (chore)

## Files Created/Modified
- `src/core/cycle_store.py` - Read-only cycle data access with load_cycle, list_cycles, list_cycles_filesystem, list_cycles_db
- `tests/core/test_cycle_store.py` - 14 unit tests with tmp_cycles_dir fixture
- `tests/core/test_import_boundaries.py` - Added cycle_store leaf import + no-graph-import tests
- `pyproject.toml` - Added rich>=13.0 and structlog>=25.0 dependencies

## Decisions Made
- ISO 8601 lexicographic sort for timestamp ordering avoids datetime parsing overhead
- Lightweight JSON key extraction in list_cycles_filesystem skips full CycleSnapshot validation for speed
- DB query uses psycopg %s parameterized queries for SQL injection safety

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added structlog to pyproject.toml dependencies**
- **Found during:** Task 2 (uv sync)
- **Issue:** uv sync removed structlog (not declared in pyproject.toml), breaking test_logging_config_imports_cleanly
- **Fix:** Added structlog>=25.0 to pyproject.toml dependencies
- **Files modified:** pyproject.toml
- **Verification:** 359 core tests pass after fix
- **Committed in:** 3f36cc2 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to prevent regression. No scope creep.

## Issues Encountered
None beyond the structlog dependency fix documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- cycle_store.py ready for use by replay CLI subcommands (26-02, 26-03)
- All 359 core tests passing, 0 regressions

---
*Phase: 26-replay-cli*
*Completed: 2026-03-09*
