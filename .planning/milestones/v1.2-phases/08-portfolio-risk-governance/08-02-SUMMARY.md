---
phase: 08-portfolio-risk-governance
plan: "02"
subsystem: security
tags: [psycopg3, postgres, institutional-guard, risk-management, drawdown, tdd]

# Dependency graph
requires:
  - phase: 08-01-portfolio-risk-governance
    provides: "TDD RED stubs for SQL column fix, exit_time index, and drawdown circuit breaker"
  - phase: 06-stop-loss-enforcement
    provides: "Phase 6 DDL schema rename: quantity->position_size, execution_price->entry_price"
provides:
  - "Fixed _get_open_positions() SQL using Phase 6 column names (position_size, entry_price)"
  - "idx_trades_exit_time index in setup_persistence() for open-position query performance"
  - "Drawdown circuit breaker in check_compliance() — blocks trades when daily loss > 5% of starting_capital"
  - "_get_daily_pnl() async helper (psycopg3, safe-fail 0.0 on DB error)"
  - "RISK-07 and RISK-08 fully satisfied; all 11 portfolio risk tests passing"
affects: [order-routing, trade-logging, phase-09, phase-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Drawdown circuit breaker: safe-fail async DB query (0.0 on error) prevents blocking trades on DB failure"
    - "TDD stub update pattern: placeholder stubs updated with real AsyncMock when implementation is ready"
    - "Internal dict key aliasing: position_size/entry_price from DB mapped to quantity/price internally for backward compat"

key-files:
  created: []
  modified:
    - src/security/institutional_guard.py
    - src/core/persistence.py
    - tests/test_institutional_guard.py
    - tests/test_portfolio_risk.py

key-decisions:
  - "Internal dict keys kept as 'quantity'/'price' after SQL fix so existing check_compliance() arithmetic unchanged"
  - "Drawdown safe-fail returns 0.0 (not raise) so DB unavailability never blocks legitimate trades"
  - "test_drawdown_circuit_breaker and test_drawdown_rejection stubs updated from placeholder assertions to real AsyncMock(_get_daily_pnl, -60000.0)"

patterns-established:
  - "Drawdown check position: after concentration check, before risk scoring — max checks fail-fast before expensive scoring"
  - "Safe-fail DB helpers: any DB query helper that reads non-critical data returns neutral default on exception"

requirements-completed: [RISK-07, RISK-08]

# Metrics
duration: 15min
completed: 2026-03-07
---

# Phase 08 Plan 02: Portfolio Risk Governance — Implementation Summary

**RISK-07 drawdown circuit breaker + SQL schema fix: all 4 RED stubs from 08-01 turned GREEN; 11/11 portfolio risk tests passing**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-07T21:45:00Z
- **Completed:** 2026-03-07T22:00:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Fixed `_get_open_positions()` SQL to use `position_size` and `entry_price` (Phase 6 schema rename), with internal aliasing to `quantity`/`price` preserving all downstream logic
- Added `idx_trades_exit_time` index to `setup_persistence()` DDL for efficient open-position queries
- Implemented `_get_daily_pnl()` async method with psycopg3 pool, COALESCE for null safety, safe-fail 0.0 on exception
- Inserted drawdown circuit breaker into `check_compliance()` after concentration check: rejects trades when daily loss exceeds 5% (max_daily_loss) of starting_capital
- Updated placeholder test stubs to use `AsyncMock(_get_daily_pnl, return_value=-60000.0)` — clean mock-driven tests requiring no live DB

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix _get_open_positions() SQL and add exit_time index** - `8fd94ce` (fix)
2. **Task 2: Implement drawdown circuit breaker in check_compliance()** - `d5bca89` (feat)

## Files Created/Modified

- `src/security/institutional_guard.py` - SQL fix, max_daily_loss/max_drawdown init, _get_daily_pnl() method, drawdown circuit breaker in check_compliance()
- `src/core/persistence.py` - Added idx_trades_exit_time index to trades DDL
- `tests/test_institutional_guard.py` - Updated test_drawdown_circuit_breaker stub with _get_daily_pnl AsyncMock
- `tests/test_portfolio_risk.py` - Updated test_drawdown_rejection stub with _get_daily_pnl AsyncMock

## Decisions Made

- Internal dict keys kept as `quantity`/`price` after SQL rename so `check_compliance()` arithmetic (`p["quantity"] * p["price"]`) unchanged — zero-impact SQL fix
- Drawdown check safe-fails to 0.0 rather than raising, so DB unavailability never blocks trades — operational resilience over strict enforcement
- Test stubs updated from placeholder `assert False` to real mock pattern per plan spec — both drawdown tests now document the exact rejection contract

## Deviations from Plan

None - plan executed exactly as written. Test stub updates were specified in the plan as expected follow-on work.

## Issues Encountered

None — all four RED stubs transitioned to GREEN cleanly. Pre-existing failures in `test_order_router.py` (4) and `test_persistence.py` (1) remain unchanged.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RISK-07 and RISK-08 fully satisfied
- `InstitutionalGuard` now enforces: restricted assets, max concurrent trades, max notional exposure, asset concentration, and daily drawdown — complete portfolio risk enforcement layer
- Phase 9 (Structured Memory Registry) and Phase 10 (Rule Validation Harness) can proceed; guard is stable
- Pre-existing test failures in order_router and persistence are pre-Phase-8 issues, not blockers

---
*Phase: 08-portfolio-risk-governance*
*Completed: 2026-03-07*
