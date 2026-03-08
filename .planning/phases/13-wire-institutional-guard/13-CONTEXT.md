# Phase 13: Wire InstitutionalGuard into LangGraph Graph - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Insert `institutional_guard_node` into the live execution path between `claw_guard` and `data_fetcher` in `orchestrator.py`. The node is already implemented (Phase 8) and already added via `add_node` — the gap is two missing `add_edge` calls plus a conditional routing function for rejection. DecisionCard `portfolio_risk_score` propagation (RISK-08) is a side-effect of wiring being correct. No new node logic needed.

</domain>

<decisions>
## Implementation Decisions

### Rejection routing
- Add a **conditional edge** after `institutional_guard`, not a straight edge to `data_fetcher`
- A new dedicated function `route_after_institutional_guard()` — mirrors `route_after_debate()` / `route_after_order_router()` pattern; one router per decision point
- On `risk_approved=False`: route to `synthesize` (not END directly), so the caller receives a summary explaining why the trade was blocked
- On `risk_approved=True` (or None/absent): route to `data_fetcher` and proceed with L3 chain
- If institutional_guard never ran (bypassed upstream), `trade_risk_score` and `portfolio_heat` remain `None` — not defaulted to `0.0`

### Integration test strategy
- New file: `tests/test_graph_wiring.py` — graph-level integration tests, separate from unit tests in `test_institutional_guard.py`
- **Phase 1 (TDD RED, 13-01):** Graph edge inspection — compile `create_orchestrator_graph({})`, inspect raw `workflow` edges before `compile()`, assert `claw_guard → institutional_guard` and `institutional_guard → data_fetcher` edges exist
- **Phase 2 (metadata propagation):** Mock-based execution test — patch `_get_open_positions` and `_get_daily_pnl` with `AsyncMock` (consistent with Phase 8 pattern), invoke `institutional_guard_node` with a minimal `SwarmState`, assert `state["metadata"]["trade_risk_score"]` and `state["metadata"]["portfolio_heat"]` are non-None after the approved path
- No live PostgreSQL or Gemini API key required for any test in this phase

### Claude's Discretion
- Exact naming of the router function (`route_after_institutional_guard` is preferred but naming is flexible)
- Internal routing dict keys (e.g. `"data_fetcher"` vs `"approved"`)
- How to access workflow edges for assertion in test (inspect `workflow._graph`, `workflow.edges`, or similar LangGraph internal)
- Comment style / inline documentation for the new edge section in orchestrator.py

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `route_after_debate()` and `route_after_order_router()` in `orchestrator.py` — template for the new `route_after_institutional_guard()` function
- `AsyncMock` pattern from `test_institutional_guard.py` — patch `_get_open_positions` and `_get_daily_pnl` for DB-free testing
- `LangGraphOrchestrator.__new__()` pattern — bypass `__init__` side-effects when testing orchestrator internals (established Phase 9)

### Established Patterns
- Conditional edge after a guard node: `workflow.add_conditional_edges(node, router_fn, {"target": "target_node"})` — used at `write_research_memory` (risk gate) and `order_router`
- `risk_approved` SwarmState field: already exists (`state.py` line 48, initialised to `None` in orchestrator); `institutional_guard_node` sets `False` on rejection
- `compliance_flags` list: appended by both `claw_guard_node` and `institutional_guard_node`; checked downstream for audit trail

### Integration Points
- **Line 303-304 in orchestrator.py**: `workflow.add_edge("risk_manager", "claw_guard")` + `workflow.add_edge("claw_guard", "data_fetcher")` — the second line is replaced by `add_edge("claw_guard", "institutional_guard")` + conditional edges from `institutional_guard`
- `institutional_guard_node` already imported at top of orchestrator.py (line 29)
- `institutional_guard` node already registered via `add_node` (line 249) — no node registration needed
- `synthesize` node is the correct rejection target (mirrors how risk_manager rejection ends: `route_after_debate` routes to `END` on hold, but `synthesize → END` produces a response)

</code_context>

<specifics>
## Specific Ideas

- The roadmap success criteria literally lists `workflow.add_edge("claw_guard", "institutional_guard")` and `workflow.add_edge("institutional_guard", "data_fetcher")` — the conditional edge for rejection is an addition beyond that, but aligns with "enforcing aggregate portfolio constraints"
- "Inspect raw workflow edges before compile()" — use LangGraph's internal structure to check edges without triggering compilation side-effects

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 13-wire-institutional-guard*
*Context gathered: 2026-03-08*
