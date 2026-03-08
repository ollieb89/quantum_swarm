"""
Unit tests for the risk-gating conditional routing function.

Validates that route_after_debate() correctly routes based on the
weighted_consensus_score threshold (STRICT > 0.6).

Plan: 02-04 — Risk Gating
"""

import pytest

from src.graph.orchestrator import route_after_debate


def _make_state(score) -> dict:
    """Build a minimal SwarmState-compatible dict for routing tests."""
    return {
        "task_id": "test-task",
        "user_input": "test",
        "intent": "trade",
        "messages": [],
        "macro_report": None,
        "quant_proposal": None,
        "bullish_thesis": None,
        "bearish_thesis": None,
        "debate_resolution": None,
        "weighted_consensus_score": score,
        "debate_history": [],
        "risk_approval": None,
        "consensus_score": 0.0,
        "compliance_flags": [],
        "risk_approved": None,
        "risk_notes": None,
        "final_decision": None,
        "metadata": {},
    }


def test_high_consensus_routes_to_risk_manager():
    """Score above threshold (0.8 > 0.6) must route to risk_manager."""
    state = _make_state(0.8)
    result = route_after_debate(state)
    assert result == "risk_manager", (
        f"Expected 'risk_manager' for score=0.8, got '{result}'"
    )


def test_low_consensus_routes_to_hold():
    """Score below threshold (0.4 <= 0.6) must route to hold."""
    state = _make_state(0.4)
    result = route_after_debate(state)
    assert result == "hold", (
        f"Expected 'hold' for score=0.4, got '{result}'"
    )


def test_boundary_excluded():
    """Boundary score (exactly 0.6) must route to hold — threshold is STRICT > 0.6."""
    state = _make_state(0.6)
    result = route_after_debate(state)
    assert result == "hold", (
        f"Expected 'hold' for score=0.6 (boundary excluded), got '{result}'"
    )


# ---------------------------------------------------------------------------
# Bug 3: risk_manager_node must write risk_approval to SwarmState
# ---------------------------------------------------------------------------


def _make_risk_state(score: float = 0.8) -> dict:
    return {
        "task_id": "test-risk-approval",
        "user_input": "Buy AAPL",
        "intent": "trade",
        "messages": [],
        "macro_report": None,
        "quant_proposal": None,
        "bullish_thesis": None,
        "bearish_thesis": None,
        "debate_resolution": None,
        "weighted_consensus_score": score,
        "debate_history": [
            {"source": "bullish_research", "hypothesis": "bullish", "evidence": "momentum", "strength": 60.0},
            {"source": "bearish_research", "hypothesis": "bearish", "evidence": "macro risk", "strength": 40.0},
        ],
        "risk_approval": None,
        "consensus_score": 0.0,
        "compliance_flags": [],
        "risk_approved": None,
        "risk_notes": None,
        "final_decision": None,
        "metadata": {},
    }


def test_risk_manager_node_writes_risk_approval_to_state():
    """Bug 3: risk_manager_node must include risk_approval in returned state dict.

    The card builder reads state.get('risk_approval'); if the node only writes to
    the Blackboard and not to state, the card will always have risk_approval={}.
    """
    from src.graph.nodes.l1 import risk_manager_node

    result = risk_manager_node(_make_risk_state(score=0.8), board=None)

    assert "risk_approval" in result, (
        "risk_manager_node must include 'risk_approval' in its returned state dict"
    )
    assert isinstance(result["risk_approval"], dict), "'risk_approval' must be a dict"
    assert "approved" in result["risk_approval"], "'risk_approval' dict must contain 'approved' key"


def test_risk_manager_node_risk_approval_reflects_approval_decision():
    """The risk_approval dict in state must reflect the actual approval outcome."""
    from src.graph.nodes.l1 import risk_manager_node

    result = risk_manager_node(_make_risk_state(score=0.8), board=None)

    assert result["risk_approval"]["approved"] is True, (
        f"Expected approved=True for score=0.8 with valid debate history, got: {result['risk_approval']}"
    )
