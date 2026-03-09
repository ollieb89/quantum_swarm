"""
tests.test_budget_tracking — Tests for BudgetManager integration and token tracking.

Covers: total_tokens incrementing, SafetyShutdown catch in orchestrator, and
record_usage in classify_intent_with_registry.
"""

import pytest
from unittest.mock import MagicMock
from src.core.budget_manager import BudgetManager
from src.graph.nodes.l1 import classify_intent_with_registry
from src.tools.verification_wrapper import SafetyShutdown


def test_classify_intent_records_and_returns_tokens():
    """classify_intent_with_registry returns the tokens used."""
    state = {"user_input": "analyse BTC", "task_id": "test-tokens"}
    config = {"orchestrator": {"intent_patterns": {"analysis": ["analyse"]}}}
    
    budget = BudgetManager(config={"budget": {"session_token_limit": 1000}})
    
    # Run node
    result = classify_intent_with_registry(state, config=config, budget=budget)
    
    assert result["intent"] == "analysis"
    assert result["total_tokens"] == 50
    assert budget.total_tokens == 50


def test_classify_intent_gate_stops_over_budget():
    """classify_intent_with_registry raises SafetyShutdown if budget is breached."""
    state = {"user_input": "analyse BTC", "task_id": "test-budget-breach"}
    
    # Create budget already at limit
    budget = BudgetManager(config={"budget": {"session_token_limit": 100}})
    budget.record_usage(input_tokens=100, output_tokens=0)
    
    with pytest.raises(SafetyShutdown):
        classify_intent_with_registry(state, budget=budget)


def test_budget_manager_record_usage():
    """BudgetManager correctly records and sums tokens."""
    budget = BudgetManager()
    budget.record_usage(input_tokens=100, output_tokens=50)
    budget.record_usage(input_tokens=200, output_tokens=100)
    
    assert budget.total_tokens == 450
    summary = budget.summary()
    assert summary["total_tokens"] == 450
    assert summary["session_usd"] > 0


# ---------------------------------------------------------------------------
# Per-agent token tracking (Phase 30, Plan 02)
# ---------------------------------------------------------------------------


def test_per_agent_tracking():
    """record_usage with agent_id tracks per-agent totals."""
    budget = BudgetManager()
    budget.record_usage(input_tokens=100, output_tokens=50, agent_id="macro_analyst")
    budget.record_usage(input_tokens=200, output_tokens=100, agent_id="macro_analyst")

    summary = budget.per_agent_summary()
    assert "macro_analyst" in summary
    entry = summary["macro_analyst"]
    assert entry["input_tokens"] == 300
    assert entry["output_tokens"] == 150
    assert entry["total_tokens"] == 450
    assert entry["usd_cost"] > 0


def test_per_agent_multiple_agents():
    """per_agent_summary returns independent totals for each agent."""
    budget = BudgetManager()
    budget.record_usage(input_tokens=100, output_tokens=50, agent_id="macro_analyst")
    budget.record_usage(input_tokens=200, output_tokens=80, agent_id="quant_modeler")

    summary = budget.per_agent_summary()
    assert len(summary) == 2
    assert summary["macro_analyst"]["total_tokens"] == 150
    assert summary["quant_modeler"]["total_tokens"] == 280


def test_per_agent_cleared_on_reset():
    """reset_session clears per-agent data (no cross-cycle leakage)."""
    budget = BudgetManager()
    budget.record_usage(input_tokens=100, output_tokens=50, agent_id="macro_analyst")
    budget.reset_session()

    summary = budget.per_agent_summary()
    assert summary == {}


def test_per_agent_none_agent_id():
    """record_usage without agent_id does not create per-agent entries."""
    budget = BudgetManager()
    budget.record_usage(input_tokens=100, output_tokens=50)

    summary = budget.per_agent_summary()
    assert summary == {}
    # Session totals still tracked
    assert budget.total_tokens == 150
