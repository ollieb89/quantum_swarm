---
phase: 15-soul-foundation
plan: 02
subsystem: personas
tags: [soul-files, markdown, personas, identity, lru_cache, agents]

requires:
  - phase: 15-01
    provides: SoulLoader module (load_soul, warmup_soul_cache, AgentSoul dataclass)

provides:
  - 15 soul files across 5 agent directories (macro_analyst, bullish_researcher, bearish_researcher, quant_modeler, risk_manager)
  - AXIOM (macro_analyst): 3 fully-populated soul files with substantive prose and Drift Guard naming recency bias / momentum chasing
  - MOMENTUM (bullish_researcher): 3 skeleton soul files with correct H2 headers
  - CASSANDRA (bearish_researcher): 3 skeleton soul files with correct H2 headers
  - SIGMA (quant_modeler): 3 skeleton soul files with correct H2 headers
  - GUARDIAN (risk_manager): 3 skeleton soul files with correct H2 headers
  - MacroAnalyst LangGraph node now injects system_prompt and active_persona into SwarmState (SOUL-05)

affects:
  - Phase 16 (KAMI Merit Index): merit scores read from soul-aware agent nodes
  - Phase 17 (Agent Church): MEMORY.md diff targeting uses H2 section names established here
  - Phase 18 (Theory of Mind Soul-Sync): reads MEMORY.md context seeded by these souls
  - Phase 19 (ARS Drift Auditor): ARS regex parsing targets section headers defined here

tech-stack:
  added: []
  patterns:
    - "Soul files: H1 for title, H2 for canonical sections, H3 for optional substructure — no YAML frontmatter"
    - "Persona naming: AXIOM (macro), MOMENTUM (bullish), CASSANDRA (bearish), SIGMA (quant), GUARDIAN (risk)"
    - "Node soul injection: load_soul() called in node function, system_prompt + active_persona returned in state dict"

key-files:
  created:
    - src/core/souls/macro_analyst/IDENTITY.md
    - src/core/souls/macro_analyst/SOUL.md
    - src/core/souls/macro_analyst/AGENTS.md
    - src/core/souls/bullish_researcher/IDENTITY.md
    - src/core/souls/bullish_researcher/SOUL.md
    - src/core/souls/bullish_researcher/AGENTS.md
    - src/core/souls/bearish_researcher/IDENTITY.md
    - src/core/souls/bearish_researcher/SOUL.md
    - src/core/souls/bearish_researcher/AGENTS.md
    - src/core/souls/quant_modeler/IDENTITY.md
    - src/core/souls/quant_modeler/SOUL.md
    - src/core/souls/quant_modeler/AGENTS.md
    - src/core/souls/risk_manager/IDENTITY.md
    - src/core/souls/risk_manager/SOUL.md
    - src/core/souls/risk_manager/AGENTS.md
  modified:
    - src/graph/agents/analysts.py

key-decisions:
  - "MacroAnalyst wired to call load_soul('macro_analyst') and return system_prompt + active_persona in state — SOUL-05 requires injection at node level so downstream agents see persona context"
  - "Soul injection auto-fix applied in Task 2 (Rule 1 — Bug): test_macro_analyst_writes_system_prompt_to_state was RED before soul files existed; once files existed, the node still needed to call load_soul() to make the test GREEN"

patterns-established:
  - "AXIOM Drift Guard: two triggers — (1) recency bias/momentum chasing, (2) narrative capture — both cause drift_flags emission and confidence reduction of 0.15"
  - "Skeleton agents receive directional prose per section (2-4 sentences) as Phase 17 evolution seed"
  - "Output Contract JSON keys are defined per-persona in AGENTS.md and serve as the canonical contract for Phase 19 ARS regex parsing"

requirements-completed: [SOUL-02, SOUL-03]

duration: 22min
completed: 2026-03-08
---

# Phase 15 Plan 02: Soul Foundation Summary

**15 Markdown soul files authored — AXIOM fully populated with Drift Guard naming recency bias, four skeleton personas (MOMENTUM/CASSANDRA/SIGMA/GUARDIAN) with correct H2 sections, MacroAnalyst node wired to inject system_prompt into SwarmState**

## Performance

- **Duration:** 22 min
- **Started:** 2026-03-08T09:15:08Z
- **Completed:** 2026-03-08T09:37:00Z
- **Tasks:** 2
- **Files modified:** 16 (15 soul files created + 1 node modified)

## Accomplishments

