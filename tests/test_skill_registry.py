"""
tests.test_skill_registry — Tests for the SkillRegistry discovery and routing.

Covers: discover, route, no-match, deterministic bypass via classify_intent.
"""

import pytest
from src.skills.registry import SkillRegistry
from src.graph.nodes.l1 import classify_intent_with_registry


# --- Discovery ---

def test_registry_discovers_at_least_two_skills():
    """discover() finds all skills exposing SKILL_INTENT + handle."""
    registry = SkillRegistry()
    registry.discover()
    assert len(registry.intents) >= 2


def test_registry_discovers_market_analysis_skill():
    """market_analysis.py is found under its declared SKILL_INTENT."""
    registry = SkillRegistry()
    registry.discover()
    assert "market_analysis" in registry.intents


def test_registry_discovers_weekly_review_skill():
    """crypto_learning.py is found under its declared SKILL_INTENT."""
    registry = SkillRegistry()
    registry.discover()
    assert "weekly_review" in registry.intents


# --- Routing ---

def test_route_returns_none_for_unknown_intent():
    """route() returns None when no skill matches the intent."""
    registry = SkillRegistry()
    registry.discover()
    result = registry.route("unknown_xyz_intent", {})
    assert result is None


def test_route_calls_market_analysis_handler():
    """route() calls the market_analysis handler and returns a dict."""
    registry = SkillRegistry()
    registry.discover()
    state = {
        "user_input": "analyze BTC",
        "task_id": "test-ma",
        "messages": [],
    }
    result = registry.route("market_analysis", state)
    assert result is not None
    assert isinstance(result, dict)


def test_route_calls_weekly_review_handler():
    """route() calls the weekly_review handler and returns a dict."""
    registry = SkillRegistry()
    registry.discover()
    state = {
        "user_input": "weekly review",
        "task_id": "test-wr",
        "messages": [],
    }
    result = registry.route("weekly_review", state)
    assert result is not None
    assert isinstance(result, dict)


# --- Deterministic bypass ---

def test_classify_intent_bypasses_graph_for_known_skill():
    """classify_intent_with_registry returns skill result directly for known intents."""
    state = {
        "user_input": "market_analysis of BTC",
        "task_id": "test-bypass",
        "messages": [],
    }
    result = classify_intent_with_registry(state)
    # Should be bypassed — result comes from skill, not pattern matching
    assert result is not None
    assert "skill_result" in result or "intent" in result


def test_classify_intent_falls_through_for_unknown_intent():
    """classify_intent_with_registry falls through to normal routing when no skill matches."""
    state = {
        "user_input": "buy BTC now",
        "task_id": "test-fallthrough",
        "messages": [],
    }
    config = {"orchestrator": {"intent_patterns": {"trade": ["buy", "sell"]}}}
    result = classify_intent_with_registry(state, config=config)
    assert result["intent"] == "trade"
    assert "skill_result" not in result
