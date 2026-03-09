---
phase: 23-full-persona-population
plan: 01
subsystem: testing
tags: [pytest, hexaco, drift-guard, persona, parametrize]

requires:
  - phase: 15-soul-foundation
    provides: soul_loader, AgentSoul, drift_eval, _KNOWN_AGENTS

provides:
  - 98-test RED suite validating structure, drift_guard, HEXACO-6, and pairwise distance for all 5 agents
  - Corrected HEXACO distance threshold (>1.0 normalized) in planning docs

affects: [23-02, 23-03, 23-04]

tech-stack:
  added: []
  patterns:
    - "Parametrized persona content tests over _KNOWN_AGENTS"
    - "_parse_hexaco() helper for extracting HEXACO-6 YAML from SOUL.md"

key-files:
  created: []
  modified:
    - tests/core/test_persona_content.py
    - .planning/REQUIREMENTS.md

key-decisions:
  - "ROADMAP.md already had correct >1.0 threshold from planning phase; only REQUIREMENTS.md needed update"

patterns-established:
  - "TestAllAgentStructure: parametrize over sorted(_KNOWN_AGENTS) for structural section checks"
  - "TestHexacoDistances: pairwise Euclidean distance via itertools.combinations + math.sqrt"

requirements-completed: [PERS-05, PERS-06]

duration: 2min
completed: 2026-03-09
---

# Phase 23 Plan 01: Test Scaffolding + Threshold Update Summary

**98-test RED suite covering structural sections, drift_guard YAML, HEXACO-6 profiles, and pairwise distance for all 5 agents, plus HEXACO threshold correction to >1.0 in planning docs**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-09T00:23:59Z
- **Completed:** 2026-03-09T00:25:23Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Extended test_persona_content.py from 13 AXIOM-only tests to 98 tests covering all 5 agents
- Added 4 new test classes: TestAllAgentStructure (60 tests), TestAllAgentDriftGuard (15 tests), TestHexacoProfiles (15 tests), TestHexacoDistances (1 test)
- Corrected PERS-05 threshold from >3.0 to >1.0 on normalized 0.0-1.0 scale in REQUIREMENTS.md
- Tests collect without import errors (RED phase — failures expected until Plans 02-04 author content)

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend persona content tests for all 5 agents + HEXACO-6 + drift_guard** - `792634d` (test)
2. **Task 2: Update ROADMAP.md and REQUIREMENTS.md HEXACO threshold** - `0146a50` (docs)

## Files Created/Modified
- `tests/core/test_persona_content.py` - Extended with 4 new parametrized test classes for all-agent validation
- `.planning/REQUIREMENTS.md` - PERS-05 threshold corrected from >3.0 to >1.0 on normalized scale

## Decisions Made
- ROADMAP.md already had the correct >1.0 threshold from the planning phase, so only REQUIREMENTS.md needed updating

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Test suite ready to validate Plans 02-04 content authoring
- All 98 tests will progressively turn green as MOMENTUM, CASSANDRA, SIGMA, and GUARDIAN personas are authored
- HEXACO-6 distance threshold confirmed at >1.0

---
*Phase: 23-full-persona-population*
*Completed: 2026-03-09*
