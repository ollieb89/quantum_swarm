---
phase: 16-kami-merit-index
plan: "02"
subsystem: graph
tags: [kami, merit-scores, langgraph, postgresql, psycopg3, ema, tdd]

requires:
  - phase: 16-01
    provides: KAMI arithmetic core (KAMIDimensions, compute_merit, apply_ema, signal helpers, ALL_SOUL_HANDLES, DEFAULT_MERIT)
  - phase: 15-soul-foundation
    provides: active_persona and system_prompt SwarmState fields, soul_loader

provides:
  - merit_loader_node async function (session-start DB read → SwarmState["merit_scores"])
  - merit_updater_node async function (post-execution EMA update for Recovery/Consensus/Fidelity → DB persist)
  - Graph wiring: merit_loader as entry point → classify_intent; merit_updater between decision_card_writer and trade_logger
  - initial_state includes merit_scores: None plus Phase 15 soul fields

affects:
  - 16-03
  - 17-memory-evolution
  - 18-theory-of-mind

tech-stack:
  added: []
  patterns:
    - "merit_loader: idempotency guard — populated state returns {} without DB call"
    - "merit_updater: DB-first write — returns {} on DB failure to keep DB and state in sync"
    - "merit_updater: Accuracy dimension is read-only in-cycle (deferred async path only)"
    - "KAMI node pattern: lightweight async nodes that mock get_pool() via unittest.mock for unit tests"

key-files:
  created:
    - src/graph/nodes/merit_loader.py
    - src/graph/nodes/merit_updater.py
  modified:
    - src/graph/orchestrator.py
    - tests/core/test_merit_loader.py
    - tests/core/test_merit_updater.py

key-decisions:
  - "merit_updater returns {} on DB failure rather than proceeding with state update — DB and in-memory state must stay in sync"
  - "Accuracy dimension is never updated in-cycle — deferred to post-trade resolution path in a later phase"
  - "merit_loader entry point replaces classify_intent as graph entry point; merit_loader → classify_intent edge added"

patterns-established:
  - "KAMI node test pattern: _make_pool_mock() factory builds AsyncMock cursor with async for row iteration via __aiter__"
  - "Persist-before-state pattern: DB write happens before state dict return; failure returns {} not partial state"

requirements-completed:
  - KAMI-03

duration: 8min
completed: 2026-03-08
---

# Phase 16 Plan 02: KAMI Merit Index Summary

**merit_loader and merit_updater LangGraph nodes wired into orchestrator: DB-backed KAMI merit scores loaded at session start and EMA-updated (Recovery/Consensus/Fidelity) after each completed cycle**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-08T11:10:00Z
- **Completed:** 2026-03-08T11:18:10Z
- **Tasks:** 2 (TDD: 2 RED/GREEN cycles)
- **Files modified:** 5

## Accomplishments

- merit_loader_node: cold-start defaults all 5 soul handles to 0.5 when DB has no rows; idempotency guard skips DB on populated state
- merit_updater_node: applies EMA to Recovery, Consensus, Fidelity via apply_ema; Accuracy is preserved in-cycle; DB-first write with {} return on failure
- Orchestrator rewired: merit_loader is now the graph entry point; merit_updater spliced between decision_card_writer and trade_logger
- 9 real tests replacing 7 skipped Plan 01 stubs; 333 total tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create merit_loader_node and implement test_merit_loader.py** - `7866e49` (feat)
2. **Task 2: Create merit_updater_node, implement test_merit_updater.py, wire orchestrator** - `bfa8e36` (feat)

**Plan metadata:** (docs commit follows)

_Note: TDD tasks — RED confirmed (ModuleNotFoundError) before each GREEN implementation._

## Files Created/Modified

- `src/graph/nodes/merit_loader.py` — Session-start async node: SELECT from agent_merit_scores, cold-start fill, idempotency guard
- `src/graph/nodes/merit_updater.py` — Post-execution async node: EMA on 3 dimensions, UPSERT to agent_merit_scores, DB-first pattern
- `src/graph/orchestrator.py` — Added imports, add_node for both, set_entry_point("merit_loader"), spliced merit_updater between decision_card_writer and trade_logger, merit_scores: None in initial_state
- `tests/core/test_merit_loader.py` — 4 real tests: cold_start, no_accumulation, idempotent, reads_db_values
- `tests/core/test_merit_updater.py` — 5 real tests: persists, skips_aborted_cycle, db_fail_no_state_update, accuracy_unchanged, rounds_to_4dp

## Decisions Made

- merit_updater returns {} on DB failure rather than returning partially-computed state — this keeps the PostgreSQL agent_merit_scores table and the in-memory SwarmState["merit_scores"] dict strictly in sync (no divergence even on transient DB errors)
- Accuracy dimension is never updated in-cycle — it requires post-trade outcome data that is only available via an async path in a later phase; in-cycle it is read and preserved unchanged
- merit_loader is the new graph entry point, replacing classify_intent directly — every LangGraph session starts with a DB read or cold-start fill before any analysis runs

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- `git stash pop` conflicted on a `.pyc` binary after verifying pre-existing test failure; resolved by `git checkout stash -- <files>` + `git stash drop`. No code changes required.

## Next Phase Readiness

- KAMI-03 requirement fully satisfied: merit scores live in the graph, loaded at session start, updated after each cycle
- Phase 16-03 (KAMI threshold routing / Phase 17 prereqs) can proceed
- The merit_scores dict in SwarmState is available to all downstream nodes for merit-weighted routing decisions

---
*Phase: 16-kami-merit-index*
*Completed: 2026-03-08*
