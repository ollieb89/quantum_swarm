---
phase: 02-l2-domain-managers
plan: "02-04"
subsystem: agents
tags: [langgraph, risk-gating, conditional-edge, consensus-threshold, orchestrator]

# Dependency graph
requires:
  - phase: 02-l2-domain-managers
    plan: "02-03"
    provides: DebateSynthesizer node and weighted_consensus_score in SwarmState
provides:
  - RiskManager LangGraph node in orchestrator.py
  - route_after_debate module-level routing function in orchestrator.py
  - Conditional edge debate_synthesizer -> risk_manager (threshold > 0.6)
  - risk_approved and risk_notes fields in SwarmState
affects:
  - Phase 3 execution node (reads risk_approved to gate actual trade execution)

# Tech tracking
tech-stack:
  added:
    - RiskManager node (state-only signature, validates provenance + score)
    - route_after_debate conditional routing function (strict >0.6 threshold)
    - LangGraph add_conditional_edges on debate_synthesizer
  patterns:
    - Conditional edge pattern: routing function returns string key matched to node/END dict
    - Risk gating pattern: validate debate provenance before allowing downstream execution
    - Module-level routing function: importable directly for unit testing without graph compilation

key-files:
  created:
    - tests/test_risk_gating.py
    - conftest.py
  modified:
    - src/graph/state.py
    - src/graph/orchestrator.py

key-decisions:
  - "RiskManager validates debate_history provenance and weighted_consensus_score — checks missing provenance, anomalous score, and missing adversarial hypotheses"
  - "route_after_debate defined as module-level function so tests can import it directly without building the full graph"
  - "Boundary value score=0.6 routes to hold — threshold is STRICT greater than 0.6 (exclusive)"
  - "conftest.py added at repo root to fix pre-existing sys.path issue blocking all pytest test collection (Rule 3 deviation)"

requirements-completed:
  - REQ-02-04

# Metrics
duration: 1min
completed: 2026-03-05
---

# Phase 02 Plan 04: Risk Gating Summary

**RiskManager LangGraph node with conditional edge from DebateSynthesizer enforcing strict >0.6 consensus threshold before execution, with provenance validation and 3-test pytest suite**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-05T22:30:00Z
- **Completed:** 2026-03-05T22:30:51Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Added `risk_approved: Optional[bool]` and `risk_notes: Optional[str]` fields to `SwarmState`
- Replaced placeholder `risk_manager_node` with a full `RiskManager` implementation that reads `debate_history` and `weighted_consensus_score`, validates provenance integrity, and returns `risk_approved`/`risk_notes`
- Added `route_after_debate` as a module-level function in `orchestrator.py` — returns `"risk_manager"` if score > 0.6 (strict), else `"hold"` (END)
- Replaced the direct `debate_synthesizer → risk_manager` edge with `add_conditional_edges` using `route_after_debate`
- Created `tests/test_risk_gating.py` with 3 passing tests covering high score (0.8), low score (0.4), and boundary (0.6)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create RiskManager node in orchestrator.py** - `a749ec3` (feat)
2. **Task 2: Add conditional edge from DebateSynthesizer to RiskManager** - `d8d6ca1` (feat)
3. **Task 3: Unit test for conditional routing threshold** - `b3e17fb` (feat)

## Files Created/Modified

- `src/graph/state.py` - Added `risk_approved: Optional[bool]` and `risk_notes: Optional[str]` fields
- `src/graph/orchestrator.py` - Replaced placeholder with full RiskManager node; added `route_after_debate` module-level function; replaced direct edge with `add_conditional_edges` on `debate_synthesizer`; updated `run_task` initial state dict
- `tests/test_risk_gating.py` - 3 pytest tests for routing: score=0.8 → risk_manager, score=0.4 → hold, score=0.6 → hold (boundary excluded)
- `conftest.py` - Added at repo root to fix pre-existing sys.path issue blocking pytest collection

## Decisions Made

- `route_after_debate` defined at module level (not as a closure inside `create_orchestrator_graph`) so tests can `from src.graph.orchestrator import route_after_debate` without building the full graph
- Threshold is strict `> 0.6`: a score of exactly 0.6 routes to hold — any ambiguity favors caution
- RiskManager validates three dimensions: (1) missing provenance (empty debate_history), (2) anomalous score (None or outside [0.0, 1.0]), (3) missing adversarial hypotheses (both bullish and bearish are expected)
- `risk_manager_node` signature changed from `(state, config: Dict)` to `(state) -> dict` — no config needed since validation is deterministic/state-driven

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] Added conftest.py to fix pre-existing pytest sys.path error**
- **Found during:** Task 3 (first pytest invocation)
- **Issue:** pytest could not collect any tests because `src.*` imports raised `ModuleNotFoundError` — the project root was not on sys.path. This affected all test files, not just the new one.
- **Fix:** Added `conftest.py` at repo root that inserts `pathlib.Path(__file__).parent` into `sys.path` at collection time.
- **Files modified:** `conftest.py` (created)
- **Commit:** `b3e17fb`

Note: The pre-existing `UserWarning` about `config` parameter typing on `classify_intent` and `synthesize_consensus` nodes is cosmetic, from Phase 1 placeholder nodes — not touched (out of scope).

## Issues Encountered

None beyond the Rule 3 sys.path deviation above.

## User Setup Required

None — no external service configuration required for this plan. The RiskManager node itself makes no API calls. An `ANTHROPIC_API_KEY` is required when running the full graph end-to-end (analyst and researcher nodes call the Anthropic API), but not for import verification, graph compilation, or routing tests.

## Next Phase Readiness

- `risk_approved` in `SwarmState` is ready to gate Phase 3 execution: an execute node can check `state["risk_approved"]` before placing any order
- `risk_notes` provides audit trail text for compliance logging
- Phase 2 graph now has the full debate → risk gating pipeline wired; Phase 3 can add an `execute` node after `risk_manager` without restructuring anything
- No blockers for Phase 3

---
*Phase: 02-l2-domain-managers*
*Completed: 2026-03-05*

## Self-Check: PASSED

| Item | Status |
|------|--------|
| src/graph/state.py | FOUND |
| src/graph/orchestrator.py | FOUND |
| tests/test_risk_gating.py | FOUND |
| conftest.py | FOUND |
| .planning/phases/02-l2-domain-managers/02-04-SUMMARY.md | FOUND |
| commit a749ec3 (Task 1) | FOUND |
| commit d8d6ca1 (Task 2) | FOUND |
| commit b3e17fb (Task 3) | FOUND |
