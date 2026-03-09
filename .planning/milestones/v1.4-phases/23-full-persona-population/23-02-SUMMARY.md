---
phase: 23-full-persona-population
plan: 02
subsystem: personas
tags: [soul-files, drift-guard, yaml, adversarial-debate, persona-authoring]

requires:
  - phase: 23-01
    provides: "Test scaffolding and threshold validation for persona content"
  - phase: 15
    provides: "Soul Foundation: AgentSoul dataclass, load_soul(), drift_eval.py"
provides:
  - "MOMENTUM fully authored persona (SOUL.md, IDENTITY.md, AGENTS.md) with 3 drift_guard rules"
  - "CASSANDRA fully authored persona (SOUL.md, IDENTITY.md, AGENTS.md) with 3 drift_guard rules"
affects: [23-03, 23-04]

tech-stack:
  added: []
  patterns:
    - "Adversarial debate pair: MOMENTUM catalyst-driven bullish vs CASSANDRA forensic bearish"
    - "drift_guard YAML with keyword_ratio, keyword_any, and regex rule types"

key-files:
  created: []
  modified:
    - src/core/souls/bullish_researcher/SOUL.md
    - src/core/souls/bullish_researcher/IDENTITY.md
    - src/core/souls/bullish_researcher/AGENTS.md
    - src/core/souls/bearish_researcher/SOUL.md
    - src/core/souls/bearish_researcher/IDENTITY.md
    - src/core/souls/bearish_researcher/AGENTS.md

key-decisions:
  - "3 drift rules per agent (not 2) for comprehensive coverage: thesis_recycling + unbounded_optimism + vague_catalyst for MOMENTUM; catastrophism + reflexive_contrarianism + certainty_in_doom for CASSANDRA"
  - "target_price as range (floor-ceiling) enforced via decision rule, not point estimate"

patterns-established:
  - "L3 researcher persona pattern: SOUL ~500 words, IDENTITY ~250 words, AGENTS ~300 words with 6 decision rules and 6 workflow steps"
  - "Adversarial pair voice differentiation: short declarative sentences (MOMENTUM) vs longer logical chains (CASSANDRA)"

requirements-completed: [PERS-01, PERS-02]

duration: 3min
completed: 2026-03-09
---

# Phase 23 Plan 02: Researcher Personas Summary

**MOMENTUM and CASSANDRA fully authored with maximally distinct voices — catalyst-punchy vs forensic-skeptical — each with 3 drift_guard YAML rules and 6 decision rules**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-09T00:27:36Z
- **Completed:** 2026-03-09T00:30:38Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- MOMENTUM (bullish_researcher) expanded from ~150-word skeleton to ~500-word fully authored persona with punchy, catalyst-driven voice
- CASSANDRA (bearish_researcher) expanded from ~150-word skeleton to ~510-word fully authored persona with forensic, risk-anchored voice
- Both agents have 3 drift_guard YAML rules that parse correctly via parse_drift_guard_yaml()
- Voices are immediately distinguishable: MOMENTUM uses short declarative sentences with price targets; CASSANDRA builds longer logical chains with percentiles and analogues
- All 28 non-Hexaco persona content tests pass for both researchers

## Task Commits

Each task was committed atomically:

1. **Task 1: Fully author MOMENTUM persona** - `587b9e9` (feat)
2. **Task 2: Fully author CASSANDRA persona** - `ff20135` (feat)

## Files Created/Modified

- `src/core/souls/bullish_researcher/SOUL.md` - MOMENTUM full soul: Core Beliefs (catalyst timing, regime awareness), Drift Guard (thesis_recycling, unbounded_optimism, vague_catalyst), Voice (punchy/directional), Non-Goals
- `src/core/souls/bullish_researcher/IDENTITY.md` - MOMENTUM identity: growth hunter, catalyst-driven analyst archetype, adversarial counterpart to CASSANDRA
- `src/core/souls/bullish_researcher/AGENTS.md` - MOMENTUM contract: 7 output keys (incl. drift_flags), 6 decision rules (incl. recycling cap, range targets), 6 workflow steps
- `src/core/souls/bearish_researcher/SOUL.md` - CASSANDRA full soul: Core Beliefs (hidden cost of consensus, unpriced risks, fatal flaw mandate), Drift Guard (catastrophism, reflexive_contrarianism, certainty_in_doom), Voice (forensic/specific), Non-Goals
- `src/core/souls/bearish_researcher/IDENTITY.md` - CASSANDRA identity: stress tester, methodological contrarian archetype, adversarial counterweight role
- `src/core/souls/bearish_researcher/AGENTS.md` - CASSANDRA contract: 7 output keys (incl. drift_flags), 6 decision rules (incl. loss transmission mechanism), 6 workflow steps

## Decisions Made

- Used 3 drift rules per agent (not minimum 2) for comprehensive coverage of each agent's distinct failure modes
- MOMENTUM target_price enforced as range via decision rule 6, matching institutional practice of floor-ceiling estimates
- Voices designed as maximal contrast pair: MOMENTUM short/active/numeric vs CASSANDRA long/logical/forensic

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- MOMENTUM and CASSANDRA fully authored, ready for Plan 03 (GUARDIAN and SIGMA)
- Plan 04 (HEXACO-6 profiles) has pre-existing test scaffolding that expects Personality Profile sections — these will be addressed in Plan 04 as designed
- All 6 files load cleanly via load_soul() with full drift rule parsing

---
*Phase: 23-full-persona-population*
*Completed: 2026-03-09*
