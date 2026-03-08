---
phase: 16-kami-merit-index
plan: 01
subsystem: core
tags: [kami, merit-index, tdd, postgres, swarm-state, yaml-config, dataclass]

# Dependency graph
requires:
  - phase: 15-soul-foundation
    provides: soul_loader.load_soul(), SoulNotFoundError, AgentSoul.identity — used by _extract_fidelity_signal in kami.py

provides:
  - "KAMIDimensions frozen dataclass with 4 merit dimensions, default 0.5 cold-start"
  - "compute_merit() alpha*acc + beta*rec + gamma*con + delta*fid, clamped [0.1, 1.0]"
  - "apply_ema() lam*signal + (1-lam)*prev EMA update function"
  - "_extract_recovery_signal(), _extract_consensus_signal(), _extract_fidelity_signal() signal helpers"
  - "DEFAULT_WEIGHTS dict: alpha=0.30 beta=0.35 gamma=0.25 delta=0.10 (sum 1.0)"
  - "agent_merit_scores PostgreSQL table DDL with evolution_suspended column (pre-declared for Phase 19)"
  - "merit_scores: Optional[Dict[str, Any]] plain field in SwarmState (no reducer)"
  - "kami: section in swarm_config.yaml with all weights and EMA lambda"
  - "Wave 0 test stubs for merit_loader and merit_updater (Plan 02 scaffold)"

affects:
  - 16-02 (merit_loader and merit_updater nodes consume this module)
  - 17-memory-evolution (KAMI delta markers written to MEMORY.md use merit scores)
  - 19-ars-drift-auditor (evolution_suspended column used by ARS suspension gate)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "KAMI arithmetic core: pure functions only, no LLM calls, no asyncio, all synchronous"
    - "IEEE 754 jitter guard: round(raw, 10) before clamping in compute_merit"
    - "Fidelity signal via lazy load_soul() probe — lazy import inside function prevents circular imports"
    - "Wave 0 stub pattern: pytest.mark.skip(reason='Implemented in Plan 02') for future TDD scaffolding"

key-files:
  created:
    - src/core/kami.py
    - tests/test_kami.py
    - tests/core/test_merit_loader.py
    - tests/core/test_merit_updater.py
  modified:
    - config/swarm_config.yaml
    - src/core/persistence.py
    - src/graph/state.py
    - tests/core/test_import_boundaries.py

key-decisions:
  - "round(raw, 10) before clamp in compute_merit — eliminates IEEE 754 jitter (0.30+0.35+0.25+0.10 != exactly 1.0)"
  - "Fidelity signal uses lazy import of load_soul() inside _extract_fidelity_signal — avoids circular import at module load time"
  - "evolution_suspended column pre-declared in agent_merit_scores — avoids ALTER TABLE migration in Phase 19 ARS-02"
  - "merit_scores is plain Optional[Dict] in SwarmState (NO Annotated reducer) — merit_loader overwrites, not accumulates"
  - "kami.py added to TestCoreLeafImports immediately on creation per Import Layer Law"

patterns-established:
  - "KAMI merit formula: w_alpha*accuracy + w_beta*recovery + w_gamma*consensus + w_delta*fidelity, clamped [0.1, 1.0]"
  - "EMA pattern: apply_ema(prev, signal, lam) = lam*signal + (1-lam)*prev"
  - "upstream error exemption: producer_agent_id != active_persona → recovery 1.0 (not self-induced)"
  - "CASSANDRA protection: consensus = min(1.0, abs(score-0.5)*2.0) — rewards strong signal, not direction"

requirements-completed: [KAMI-01, KAMI-02, KAMI-03]

# Metrics
duration: 4min
completed: 2026-03-08
---

# Phase 16 Plan 01: KAMI Merit Index Foundation Summary

