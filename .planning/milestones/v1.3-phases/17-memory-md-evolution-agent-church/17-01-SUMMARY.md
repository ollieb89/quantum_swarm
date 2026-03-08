---
phase: 17-memory-md-evolution-agent-church
plan: "01"
subsystem: memory
tags: [memory-writer, kami, soul-errors, langraph, yaml-config, tdd]

# Dependency graph
requires:
  - phase: 16-kami-merit-index
    provides: merit_scores in SwarmState, ALL_SOUL_HANDLES, composite score per handle
  - phase: 15-soul-foundation
    provides: soul_loader, souls/ directory structure, SoulError hierarchy
provides:
  - memory_writer_node (LangGraph node, always returns {}, non-blocking)
  - Per-agent MEMORY.md structured forensic log at src/core/souls/{agent_id}/MEMORY.md
  - RequiresHumanApproval exception in soul_errors hierarchy
  - phase17 config block in swarm_config.yaml (8 tunables)
affects:
  - 17-02 (soul_proposal_writer reads MEMORY.md tail for trigger detection)
  - 17-03 (agent_church reads MEMORY.md; raises RequiresHumanApproval for L1 proposals)
  - 18-theory-of-mind-soul-sync (reads MEMORY.md for context)
  - 19-ars-drift-auditor (reads [KAMI_DELTA:] and [DRIFT_FLAGS:] markers)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_get_souls_dir() monkeypatchable path helper for test isolation of file I/O"
    - "MEMORY.md entry split on === timestamp === headers (not raw line grep)"
    - "_parse_entries + _cap_entries composable helpers for 50-entry cap enforcement"
    - "memory_writer_node returns {} unconditionally (silent node pattern)"
    - "_load_p17_config() lazy YAML loader replicating merit_updater._load_kami_config()"

key-files:
  created:
    - src/graph/nodes/memory_writer.py
    - tests/core/test_memory_writer.py
  modified:
    - src/core/soul_errors.py
    - config/swarm_config.yaml

key-decisions:
  - "MEMORY.md prev_score default is 0.5 (cold-start), not 0.0 — matches KAMI DEFAULT_MERIT"
  - "_extract_prev_score reads from MEMORY.md path (not state['merit_scores']) — ensures delta reflects persisted history, not in-memory session data"
  - "memory_writer_node is fully synchronous I/O (Path.read_text/write_text) — asyncio.run() inside node functions is project-breaking pattern (MEM-06)"
  - "_get_souls_dir() extracted as a separate function (not inlined) to allow monkeypatching in tests without touching real souls/ directories"
  - "GUARDIAN canonical field is 'risk_approval' (not a special case) — _extract_thesis_summary handles nested 'reasoning' key via dict key priority order"

patterns-established:
  - "Test isolation for file I/O: monkeypatch module-level _get_souls_dir() to return tmp_path"
  - "MEMORY.md entry boundaries: === ISO8601Z === headers, parsed by _parse_entries (regex finditer)"
  - "50-entry cap: _cap_entries slices entries[-50:] (oldest at front, newest at back)"
  - "Non-blocking node: catch Exception per handle in loop, log error, continue"

requirements-completed:
  - EVOL-01

# Metrics
duration: 2min
completed: "2026-03-08"
---

# Phase 17 Plan 01: Memory Writer (EVOL-01) Summary

**memory_writer_node writing structured MEMORY.md forensic logs per-agent per-cycle, with 50-entry cap, KAMI delta computation, and RequiresHumanApproval added to soul_errors**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-08T13:27:36Z
- **Completed:** 2026-03-08T13:29:48Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- memory_writer_node implemented as silent, non-blocking LangGraph node (always returns {}, catches all exceptions per-handle)
- Fixed-field MEMORY.md entry format with UTC timestamp, [AGENT:], [KAMI_DELTA:], [MERIT_SCORE:], [DRIFT_FLAGS:], [THESIS_SUMMARY:] — Phase 19 ARS Drift Auditor can parse deterministically
- 50-entry cap enforced via _parse_entries (regex header split) + _cap_entries (oldest-first drop)
- RequiresHumanApproval(SoulError) added to soul_errors hierarchy for Plan 03 Agent Church L1-self-approval guard
- phase17 config block added to swarm_config.yaml with all 8 tunables
- 6/6 EVOL-01 unit tests passing; full suite 345/346 (1 pre-existing PostgreSQL failure unrelated)

## Task Commits

Each task was committed atomically:

1. **Task 1: RequiresHumanApproval + phase17 config block** - `62b177b` (feat)
2. **Task 2 RED: Failing tests for memory_writer_node** - `7bb4b26` (test)
3. **Task 2 GREEN: memory_writer_node implementation** - `f4bd1f2` (feat)

_TDD tasks produced RED + GREEN commits as required._

## Files Created/Modified

- `src/graph/nodes/memory_writer.py` - LangGraph node + all helpers (CANONICAL_FIELD_MAP, HANDLE_TO_AGENT_ID, parse/cap/build/write functions)
- `tests/core/test_memory_writer.py` - 6 unit tests covering all EVOL-01 behaviours
- `src/core/soul_errors.py` - RequiresHumanApproval(SoulError) appended after SoulSecurityError
- `config/swarm_config.yaml` - phase17: block with 8 tunables appended after kami: block

## Decisions Made

- MEMORY.md prev_score default is 0.5 (cold-start), matching KAMI DEFAULT_MERIT — first entry computes delta against neutral rather than 0.0
- _extract_prev_score reads from the MEMORY.md file on disk (not state['merit_scores']) to ensure delta reflects persisted history across sessions
- memory_writer_node uses synchronous file I/O only — asyncio.run() inside nodes is a known project-breaking pattern (MEM-06 defect)
- _get_souls_dir() extracted as module-level function to allow monkeypatching without real fs side-effects in tests
- GUARDIAN's risk_approval field handled via standard _extract_thesis_summary dict key priority ('content', 'reasoning', 'summary', 'thesis') — no special-case code needed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 17-02 can import memory_writer_node and access HANDLE_TO_AGENT_ID, _parse_entries, _extract_prev_score helpers directly
- RequiresHumanApproval available for Plan 03 Agent Church L1 self-approval guard
- phase17 config tunables (kami_delta_threshold, drift_streak_n, merit_floor, merit_floor_k) available for Plan 02 proposal trigger logic
- MEMORY.md format is locked — Phase 19 ARS Drift Auditor depends on === timestamp === header + [KAMI_DELTA:] / [DRIFT_FLAGS:] labeled lines

## Self-Check: PASSED

All files and commits verified present:
- src/graph/nodes/memory_writer.py: FOUND
- tests/core/test_memory_writer.py: FOUND
- src/core/soul_errors.py: FOUND
- config/swarm_config.yaml: FOUND
- 17-01-SUMMARY.md: FOUND
- 62b177b (feat: RequiresHumanApproval + phase17 config): FOUND
- 7bb4b26 (test: RED failing tests): FOUND
- f4bd1f2 (feat: memory_writer_node GREEN): FOUND

---
*Phase: 17-memory-md-evolution-agent-church*
*Completed: 2026-03-08*
