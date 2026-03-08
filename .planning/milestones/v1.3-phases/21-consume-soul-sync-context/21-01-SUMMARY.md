---
phase: 21-consume-soul-sync-context
plan: 01
subsystem: debate
tags: [soul-sync, debate-history, theory-of-mind, peer-summary]

# Dependency graph
requires:
  - phase: 18-theory-of-mind-soul-sync
    provides: soul_sync_context in SwarmState with peer soul summaries
provides:
  - peer_soul_summary field in debate_history entries when soul_sync_context is present
  - _OPPONENT_MAP constant mapping debate source to opponent soul handle
affects: [decision-card-writer, risk-manager, audit-trail]

# Tech tracking
tech-stack:
  added: []
  patterns: [optional-field-omission, opponent-mapping, context-in-artifacts-out]

key-files:
  created: []
  modified:
    - src/graph/debate.py
    - tests/test_adversarial_debate.py

key-decisions:
  - "_OPPONENT_MAP lives in debate.py not kami.py -- presentation-adjacent logic"
  - "peer_soul_summary omitted entirely when absent/empty -- no None values, no warnings"

patterns-established:
  - "Optional provenance enrichment: conditional field addition to debate_history entries"
  - "Context-in artifacts-out: DebateSynthesizer reads soul_sync_context but does not return it"

requirements-completed: [TOM-01]

# Metrics
duration: 2min
completed: 2026-03-08
---

# Phase 21 Plan 01: Consume Soul-Sync Context Summary

**Peer soul summaries wired into debate_history via _OPPONENT_MAP lookup, closing INT-02 orphaned soul_sync_context gap**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-08T19:21:23Z
- **Completed:** 2026-03-08T19:23:01Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Wired soul_sync_context into DebateSynthesizer with ~10 lines of production code
- 5 new tests covering present/absent/partial/scoring-invariance/neutral-placeholder scenarios
- Scoring math completely unchanged -- soul summaries are provenance only, not weighting
- INT-02 gap (orphaned soul_sync_context output) is closed

## Task Commits

Each task was committed atomically:

1. **Task 1: Add soul context consumption tests** - `07993b6` (test -- TDD RED phase)
2. **Task 2: Wire soul_sync_context into DebateSynthesizer** - `a694264` (feat -- TDD GREEN phase)

_Note: TDD plan -- test commit (RED) followed by implementation commit (GREEN)_

## Files Created/Modified
- `src/graph/debate.py` - Added _OPPONENT_MAP constant and soul_sync_context consumption in DebateSynthesizer; conditionally enriches debate_history entries with peer_soul_summary
- `tests/test_adversarial_debate.py` - 5 new Phase 21 tests for soul context present/absent/partial/scoring/placeholder

## Decisions Made
- _OPPONENT_MAP placed in debate.py (not kami.py) -- presentation-adjacent logic, not merit logic (~3 lines)
- peer_soul_summary omitted entirely when opponent summary is absent or empty string -- no None values, no warnings logged
- Added INFO log line for soul_sync_context consumption count (Claude's discretion per CONTEXT.md)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Theory of Mind data flow complete: soul_sync_handshake_node -> soul_sync_context -> debate_history[].peer_soul_summary
- decision_card_writer automatically serializes peer_soul_summary through debate_history
- Ready for any downstream consumers (risk_manager, explainer modules) in future phases

---
*Phase: 21-consume-soul-sync-context*
*Completed: 2026-03-08*
