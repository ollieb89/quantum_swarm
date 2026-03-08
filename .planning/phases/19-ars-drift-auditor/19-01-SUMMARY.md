---
phase: 19-ars-drift-auditor
plan: 01
subsystem: safety
tags: [ars, drift-detection, audit, sentiment-analysis, cosine-distance, breach-escalation]

# Dependency graph
requires:
  - phase: 17-memory-md-evolution-agent-church
    provides: "MEMORY.md entry format, SoulProposal schema, PROPOSALS_DIR"
  - phase: 16-kami-merit-index
    provides: "agent_merit_scores table with evolution_suspended column, KAMIDimensions"
provides:
  - "Standalone ARS drift auditor with 5 metrics, CLI, DB persistence"
  - "ars_state PostgreSQL table for breach counter persistence"
  - "ars: config section in swarm_config.yaml with thresholds and lexicons"
  - "Context-aware role boundary vocabulary violation detection"
  - "Flag-then-suspend breach escalation (WARNING -> CRITICAL -> suspend)"
affects: [19-02-ars-memory-writer-gate, 20-ars-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Counter-based cosine distance for sentiment analysis (stdlib only)"
    - "Context-aware violation counting with assertion/negation proximity guards"
    - "Flag-then-suspend escalation with persistent breach counters"
    - "Dual-threshold sentiment gating (distance AND polarity must exceed)"

key-files:
  created:
    - "src/core/ars_auditor.py"
    - "tests/core/test_ars_auditor.py"
  modified:
    - "config/swarm_config.yaml"
    - "src/core/persistence.py"
    - "tests/core/test_import_boundaries.py"

key-decisions:
  - "Counter-based cosine distance for sentiment shift — stdlib only, no numpy dependency needed"
  - "Context-aware role boundary counting: forbidden terms only count as violations near assertion markers and NOT near negation markers"
  - "Sentiment shift requires BOTH distance AND polarity delta to exceed thresholds — prevents false flags on minor wording drift"
  - "ars_state is a separate table from agent_merit_scores — merit = learned performance, ARS = control/safety state machine"
  - "_load_merit_dimensions lazy-imports from src.core.db to avoid DB connection at import time"

patterns-established:
  - "ARS standalone __main__ script pattern (same as agent_church.py) — not a LangGraph node"
  - "Monkeypatchable path helpers (_get_souls_dir, _get_proposals_dir, _get_audit_path) for test isolation"
  - "AsyncMock-based DB mocking for deterministic tests without PostgreSQL"

requirements-completed: [ARS-01]

# Metrics
duration: 5min
completed: 2026-03-08
---

# Phase 19 Plan 01: ARS Drift Auditor Summary

**Standalone ARS drift auditor with 5 stdlib-only metrics (proposal rejection, drift flags, KAMI variance, alignment mutations, sentiment shift, role boundary violations), 30-cycle warm-up, flag-then-suspend escalation, and CLI with --agent/--dry-run/--unsuspend**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-08T15:58:02Z
- **Completed:** 2026-03-08T16:03:02Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- All 5 drift metrics implemented using stdlib only (re, statistics, collections.Counter, math)
- 30-cycle warm-up enforcement prevents false alerts on new agents
- Flag-then-suspend escalation: 1st breach=WARNING, 3 consecutive=CRITICAL+evolution_suspended=True
- Breach counters persist in ars_state PostgreSQL table, reset on clean audit cycle
- Context-aware role boundary violations (assertion/negation proximity guards)
- Dual-threshold sentiment shift gating (cosine distance AND polarity delta)
- 65 tests passing (49 ARS + 16 import boundaries) — deterministic, no LLM calls, no PostgreSQL

## Task Commits

Each task was committed atomically:

1. **Task 1: ARS config section + ars_state DDL + test scaffold** - `4b9d8e2` (feat)
2. **Task 2: ARS auditor module — 5 drift metrics + CLI + flag-then-suspend** - `eeb2c2d` (feat)

## Files Created/Modified
- `src/core/ars_auditor.py` - Standalone ARS drift auditor (727 lines) with 5 metrics, CLI, breach management
- `tests/core/test_ars_auditor.py` - Deterministic test suite (692 lines) covering all metrics, warm-up, escalation
- `config/swarm_config.yaml` - Added ars: section with thresholds, lexicons, forbidden vocabulary
- `src/core/persistence.py` - Added ars_state table DDL in setup_persistence()
- `tests/core/test_import_boundaries.py` - Added ars_auditor import boundary tests

## Decisions Made
- Counter-based cosine distance for sentiment shift — stdlib only, no numpy dependency needed
- Context-aware role boundary counting: forbidden terms only count near assertion markers and NOT near negation markers
- Sentiment shift requires BOTH distance AND polarity delta to exceed thresholds — prevents false flags
- ars_state is a separate table from agent_merit_scores — merit = learned performance, ARS = control/safety state machine
- _load_merit_dimensions lazy-imports from src.core.db to avoid DB connection at import time

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ARS auditor ready for out-of-band scheduling via systemd timer
- memory_writer_node needs evolution_suspended gate check (Plan 02 scope)
- All 5 agents can be audited with `python -m src.core.ars_auditor --dry-run`

---
*Phase: 19-ars-drift-auditor*
*Completed: 2026-03-08*
