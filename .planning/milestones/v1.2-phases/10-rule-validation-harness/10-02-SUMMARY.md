---
phase: 10-rule-validation-harness
plan: "02"
subsystem: agents
tags: [rule-validation, backtesting, memory-registry, audit-trail, mifid-ii, nautilus-trader]

requires:
  - phase: 10-01
    provides: TDD RED test stubs (9 stubs), MemoryRegistry.get_proposed_rules(), swarm_config YAML keys

provides:
  - RuleValidator class with validate_proposed_rules(), _passes_validation(), _write_audit()
  - 2-of-3 majority vote on Sharpe / drawdown / win_rate metrics using NautilusTrader backtests
  - MiFID II audit events appended to data/audit.jsonl per promotion/rejection
  - evidence dict on each MemoryRule with six baseline/treatment metric keys

affects:
  - Phase 11 Explainability (reads audit.jsonl and rule.evidence for decision cards)
  - RuleGenerator (validate_proposed_rules() is called after persist_rules() in self-improvement loop)
  - src/graph/orchestrator.py (drives the full review -> generate -> validate cycle)

tech-stack:
  added: []
  patterns:
    - "asyncio.run(asyncio.to_thread(fn, ...)) pattern for calling synchronous backtester from synchronous context"
    - "Registry stale-read prevention: self.registry.schema = self.registry._load() at start of validate_proposed_rules()"
    - "Patch at consumer import path: patch('src.agents.rule_validator._run_nautilus_backtest')"
    - "Instance attributes redirectable in tests (.registry, .audit_path) — same isolation pattern as RuleGenerator"

key-files:
  created:
    - src/agents/rule_validator.py
  modified:
    - tests/test_rule_validator.py

key-decisions:
  - "validate_proposed_rules() is synchronous — called from synchronous persist_rules(); avoids nested asyncio.run() issues by calling asyncio.run(asyncio.to_thread(...)) per backtest call"
  - "drawdown improvement direction: treatment_drawdown > baseline_drawdown = improvement (less negative is better)"
  - "Evidence dict populated after update_status() call so the live registry object reflects the new values before save()"
  - "Backtest errors are caught and logged; rule stays proposed rather than raising — prevents one bad rule halting full batch"
  - "Tests replace NotImplementedError stubs with real assertions in same file from Plan 01"

patterns-established:
  - "RuleValidator pattern: no LLM dependency — pure data pipeline using backtester + registry"
  - "Audit JSONL append: create parent dirs, open in 'a' mode, json.dumps + newline per event"

requirements-completed:
  - MEM-06

duration: 12min
completed: 2026-03-08
---

# Phase 10 Plan 02: Rule Validation Harness Summary

**RuleValidator class: 2-of-3 NautilusTrader backtest gating that promotes or rejects proposed memory rules and writes MiFID II audit events to data/audit.jsonl**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-08T00:00:00Z
- **Completed:** 2026-03-08
- **Tasks:** 1 (TDD GREEN)
- **Files modified:** 2

## Accomplishments

- Implemented `src/agents/rule_validator.py` (~130 lines) with `RuleValidator` class
- `validate_proposed_rules()` runs two NautilusTrader backtests per proposed rule (baseline + treatment), applies 2-of-3 majority vote, updates registry status, writes audit events
- All 9 `TestRuleValidator` unit tests turned GREEN; 14/14 `TestStructuredMemory` tests still passing (23 total)

## Task Commits

1. **Task 1: Implement RuleValidator class (TDD GREEN)** - `f2d0d79` (feat)

## Files Created/Modified

- `src/agents/rule_validator.py` - RuleValidator with validate_proposed_rules(), _passes_validation(), _write_audit()
- `tests/test_rule_validator.py` - 9 NotImplementedError stubs replaced with passing assertions

## Decisions Made

- `validate_proposed_rules()` is synchronous and calls `asyncio.run(asyncio.to_thread(...))` twice per rule. This avoids the nested asyncio.run() problem since it is called from synchronous context (persist_rules()).
- Evidence is populated on the live rule object after `update_status()` so the registry's in-memory object reflects evidence before `save()`.
- Backtest exceptions are caught (Rule 1 scope): errors leave the rule in proposed state rather than raising, preventing one bad rule from halting the entire batch.
- Stale registry reload pattern applied: `self.registry.schema = self.registry._load()` at entry to pick up rules written by persist_rules() before the validator runs.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 10 complete: full rule validation harness operational (Plan 01: RED scaffold + infrastructure; Plan 02: GREEN implementation)
- Phase 11 Explainability can read `rule.evidence` and `data/audit.jsonl` for decision card generation
- Self-improvement loop end-to-end: PerformanceReviewAgent -> RuleGenerator.persist_rules() -> RuleValidator.validate_proposed_rules()

---
*Phase: 10-rule-validation-harness*
*Completed: 2026-03-08*
