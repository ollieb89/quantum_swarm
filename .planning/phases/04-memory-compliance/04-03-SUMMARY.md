---
phase: 04-memory-compliance
plan: "03"
subsystem: database
tags: [postgresql, ddl, schema, institutional-guard, compliance, testing, asyncio, asyncmock]

# Dependency graph
requires:
  - phase: 04-01
    provides: initial gap analysis identifying exit_time DDL bug and vacuous test patterns
  - phase: 04-02
    provides: KnowledgeBase lazy init fix, establishing async patterns for module-level objects
provides:
  - trades DDL with exit_time TIMESTAMPTZ column (InstitutionalGuard can now run against live DB)
  - Three passing async-correct institutional guard tests covering SEC-02, SEC-04, RISK-02
affects: [phase-05, phase-06, any phase using trades table or InstitutionalGuard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "asyncio.run() wrapper pattern for testing async methods in Python 3.12 (no pytest-asyncio)"
    - "AsyncMock + patch.object for mocking async database methods in unit tests"
    - "Early-exit guard pattern: restricted-asset check fires before DB call (no mock needed)"

key-files:
  created: []
  modified:
    - src/core/persistence.py
    - tests/test_institutional_guard.py

key-decisions:
  - "Replace vacuous leverage test with concurrent-trades test matching actual check_compliance() code path"
  - "Add migration comment above CREATE TABLE for backward compatibility with existing DBs"
  - "Mock _get_open_positions at the class level via patch.object to avoid live PostgreSQL in tests"

patterns-established:
  - "AsyncMock pattern: patch.object(Class, '_async_method', new_callable=AsyncMock, return_value=...) for DB mocking"
  - "Early-exit paths (restricted asset) require no mock; downstream paths (DB call) require AsyncMock"

requirements-completed: [MEM-01, SEC-02, SEC-04, RISK-02]

# Metrics
duration: 5min
completed: 2026-03-07
---

# Phase 04 Plan 03: Gap Closure — trades DDL and Institutional Guard Tests Summary

**Fixed two silent pre-existing bugs: missing exit_time column in trades DDL and vacuous guard tests that were asserting against coroutine objects instead of result dicts**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-07T18:56:40Z
- **Completed:** 2026-03-07T19:02:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `exit_time TIMESTAMPTZ` to the trades CREATE TABLE DDL, eliminating the `psycopg.errors.UndefinedColumn` that InstitutionalGuard._get_open_positions() would raise against any live database
- Added migration comment above CREATE TABLE so existing databases can apply the column via ALTER TABLE
- Replaced all three tests in test_institutional_guard.py — each previously called async methods without asyncio.run(), making every assertion evaluate against a coroutine object rather than a dict
- Replaced the vacuous leverage test (checking a check_compliance() branch that does not exist) with a concurrent-trades test that exercises the actual production code path (len(open_positions) >= max_concurrent)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add exit_time column to trades DDL** - `ca1abd8` (fix)
2. **Task 2: Rewrite test_institutional_guard.py with asyncio.run() and AsyncMock** - `6488902` (fix)

## Files Created/Modified

- `src/core/persistence.py` — Added `exit_time TIMESTAMPTZ,` after `execution_time` in trades CREATE TABLE block; added migration comment above the statement
- `tests/test_institutional_guard.py` — Full rewrite: asyncio.run() wrappers, AsyncMock on _get_open_positions, leverage test replaced with concurrent-trades test

## Decisions Made

- **Replace leverage test with concurrent-trades test:** The original test_institutional_guard_leverage asserted `"leverage" in result["violation"]` but check_compliance() has no leverage check — it would never produce that violation. The replacement test exercises the actual `len(open_positions) >= max_concurrent` branch with 10 mocked positions.
- **Migration comment above CREATE TABLE:** Existing databases already have the trades table without exit_time. The comment makes the required ALTER TABLE obvious to any operator doing a schema upgrade without dropping and recreating.
- **patch.object at class level:** Using `patch.object(InstitutionalGuard, "_get_open_positions", new_callable=AsyncMock, return_value=[...])` rather than instance-level patching ensures consistent behavior across both single-path and dual-path tests.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. Both fixes were straightforward targeted changes: a single DDL line insertion and a full test file rewrite following the exact patterns specified in the plan interfaces block.

## Final Test Counts

- `tests/test_institutional_guard.py` — 3/3 passing
- Broader regression suite (institutional_guard + blackboard + budget + memory + memory_nodes) — 53/53 passing

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- SEC-02, SEC-04, and RISK-02 requirements each have at least one passing automated test
- InstitutionalGuard._get_open_positions() will no longer raise UndefinedColumn at runtime
- Phase 04 gap closure complete; Phase 05 can proceed

---
*Phase: 04-memory-compliance*
*Completed: 2026-03-07*
