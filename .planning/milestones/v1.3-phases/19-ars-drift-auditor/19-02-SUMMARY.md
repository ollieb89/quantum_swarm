---
phase: 19-ars-drift-auditor
plan: 02
subsystem: safety
tags: [ars, evolution-suspension, memory-writer, systemd-timer, scope-boundary]

# Dependency graph
requires:
  - phase: 19-ars-drift-auditor
    plan: 01
    provides: "ARS auditor with _suspend_agent/_unsuspend_agent, evolution_suspended column in agent_merit_scores"
  - phase: 17-memory-md-evolution-agent-church
    provides: "memory_writer_node, _process_agent, MEMORY.md write + proposal emission"
provides:
  - "evolution_suspended gate in memory_writer_node — suspended agents skip MEMORY.md writes and proposal emission"
  - "ARS systemd timer (quantum-swarm-ars-auditor) for daily 06:00 UTC scheduled audits"
  - "Scope boundary verified: evolution_suspended never in order_router or institutional_guard"
affects: [20-ars-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fail-open DB query pattern: _check_evolution_suspended returns False on error so memory writes proceed by default"
    - "Async suspension check before sync _process_agent — DB query in async node, file I/O stays sync"

key-files:
  created:
    - "scripts/install_ars_timer.sh"
  modified:
    - "src/graph/nodes/memory_writer.py"
    - "tests/core/test_memory_writer.py"

key-decisions:
  - "_check_evolution_suspended queries DB directly rather than relying on merit_loader — keeps plan minimal and avoids touching SwarmState schema"
  - "Fail-open on DB errors: suspension check returns False if DB unavailable — memory evolution proceeds, only suspension enforcement lost"
  - "ARS timer uses separate service name (quantum-swarm-ars-auditor) from Obsidian timer (quantum-swarm-tracking)"

patterns-established:
  - "Async DB check gating sync file I/O in LangGraph nodes"
  - "Negative source-level assertions for scope boundary enforcement (test_order_router_no_evolution_suspended)"

requirements-completed: [ARS-02]

# Metrics
duration: 4min
completed: 2026-03-08
---

# Phase 19 Plan 02: ARS Memory Writer Gate Summary

**evolution_suspended DB gate in memory_writer_node skips MEMORY.md writes and proposal emission for suspended agents, with ARS systemd timer for daily scheduled audits at 06:00 UTC**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-08T16:06:25Z
- **Completed:** 2026-03-08T16:10:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- memory_writer_node checks evolution_suspended from DB before each agent's _process_agent call
- Suspended agents skip MEMORY.md write AND proposal emission with WARNING log
- ARS systemd timer script (132 lines) follows install_obsidian_tracking_timer.sh pattern
- Scope boundary verified: evolution_suspended appears only in ars_auditor.py, persistence.py, memory_writer.py, and test files
- 431 tests pass (2 pre-existing PostgreSQL env failures excluded)

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for evolution_suspended gate** - `e1036a0` (test)
2. **Task 1 (GREEN): Wire evolution_suspended gate into memory_writer_node** - `8819537` (feat)
3. **Task 2: ARS systemd timer + full phase verification** - `f23d08f` (feat)

## Files Created/Modified
- `src/graph/nodes/memory_writer.py` - Added _check_evolution_suspended() and suspension gate in memory_writer_node
- `tests/core/test_memory_writer.py` - Added TestEvolutionSuspendedGate (4 tests) and TestTradePathIsolation (2 negative assertions)
- `scripts/install_ars_timer.sh` - Systemd timer installer for daily ARS drift audits (--install/--uninstall/--status)

## Decisions Made
- _check_evolution_suspended queries DB directly rather than relying on merit_loader — avoids touching SwarmState schema or merit_loader code
- Fail-open on DB errors: suspension check returns False if DB unavailable — evolution proceeds, only enforcement lost
- ARS timer separate service name from Obsidian timer to allow independent scheduling

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ARS-01 and ARS-02 both satisfied — Phase 19 complete
- ARS auditor can be scheduled via `scripts/install_ars_timer.sh --install`
- Manual unsuspend available via `python -m src.core.ars_auditor --unsuspend AGENT_HANDLE`

## Self-Check: PASSED

All artifacts verified:
- src/graph/nodes/memory_writer.py: FOUND, contains _check_evolution_suspended
- scripts/install_ars_timer.sh: FOUND, executable, 132 lines
- tests/core/test_memory_writer.py: FOUND, 12 tests passing
- Commits: e1036a0, 8819537, f23d08f all exist

---
*Phase: 19-ars-drift-auditor*
*Completed: 2026-03-08*
