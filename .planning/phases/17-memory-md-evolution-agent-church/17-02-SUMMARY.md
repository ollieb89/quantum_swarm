---
phase: 17-memory-md-evolution-agent-church
plan: "02"
subsystem: memory
tags: [soul-proposal, trigger-evaluation, atomic-write, rate-limit, pydantic, tdd]

# Dependency graph
requires:
  - phase: 17-01
    provides: memory_writer_node, _parse_entries, _extract_prev_score, _get_souls_dir, HANDLE_TO_AGENT_ID, phase17 config block
  - phase: 16-kami-merit-index
    provides: merit_scores in SwarmState, composite score per handle
  - phase: 15-soul-foundation
    provides: soul_loader, souls/ directory structure, SoulError hierarchy

provides:
  - SoulProposal Pydantic v2 model (src/core/soul_proposal.py)
  - build_proposal_id: deterministic unique proposal ID with microsecond precision
  - write_proposal_atomic: temp-file + os.rename atomic JSON write
  - check_rate_limit: scan proposal ledger for (agent_id, target_section) rejection count in window
  - _check_triggers: KAMI_SPIKE, DRIFT_STREAK, MERIT_FLOOR evaluation in memory_writer
  - _build_proposal_rationale: human-readable trigger summary for proposal rationale field
  - Extended _process_agent: emits SoulProposal after trigger fires, rate-limit guarded
  - data/soul_proposals/ as rejection ledger (created lazily on first write)
  - Import boundary tests for soul_proposal in test_import_boundaries.py

