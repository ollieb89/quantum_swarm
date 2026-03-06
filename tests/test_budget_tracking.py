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
