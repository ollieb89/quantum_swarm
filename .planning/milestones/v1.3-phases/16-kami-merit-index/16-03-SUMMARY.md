---
phase: 16-kami-merit-index
plan: "03"
subsystem: debate
tags: [kami, merit, debate, audit, swarm-state]

# Dependency graph
requires:
  - phase: 16-01
    provides: kami.py with RESEARCHER_HANDLE_MAP, DEFAULT_MERIT, MERIT_FLOOR constants
  - phase: 16-02
    provides: merit_scores populated in SwarmState by merit_loader_node each cycle
provides:
  - DebateSynthesizer using KAMI merit composites instead of character-length proxy
  - Merit-based weighted_consensus_score (bull_w / (bull_w + bear_w))
  - Neutral fallback score=0.5 when no merit_scores in state (cold start safe)
  - debate_history 'strength' field is merit composite float
  - test_merit_scores_in_audit_hash — verifies merit_scores enters MiFID II hash chain
  - data/thesis_records/ directory stub for deferred Accuracy path
affects:
  - Phase 17 (MEMORY.md Evolution) — debate weighting now merit-driven; KAMI delta markers meaningful
  - Phase 19 (ARS Drift Auditor) — ARS reads from debate outputs influenced by merit

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RESEARCHER_HANDLE_MAP imported in graph node (debate.py) — maps agent output names to soul handles"
    - "merit composite lookup pattern: state.get('merit_scores') or {} with DEFAULT_MERIT fallback"
    - "Neutral fallback: equal DEFAULT_MERIT on both sides → score=0.5 (never crashes on cold start)"

key-files:
  created:
    - data/thesis_records/.gitkeep
    - data/thesis_records/README.txt
  modified:
    - src/graph/debate.py
    - tests/test_adversarial_debate.py
    - tests/test_audit_chain.py

key-decisions:
  - "Character-length proxy (len(text)) fully removed from DebateSynthesizer — merit composite is the only strength signal"
  - "Cold-start / no merit_scores → both sides use DEFAULT_MERIT=0.5 → score=0.5 (neutral, deterministic)"
  - "Accuracy dimension deferred — thesis_records/ stub established for future reconciliation process"
  - "test_scenario_a_overfitting updated: now expects score=0.5 (neutral) not <0.5 (length-driven)"

patterns-established:
  - "Merit-weighted debate: bull_w / (bull_w + bear_w) using KAMI composites from SwarmState"
  - "Thesis record directory: data/thesis_records/{decision_id}.jsonl for deferred Accuracy updates"

requirements-completed: [KAMI-04, KAMI-01]

# Metrics
duration: 4min
completed: "2026-03-08"
---

# Phase 16 Plan 03: KAMI Merit Index Integration Summary

**DebateSynthesizer rewired to KAMI merit composites from SwarmState — character-length proxy eliminated, strength field is now earned merit, neutral fallback is deterministic 0.5**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-08T11:21:09Z
- **Completed:** 2026-03-08T11:25:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Replaced `len(text)` character-length proxy in DebateSynthesizer with KAMI merit composite lookup via `RESEARCHER_HANDLE_MAP` and `SwarmState['merit_scores']`
- Cold-start neutral fallback: absent or empty `merit_scores` → both sides default to `DEFAULT_MERIT=0.5` → `weighted_consensus_score=0.5` (deterministic, no crash)
- `debate_history[*]['strength']` field is now merit composite float instead of character count
- Added 4 new TDD tests covering merit weighting, neutral fallback, skeleton domination prevention, and strength field type
- Added `test_merit_scores_in_audit_hash` verifying `merit_scores` is NOT in `AUDIT_EXCLUDED_FIELDS` and produces deterministic SHA-256 hashes with 4dp rounding
- Created `data/thesis_records/` directory stub for deferred Accuracy EMA path

## Task Commits

