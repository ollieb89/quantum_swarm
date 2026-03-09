---
phase: 26-replay-cli
plan: 02
subsystem: cli
tags: [rich, argparse, replay, terminal-ui, bar-charts]

# Dependency graph
requires:
  - phase: 26-replay-cli
    provides: cycle_store.py with load_cycle and list_cycles
provides:
  - "handle_list() — rich table or JSON listing of cycles with filters"
  - "handle_show() — full cycle rendering with merit bar charts and drift annotations"
  - "handle_compare() — sequential delta comparison with directional arrows"
  - "register_replay_parser() — argparse integration for replay subcommands"
affects: [26-replay-cli]

# Tech tracking
tech-stack:
  added: []
  patterns: [cli-handler-pattern, rich-console-injection, tdd]

key-files:
  created: [src/cli/__init__.py, src/cli/replay.py, tests/cli/__init__.py, tests/cli/test_replay.py]
  modified: [src/main.py]

key-decisions:
  - "Console/stdout injection for testability: handlers accept optional console and stdout params"
  - "Default limit 20 for list command to avoid overwhelming terminal output"
  - "Error messages via Console(stderr=True) to keep stdout clean for --json piping"

patterns-established:
  - "CLI handler pattern: each handler takes Namespace args + optional base_dir/console/stdout for DI"
  - "Rich Console injection: pass Console(file=StringIO) in tests to capture output without mocking"

requirements-completed: [REPL-01, REPL-02, REPL-03, REPL-04, REPL-05, REPL-06]

# Metrics
duration: 4min
completed: 2026-03-09
---

# Phase 26 Plan 02: CLI Rendering Summary

**Rich-formatted replay CLI with list/show/compare handlers, merit bar charts, drift annotations, and directional delta arrows**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-09T07:24:30Z
- **Completed:** 2026-03-09T07:28:30Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Created replay CLI module with 3 subcommand handlers (list, show, compare)
- Merit weight bar charts with green block chars and numeric composites
- Drift annotations inline with merit weights when soul_sync_context present
- Directional arrows (triangle up/down) for compare deltas
- 11 TDD tests covering all handlers, error paths, and JSON output
- Wired replay subcommands into main.py alongside existing analyze command

## Task Commits

Each task was committed atomically:

1. **Task 1: Create src/cli/replay.py with rich rendering handlers** - `bc3cf9d` (feat)
2. **Task 2: Wire replay subcommands into main.py** - `92df5c8` (feat)

## Files Created/Modified
- `src/cli/__init__.py` - CLI package init
- `src/cli/replay.py` - Replay subcommand handlers with rich rendering (list, show, compare)
- `tests/cli/__init__.py` - Test package init
- `tests/cli/test_replay.py` - 11 integration tests with fixture helpers and Console capture
- `src/main.py` - Added replay import and parser registration, dispatch to handle_replay

## Decisions Made
- Console/stdout injection pattern for testability: handlers accept optional console and stdout params instead of using globals
- Default limit of 20 for list to keep terminal output manageable
- Error output via Console(stderr=True) to keep stdout clean for --json pipe consumers
- Bar width = int(composite * 30) for merit charts, providing readable visual scaling

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All replay CLI handlers ready for end-to-end testing with real cycle data
- 48 tests passing across cli, cycle_store, and import boundary suites
- main.py dispatches both analyze and replay commands correctly

---
*Phase: 26-replay-cli*
*Completed: 2026-03-09*
