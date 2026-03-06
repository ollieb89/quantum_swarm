"""
Unit tests for MacroAnalyst and QuantModeler LangGraph node functions.

All tests are offline — no real LLM calls are made. The lazy-init singletons
(_macro_agent, _quant_agent) are pre-set with MagicMock instances before each
node function is invoked, so create_react_agent / ChatGoogleGenerativeAI are
never triggered.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

import src.graph.agents.analysts as analysts_mod
from src.graph.agents.analysts import MacroAnalyst, QuantModeler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_analyst_singletons():
    """Reset lazy singletons before and after every test."""
    analysts_mod._macro_agent = None
    analysts_mod._quant_agent = None
    yield
    analysts_mod._macro_agent = None
    analysts_mod._quant_agent = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**overrides) -> dict:
    """Return a minimal SwarmState-compatible dict."""
    base = {
        "task_id": "test-task-analysts",
        "user_input": "Should I buy BTC?",
        "intent": "analysis",
        "messages": [],
        "macro_report": None,
        "quant_proposal": None,
        "bullish_thesis": None,
        "bearish_thesis": None,
        "debate_resolution": None,
        "weighted_consensus_score": None,
        "debate_history": [],
        "risk_approval": None,
        "consensus_score": 0.0,
        "compliance_flags": [],
        "risk_approved": None,
        "risk_notes": None,
        "final_decision": None,
        "metadata": {},
    }
    base.update(overrides)
    return base


def _make_mock_agent(content: str) -> MagicMock:
    """Return a MagicMock agent whose .invoke() returns a single AIMessage."""
    fake_msg = AIMessage(content=content)
    mock = MagicMock()
    mock.invoke.return_value = {"messages": [fake_msg]}
    return mock


# ---------------------------------------------------------------------------
# MacroAnalyst tests
# ---------------------------------------------------------------------------


def test_macro_analyst_returns_messages_dict():
    """MacroAnalyst returns a dict with a non-empty 'messages' list."""
    analysts_mod._macro_agent = _make_mock_agent("macro analysis result")
    result = MacroAnalyst(_make_state())

    assert isinstance(result, dict), "MacroAnalyst must return a dict"
    assert "messages" in result, "Result must contain 'messages' key"
    assert isinstance(result["messages"], list), "'messages' must be a list"
    assert len(result["messages"]) > 0, "'messages' list must be non-empty"


def test_macro_analyst_message_name():
    """The AIMessage produced by MacroAnalyst has name == 'MacroAnalyst'."""
    analysts_mod._macro_agent = _make_mock_agent("macro result content")
    result = MacroAnalyst(_make_state())

    msg = result["messages"][0]
    assert isinstance(msg, AIMessage), "Message must be an AIMessage instance"
    assert msg.name == "MacroAnalyst", (
        f"Expected name='MacroAnalyst', got name='{msg.name}'"
    )


def test_macro_analyst_empty_agent_output():
    """When mock agent returns empty messages list, node still returns a fallback message."""
    mock = MagicMock()
    mock.invoke.return_value = {"messages": []}
    analysts_mod._macro_agent = mock

    result = MacroAnalyst(_make_state())

    assert isinstance(result, dict), "MacroAnalyst must return a dict even on empty output"
    assert "messages" in result
    assert len(result["messages"]) > 0, "Node must produce a fallback message"

    msg = result["messages"][0]
    assert isinstance(msg, AIMessage)
    # Fallback content should mention MacroAnalyst
    assert "MacroAnalyst" in msg.content, (
        f"Fallback content should reference 'MacroAnalyst', got: '{msg.content}'"
    )


# ---------------------------------------------------------------------------
# QuantModeler tests
# ---------------------------------------------------------------------------


def test_quant_modeler_returns_messages_dict():
    """QuantModeler returns a dict with a non-empty 'messages' list."""
    analysts_mod._quant_agent = _make_mock_agent("quant trade proposal")
    result = QuantModeler(_make_state())

    assert isinstance(result, dict), "QuantModeler must return a dict"
    assert "messages" in result, "Result must contain 'messages' key"
    assert isinstance(result["messages"], list), "'messages' must be a list"
    assert len(result["messages"]) > 0, "'messages' list must be non-empty"


def test_quant_modeler_message_name():
    """The AIMessage produced by QuantModeler has name == 'QuantModeler'."""
    analysts_mod._quant_agent = _make_mock_agent("quant result content")
    result = QuantModeler(_make_state())

    msg = result["messages"][0]
    assert isinstance(msg, AIMessage), "Message must be an AIMessage instance"
    assert msg.name == "QuantModeler", (
        f"Expected name='QuantModeler', got name='{msg.name}'"
    )


def test_quant_modeler_empty_agent_output():
    """When mock agent returns empty messages list, node still returns a fallback message."""
    mock = MagicMock()
    mock.invoke.return_value = {"messages": []}
    analysts_mod._quant_agent = mock

    result = QuantModeler(_make_state())

    assert isinstance(result, dict), "QuantModeler must return a dict even on empty output"
    assert "messages" in result
    assert len(result["messages"]) > 0, "Node must produce a fallback message"

    msg = result["messages"][0]
    assert isinstance(msg, AIMessage)
    # Fallback content should be non-empty and mention no output
    assert "no output" in msg.content or len(msg.content) > 0, (
        f"Fallback content should be non-empty, got: '{msg.content}'"
    )


def test_quant_modeler_uses_macro_context():
    """QuantModeler called with macro_report in state doesn't crash; agent invoked once."""
    macro_context = {
        "phase": "Bullish",
        "risk_on": True,
        "confidence": 0.78,
        "sentiment": "Risk-On",
        "outlook": "2-3 days",
        "indicators": {"vix": 14.5},
    }
    mock_agent = _make_mock_agent("quant proposal with macro context")
    analysts_mod._quant_agent = mock_agent

    state = _make_state(macro_report=macro_context)
    result = QuantModeler(state)

    # Node must succeed and return expected shape
    assert isinstance(result, dict)
    assert "messages" in result
    assert len(result["messages"]) > 0

    # Underlying mock agent must have been called exactly once
    mock_agent.invoke.assert_called_once()
