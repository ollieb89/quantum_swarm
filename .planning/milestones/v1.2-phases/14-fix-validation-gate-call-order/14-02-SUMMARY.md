---
phase: 14-fix-validation-gate-call-order
plan: 02
subsystem: testing
tags: [rule-validator, rule-generator, memory-registry, audit, mem-06, tdd]

# Dependency graph
requires:
  - phase: 14-fix-validation-gate-call-order
    plan: 01
    provides: "5 RED tests in test_mem06_gate_order.py; working-tree fix already applied to rule_generator.py"
  - phase: 10-rule-validation-harness
    provides: RuleValidator.validate_proposed_rules() with 2-of-3 backtest harness
provides:
  - "persist_rules() for loop calls only add_rule() — no premature update_status in loop"
  - "MEM-06 gate order enforced: proposed → validator → active/rejected with audit trail"
  - "Updated MC-01 tests using backtest mocks to drive validator-mediated promotion"
  - "All 21 tests across test_mem06_gate_order.py + test_mem03_integration.py + test_rule_validator.py pass GREEN"
affects: [15-phase-next, any-phase-using-persist_rules, memory-registry-consumers]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Backtest mock side_effect pattern for MC-01 tests: patch _run_nautilus_backtest with [BASELINE, PASS] to drive validator promotion without live NautilusTrader"
    - "patched_init closure pattern: redirect RuleValidator.audit_path to tmp file via patch.object(__init__) without changing production interface"

key-files:
  created: []
  modified:
    - src/agents/rule_generator.py
    - tests/test_mem03_integration.py
    - tests/test_structured_memory.py

key-decisions:
  - "Committed working-tree fix directly — line removed was self.registry.update_status(rule.id, 'active') from the for loop in persist_rules() (old line ~113)"
  - "test_structured_memory.py included in Task 2 commit — stale assertions from Phase 12 (direct promotion) updated to match MEM-06 validator-mediated path"
  - "4 pre-existing failures in test_knowledge_base.py (duckdb env) + 2 errors in test_audit_chain.py (psycopg DB) — not caused by this plan, documented as known env issues"

patterns-established:
  - "MEM-06 gate order: add_rule() as 'proposed' → validate_proposed_rules() → update_status('active'/'rejected') — enforced in persist_rules()"
  - "Stale direct-promotion tests updated with backtest mocks so test correctness tracks production behavior"

requirements-completed: [MEM-06]

# Metrics
duration: 10min
completed: 2026-03-08
---

# Phase 14 Plan 02: Fix Validation Gate Call Order Summary

**MEM-06 closed: removed premature update_status('active') from persist_rules() so validator is the sole promoter; 21 target tests pass GREEN (5+5+11)**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-08T06:16:10Z
- **Completed:** 2026-03-08T06:26:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Committed the working-tree fix: removed `self.registry.update_status(rule.id, "active")` from the for loop in `persist_rules()` (was line ~113 in `src/agents/rule_generator.py`)
- Updated 2 MC-01 tests in `test_mem03_integration.py` to use `_run_nautilus_backtest` mocks so they pass via the validator path (not the removed direct promotion path)
- Updated 2 stale tests in `test_structured_memory.py` from Phase 12 direct-promotion assertions to MEM-06 validator-mediated assertions
- Full 21-test suite passes GREEN: 5 gate-order tests + 5 integration tests + 11 validator tests
- Full regression suite: 246 passed, 0 new failures (4 pre-existing duckdb failures + 2 psycopg errors unchanged)

## Exact Change in rule_generator.py

**Removed line** (was in the for loop of persist_rules(), around line 113):
```python
self.registry.update_status(rule.id, "active")   # REMOVED — MEM-06
```

**Before:**
```python
for rule in rules:
    self.registry.add_rule(rule)
    self.registry.update_status(rule.id, "active")
```

**After:**
```python
for rule in rules:
    self.registry.add_rule(rule)
```

The validator wiring at the end of `persist_rules()` (lines 123-126) is unchanged:
```python
validator = RuleValidator()
validator.registry = self.registry
validator.validate_proposed_rules()
```

## Lines Changed in test_mem03_integration.py

**test_persist_rules_promotes_to_active** — Before (inner call only):
```python
with patch.object(RuleValidator, "__init__", patched_init):
    rg.persist_rules([temp_rule])
```

