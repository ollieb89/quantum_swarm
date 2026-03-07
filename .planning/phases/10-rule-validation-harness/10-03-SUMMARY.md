---
phase: 10-rule-validation-harness
plan: "03"
subsystem: agents
tags: [rule-validator, rule-generator, memory-registry, backtest, integration-tests, MEM-06]

requires:
  - phase: 10-02
    provides: RuleValidator with validate_proposed_rules() synchronous interface and audit trail
  - phase: 09-01
    provides: MemoryRegistry with get_proposed_rules() and update_status() lifecycle controls

provides:
  - persist_rules() auto-fires RuleValidator.validate_proposed_rules() after every registry write
  - Integration tests verifying the full persist -> validate -> promote/reject chain
  - MEM-06 fully satisfied: proposed rules auto-promote or auto-reject via backtest harness

affects: [phase-11-explainability, self-improvement-loop, rule-generator, rule-validator]

tech-stack:
  added: []
  patterns:
    - "Shared registry instance pattern: validator.registry = self.registry ensures validator sees in-flight rules without disk round-trip"
    - "RuleValidator.__init__ patching: redirect audit_path in integration tests by wrapping original_init"

key-files:
  created: []
  modified:
    - src/agents/rule_generator.py
    - tests/test_rule_validator.py

key-decisions:
  - "persist_rules() creates a RuleValidator inline (not injected) and assigns self.registry to share the same MemoryRegistry instance — validator's internal _load() refresh is safe because both sides reference the same object"
  - "Integration tests redirect validator.audit_path via patched __init__ wrapper rather than constructor injection — minimises changes to RuleValidator interface"
  - "Integration tests call rg.persist_rules([rule]) with mocked backtester (not validate_proposed_rules() directly) to verify auto-wiring end-to-end"

patterns-established:
  - "Auto-wiring pattern: side-effecting agents call downstream agents inline at the end of their write path, sharing the same registry instance"
  - "Integration test isolation: redirect .registry and .memory_md_path on RuleGenerator; redirect .audit_path on RuleValidator via patched __init__"

requirements-completed: [MEM-06]

duration: 5min
completed: 2026-03-08
---

# Phase 10 Plan 03: Rule Validation Harness — Integration Wiring Summary

**persist_rules() auto-calls RuleValidator.validate_proposed_rules() after every registry write, closing the self-improvement loop end-to-end; 2 integration tests verify the full chain with mocked backtester, 30/30 tests green**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-07T23:26:10Z
- **Completed:** 2026-03-07T23:31:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Wired `RuleGenerator.persist_rules()` to call `RuleValidator.validate_proposed_rules()` automatically after writing rules to the registry — no manual call required
- Replaced two integration test stubs with real assertions that call `rg.persist_rules([rule])` and verify zero rules remain in proposed state
- Full phase gate: 11/11 TestRuleValidator + TestRuleValidatorIntegration, 14/14 TestStructuredMemory, 5/5 TestSelfImprovement — 30 tests, zero failures
- MEM-06 requirement fully satisfied

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire persist_rules() to call RuleValidator** - `7a63135` (feat)
2. **Task 2: Implement integration test stubs** - `cc58d20` (feat)

## Files Created/Modified

- `src/agents/rule_generator.py` — Added `from src.agents.rule_validator import RuleValidator` import and 3-line inline call at end of `persist_rules()` after logger.info()
- `tests/test_rule_validator.py` — Replaced TestRuleValidatorIntegration stubs with real test_persist_then_validate and test_full_audit_trail assertions that drive the chain through `rg.persist_rules()`

## Decisions Made

- Shared registry instance: `validator.registry = self.registry` avoids stale-read issues; RuleValidator's internal `_load()` call at entry of `validate_proposed_rules()` refreshes from disk safely on the shared object
- Integration test audit_path redirection: patched `RuleValidator.__init__` wraps `original_init` then sets `self_v.audit_path = test_audit_file` — cleaner than constructor injection which would require changing the production interface
- Tests call `rg.persist_rules([rule])` (not `validator.validate_proposed_rules()` directly) to verify the auto-wiring is real, not a test artifact

## Deviations from Plan

The integration tests in TestRuleValidatorIntegration already existed in GREEN form (calling `validate_proposed_rules()` directly) from Plan 10-02 work. The stubs from Plan 10-01 had been replaced during 10-02. Task 2 updated them to call `rg.persist_rules([rule])` to verify the auto-wiring specifically — this was the intended behaviour described in the plan's must_haves ("A full cycle — persist_rules([rule]) then implicit validation").

None — plan executed exactly as written for the core wiring and test implementation.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 10 fully complete: MemoryRegistry lifecycle + RuleValidator + auto-wiring from persist_rules()
- MEM-06 verified: proposed rules automatically promoted or rejected via backtest harness
- Phase 11 (Explainability & Decision Cards) can proceed; rule evidence dict (six metric keys) is stable

---
*Phase: 10-rule-validation-harness*
*Completed: 2026-03-08*

## Self-Check: PASSED

- src/agents/rule_generator.py: FOUND
- tests/test_rule_validator.py: FOUND
- 10-03-SUMMARY.md: FOUND
- Commits 7a63135, cc58d20: FOUND
