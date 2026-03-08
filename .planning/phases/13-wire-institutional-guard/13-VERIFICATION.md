---
phase: 13-wire-institutional-guard
verified: 2026-03-08T05:00:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 13: Wire Institutional Guard — Verification Report

**Phase Goal:** Close the RISK-07/RISK-08 integration gap so that institutional_guard_node executes on every trade, enforcing aggregate portfolio constraints and propagating trade_risk_score/portfolio_heat metadata to DecisionCards.
**Verified:** 2026-03-08T05:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | claw_guard → institutional_guard edge exists in compiled orchestrator graph | VERIFIED | `workflow.add_edge("claw_guard", "institutional_guard")` at orchestrator.py:321; `test_institutional_guard_wired_in_graph` PASSES |
| 2 | institutional_guard → data_fetcher edge exists on approved path | VERIFIED | `add_conditional_edges("institutional_guard", route_after_institutional_guard, {"data_fetcher": "data_fetcher", "synthesize": "synthesize"})` at orchestrator.py:322-326 |
| 3 | institutional_guard → synthesize edge exists on rejected path (risk_approved=False) | VERIFIED | Same `add_conditional_edges` call maps "synthesize" target; `route_after_institutional_guard` returns "synthesize" when `state.get("risk_approved") is False` |
| 4 | state['metadata']['trade_risk_score'] is non-None after approved institutional_guard execution | VERIFIED | `test_institutional_guard_metadata_propagation` PASSES; assertion confirmed against live node execution with AsyncMock patches |
| 5 | state['metadata']['portfolio_heat'] is non-None after approved institutional_guard execution | VERIFIED | Same test; both fields asserted non-None |
| 6 | DecisionCard.portfolio_risk_score is non-null on normal trade (sourced from metadata.trade_risk_score) | VERIFIED | `decision_card.py:145-155` — `portfolio_risk_score = state.get("metadata", {}).get("trade_risk_score")` already wired in Phase 11; now receives value because institutional_guard_node runs |
| 7 | All Phase 8 tests in tests/test_institutional_guard.py continue to pass | VERIFIED | 7/7 tests PASSED (confirmed by test run: 120s runtime, all green) |
| 8 | Both tests in tests/test_graph_wiring.py pass GREEN | VERIFIED | `test_institutional_guard_wired_in_graph` PASSED, `test_institutional_guard_metadata_propagation` PASSED |

**Score:** 8/8 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/graph/orchestrator.py` | route_after_institutional_guard() + new edge calls | VERIFIED | Function at lines 85-99; edges at lines 321-326; old `claw_guard→data_fetcher` direct edge absent (grep confirms zero matches) |
| `tests/test_graph_wiring.py` | Two integration tests GREEN | VERIFIED | 124 lines; both tests PASS; branches inspection pattern correctly checks `workflow.branches[node_name][fn_name].ends` for conditional destinations |
| `tests/test_l3_integration.py` | Stale assertion updated | VERIFIED | Line 222 asserts `("claw_guard", "institutional_guard")` — old `claw_guard→data_fetcher` assertion removed |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| orchestrator.py (claw_guard) | orchestrator.py (institutional_guard) | `workflow.add_edge("claw_guard", "institutional_guard")` | WIRED | Line 321; confirmed present, old direct edge to data_fetcher absent |
| orchestrator.py (institutional_guard) | orchestrator.py (data_fetcher or synthesize) | `workflow.add_conditional_edges("institutional_guard", route_after_institutional_guard, {...})` | WIRED | Lines 322-326; both routing targets registered |
| decision_card.py (build_decision_card) | state['metadata']['trade_risk_score'] | `state.get("metadata", {}).get("trade_risk_score")` | WIRED | Lines 144-155 in decision_card.py; pre-existing Phase 11 wiring now receives value |
| tests/test_graph_wiring.py | orchestrator.py (create_orchestrator_graph) | `create_orchestrator_graph({})` call with StateGraph.compile monkeypatched | WIRED | Lines 12, 39 in test file; closure pattern captures raw workflow for edge inspection |
| tests/test_graph_wiring.py | institutional_guard_node | `asyncio.run(institutional_guard_node(state, config=config))` with AsyncMock patches | WIRED | Line 117 in test file; _get_open_positions and _get_daily_pnl patched |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| RISK-07 | 13-01-PLAN.md, 13-02-PLAN.md | Aggregate portfolio constraints enforced at institutional_guard gate on every trade | SATISFIED | institutional_guard_node now in live execution path between claw_guard and data_fetcher; graph wiring test GREEN |
| RISK-08 | 13-01-PLAN.md, 13-02-PLAN.md | Pre-trade risk scoring sets state["metadata"]["trade_risk_score"] and ["portfolio_heat"]; values recorded in DecisionCard.portfolio_risk_score | SATISFIED | metadata propagation test GREEN; decision_card.py wiring confirmed |

**Orphaned requirements:** None. Both IDs declared in both plans and confirmed in REQUIREMENTS.md lines 53-54, 142-143.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None detected | — | — |

No TODO/FIXME/PLACEHOLDER/stub patterns found in `src/graph/orchestrator.py` or `tests/test_graph_wiring.py`. Router functions return concrete string values ("data_fetcher", "synthesize"), not null or empty structures.

---

### Human Verification Required

None. All goal truths are verifiable programmatically via test execution and static analysis. The rejected path (`risk_approved=False → synthesize`) routing logic is encoded in `route_after_institutional_guard` and covered by the router function structure (the `is False` identity check is the only non-obvious subtlety — confirmed correct in code).

---

### Commits Verified

| Hash | Message | Status |
|------|---------|--------|
| 999a6d0 | test(13-01): add RED tests for institutional guard graph wiring | EXISTS |
| 3b6dd8d | feat(13-02): wire institutional_guard into execution graph | EXISTS |
| 5138e10 | fix(13-02): update stale test_l3_chain_order edge assertion | EXISTS |
| 9836afd | docs(13-01): complete wire-institutional-guard TDD RED scaffold plan | EXISTS |
| 2f21117 | docs(13-02): complete wire-institutional-guard plan — RISK-07 + RISK-08 closed | EXISTS |

---

### Gaps Summary

No gaps. All 8 must-haves from Plan 02 verified against the actual codebase:

- `route_after_institutional_guard()` function is substantive (11 lines, uses `is False` identity check, has logging, returns one of two concrete node names).
- The old broken edge `claw_guard → data_fetcher` is gone (zero grep matches).
- The new edges are registered in the correct order: direct edge first, then conditional edge with both routing targets.
- Both test functions in `test_graph_wiring.py` are substantive (not stubs) and pass GREEN under current runtime.
- Phase 8 regression: 7/7 tests pass.
- DecisionCard `portfolio_risk_score` field receives `trade_risk_score` from state metadata via pre-existing wiring that was already correct but starved — now satisfied because `institutional_guard_node` is reachable.

---

_Verified: 2026-03-08T05:00:00Z_
_Verifier: Claude (gsd-verifier)_