**After:**
```python
with patch.object(RuleValidator, "__init__", patched_init):
    with patch(
        "src.agents.rule_validator._run_nautilus_backtest",
        side_effect=[
            {"sharpe_ratio": 1.0, "max_drawdown": -0.10, "win_rate": 0.50, "total_trades": 15},
            {"sharpe_ratio": 1.5, "max_drawdown": -0.05, "win_rate": 0.60, "total_trades": 15},
        ],
    ):
        rg.persist_rules([temp_rule])
```

Docstring updated from Phase 12 "MC-01" framing to Phase 14 "MEM-06 validator-mediated" framing.

**test_persist_rules_active_rules_accessible_across_registry_instances** — same backtest mock added around the persist_rules() call. The fresh_registry cross-instance durability check is unchanged.

## Full Test Results

```
tests/test_mem06_gate_order.py — 5/5 PASS
tests/test_mem03_integration.py — 5/5 PASS
tests/test_rule_validator.py — 11/11 PASS
Total: 21 passed in 1.81s
```

Full regression (excluding known-broken files):
```
246 passed, 9 warnings, 4 failed (duckdb env), 2 errors (psycopg pool) in 554s
0 new failures caused by this plan
```

## Task Commits

1. **Task 1: Remove premature update_status from persist_rules()** - `2e15a5d` (fix)
2. **Task 2: Update MC-01 tests to backtest mocks; fix structured_memory stale assertions** - `10fd721` (test)

## Files Created/Modified

- `src/agents/rule_generator.py` — Removed update_status(rule.id, "active") from persist_rules() for loop; docstring updated to reflect MEM-06 gate order
- `tests/test_mem03_integration.py` — Two MC-01 tests updated to use _run_nautilus_backtest mock with [BASELINE, PASS] side_effect; docstring updated for MEM-06
- `tests/test_structured_memory.py` — Two stale direct-promotion tests updated: test_persist_rules_stores_proposed now asserts "proposed" (not "active") when validator is no-op; test_promote_rule_appears_in_active uses backtest mock to drive real validator promotion

## Decisions Made

- Working-tree `rule_generator.py` fix was pre-applied before this plan ran (noted in 14-01 SUMMARY as informational deviation). Plan 02 committed it directly without re-making the change.
- `test_structured_memory.py` included in Task 2 commit — the stale assertions were directly caused by the same production behavior change and needed to be updated in the same wave.
- Pre-existing test failures in `test_knowledge_base.py` (duckdb IOError) and `test_audit_chain.py` (psycopg pool) are env issues unrelated to this plan — documented, not fixed.

## Deviations from Plan

### Deviation: test_structured_memory.py updated (not in plan scope)

**Rule:** Rule 2 (Auto-add missing critical functionality) / Rule 1 (Auto-fix bug)

**Found during:** Task 2 (verifying full test suite)

**Issue:** `test_structured_memory.py` had two tests with stale Phase 12 assertions — `test_persist_rules_stores_proposed` asserted `status == "active"` after persist_rules() with a no-op validator mock, and `test_promote_rule_appears_in_active` expected active rules without mocking the backtest. Both would FAIL against the production fix if left unchanged.

**Fix:** Updated `test_persist_rules_stores_proposed` to assert `status == "proposed"` (validator mocked as no-op, so no promotion); updated `test_promote_rule_appears_in_active` to use the real validator with backtest mock returning improved metrics.

**Files modified:** `tests/test_structured_memory.py`

**Committed in:** `10fd721` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — stale test assertions that would fail against the production fix)
**Impact on plan:** Required for correctness — stale tests guarding old wrong behavior would hide regressions. No scope creep.

## MEM-06 Gap Closure Confirmation

MEM-06 is fully closed:
- `persist_rules()` adds rules as 'proposed' via `add_rule()` — no premature promotion
- `validate_proposed_rules()` is the sole code path transitioning rules from 'proposed' to 'active' or 'rejected'
- Rules passing the 2-of-3 backtest harness end up 'active' after `persist_rules()` returns
- Rules failing the 2-of-3 backtest harness end up 'rejected' after `persist_rules()` returns
- Each validation outcome writes one event line to `data/audit.jsonl`
- All 5 tests in `test_mem06_gate_order.py` pass GREEN
- All 5 tests in `test_mem03_integration.py` pass GREEN
- All 11 tests in `test_rule_validator.py` pass GREEN

## Issues Encountered

None — working-tree fix was pre-applied; plan executed as verification and commit of existing correct state.

## Next Phase Readiness

- MEM-06 fully satisfied: validator-gated rule promotion with audit trail
- Phase 14 complete (2/2 plans done)
- 246 tests passing (excluding 2 known-broken env files)
- Ready for next phase

---
*Phase: 14-fix-validation-gate-call-order*
*Completed: 2026-03-08*
