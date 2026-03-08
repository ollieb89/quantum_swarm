---
phase: 13-wire-institutional-guard
plan: "02"
subsystem: graph
tags: [langgraph, institutional-guard, routing, compliance, risk-governance]

# Dependency graph
requires:
  - phase: 13-01
    provides: TDD RED scaffold with test_graph_wiring.py failing tests
  - phase: 08-portfolio-risk-governance
    provides: institutional_guard_node implementation and Phase 8 tests

provides:
  - route_after_institutional_guard() router function in orchestrator.py
  - claw_guard → institutional_guard direct edge
  - institutional_guard → data_fetcher/synthesize conditional edges
  - RISK-07 closed: institutional_guard_node now in live execution graph
  - RISK-08 closed: trade_risk_score and portfolio_heat populated on approved trades

affects:
  - DecisionCard.portfolio_risk_score (now non-null on approved trades via existing Phase 11 wiring)
  - Any future phases that modify execution graph routing

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Conditional edge router: check state.get('risk_approved') is False (not falsy) to distinguish rejected from not-yet-set"
    - "LangGraph branches vs edges: conditional edges stored in workflow.branches; workflow.edges only holds direct edges — tests must check both"

key-files:
  created: []
  modified:
    - src/graph/orchestrator.py
    - tests/test_graph_wiring.py
    - tests/test_l3_integration.py

key-decisions:
  - "route_after_institutional_guard routes to 'synthesize' on rejection (risk_approved=False) so rejected trades receive an explanatory summary rather than silently ending"
  - "Conditional edges stored in workflow.branches not workflow.edges in this version of LangGraph — test inspection logic updated to check both"
  - "test_l3_chain_order stale assertion (claw_guard→data_fetcher) updated to reflect Phase 13 wiring (claw_guard→institutional_guard)"
  - "test_audit_chain PoolTimeout errors are pre-existing DB infra issue (no PostgreSQL running), not regressions"

patterns-established:
  - "Router identity check: use 'is False' not '== False' or 'not value' to distinguish explicit False from None/unset"
  - "LangGraph edge inspection: workflow.branches[node_name][fn_name].ends gives conditional targets; workflow.edges gives direct edges only"

requirements-completed: [RISK-07, RISK-08]

# Metrics
duration: 19min
completed: 2026-03-08
---

# Phase 13 Plan 02: Wire Institutional Guard Summary

**institutional_guard_node wired into live LangGraph execution graph via claw_guard→institutional_guard direct edge and institutional_guard→data_fetcher/synthesize conditional routing, closing RISK-07 and RISK-08**

## Performance

- **Duration:** 19 min
- **Started:** 2026-03-08T03:49:37Z
- **Completed:** 2026-03-08T04:08:41Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `route_after_institutional_guard()` to orchestrator.py: routes approved trades to `data_fetcher`, rejected trades (risk_approved=False) to `synthesize`
- Replaced broken `claw_guard→data_fetcher` direct edge with `claw_guard→institutional_guard` + conditional edges — all Phase 8 institutional guard tests continue to pass GREEN
- Fixed test inspection logic to check `workflow.branches` for conditional edge destinations (LangGraph stores conditional edges there, not in `workflow.edges`)
- Full regression: 244 tests pass, 0 new failures introduced

## Task Commits

Each task was committed atomically:

1. **Task 1: Add route_after_institutional_guard() and wire edges** - `3b6dd8d` (feat)
2. **Task 2: Full regression pass — fix stale test assertion** - `5138e10` (fix)

**Plan metadata:** (docs commit — see final_commit)

## Files Created/Modified

- `src/graph/orchestrator.py` - Added `route_after_institutional_guard()` function; replaced `add_edge("claw_guard", "data_fetcher")` with `add_edge("claw_guard", "institutional_guard")` + `add_conditional_edges("institutional_guard", ...)`
- `tests/test_graph_wiring.py` - Fixed edge inspection to check `workflow.branches` for conditional edge destinations in addition to `workflow.edges`
- `tests/test_l3_integration.py` - Updated stale `test_l3_chain_order` assertion from `claw_guard→data_fetcher` to `claw_guard→institutional_guard`

## Decisions Made

- Used `state.get("risk_approved") is False` (identity check) to distinguish explicit rejection from trade not yet evaluated (None)
- Rejection path routes to `synthesize` rather than `END` so callers receive an explanatory summary
- Conditional edge targets for `institutional_guard`: `{"data_fetcher": "data_fetcher", "synthesize": "synthesize"}`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_graph_wiring.py edge inspection missed conditional edges**
- **Found during:** Task 1 (Add route_after_institutional_guard and wire edges)
- **Issue:** Test used `workflow._graph.edges()` (raises AttributeError) with fallback to `workflow.edges` — but `workflow.edges` only contains direct edges; conditional edges live in `workflow.branches`. Test therefore reported empty destinations for `institutional_guard` even after correct wiring.
- **Fix:** Added `conditional_destinations()` helper in test that reads `workflow.branches[node_name][fn_name].ends` and merges with direct edges before asserting
- **Files modified:** tests/test_graph_wiring.py
- **Verification:** `test_institutional_guard_wired_in_graph` now PASSES GREEN
- **Committed in:** 3b6dd8d (Task 1 commit)

**2. [Rule 1 - Bug] test_l3_chain_order asserted removed edge claw_guard→data_fetcher**
- **Found during:** Task 2 (Full regression pass)
- **Issue:** Pre-existing test `test_l3_chain_order` asserted `("claw_guard", "data_fetcher")` in edge_pairs — this direct edge was replaced by the institutional_guard chain in Task 1
- **Fix:** Updated assertion to `("claw_guard", "institutional_guard")` with updated comment
- **Files modified:** tests/test_l3_integration.py
- **Verification:** `test_l3_chain_order` now PASSES GREEN
- **Committed in:** 5138e10 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2x Rule 1 - Bug)
**Impact on plan:** Both auto-fixes necessary for correct test coverage. The wiring change in orchestrator.py correctly invalidated two tests that asserted the old broken edge; both tests updated to reflect correct wiring.

## Issues Encountered

- `test_audit_chain.py` errors (PoolTimeout) are pre-existing DB infra issues — no PostgreSQL running in the test environment. Verified these errors existed before our changes via `git stash` check. Not introduced by Phase 13 work.

## Next Phase Readiness

- RISK-07 closed: institutional_guard_node is in the live execution path for every trade
- RISK-08 closed: `state["metadata"]["trade_risk_score"]` and `["portfolio_heat"]` now populated on every approved trade; `DecisionCard.portfolio_risk_score` auto-populates via existing Phase 11 wiring
- Phase 13 complete: both plans (01 + 02) done; phase requirements RISK-07 and RISK-08 satisfied

## Self-Check: PASSED

- FOUND: src/graph/orchestrator.py (route_after_institutional_guard + correct edges)
- FOUND: tests/test_graph_wiring.py (branches inspection fix)
- FOUND: tests/test_l3_integration.py (stale edge assertion fix)
- FOUND: 13-02-SUMMARY.md
- FOUND: commit 3b6dd8d (Task 1)
- FOUND: commit 5138e10 (Task 2)

---
*Phase: 13-wire-institutional-guard*
*Completed: 2026-03-08*
