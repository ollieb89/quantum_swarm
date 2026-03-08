---
phase: 07-self-improvement-loop
plan: "02"
subsystem: agents
tags: [postgresql, duckdb, memory, self-improvement, sql, tdd]

# Dependency graph
requires:
  - phase: 06-stop-loss-enforcement
    provides: "Phase 06 schema rename: quantity->position_size, execution_price->entry_price in trades table"
  - phase: 07-01
    provides: "PerformanceReviewAgent, RuleGenerator, SelfLearningPipeline, MEMORY.md dual-source loading"
provides:
  - "Corrected SQL query in review_agent.py using Phase 06 column names (position_size, entry_price)"
  - "persist_rules() appends PREFER/AVOID/CAUTION timestamped entries to data/MEMORY.md"
  - "test_persist_rules_writes_memory_md verifying MEMORY.md write path"
affects: ["phase-08-portfolio-risk-governance", "phase-09-structured-memory-registry"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "memory_md_path instance attribute on RuleGenerator enables test injection without monkeypatching module globals"
    - "_rule_to_prefix() maps MemoryRule.type + action values to PREFER/AVOID/CAUTION without schema changes"

key-files:
  created: []
  modified:
    - src/agents/review_agent.py
    - src/agents/rule_generator.py
    - tests/test_self_improvement.py

key-decisions:
  - "Derive PREFER/AVOID/CAUTION from action dict values (string matching 'avoid'/'reduce'/'short_only') rather than adding a new MemoryRule field — keeps schema stable"
  - "Expose memory_md_path as instance attribute on RuleGenerator so tests can patch it per-instance without module-level globals"

patterns-established:
  - "Instance-level path attributes for file outputs allow clean test isolation via direct attribute assignment"
  - "TDD RED-GREEN cycle enforced: test written first, confirmed failing, then implementation added"

requirements-completed: [MEM-02, MEM-03]

# Metrics
duration: 2min
completed: 2026-03-07
---

# Phase 07 Plan 02: Gap-Closure Summary

**SQL column fix (quantity->position_size, execution_price->entry_price) and MEMORY.md append path in persist_rules() close the two Phase 7 verification gaps (MEM-02, MEM-03), bringing all 5 self-improvement tests to green.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-07T21:05:17Z
- **Completed:** 2026-03-07T21:07:01Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Fixed SQL column name mismatch in `get_recent_trade_data()`: `t.quantity`/`t.execution_price` corrected to `t.position_size`/`t.entry_price` per Phase 06 schema (commit 2f70422)
- Added `_rule_to_prefix()` helper and MEMORY.md append block to `persist_rules()` so the pipeline writes parseable PREFER/AVOID/CAUTION lines after every JSON registry save
- Added `test_persist_rules_writes_memory_md` using a temp file to verify the write path without polluting real MEMORY.md; 5/5 tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix SQL column names in review_agent.py** - `9375e5e` (fix)
2. **Task 2: Add MEMORY.md write path and test (TDD RED->GREEN)** - `5f540d4` (feat)

## Files Created/Modified
- `src/agents/review_agent.py` - SQL SELECT and row mapping updated to position_size/entry_price
- `src/agents/rule_generator.py` - Added datetime/Path imports, memory_md_path attribute, _rule_to_prefix(), updated persist_rules()
- `tests/test_self_improvement.py` - Added test_persist_rules_writes_memory_md

## Decisions Made
- Derived PREFER/AVOID/CAUTION prefix from action dict string values rather than adding a field to MemoryRule — avoids schema churn and keeps the format stable for _load_institutional_memory()
- Exposed memory_md_path as an instance attribute (not a module-level constant) so each test can redirect writes to a temp file without module-level patching

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 7 verification gap count drops from 2/5 to 0/5: both MEM-02 (SQL schema) and MEM-03 (MEMORY.md write) are now satisfied
- Phase 8 (Portfolio Risk Governance) and Phase 9 (Structured Memory Registry) can proceed; they both consume persist_rules() output via MEMORY.md

---
*Phase: 07-self-improvement-loop*
*Completed: 2026-03-07*