**Pure-function KAMI arithmetic core (KAMIDimensions, compute_merit, apply_ema, signal extractors) with PostgreSQL DDL, SwarmState field, and YAML config — 23 unit tests, zero LLM calls**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-08T09:46:53Z
- **Completed:** 2026-03-08T09:50:02Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- `src/core/kami.py` — KAMIDimensions frozen dataclass, compute_merit(), apply_ema(), three signal extractor helpers, all constants; pure functions only
- TDD suite (23 tests) covering formula correctness, floor/ceil clamping, EMA edge cases, recovery signal upstream exemption, fidelity probe via load_soul()
- `agent_merit_scores` PostgreSQL table with `evolution_suspended` column pre-declared for Phase 19 (ARS-02), avoiding future ALTER TABLE migration
- `merit_scores: Optional[Dict[str, Any]]` added to SwarmState as plain field with no Annotated reducer
- `kami:` section added to `swarm_config.yaml` with all four weights (sum to 1.0), lambda=0.9, floor/ceil
- Wave 0 stub test files for merit_loader and merit_updater (Plan 02 TDD scaffold)
- kami.py registered in `TestCoreLeafImports` per Import Layer Law

## Task Commits

Each task was committed atomically:

1. **Task 1: Create src/core/kami.py with KAMIDimensions, compute_merit, apply_ema, and signal helpers** — `f8cb512` (feat)
2. **Task 2: Add kami: config section, agent_merit_scores DB table, merit_scores SwarmState field, and test stubs** — `8194743` (feat)
3. **Import boundary registration** — `bd9c473` (test)

## Files Created/Modified

- `src/core/kami.py` — KAMI arithmetic core: KAMIDimensions, compute_merit, apply_ema, signal extractors
- `tests/test_kami.py` — 23 unit tests covering all behaviors, no LLM calls
- `tests/core/test_merit_loader.py` — 3 skip-marked Wave 0 stubs for Plan 02
- `tests/core/test_merit_updater.py` — 3 skip-marked Wave 0 stubs for Plan 02
- `config/swarm_config.yaml` — kami: section appended (weights, lambda, floor/ceil)
- `src/core/persistence.py` — agent_merit_scores CREATE TABLE IF NOT EXISTS block added
- `src/graph/state.py` — merit_scores field added, Dict imported from typing
- `tests/core/test_import_boundaries.py` — kami.py registered in TestCoreLeafImports

## Decisions Made

- `round(raw, 10)` before clamp in `compute_merit` — IEEE 754 jitter causes `0.30+0.35+0.25+0.10` to land at `0.9999999999999999`, which fails `== MERIT_CEIL`. Rounding to 10 decimal places resolves this without altering precision needed for merit computations.
- Fidelity signal uses lazy `from src.core.soul_loader import load_soul` inside `_extract_fidelity_signal()` — prevents circular import at module load time while still maintaining core-to-core import legality.
- `evolution_suspended BOOLEAN DEFAULT FALSE` pre-declared in DDL — avoids ALTER TABLE migration in Phase 19 when ARS suspension gate is wired.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] IEEE 754 float jitter in compute_merit ceiling clamp**
- **Found during:** Task 1 GREEN phase (running tests)
- **Issue:** `0.30*1 + 0.35*1 + 0.25*1 + 0.10*1 == 0.9999999999999999` in Python IEEE 754 — `min(MERIT_CEIL, raw)` returned `0.9999999999999999` not `1.0`, failing `test_ceiling_clamp_on_all_ones`
- **Fix:** Added `raw = round(raw, 10)` before the clamp operation in `compute_merit()`
- **Files modified:** `src/core/kami.py`
- **Verification:** All 23 tests pass including ceiling clamp test
- **Committed in:** `f8cb512` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug)
**Impact on plan:** Necessary for correctness. The raw formula result must be rounded before clamping to prevent IEEE 754 jitter. No scope creep.

## Issues Encountered

- `git stash pop` during pre-existing failure check reverted Task 2 changes due to untracked binary files (`data/chroma_db/chroma.sqlite3`, `.pyc`) blocking the merge. Task 2 changes were reapplied manually from memory — no data loss, all verification re-run.

## Next Phase Readiness

- `src/core/kami.py` is fully tested and ready for Plan 02 (merit_loader, merit_updater graph nodes)
- `agent_merit_scores` DDL is in place — Plan 02 can INSERT/SELECT immediately
- `merit_scores` in SwarmState is available — Plan 02 nodes can write to it
- Wave 0 stub files define the expected test names Plan 02 must implement

---
*Phase: 16-kami-merit-index*
*Completed: 2026-03-08*
