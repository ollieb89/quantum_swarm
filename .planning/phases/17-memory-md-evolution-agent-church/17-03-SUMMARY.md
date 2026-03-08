---
phase: 17-memory-md-evolution-agent-church
plan: 03
subsystem: agent-soul
tags: [agent-church, soul-proposal, soul-loader, lru-cache, memory-writer, orchestrator, langgraph, pydantic, tdd]

# Dependency graph
requires:
  - phase: 17-01
    provides: memory_writer_node, MEMORY.md structured log entries, HANDLE_TO_AGENT_ID mapping
  - phase: 17-02
    provides: SoulProposal model, write_proposal_atomic, PROPOSALS_DIR, RequiresHumanApproval in soul_errors.py
  - phase: 15
    provides: soul_loader.py (load_soul lru_cache, warmup_soul_cache, SOULS_DIR), AgentSoul frozen dataclass

provides:
  - src/core/agent_church.py standalone review script (EVOL-03 complete)
  - review_proposals() with 5 structural heuristics + L1 self-proposal guard
  - _replace_h2_section() regex-based SOUL.md section patch
  - memory_writer_node wired into orchestrator graph: merit_updater → memory_writer → trade_logger
  - 5 unit tests for agent_church behaviours
  - 2 import boundary assertions (isolated import + source-level graph check)
  - 1 graph wiring test confirming memory_writer position

affects:
  - phase-18 (Theory of Mind Soul-Sync): reads MEMORY.md and SOUL.md after Agent Church can mutate them
  - phase-19 (ARS Drift Auditor): reads [KAMI_DELTA:] markers; SOUL.md evolution now gated by Agent Church

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Standalone __main__ script pattern for out-of-band graph operations (Agent Church is NOT a LangGraph node)"
    - "Phase 15 cache invalidation order: load_soul.cache_clear() always before warmup_soul_cache()"
    - "HANDLE_TO_AGENT_ID copied into agent_church.py — do not import from src.graph.nodes (Import Layer Law)"
    - "Structural heuristic rejection: section-exists, char-limit, non-empty content/reasons"
    - "L1 self-proposal guard: agent_id not in ALL_SOUL_HANDLES raises RequiresHumanApproval (propagates to caller)"

key-files:
  created:
    - src/core/agent_church.py
    - tests/core/test_agent_church.py
  modified:
    - src/graph/orchestrator.py
    - tests/core/test_import_boundaries.py
    - tests/test_graph_wiring.py

key-decisions:
  - "Agent Church is a standalone __main__ script — NOT a LangGraph node (blocking node causes deadlock and L1 self-approval conflict-of-interest)"
  - "RequiresHumanApproval is raised and NOT caught inside review_proposals — propagates to __main__ caller"
  - "SOUL.md write uses synchronous Path.write_text (single-writer; Agent Church is out-of-band, not concurrent)"
  - "Rejection order: char-limit checked before section-existence to short-circuit I/O on trivially oversized content"
  - "memory_writer_node wired between merit_updater and trade_logger replacing the Phase 16 direct edge"

patterns-established:
  - "Agent Church approval sequence: L1 guard → char limit → empty content → empty reasons → section exists → approve"
  - "Cache refresh pattern: load_soul.cache_clear() then warmup_soul_cache() — always this order (Phase 15 locked)"
  - "Standalone scripts in src.core.* run via python -m src.core.<module> — no src.graph imports permitted"

requirements-completed:
  - EVOL-03

# Metrics
duration: 4min
completed: 2026-03-08
---

# Phase 17 Plan 03: Agent Church + Orchestrator Wiring Summary

**Agent Church standalone review script with 5 structural heuristics and L1 self-proposal guard, memory_writer_node wired into orchestrator graph between merit_updater and trade_logger, completing EVOL-03**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-08T13:41:35Z
- **Completed:** 2026-03-08T13:45:05Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- `src/core/agent_church.py` implements `review_proposals()` with L1 self-proposal guard, section-existence check, char-limit heuristic, empty-content/reasons guards, and Phase 15 cache invalidation order
- Orchestrator graph updated: `merit_updater → memory_writer → trade_logger` chain (replaces former direct edge)
- 5 Agent Church unit tests pass; 2 import boundary assertions added; 1 graph wiring test verifying the edge chain
- Full test suite: 362 passing (up from 354 in Phase 17-02); 1 pre-existing PostgreSQL failure unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Agent Church standalone script + tests** - `c116b66` (feat + test — TDD RED/GREEN)
2. **Task 2: Orchestrator wiring + import boundary assertions** - `28a013f` (feat)

**Plan metadata:** (final commit — this SUMMARY + STATE + ROADMAP)

## Files Created/Modified

- `src/core/agent_church.py` — Standalone Agent Church review script: `review_proposals()`, `_replace_h2_section()`, `_apply_proposal()`, `_reject_proposal()`, `_get_soul_path()`, `_is_l1_orchestrator()`, `_load_p17_config()`; `__main__` block
- `tests/core/test_agent_church.py` — 5 unit tests: approves, rejects-missing-section, rejects-too-long, l1-raises, cache-refresh
- `src/graph/orchestrator.py` — Added `memory_writer_node` import, `add_node("memory_writer")`, edge chain `merit_updater → memory_writer → trade_logger`
- `tests/core/test_import_boundaries.py` — Added `test_agent_church_imports_cleanly` (isolated import) + `test_agent_church_does_not_import_graph` (source-level)
- `tests/test_graph_wiring.py` — Added `test_memory_writer_wired_between_merit_updater_and_trade_logger`

## Decisions Made

- Agent Church is a standalone `__main__` script (not a LangGraph node) — blocking node causes deadlock and enables L1 self-approval conflict-of-interest; this is locked design from STATE.md accumulated context
- `RequiresHumanApproval` propagates from `review_proposals()` to caller — not caught internally — so the `__main__` block and any programmatic caller receives the exception and can decide how to handle it
- `HANDLE_TO_AGENT_ID` is copied into `agent_church.py` (not imported from `memory_writer.py`) to maintain the Import Layer Law — `src.graph.nodes` is forbidden from `src.core.*`
- Rejection order places char-limit before section-existence check to avoid reading SOUL.md on trivially oversized content

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- EVOL-01 (memory_writer_node writing MEMORY.md entries), EVOL-02 (SoulProposal triggers), and EVOL-03 (Agent Church review) are all complete — Phase 17 MEMORY.md Evolution + Agent Church is fully satisfied end-to-end
- Phase 18 (Theory of Mind Soul-Sync) can now read MEMORY.md context entries and SOUL.md files that may have been mutated by Agent Church
- Phase 19 (ARS Drift Auditor) can read `[KAMI_DELTA:]` markers from MEMORY.md written by EVOL-01; SOUL.md evolution is now gated by Agent Church structural heuristics

---
*Phase: 17-memory-md-evolution-agent-church*
*Completed: 2026-03-08*
