---
phase: 08-portfolio-risk-governance
plan: "01"
subsystem: testing
tags: [pytest, tdd, institutional-guard, risk-governance, portfolio-risk, drawdown, sql]

# Dependency graph
requires:
  - phase: 07-self-improvement-loop
    provides: Phase 6 schema rename (position_size/entry_price) that makes RISK-07 SQL tests meaningful
  - phase: 06-stop-loss-enforcement
    provides: trades DDL with position_size, entry_price, exit_time columns
provides:
  - Four failing RED test stubs defining Phase 8 implementation contract
  - GREEN confirmation of RISK-08 metadata passthrough in institutional_guard_node
  - test_get_open_positions_correct_columns (RED) — SQL column name fix contract
  - test_exit_time_index_exists (RED) — exit_time index gap contract
  - test_drawdown_circuit_breaker (RED) — drawdown rejection contract
  - test_drawdown_rejection (RED) — TestPortfolioRisk drawdown contract
  - test_guard_node_metadata_propagation (GREEN) — RISK-08 already works
affects:
  - 08-02-PLAN.md — implementation must drive all 4 RED stubs to GREEN

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "inspect.getsource() for SQL string validation without live DB"
    - "AssertionError-based RED stubs: call existing method, assert counterfactual outcome"
    - "AsyncMock patch.object for _get_open_positions avoids PostgreSQL in unit tests"
    - "asyncio.new_event_loop() in TestCase.test_* calling async helper methods"

key-files:
  created: []
  modified:
    - tests/test_institutional_guard.py
    - tests/test_portfolio_risk.py

key-decisions:
  - "Used inspect.getsource() to validate SQL column names without live DB — fails at assertion level not connection level"
  - "RED drawdown stubs call check_compliance() without drawdown mock so they return approved=True, then assert False — clean AssertionError"
  - "Added max_daily_loss/max_drawdown to TestPortfolioRisk.setUp so GREEN implementation can read config without setUp changes"
  - "test_guard_node_metadata_propagation included in Task 1 commit (not separate Task 2 commit) since it was appended in same action"

patterns-established:
  - "TDD RED stub pattern: call real method with mocked DB, assert the counterfactual (expected post-implementation result), get clean AssertionError"
  - "inspect.getsource() test pattern: validate SQL strings in source without DB connection"

requirements-completed: [RISK-07, RISK-08]

# Metrics
duration: 1min
completed: 2026-03-07
---

# Phase 08 Plan 01: Portfolio Risk Governance TDD RED Stubs

**Four failing test stubs establishing RISK-07 SQL/index/drawdown contract plus GREEN confirmation of RISK-08 metadata passthrough**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-07T21:38:08Z
- **Completed:** 2026-03-07T21:39:30Z
- **Tasks:** 2 (both in single commit)
- **Files modified:** 2

## Accomplishments
- Added 4 RED failing stubs to tests/test_institutional_guard.py and tests/test_portfolio_risk.py
- test_guard_node_metadata_propagation passes GREEN immediately — RISK-08 already implemented
- Added max_daily_loss and max_drawdown to TestPortfolioRisk.setUp for smooth GREEN transition
- All 7 pre-existing tests remain green (no regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1 + 2: Write failing stubs for RISK-07 and RISK-08 confirmation** - `fc632e4` (test)

_Note: Task 2 (RISK-08 confirmation test) was appended in the same file edit action as Task 1 and included in the same commit._

## Files Created/Modified
- `tests/test_institutional_guard.py` - Added import inspect, src.core.persistence; appended 4 new test functions
- `tests/test_portfolio_risk.py` - Added max_daily_loss/max_drawdown to setUp; appended test_drawdown_rejection

## Decisions Made
- Used `inspect.getsource(InstitutionalGuard._get_open_positions)` to validate SQL column names without a live DB connection — ensures test fails at AssertionError not connection error.
- RED drawdown stubs call `check_compliance()` without a drawdown mock (so current code returns approved=True), then `assert result["approved"] is False` — produces clean AssertionError as required.
- Added `max_daily_loss: 0.05` and `max_drawdown: 0.15` to `TestPortfolioRisk.setUp` now so Plan 08-02 implementation can read config without changing the test.
- Included test_guard_node_metadata_propagation in same commit as RISK-07 stubs since it was part of the same file append action.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 4 RED stubs define exact implementation contract for Plan 08-02
- Plan 08-02 must: fix SQL column names in _get_open_positions(), add idx_trades_exit_time index to setup_persistence(), implement drawdown circuit breaker in check_compliance()
- test_guard_node_metadata_propagation already GREEN — no RISK-08 implementation work needed

---
*Phase: 08-portfolio-risk-governance*
*Completed: 2026-03-07*
