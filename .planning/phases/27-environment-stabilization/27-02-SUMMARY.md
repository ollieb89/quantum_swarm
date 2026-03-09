---
phase: 27-environment-stabilization
plan: 02
subsystem: testing
tags: [pytest, asyncio, pytest-asyncio, postgresql]

requires:
  - phase: 27-01
    provides: "asyncio_mode=auto in pyproject.toml, lazy ccxt init"
provides:
  - "Clean test files with no redundant @pytest.mark.asyncio decorators"
  - "Full test suite green (680 passed, 4 skipped, 0 failures)"
  - "PostgreSQL tests isolated with skipif markers"
affects: [28-test-hardening, 29-ci-pipeline]

tech-stack:
  added: []
  patterns: ["asyncio_mode=auto handles all async test detection", "PG_AVAILABLE skipif pattern for infrastructure tests"]

key-files:
  created: []
  modified:
    - tests/test_data_fetcher.py
    - tests/test_calibration.py
    - tests/test_dexter_bridge.py
    - tests/test_audit_chain.py
    - tests/test_persistence.py
    - tests/test_trade_logger.py
    - tests/test_knowledge_base.py

key-decisions:
  - "Used per-test _pg_skip markers on test_audit_chain.py to preserve non-PG test_merit_scores_in_audit_hash"
  - "Used module-level pytestmark on test_persistence.py since all tests require PG"

patterns-established:
  - "PG skipif pattern: PG_AVAILABLE = bool(os.getenv('DB_URL')); pytestmark = pytest.mark.skipif(not PG_AVAILABLE, ...)"
  - "No @pytest.mark.asyncio decorators needed with asyncio_mode=auto"

requirements-completed: [ENV-03, ENV-04]

duration: 20min
completed: 2026-03-09
---

# Phase 27 Plan 02: Strip Async Decorators Summary

**Removed 19 redundant @pytest.mark.asyncio decorators and achieved fully green test suite (680 passed, 4 skipped, 0 failures)**

## Performance

- **Duration:** 20 min
- **Started:** 2026-03-09T15:51:49Z
- **Completed:** 2026-03-09T16:11:49Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Stripped all 19 @pytest.mark.asyncio decorators from 7 test files
- Removed unused pytest imports from 4 files where decorator was only pytest usage
- Added PG skipif markers to isolate PostgreSQL-dependent tests
- Full suite: 680 passed, 4 skipped, 0 failures (above 681 baseline when counting skips)

## Task Commits

Each task was committed atomically:

1. **Task 1: Strip @pytest.mark.asyncio decorators** - `8448578` (refactor)
2. **Task 2: Verify full suite green + PG isolation** - `834c796` (fix)

## Files Created/Modified
- `tests/test_data_fetcher.py` - Removed 5 decorators + unused pytest import
- `tests/test_calibration.py` - Removed 4 decorators (kept pytest for approx)
- `tests/test_dexter_bridge.py` - Removed 3 decorators (kept pytest for raises)
- `tests/test_audit_chain.py` - Removed 2 decorators, added PG skip on 2 tests
- `tests/test_persistence.py` - Removed 2 decorators, added module-level PG skip
- `tests/test_trade_logger.py` - Removed 2 decorators + unused pytest import
- `tests/test_knowledge_base.py` - Removed 1 decorator + unused pytest import

## Decisions Made
- Used per-test skip markers on test_audit_chain.py rather than module-level, because test_merit_scores_in_audit_hash is a pure unit test that does not need PG
- Used module-level pytestmark on test_persistence.py since all tests in that file require PostgreSQL

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 27 environment stabilization complete (both plans done)
- All environment-related test failures resolved
- Ready for Phase 28 (test hardening) or subsequent phases

---
*Phase: 27-environment-stabilization*
*Completed: 2026-03-09*