1. **Task 1: Rewrite DebateSynthesizer + 4 merit tests** - `6af36c7` (feat)
2. **Task 2: Audit hash test + thesis_records stub** - `1bb58e8` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/graph/debate.py` — removed `len(text)` proxy; added `RESEARCHER_HANDLE_MAP`/`DEFAULT_MERIT` import; merit-based `bull_w`/`bear_w`; neutral fallback; updated logger and `debate_history['strength']`
- `tests/test_adversarial_debate.py` — added 4 KAMI merit tests; updated `test_scenario_a_overfitting` to expect neutral `0.5` (no merit_scores → fallback)
- `tests/test_audit_chain.py` — appended `test_merit_scores_in_audit_hash` (synchronous, no DB)
- `data/thesis_records/.gitkeep` — git-tracks the deferred Accuracy output directory
- `data/thesis_records/README.txt` — documents JSONL format and future reconciliation intent

## Decisions Made

- Character-length proxy removed entirely (not kept as fallback) — the plan's neutral `DEFAULT_MERIT` fallback is sufficient and cleaner than mixing two strategies
- `test_scenario_a_overfitting` assertion changed from `< 0.5` to `== 0.5`: the old test tested the removed len() behavior; the correct new behavior for "no merit_scores" is neutral 0.5
- Audit hash test uses entry-format dict (with `input_data`/`output_data` keys) matching the real `_calculate_hash(entry, prev_hash)` signature — the plan's test template used a flat dict which would not hit `merit_scores` via `entry.get("input_data")`; adapted to real API

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_scenario_a_overfitting assertion to match new correct behavior**
- **Found during:** Task 1 (GREEN phase — running full test suite)
- **Issue:** Existing test expected `score < 0.5` based on character-length proxy. After removing the proxy, the test with no `merit_scores` correctly returns neutral 0.5. Test assertion was wrong for the new behavior.
- **Fix:** Changed assertion from `assert score < 0.5` to `assert score == 0.5` with updated comment explaining the neutral fallback.
- **Files modified:** `tests/test_adversarial_debate.py`
- **Verification:** Full suite passes — 8/8 tests in test_adversarial_debate.py
- **Committed in:** `6af36c7` (Task 1 commit)

**2. [Rule 1 - Bug] Adapted audit hash test to match real _calculate_hash(entry, prev_hash) signature**
- **Found during:** Task 2 (reading audit_logger.py)
- **Issue:** Plan's test template called `logger._calculate_hash(state_a)` with flat dict and no `prev_hash`. Actual signature is `_calculate_hash(self, entry, prev_hash)` requiring `entry` dict with `task_id`, `timestamp`, `node_id`, `input_data`, `output_data` keys.
- **Fix:** Wrote test with full entry-format dicts placing `merit_scores` in `output_data`, passing `None` as `prev_hash`.
- **Files modified:** `tests/test_audit_chain.py`
- **Verification:** `test_merit_scores_in_audit_hash` passes; hash_a != hash_b, hash_a == hash_c verified.
- **Committed in:** `1bb58e8` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bug in plan's test assumptions)
**Impact on plan:** Both fixes necessary for correctness. No scope creep. All plan objectives fully delivered.

## Issues Encountered

- `git stash pop` blocked by binary `.pyc` file conflict — resolved by `git stash drop` (changes were already committed, stash content was from pre-fix state)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- KAMI Phase 16 complete: all 4 requirements KAMI-01 through KAMI-04 satisfied
- 337 tests passing (pre-existing `test_trade_warehouse_persistence` DB failure excluded — PostgreSQL not running in dev environment)
- Phase 17 (MEMORY.md Evolution + Agent Church) can proceed — merit scores are now live in debate weighting

---
*Phase: 16-kami-merit-index*
*Completed: 2026-03-08*

## Self-Check: PASSED

- FOUND: src/graph/debate.py
- FOUND: data/thesis_records/.gitkeep
- FOUND: .planning/phases/16-kami-merit-index/16-03-SUMMARY.md
- FOUND: commit 6af36c7 (feat(16-03): replace character-length proxy)
- FOUND: commit 1bb58e8 (feat(16-03): add audit hash test + thesis_records)
