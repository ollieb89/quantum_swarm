---
phase: 12-mem03-integration-fix
plan: "01"
subsystem: testing
tags: [tdd, mem-03, memory-registry, analysts, red-scaffold, integration-tests]

# Dependency graph
requires:
  - phase: 07-self-improvement-loop
    provides: "RuleGenerator.persist_rules(), MacroAnalyst/QuantModeler with institutional memory"
  - phase: 09-structured-memory-registry
    provides: "MemoryRegistry lifecycle, get_active_rules(), update_status()"
  - phase: 10-rule-validation-harness
    provides: "RuleValidator.validate_proposed_rules() auto-wired in persist_rules()"
  - phase: 11-explainability-decision-cards
    provides: "analysts.py with macro_report/quant_proposal state fields"
provides:
  - "TDD RED scaffold: 5 tests in tests/test_mem03_integration.py"
  - "MC-01 failure signal: persist_rules() does not promote rules to active"
  - "MC-02 failure signal: memory message not forwarded into analyst invoke() calls"
  - "Regression guard: test_macro_analyst_no_memory_state_still_works"
affects: [12-02-PLAN, plan-02-implementation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RuleGenerator test isolation: redirect .registry and .memory_md_path to tmp_path fixtures"
    - "Analyst memory-forwarding test: capture invoke.call_args[0][0]['messages'] to inspect first message"
    - "RuleValidator patch via patch.object(RuleValidator, 'validate_proposed_rules', return_value=0) to suppress live backtests"
    - "Memory message assertions: check .content attribute or dict 'content' key generically — no hardcoded LangChain types"

key-files:
  created:
    - tests/test_mem03_integration.py
  modified: []

key-decisions:
  - "RuleValidator.validate_proposed_rules patched to return_value=0 (not mocked to promote) — ensures test isolates the MC-01 gap: persist_rules() itself must promote, not the validator"
  - "Memory message checked generically (hasattr .content else dict['content']) so test survives Plan 02 converting dict -> LangChain message type"
  - "Regression guard test (no memory state) placed in same file alongside RED tests to signal that Plan 02 must not break empty-state path"

patterns-established:
  - "Test isolation for RuleGenerator: redirect instance attributes .registry and .memory_md_path to tmp_path after construction — no mocks needed for persistence layer"
  - "TDD RED docstring convention: each failing test documents the exact line number in production code that causes the failure and the Plan 02 fix"

requirements-completed: [MEM-03]

# Metrics
duration: 2min
completed: 2026-03-08
---

# Phase 12 Plan 01: MEM-03 Integration Fix — TDD RED Scaffold Summary

**5 failing tests that precisely describe MC-01 (rule lifecycle promotion gap) and MC-02 (institutional memory not forwarded into analyst sub-graph invocations)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-08T02:23:29Z
- **Completed:** 2026-03-08T02:25:08Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created tests/test_mem03_integration.py with 5 test functions covering both integration gaps identified in v1.1 milestone audit
- MC-01 (2 tests): Precisely describe that persist_rules() leaves rules as "proposed", get_active_rules() returns [], both in-memory and on fresh registry load
- MC-02 (2 tests): Precisely describe that MacroAnalyst and QuantModeler invoke() is called with 1 message (only the query), not 2+ (memory + query)
- Regression guard (1 test): Confirms no-memory state path works — passes before and after Plan 02 implementation
- Zero regressions in 9 existing test_analysts.py tests

## Task Commits

1. **Task 1: TDD RED scaffold for MC-01 and MC-02** - `8cb707d` (test)

## Files Created/Modified

- `tests/test_mem03_integration.py` — 5 tests: 2 for MC-01 rule lifecycle, 2 for MC-02 memory forwarding, 1 regression guard

## Decisions Made

- Patched RuleValidator.validate_proposed_rules to return 0 (no-op) rather than mocking it to promote rules. This ensures the test isolates the correct gap: the fix must live in persist_rules() itself (calling update_status after add_rule), not in the validator path.
- Memory message assertions use duck-typing (hasattr .content else dict.get("content")) so the test file doesn't need updating when Plan 02 converts raw dicts to LangChain message objects.
- Placed the regression guard (no-memory state) in the same file alongside the RED tests — it will naturally turn from a passing regression guard into a confirmed working test post-Plan 02.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — all imports resolved, test isolation patterns worked as documented in STATE.md accumulated context.

## Next Phase Readiness

- Plan 02 (12-02) can now proceed with full automated failure signal in place
- Fix targets are precisely identified: persist_rules() must call registry.update_status(rule.id, "active") and analysts.py must prepend memory message to invoke() calls
- All 4 RED tests will turn GREEN when Plan 02 implementation is complete
- Regression guard test provides immediate feedback if no-memory path is accidentally broken

---
*Phase: 12-mem03-integration-fix*
*Completed: 2026-03-08*