- All 15 soul files created across 5 agent directories with correct H1/H2 structure and no YAML frontmatter
- AXIOM (macro_analyst) fully populated: 3 files with substantive institutional-voice prose; Drift Guard explicitly names recency bias and momentum chasing as primary trigger
- Four skeleton personas authored (MOMENTUM, CASSANDRA, SIGMA, GUARDIAN) with correct H2 sections and 2-4 sentences of directional prose per section
- warmup_soul_cache() passes all 5 agent IDs without error
- MacroAnalyst node wired to call load_soul("macro_analyst") and emit system_prompt + active_persona in state (SOUL-05 injection)
- 291 tests passing after all changes (up from 244 baseline at Phase 13 completion)

## Task Commits

1. **Task 1: Author AXIOM soul files** - `c7e9be9` (feat)
2. **Task 2: Author four skeleton soul dirs + wire MacroAnalyst soul injection** - `cc21933` (feat)

## Files Created/Modified

- `src/core/souls/macro_analyst/IDENTITY.md` - AXIOM identity: sections Identity, Archetype, Role in Swarm
- `src/core/souls/macro_analyst/SOUL.md` - AXIOM soul: Core Beliefs, Drift Guard (recency bias primary trigger), Voice, Non-Goals
- `src/core/souls/macro_analyst/AGENTS.md` - AXIOM output contract with full JSON schema + Decision Rules + Workflow
- `src/core/souls/bullish_researcher/IDENTITY.md` - MOMENTUM identity stub
- `src/core/souls/bullish_researcher/SOUL.md` - MOMENTUM soul stub
- `src/core/souls/bullish_researcher/AGENTS.md` - MOMENTUM output contract stub
- `src/core/souls/bearish_researcher/IDENTITY.md` - CASSANDRA identity stub
- `src/core/souls/bearish_researcher/SOUL.md` - CASSANDRA soul stub
- `src/core/souls/bearish_researcher/AGENTS.md` - CASSANDRA output contract stub
- `src/core/souls/quant_modeler/IDENTITY.md` - SIGMA identity stub
- `src/core/souls/quant_modeler/SOUL.md` - SIGMA soul stub
- `src/core/souls/quant_modeler/AGENTS.md` - SIGMA output contract stub
- `src/core/souls/risk_manager/IDENTITY.md` - GUARDIAN identity stub
- `src/core/souls/risk_manager/SOUL.md` - GUARDIAN soul stub
- `src/core/souls/risk_manager/AGENTS.md` - GUARDIAN output contract stub
- `src/graph/agents/analysts.py` - MacroAnalyst node: added load_soul() call + system_prompt/active_persona state injection

## Decisions Made

- MacroAnalyst wired to call load_soul("macro_analyst") and return system_prompt + active_persona in state — SOUL-05 requires injection at node level so downstream agents see persona context in the state dict
- Soul injection code placed after the agent invoke call (not before) so it doesn't block the mock agent in tests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] MacroAnalyst node not injecting system_prompt into state**
- **Found during:** Task 2 (full test suite run after writing skeleton files)
- **Issue:** test_macro_analyst_writes_system_prompt_to_state was RED — MacroAnalyst returned state dict without system_prompt or active_persona keys. The test was scaffolded in Plan 01 expecting Plan 02 to both create soul files AND wire the injection. The node was missing the load_soul() call entirely.
- **Fix:** Added `from src.core.soul_loader import load_soul` import and `soul = load_soul("macro_analyst")` call in MacroAnalyst(); returns system_prompt and active_persona in the state update dict
- **Files modified:** src/graph/agents/analysts.py
- **Verification:** All 6 TestMacroAnalystSoulInjection + TestAuditFieldExclusion tests pass
- **Committed in:** cc21933 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug)
**Impact on plan:** Essential for SOUL-05 correctness. No scope creep.

## Issues Encountered

- test_trade_warehouse_persistence continues to fail (pre-existing — PostgreSQL not available in local dev environment; confirmed pre-existing before Phase 15 work started)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 16 (KAMI Merit Index): Soul files exist and are loadable; warmup_soul_cache() passes all 5 agents; MacroAnalyst injects soul context into state — Phase 16 can begin building the merit scoring system on top of this foundation
- Soul H2 section names are canonical and locked for Phase 17 Agent Church diff targeting and Phase 19 ARS regex parsing
- Skeleton personas (MOMENTUM, CASSANDRA, SIGMA, GUARDIAN) have directional seeds ready for Phase 17 MEMORY.md evolution

---
*Phase: 15-soul-foundation*
*Completed: 2026-03-08*
