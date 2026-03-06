"""
tests.test_blackboard — Tests for the filesystem Blackboard.

Covers: write, read, slot isolation, missing slot, overwrite, orchestrator wiring.
"""

import pytest
from src.blackboard.board import Blackboard
from src.graph.nodes.l1 import risk_manager_node, synthesize_consensus


def test_write_and_read_slot(tmp_path):
    """Written data is retrievable from the same slot."""
    board = Blackboard(base_dir=tmp_path)
    board.write("macro_report", {"symbol": "BTC", "trend": "bullish"})

    result = board.read("macro_report")

    assert result == {"symbol": "BTC", "trend": "bullish"}


def test_read_missing_slot_returns_none(tmp_path):
    """Reading a slot that was never written returns None."""
    board = Blackboard(base_dir=tmp_path)

    result = board.read("quant_proposal")

    assert result is None


def test_slot_isolation(tmp_path):
    """Writing to one slot does not affect another slot."""
    board = Blackboard(base_dir=tmp_path)
    board.write("macro_report", {"value": 1})
    board.write("risk_approval", {"approved": True})

    assert board.read("macro_report") == {"value": 1}
    assert board.read("risk_approval") == {"approved": True}


def test_overwrite_slot(tmp_path):
    """Writing to an existing slot replaces its content."""
    board = Blackboard(base_dir=tmp_path)
    board.write("debate_resolution", {"winner": "bull"})
    board.write("debate_resolution", {"winner": "bear"})

    result = board.read("debate_resolution")

    assert result == {"winner": "bear"}


def test_clear_slot(tmp_path):
    """Clearing a slot makes it read as None."""
    board = Blackboard(base_dir=tmp_path)
    board.write("macro_report", {"data": "x"})
    board.clear("macro_report")

    assert board.read("macro_report") is None


def test_list_slots(tmp_path):
    """list_slots returns all slot names that have been written."""
    board = Blackboard(base_dir=tmp_path)
    board.write("macro_report", {})
    board.write("quant_proposal", {})

    slots = board.list_slots()

    assert set(slots) == {"macro_report", "quant_proposal"}


# --- Orchestrator wiring tests ---

def test_risk_manager_writes_risk_approval_to_blackboard(tmp_path):
    """risk_manager_node writes risk_approval slot when board is provided."""
    board = Blackboard(base_dir=tmp_path)
    state = {
        "task_id": "test-rm",
        "debate_history": [{"hypothesis": "bullish"}, {"hypothesis": "bearish"}],
        "weighted_consensus_score": 0.75,
        "messages": [],
    }

    risk_manager_node(state, board=board)

    result = board.read("risk_approval")
    assert result is not None
    assert result["approved"] is True
    assert "notes" in result


def test_risk_manager_no_board_still_returns_state(tmp_path):
    """risk_manager_node works normally when board=None (backward-compatible)."""
    state = {
        "task_id": "test-no-board",
        "debate_history": [{"hypothesis": "bullish"}, {"hypothesis": "bearish"}],
        "weighted_consensus_score": 0.75,
        "messages": [],
    }

    result = risk_manager_node(state)

    assert result["risk_approved"] is True


def test_synthesize_writes_final_decision_to_blackboard(tmp_path):
    """synthesize_consensus writes final_decision slot when board is provided."""
    board = Blackboard(base_dir=tmp_path)
    state = {"task_id": "test-synth", "messages": []}

    synthesize_consensus(state, config={}, board=board)

    result = board.read("final_decision")
    assert result is not None
    assert result["task_id"] == "test-synth"
