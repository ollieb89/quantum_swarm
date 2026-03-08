"""
Phase 13 — Plan 01: TDD RED scaffold for institutional guard graph wiring.

test_institutional_guard_wired_in_graph: FAILS in RED state (claw_guard → data_fetcher gap).
test_institutional_guard_metadata_propagation: PASSES in RED state (node logic already correct).

After Plan 02 fixes the wiring, both tests must be GREEN.
"""
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

from src.graph.orchestrator import create_orchestrator_graph
from src.security.institutional_guard import InstitutionalGuard, institutional_guard_node


def test_institutional_guard_wired_in_graph():
    """
    Assert that the orchestrator workflow contains:
      (a) an edge from "claw_guard" to "institutional_guard"
      (b) an edge from "institutional_guard" toward "data_fetcher"

    RED state: claw_guard currently goes directly to data_fetcher,
    bypassing institutional_guard entirely. This test fails with AssertionError.
    """
    captured = {}

    original_compile = None

    def fake_compile(self, *args, **kwargs):
        # Capture the StateGraph instance before it is compiled so we can inspect edges.
        captured["workflow"] = self
        # Return the workflow object itself (not a CompiledGraph) so the caller
        # receives a StateGraph; we don't need a working app, just edge data.
        return self

    # Patch StateGraph.compile at the langgraph.graph level so create_orchestrator_graph
    # returns the raw workflow object without running graph compilation.
    with patch("langgraph.graph.StateGraph.compile", fake_compile):
        graph_obj = create_orchestrator_graph({})

    workflow = captured.get("workflow", graph_obj)

    # Extract direct edges — LangGraph StateGraph exposes a networkx DiGraph via ._graph
    # or falls back to .edges depending on version.
    try:
        edges = list(workflow._graph.edges())
    except AttributeError:
        # Current langgraph: workflow.edges is a set of (src, dst) tuples for direct edges.
        edges = [(e[0], e[1]) for e in getattr(workflow, "edges", [])]

    # Extract conditional-edge destinations from workflow.branches.
    # branches: {source_node: {fn_name: BranchSpec(ends={label: target, ...})}}
    branches = getattr(workflow, "branches", {})

    def conditional_destinations(node_name):
        """Return all target nodes reachable via conditional edges from node_name."""
        dests = []
        for branch_specs in branches.get(node_name, {}).values():
            ends = getattr(branch_specs, "ends", {})
            dests.extend(ends.values())
        return dests

    # (a) claw_guard must route INTO institutional_guard via a direct edge
    assert ("claw_guard", "institutional_guard") in edges, (
        f"Expected edge claw_guard -> institutional_guard not found in graph. "
        f"Edges from claw_guard: {[e for e in edges if e[0] == 'claw_guard']}"
    )

    # (b) institutional_guard must route toward data_fetcher (direct or conditional)
    ig_direct = [e[1] for e in edges if e[0] == "institutional_guard"]
    ig_conditional = conditional_destinations("institutional_guard")
    ig_destinations = ig_direct + ig_conditional
    assert any("data_fetcher" in dest for dest in ig_destinations), (
        f"Expected institutional_guard to route toward data_fetcher. "
        f"Destinations from institutional_guard: {ig_destinations}"
    )


def test_institutional_guard_metadata_propagation():
    """
    Assert that institutional_guard_node populates metadata with trade_risk_score
    and portfolio_heat on the approved path.

    PASSES in RED state — the node logic is already correct; the gap is the graph wiring.
    """
    state = {
        "quant_proposal": {
            "symbol": "BTC/USDT",
            "entry_price": 50000.0,
            "quantity": 1.0,
            "stop_loss": 48000.0,
            "confidence": 0.8,
        },
        "metadata": {},
        "compliance_flags": [],
        "risk_notes": "",
    }

    config = {
        "risk_limits": {
            "max_notional_exposure": 500000.0,
            "max_concurrent_trades": 10,
            "max_asset_concentration_pct": 0.20,
            "starting_capital": 1000000.0,
            "max_daily_loss": 0.05,
            "max_drawdown": 0.15,
        }
    }

    with patch.object(
        InstitutionalGuard, "_get_open_positions",
        new_callable=AsyncMock, return_value=[]
    ), patch.object(
        InstitutionalGuard, "_get_daily_pnl",
        new_callable=AsyncMock, return_value=0.0
    ):
        result = asyncio.run(institutional_guard_node(state, config=config))

    assert result.get("metadata", {}).get("trade_risk_score") is not None, (
        "Expected trade_risk_score to be set in metadata after institutional_guard_node approval"
    )
    assert result.get("metadata", {}).get("portfolio_heat") is not None, (
        "Expected portfolio_heat to be set in metadata after institutional_guard_node approval"
    )
