---
phase: 14-fix-validation-gate-call-order
plan: 01
subsystem: testing
tags: [rule-validator, rule-generator, memory-registry, audit, tdd, mem-06]

# Dependency graph
requires:
  - phase: 10-rule-validation-harness
    provides: RuleValidator.validate_proposed_rules() with 2-of-3 backtest harness
  - phase: 12-mc01-mc02-gap-closure
    provides: persist_rules() wiring that introduced update_status("active") before validator (the bug)
provides:
  - "5 integration tests in tests/test_mem06_gate_order.py asserting correct MEM-06 gate order"
  - "RED test harness: 4/5 tests fail against Phase 12 buggy persist_rules(); all 5 pass against the fix"
affects: [14-02-fix-gate-call-order]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "recording_backtest side_effect pattern: captures registry state during validator execution to verify intermediate proposed status"
    - "patch.object(RuleValidator, 'validate_proposed_rules') wrapping to record processed count without breaking the real logic"
    - "_patch_validator_audit() helper centralises audit_path redirection via patched __init__ — reused from test_rule_validator.py pattern"

key-files:
  created:
    - tests/test_mem06_gate_order.py
  modified: []

key-decisions:
  - "Tests written to assert correct MEM-06 gate order (proposed → validator → active/rejected), not just the eventual outcome"
  - "Test 1 uses recording side_effect to observe registry state DURING validator backtest calls — catches premature promotion before the validator runs"
  - "Test 2 may pass incidentally (outcome=active is correct even with wrong path) — acceptable per plan spec"
  - "Deviation documented: working tree rule_generator.py already had the Phase 12 update_status bug removed, so all 5 tests pass GREEN against the working tree"

patterns-established:
  - "TDD RED verification via git stash: stash working-tree fix, run tests, confirm RED, pop stash, confirm GREEN — validates test quality before committing"

requirements-completed: [MEM-06]

# Metrics
duration: 12min
completed: 2026-03-08
---

# Phase 14 Plan 01: MEM-06 Gate Order RED Test Scaffold Summary

**5 integration tests asserting persist_rules() gate order: add_rule() as 'proposed', then validator exclusively promotes/rejects via 2-of-3 backtest harness**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-08T05:10:00Z
- **Completed:** 2026-03-08T05:22:00Z
- **Tasks:** 1 (single TDD RED scaffold task)
- **Files modified:** 1

## Accomplishments
- Wrote 5 integration tests documenting MEM-06 correct gate order in `tests/test_mem06_gate_order.py`
- Verified tests FAIL RED (4/5) against the committed Phase 12 buggy code via `git stash` round-trip
- Verified tests PASS GREEN (5/5) against the working-tree fix (update_status removed)
- Confirmed existing 16 tests in test_rule_validator.py + test_mem03_integration.py unaffected

## Test Names and RED/GREEN Status

Against committed Phase 12 buggy code (update_status before validator):

| Test | Name | Status |
|------|------|--------|
| 1 | test_rule_is_proposed_when_validator_backtests_run | **FAIL RED** |
| 2 | test_passing_backtest_promotes_to_active_via_validator | PASS (incidental — outcome correct, path wrong) |
| 3 | test_failing_backtest_rejects_rule_and_never_promotes | **FAIL RED** |
| 4 | test_validator_processes_at_least_one_proposed_rule | **FAIL RED** |
| 5 | test_audit_event_written_per_processed_rule | **FAIL RED** |

Against working-tree fix (update_status removed):

| Test | Name | Status |
|------|------|--------|
| 1 | test_rule_is_proposed_when_validator_backtests_run | PASS |
| 2 | test_passing_backtest_promotes_to_active_via_validator | PASS |
| 3 | test_failing_backtest_rejects_rule_and_never_promotes | PASS |
| 4 | test_validator_processes_at_least_one_proposed_rule | PASS |
| 5 | test_audit_event_written_per_processed_rule | PASS |

## Failure Messages for RED Tests (against buggy committed code)

**Test 1:**
```
AssertionError: MEM-06 RED: When validate_proposed_rules() runs its backtests,
the rule must still be in 'proposed' state (observed_proposed must be non-empty).
Currently persist_rules() calls update_status('active') BEFORE the validator,
so by the time backtests run, get_proposed_rules() returns [] and
observed_proposed is always empty.
```

**Test 3:**
```
AssertionError: MEM-06 RED: A rule failing the 2-of-3 harness must end up 'rejected'.
Got status='active'. Currently Phase 12 promotes to 'active' before the validator runs,
so a failing backtest cannot demote it — 'active -> rejected' is blocked
by VALID_TRANSITIONS when the rule is already active.
```

**Test 4:**
```
AssertionError: MEM-06 RED: validate_proposed_rules() must process at least 1 rule.
Got processed=0. Currently persist_rules() promotes the rule to 'active' before calling
the validator, so the validator finds [] proposed rules and returns 0.
```

**Test 5:**
```
AssertionError: MEM-06 RED: audit.jsonl must exist after persist_rules() runs the validator.
Currently no audit events are written because the validator finds [] proposed rules.
```

## Task Commits

1. **Task 1: Write 5 RED tests for MEM-06 gate order** - `1125c6f` (test)

**Plan metadata:** (included in final docs commit)

## Files Created/Modified
- `tests/test_mem06_gate_order.py` - 5 integration tests for MEM-06 gate order; recording side_effect pattern to observe registry during validator execution

## Decisions Made
- Tests assert the PROCESS (proposed state during validator) not just the outcome (active/rejected) — catching the Phase 12 wrong path even when the outcome looks correct
- _patch_validator_audit() extracted as a shared helper to avoid repetition across 4 tests that need audit_path redirection
- git stash round-trip used to validate RED state before committing the test file

## Deviations from Plan

### Deviation: Working tree already had the fix applied

**Found during:** Task 1 (writing tests)

**Issue:** The plan assumed the Phase 12 bug (`update_status("active")` before validator) was still present in `rule_generator.py`. The working tree had already removed that line (the fix was pre-applied before this plan ran). As a result, all 5 tests pass GREEN immediately against the working tree.

**Resolution:** Used `git stash` to temporarily restore the committed (buggy) version, confirmed 4/5 tests fail RED as expected, then popped the stash. The tests are correctly written as RED tests — they will fail against the committed code and pass after the working-tree fix is committed in Plan 02.

**Impact:** Plan 02 (the "fix" plan) can now simply commit the already-applied working-tree change to `rule_generator.py` rather than making new code changes.

**Type:** Informational deviation — no code change required, no scope impact.

---

**Total deviations:** 1 informational (pre-applied fix discovered in working tree)
**Impact on plan:** No scope change — tests are correctly RED against committed code and GREEN against the fix.

## Issues Encountered
- The `patch.object(RuleValidator, "__init__", patched_init)` pattern requires the patched `__init__` to use `**kwargs` (keyword arguments) not positional — the `RuleValidator.__init__` signature uses only kwargs after `self`, so this works correctly.

## Next Phase Readiness
- `tests/test_mem06_gate_order.py` provides the RED test harness Plan 02 will turn GREEN
- Working-tree `src/agents/rule_generator.py` already has the fix applied — Plan 02 commits it
- Modified `tests/test_mem03_integration.py` and `tests/test_structured_memory.py` also in working tree — Plan 02 should review and commit those too if they support MEM-06

---
*Phase: 14-fix-validation-gate-call-order*
*Completed: 2026-03-08*
