---
phase: 10-rule-validation-harness
plan: "01"
subsystem: testing
tags: [tdd, rule-validation, memory-registry, yaml-config, pytest]

# Dependency graph
requires:
  - phase: 09-structured-memory-registry
    provides: MemoryRegistry class with add_rule/update_status, MemoryRule model, get_active_rules()
provides:
  - 11 TDD RED stubs in tests/test_rule_validator.py (TestRuleValidator + TestRuleValidatorIntegration)
  - MemoryRegistry.get_proposed_rules() method
  - config/swarm_config.yaml validation_lookback_days and validation_min_trades keys
affects:
  - 10-02 (GREEN phase: implements RuleValidator to turn stubs green)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED scaffold: import fails with ModuleNotFoundError until implementation module is created"
    - "Test isolation via instance attribute redirect: validator.registry = MemoryRegistry(tmp_path); validator.audit_path = Path(tmp_audit)"
    - "Shared mock backtest result dicts (_BASELINE_RESULT, _TREATMENT_IMPROVED, _TREATMENT_WORSE) at module level for reuse across test cases"

key-files:
  created:
    - tests/test_rule_validator.py
  modified:
    - src/core/memory_registry.py
    - config/swarm_config.yaml

key-decisions:
  - "No separate config-keys stub test needed — config loading is verified implicitly through test_insufficient_trades_skipped behaviour"
  - "10 test stubs (not 11) in original commit; removed test_config_keys_read stub in fix commit to align unit count with must_haves (9 unit + 2 integration = 11)"
  - "get_proposed_rules() mirrors get_active_rules() pattern exactly — one-line filter on status == 'proposed'"

patterns-established:
  - "RuleValidator test isolation: redirect .registry and .audit_path instance attributes to temp paths — same pattern as RuleGenerator"
  - "Wave 0 scaffold: every behaviour expressed as failing test before implementation begins"

requirements-completed:
  - MEM-06

# Metrics
duration: 1min
completed: 2026-03-08
---

# Phase 10 Plan 01: Rule Validation Harness Summary

**TDD RED scaffold: 11 failing stubs across TestRuleValidator/TestRuleValidatorIntegration, MemoryRegistry.get_proposed_rules() added, and validation config keys wired into swarm_config.yaml**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-07T23:18:06Z
- **Completed:** 2026-03-07T23:19:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `tests/test_rule_validator.py` with 11 stub methods (9 unit + 2 integration) all failing RED via `ModuleNotFoundError` on `src.agents.rule_validator`
- Added `MemoryRegistry.get_proposed_rules()` immediately after `get_active_rules()`, mirroring the exact filter pattern; 14/14 existing structured memory tests still pass
- Added `validation_lookback_days: 90` and `validation_min_trades: 10` to `config/swarm_config.yaml` under `self_improvement`

## Task Commits

Each task was committed atomically:

1. **Task 1: Write test stubs for RuleValidator (TDD RED)** - `f426a0c` (test)
2. **Task 2: Add get_proposed_rules() to MemoryRegistry + YAML config keys** - `94c65e1` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `tests/test_rule_validator.py` - 11 TDD RED stubs across TestRuleValidator (9 unit) and TestRuleValidatorIntegration (2 integration); all raise NotImplementedError
- `src/core/memory_registry.py` - Added `get_proposed_rules()` method at line ~67, alongside `get_active_rules()`
- `config/swarm_config.yaml` - Added `validation_lookback_days: 90` and `validation_min_trades: 10` under `self_improvement`

## Decisions Made

- No separate `test_config_keys_read` stub was needed: the plan spec clarifies config loading is verified implicitly via `test_insufficient_trades_skipped` (validator must read config to know `min_trades`).
- `get_proposed_rules()` one-liner mirrors `get_active_rules()` exactly — no additional logic required at this stage.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 0 scaffold complete: all 11 stubs RED, confirming no implementation exists yet
- Plan 02 (GREEN phase) can now implement `src/agents/rule_validator.py` and turn all 11 stubs green
- `MemoryRegistry.get_proposed_rules()` is ready for `RuleValidator.__init__` to call
- YAML config keys `validation_lookback_days` and `validation_min_trades` are readable by `yaml.safe_load`

---
*Phase: 10-rule-validation-harness*
*Completed: 2026-03-08*