affects:
  - 17-03 (Agent Church reads data/soul_proposals/*.json as the rejection ledger; no separate DB)
  - 18-theory-of-mind-soul-sync (peers may inspect proposal ledger for drift signals)
  - 19-ars-drift-auditor (ARS may read proposal count as meta-signal for suspension)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "write_proposal_atomic: NamedTemporaryFile + os.rename — no partial write visible to readers"
    - "check_rate_limit: glob *.json + fromisoformat + timezone-aware comparison — no DB required"
    - "PROPOSALS_DIR = Path('data/soul_proposals') as module-level constant — monkeypatchable in tests"
    - "_check_triggers: fewer entries than N/K → trigger cannot fire (safety floor)"
    - "Trigger logic reads MEMORY.md *after* entry is written — streak = persisted entries only"

key-files:
  created:
    - src/core/soul_proposal.py
    - tests/core/test_soul_proposal.py
  modified:
    - src/graph/nodes/memory_writer.py
    - tests/core/test_import_boundaries.py

key-decisions:
  - "PROPOSALS_DIR is a module-level Path constant — not created at import time, only on first write_proposal_atomic call"
  - "agent_id in SoulProposal is set to the soul HANDLE (e.g. 'CASSANDRA') not the agent_id directory name — consistent with Agent Church SOUL.md lookup pattern"
  - "proposed_content is a sentinel '[PENDING — Agent Church will draft content]' — memory_writer does NOT draft soul content; Agent Church does this in Plan 03"
  - "Rate-limit check uses PROPOSALS_DIR as a module-level attribute (not hardcoded path) — allows test patching via patch.object"
  - "Proposal emission failures are non-blocking — caught in try/except, logged as error, cycle continues"

patterns-established:
  - "Atomic file write: NamedTemporaryFile(delete=False) + os.rename; no .tmp residue on success"
  - "Ledger-based rate-limiting: scan *.json files for status=='rejected' within window, no separate table"
  - "Trigger guards: if len(entries) < N, trigger cannot fire (prevents false positives at cold-start)"
  - "Import Layer Law: src.core.soul_proposal has no src.graph.* imports; enforced by test_import_boundaries.py"

requirements-completed:
  - EVOL-02

# Metrics
duration: 4min
completed: "2026-03-08"
---

# Phase 17 Plan 02: SoulProposal Writer (EVOL-02) Summary

**SoulProposal Pydantic model with atomic JSON write, three proposal triggers (KAMI_SPIKE, DRIFT_STREAK, MERIT_FLOOR), rate-limit guard, and data/soul_proposals/ as Agent Church's rejection ledger**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-08T13:33:43Z
- **Completed:** 2026-03-08T13:37:31Z
- **Tasks:** 2 (TDD: RED + GREEN each)
- **Files modified:** 4

## Accomplishments

- SoulProposal Pydantic v2 BaseModel with status Literal enum (pending/approved/rejected/rate_limited) and all required fields
- write_proposal_atomic: temp-file + os.rename ensures no partial writes; data/soul_proposals/ created lazily on first call
- check_rate_limit: scans *.json ledger for rejected proposals within (agent_id, target_section, window_days) — no database required
- _check_triggers: evaluates KAMI_SPIKE (|delta| >= threshold), DRIFT_STREAK (last N entries all non-empty DRIFT_FLAGS), MERIT_FLOOR (last K entries all <= floor); fewer entries than N/K means trigger cannot fire
- _process_agent extended: triggers evaluated post-write, rate-limit checked, single merged proposal emitted when multiple triggers fire simultaneously
- Import Layer Law enforced: soul_proposal.py has zero src.graph.* imports; registered in test_import_boundaries.py
- 7/7 EVOL-02 unit tests passing; full suite 354/355 (1 pre-existing PostgreSQL failure unrelated)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for schema + atomic write** - `da84c4d` (test)
2. **Task 1 GREEN: SoulProposal model + write helpers** - `be95c0e` (feat)
3. **Task 2 GREEN: memory_writer trigger logic + rate-limit** - `2d06cb7` (feat)
4. **Import boundary registration** - `aa23e27` (feat)

_TDD tasks produced RED + GREEN commits as required._

## Files Created/Modified

- `src/core/soul_proposal.py` - SoulProposal model, build_proposal_id, write_proposal_atomic, check_rate_limit
- `tests/core/test_soul_proposal.py` - 7 unit tests covering all EVOL-02 behaviours
- `src/graph/nodes/memory_writer.py` - Extended with _extract_drift_flags, _extract_merit_score_from_entry, _check_triggers, _build_proposal_rationale; _process_agent now emits proposals post-write
- `tests/core/test_import_boundaries.py` - Added test_soul_proposal_imports_cleanly + test_soul_proposal_does_not_import_graph

## Decisions Made

- PROPOSALS_DIR is a module-level Path constant (not created at import) — ensures clean import without side-effects
- agent_id in SoulProposal set to soul HANDLE (not agent_id directory name) — consistent with how Agent Church looks up SOUL.md files
- proposed_content is a sentinel string — memory_writer does not draft soul content; Agent Church generates actual replacement text in Plan 03
- Rate-limit uses module-level PROPOSALS_DIR attribute to enable test patching via patch.object without monkeypatching Path itself
- Trigger guard: fewer entries than drift_streak_n or merit_floor_k → trigger does not fire (prevents false positives at cold-start when MEMORY.md has < N entries)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Registered soul_proposal in import boundary test suite**
- **Found during:** Post-Task 2 verification
- **Issue:** Import Layer Law states "Add new core modules to TestCoreLeafImports immediately on creation" — soul_proposal was not registered
- **Fix:** Added test_soul_proposal_imports_cleanly to TestCoreLeafImports and test_soul_proposal_does_not_import_graph to TestNoCoreToAgentImport; fixed assertion to match only import statement lines (not docstring text)
- **Files modified:** tests/core/test_import_boundaries.py
- **Verification:** 12/12 import boundary tests pass
- **Committed in:** aa23e27

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing critical enforcement)
**Impact on plan:** Import boundary registration is mandatory per project rules. No scope creep.

## Issues Encountered

The initial test_soul_proposal_does_not_import_graph assertion used `assert "from src.graph" not in source` which matched the docstring text "from src.graph.*" in soul_proposal.py. Fixed by filtering to actual import statement lines only (lines starting with "from " or "import ").

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 17-03 (Agent Church) can read data/soul_proposals/*.json as the rejection ledger — no separate DB setup needed
- SoulProposal model ready for Agent Church to update status from "pending" to "approved" or "rejected"
- RequiresHumanApproval (from Plan 01) available for L1-self-approval guard in Agent Church
- Memory writer now fully wired: MEMORY.md forensic log + EVOL trigger → SoulProposal pipeline complete

## Self-Check: PASSED

All files and commits verified present:
- src/core/soul_proposal.py: FOUND
- tests/core/test_soul_proposal.py: FOUND
- src/graph/nodes/memory_writer.py (modified): FOUND
- tests/core/test_import_boundaries.py (modified): FOUND
- da84c4d (test: RED failing tests): FOUND
- be95c0e (feat: SoulProposal model GREEN): FOUND
- 2d06cb7 (feat: memory_writer trigger logic): FOUND
- aa23e27 (feat: import boundary registration): FOUND

---
*Phase: 17-memory-md-evolution-agent-church*
*Completed: 2026-03-08*
