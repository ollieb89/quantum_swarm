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
