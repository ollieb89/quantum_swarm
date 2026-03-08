---
phase: 20-wire-drift-flags-pipeline
plan: 01
subsystem: core
tags: [drift-detection, dataclass, yaml-parser, soul-loader, frozen-dataclass]

# Dependency graph
requires:
  - phase: 15-soul-foundation
    provides: "AgentSoul frozen dataclass, load_soul with lru_cache, SOUL.md file structure"
provides:
  - "DriftRule frozen dataclass with 5 fields"
  - "parse_drift_guard_yaml() YAML extractor and validator"
  - "evaluate_drift() multi-rule evaluator for keyword_ratio, keyword_any, regex"
  - "AgentSoul.drift_rules field populated at load time"
  - "AXIOM SOUL.md machine-readable drift_guard YAML block"
affects: [20-02-wire-drift-flags-pipeline, memory-writer, ars-auditor]

# Tech tracking
tech-stack:
  added: [pyyaml]
  patterns: [yaml-in-markdown-extraction, fail-soft-drift-parse, frozen-rule-tuples]

key-files:
  created:
    - src/core/drift_eval.py
    - tests/core/test_drift_eval.py
  modified:
    - src/core/soul_loader.py
    - src/core/souls/macro_analyst/SOUL.md
    - tests/core/test_soul_loader.py

key-decisions:
  - "Fail-soft on malformed YAML: log warning, set drift_rules=() — agent functions without drift eval rather than crashing"
  - "drift_rules field is last in AgentSoul (Python dataclass default-after-non-default rule)"
  - "certainty_overreach regex rule derived from AXIOM Voice section ('Certainty language is absent')"

patterns-established:
  - "YAML-in-Markdown: drift_guard rules in fenced ```yaml blocks within ## Drift Guard section"
  - "Rule validation at parse time: fail-fast on bad rules, fail-soft at load time"
  - "evaluate_drift returns list[str] of flag_ids — downstream consumers check membership"

requirements-completed: [EVOL-02, ARS-01]

# Metrics
duration: 3min
completed: 2026-03-08
---

# Phase 20 Plan 01: DriftRule + YAML Parser + Evaluator Summary

**DriftRule frozen dataclass with YAML parser and 3-type evaluator (keyword_ratio, keyword_any, regex) wired into AgentSoul at load time**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-08T17:42:14Z
- **Completed:** 2026-03-08T17:45:02Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- DriftRule frozen dataclass with 5 fields, full validation at parse time
- YAML parser extracts drift_guard block from ## Drift Guard section of SOUL.md
- evaluate_drift supports keyword_ratio (token ratio), keyword_any (substring), regex (pattern match)
- AgentSoul.drift_rules populated automatically at load_soul() time with fail-soft error handling
- AXIOM SOUL.md has 3 structured rules: recency_bias, narrative_capture, certainty_overreach
- 43 tests passing (24 drift_eval + 19 soul_loader including 4 new integration tests)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: DriftRule + parse + evaluate tests** - `3d84bbb` (test)
2. **Task 1 GREEN: DriftRule + parse + evaluate impl** - `ba12856` (feat)
3. **Task 2: AgentSoul extension + AXIOM YAML + integration tests** - `aec648f` (feat)

_Note: Task 1 followed TDD (RED then GREEN commits)_

## Files Created/Modified
- `src/core/drift_eval.py` - DriftRule dataclass, parse_drift_guard_yaml, evaluate_drift, SUPPORTED_TYPES
- `src/core/souls/macro_analyst/SOUL.md` - Added YAML drift_guard block with 3 rules
- `src/core/soul_loader.py` - Added drift_rules field to AgentSoul, import and call parse_drift_guard_yaml in load_soul
- `tests/core/test_drift_eval.py` - 24 unit tests covering all rule types and validation
- `tests/core/test_soul_loader.py` - 4 new integration tests for drift_rules field

## Decisions Made
- Fail-soft on malformed YAML: log warning and set drift_rules=() rather than crash — agent functions without drift eval
- drift_rules placed as last field in AgentSoul (Python dataclass requires defaults after non-defaults)
- certainty_overreach regex rule derived from AXIOM Voice section which says "Certainty language is absent"

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DriftRule + evaluate_drift ready for Plan 02 to wire into memory_writer_node
- AXIOM's 3 rules available via load_soul("macro_analyst").drift_rules
- Skeleton agents return empty drift_rules (safe no-op path)

## Self-Check: PASSED

- All 5 files exist on disk
- All 3 commits verified in git log

---
*Phase: 20-wire-drift-flags-pipeline*
*Completed: 2026-03-08*
