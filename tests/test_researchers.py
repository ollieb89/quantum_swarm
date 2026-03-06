"""
Unit tests for BullishResearcher and BearishResearcher LangGraph node functions.

All tests are offline — no real LLM calls are made. The lazy-init singletons
(_bullish_llm, _bearish_llm) are pre-set with MagicMock instances before each
node function is invoked, so ChatGoogleGenerativeAI is never triggered.

The mock strategy terminates the ReAct loop on the first pass by returning an
AIMessage with an empty tool_calls list, which causes `not tool_calls` to be
True and the loop to break immediately.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

import src.graph.agents.researchers as researchers_mod
from src.graph.agents.researchers import BullishResearcher, BearishResearcher
from src.tools.verification_wrapper import ToolCache


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_researcher_singletons():
    """Reset lazy singletons and ToolCache before and after every test."""
    ToolCache.clear()
    researchers_mod._bullish_llm = None
    researchers_mod._bearish_llm = None
    yield
    ToolCache.clear()
    researchers_mod._bullish_llm = None
    researchers_mod._bearish_llm = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**overrides) -> dict:
    """Return a SwarmState-compatible dict with all Phase 3 fields populated."""
    base = {
        "task_id": "test-task-researchers",
        "user_input": "Should I buy BTC?",
        "intent": "trade",
        "messages": [],
        "macro_report": {"phase": "Bullish", "risk_on": True, "confidence": 0.78},
        "quant_proposal": {"signal": "BUY", "confidence": 0.72, "symbol": "BTC-USD"},
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
        "trade_history": [],
        "execution_mode": "paper",
        "data_fetcher_result": None,
        "backtest_result": None,
        "execution_result": None,
    }
    base.update(overrides)
    return base


def _make_mock_llm(content: str):
    """Return (mock_llm, bound_mock) where bound_mock.invoke returns a terminal AIMessage."""
    fake_final = AIMessage(content=content)
    fake_final.tool_calls = []  # no tool calls -> loop terminates immediately
    bound_mock = MagicMock()
    bound_mock.invoke.return_value = fake_final
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = bound_mock
    return mock_llm, bound_mock


# ---------------------------------------------------------------------------
# BullishResearcher tests
# ---------------------------------------------------------------------------


def test_bullish_researcher_returns_messages_dict():
    """BullishResearcher returns a dict with a non-empty 'messages' list."""
    mock_llm, _ = _make_mock_llm('{"hypothesis": "BTC is bullish", "confidence": 0.75}')
    researchers_mod._bullish_llm = mock_llm

    result = BullishResearcher(_make_state())

    assert isinstance(result, dict), "BullishResearcher must return a dict"
    assert "messages" in result, "Result must contain 'messages' key"
    assert isinstance(result["messages"], list), "'messages' must be a list"
    assert len(result["messages"]) > 0, "'messages' list must be non-empty"


def test_bullish_researcher_message_name():
    """The AIMessage produced by BullishResearcher has name == 'bullish_research'."""
    mock_llm, _ = _make_mock_llm("bullish research findings")
    researchers_mod._bullish_llm = mock_llm

    result = BullishResearcher(_make_state())

    msg = result["messages"][0]
    assert isinstance(msg, AIMessage), "Message must be an AIMessage instance"
    assert msg.name == "bullish_research", (
        f"Expected name='bullish_research', got name='{msg.name}'"
    )


def test_bullish_researcher_content_is_string():
    """The AIMessage content produced by BullishResearcher is a non-empty string."""
    expected_content = '{"hypothesis": "BTC bullish", "supporting_evidence": ["RSI > 60"], "confidence": 0.8}'
    mock_llm, _ = _make_mock_llm(expected_content)
    researchers_mod._bullish_llm = mock_llm

    result = BullishResearcher(_make_state())

    msg = result["messages"][0]
    assert isinstance(msg.content, str), "Message content must be a string"
    assert len(msg.content) > 0, "Message content must be non-empty"


def test_bullish_researcher_with_trade_history():
    """BullishResearcher handles state with a non-empty trade_history without crashing."""
    mock_llm, _ = _make_mock_llm("bullish thesis with trade history context")
    researchers_mod._bullish_llm = mock_llm

    trade_history = [
        {"symbol": "BTC-USD", "side": "BUY", "entry_price": 45000.0, "pnl_pct": 5.2},
        {"symbol": "ETH-USD", "side": "SELL", "entry_price": 2800.0, "pnl_pct": -1.1},
    ]
    result = BullishResearcher(_make_state(trade_history=trade_history))

    assert isinstance(result, dict)
    assert "messages" in result
    assert len(result["messages"]) > 0


def test_bullish_researcher_empty_messages():
    """BullishResearcher handles state with messages=[], macro_report=None, quant_proposal=None."""
    mock_llm, _ = _make_mock_llm("bullish research with no prior context")
    researchers_mod._bullish_llm = mock_llm

    state = _make_state(messages=[], macro_report=None, quant_proposal=None)
    result = BullishResearcher(state)

    assert isinstance(result, dict)
    assert "messages" in result
    assert len(result["messages"]) > 0


# ---------------------------------------------------------------------------
# BearishResearcher tests
# ---------------------------------------------------------------------------


def test_bearish_researcher_returns_messages_dict():
    """BearishResearcher returns a dict with a non-empty 'messages' list."""
    mock_llm, _ = _make_mock_llm('{"hypothesis": "BTC is bearish", "confidence": 0.65}')
    researchers_mod._bearish_llm = mock_llm

    result = BearishResearcher(_make_state())

    assert isinstance(result, dict), "BearishResearcher must return a dict"
    assert "messages" in result, "Result must contain 'messages' key"
    assert isinstance(result["messages"], list), "'messages' must be a list"
    assert len(result["messages"]) > 0, "'messages' list must be non-empty"


def test_bearish_researcher_message_name():
    """The AIMessage produced by BearishResearcher has name == 'bearish_research'."""
    mock_llm, _ = _make_mock_llm("bearish research findings")
    researchers_mod._bearish_llm = mock_llm

    result = BearishResearcher(_make_state())

    msg = result["messages"][0]
    assert isinstance(msg, AIMessage), "Message must be an AIMessage instance"
    assert msg.name == "bearish_research", (
        f"Expected name='bearish_research', got name='{msg.name}'"
    )


def test_bearish_researcher_content_is_string():
    """The AIMessage content produced by BearishResearcher is a non-empty string."""
    expected_content = '{"hypothesis": "BTC bearish", "refuting_evidence": ["RSI < 40"], "confidence": 0.7}'
    mock_llm, _ = _make_mock_llm(expected_content)
    researchers_mod._bearish_llm = mock_llm

    result = BearishResearcher(_make_state())

    msg = result["messages"][0]
    assert isinstance(msg.content, str), "Message content must be a string"
    assert len(msg.content) > 0, "Message content must be non-empty"


def test_bearish_researcher_with_trade_history():
    """BearishResearcher handles non-empty trade_history without crashing."""
    mock_llm, _ = _make_mock_llm("bearish thesis with trade history context")
    researchers_mod._bearish_llm = mock_llm

    trade_history = [
        {"symbol": "BTC-USD", "side": "BUY", "entry_price": 50000.0, "pnl_pct": -3.5},
        {"symbol": "SOL-USD", "side": "BUY", "entry_price": 120.0, "pnl_pct": None},
    ]
    result = BearishResearcher(_make_state(trade_history=trade_history))

    assert isinstance(result, dict)
    assert "messages" in result
    assert len(result["messages"]) > 0
