---
phase: 23-full-persona-population
plan: 03
subsystem: souls
tags: [persona, drift-guard, soul-loader, quant-modeler, risk-manager]

requires:
  - phase: 23-01
    provides: "test scaffolding and drift_guard threshold update"
  - phase: 15-soul-foundation
    provides: "AgentSoul dataclass, load_soul(), drift_eval parser"
provides:
  - "Fully authored SIGMA (quant_modeler) persona with 3 drift_guard YAML rules"
  - "Fully authored GUARDIAN (risk_manager) persona with 3 drift_guard YAML rules"
affects: [23-04-hexaco-profiles, soul-sync, ars-drift-auditor]

tech-stack:
  added: []
  patterns:
    - "Drift guard YAML: keyword_any for semantic drift, regex for numeric precision drift"
    - "Voice differentiation: SIGMA=statistics-lead claim-then-evidence, GUARDIAN=procedural binary short-sentence"

key-files:
  created: []
  modified:
    - src/core/souls/quant_modeler/SOUL.md
    - src/core/souls/quant_modeler/IDENTITY.md
    - src/core/souls/quant_modeler/AGENTS.md
    - src/core/souls/risk_manager/SOUL.md
    - src/core/souls/risk_manager/IDENTITY.md
    - src/core/souls/risk_manager/AGENTS.md

key-decisions:
  - "3 drift rules per agent (overfit_signal + false_precision + untested_signal for SIGMA; threshold_erosion + scope_creep + ambiguous_approval for GUARDIAN)"
  - "GUARDIAN drift_flags are informational (warning note) not auto-reject — risk constraints are the gate, not drift"

patterns-established:
  - "Voice contrast pattern: mathematical/statistics-lead vs procedural/binary for differentiated agent personas"
  - "Non-Goals cross-reference pattern: each agent explicitly cites which other agent owns excluded capabilities"

requirements-completed: [PERS-03, PERS-04]

duration: 3min
completed: 2026-03-09
---

# Phase 23 Plan 03: SIGMA and GUARDIAN Persona Population Summary

**Fully authored SIGMA (quant_modeler) and GUARDIAN (risk_manager) from ~150-word skeletons to ~500-word personas with 3 drift_guard YAML rules each**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-09T00:27:39Z
- **Completed:** 2026-03-09T00:30:24Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- SIGMA: statistics-lead voice with overfit_signal, false_precision (regex), and untested_signal drift rules
- GUARDIAN: procedural/non-negotiable voice with threshold_erosion, scope_creep, and ambiguous_approval (regex) drift rules
- Both agents expanded from 3-4 decision rules to 7 each, with explicit workflow steps
- Voices are maximally distinct: SIGMA uses claim-then-evidence structure with confidence intervals; GUARDIAN uses short binary sentences with constraint citations

## Task Commits

Each task was committed atomically:

1. **Task 1: Fully author SIGMA (quant_modeler) persona** - `c1e5243` (feat)
2. **Task 2: Fully author GUARDIAN (risk_manager) persona** - `ed58cd9` (feat)

## Files Created/Modified
- `src/core/souls/quant_modeler/SOUL.md` - Full SIGMA personality: Core Beliefs, Drift Guard (3 YAML rules), Voice, Non-Goals
- `src/core/souls/quant_modeler/IDENTITY.md` - SIGMA identity with archetype and peer relations
- `src/core/souls/quant_modeler/AGENTS.md` - SIGMA agents contract with 7 decision rules, 7 workflow steps
- `src/core/souls/risk_manager/SOUL.md` - Full GUARDIAN personality: Core Beliefs, Drift Guard (3 YAML rules), Voice, Non-Goals
- `src/core/souls/risk_manager/IDENTITY.md` - GUARDIAN identity with archetype and peer relations
- `src/core/souls/risk_manager/AGENTS.md` - GUARDIAN agents contract with 7 decision rules, 6 workflow steps

## Decisions Made
- Used 3 drift rules per agent (plan suggested 2-3, went with 3 for comprehensive coverage)
- GUARDIAN drift_flags are informational only (add warning note, don't auto-reject) — risk constraints remain the sole gate
- Both agents include `drift_flags` in output contract for downstream visibility

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Test `test_soul_has_personality_profile_section` fails for quant_modeler/risk_manager — expected, as plan explicitly defers `## Personality Profile` to Plan 04

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- SIGMA and GUARDIAN fully authored and loading via `load_soul()` without errors
- Ready for Plan 04: HEXACO-6 personality profiles for all agents
- All 28 relevant persona content tests pass (excluding hexaco tests which are Plan 04 scope)

## Self-Check: PASSED

- All 7 files found on disk
- Both task commits verified (c1e5243, ed58cd9)
- Line counts meet minimums: SOUL.md 42/40, IDENTITY.md 15/15, AGENTS.md 39/20 (SIGMA); SOUL.md 42/40, IDENTITY.md 15/15, AGENTS.md 32/20 (GUARDIAN)
- Both agents load via load_soul() with 3 drift rules each

---
*Phase: 23-full-persona-population*
*Completed: 2026-03-09*
