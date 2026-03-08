"""
TDD RED scaffold for Phase 12 gap closure — MEM-03 integration fixes.

Tests in this file describe two broken behaviors identified by the v1.1 milestone audit:

  MC-01: RuleGenerator.persist_rules() stores rules as "proposed" status.
         get_active_rules() returns only "active" rules — JSON registry branch of
         _load_institutional_memory() is always empty after persist_rules().

  MC-02: MacroAnalyst and QuantModeler invoke() calls start fresh HumanMessage
         conversations — the institutional memory injected into initial_state["messages"]
         is never forwarded into the ReAct sub-graph LLM context.

All MC-01 and MC-02 tests FAIL RED before Plan 02 implementation.
The single regression guard test (test_macro_analyst_no_memory_state_still_works) PASSES
both before and after Plan 02.

Run: .venv/bin/python3.12 -m pytest tests/test_mem03_integration.py -v
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from src.core.memory_registry import MemoryRegistry
from src.models.memory import MemoryRule
from src.agents.rule_generator import RuleGenerator
from src.agents.rule_validator import RuleValidator
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


@pytest.fixture()
def temp_rule(tmp_path) -> MemoryRule:
    """Return a minimal valid MemoryRule for use in persist_rules() tests."""
    return MemoryRule(
        title="PREFER: diversified assets to reduce concentration risk",
        type="strategy_preference",
        condition={"concentration_risk": "high"},
        action={"diversify": True},
        evidence={},
    )


@pytest.fixture()
def isolated_rule_generator(tmp_path) -> RuleGenerator:
    """
    Return a RuleGenerator with registry and memory_md_path redirected to tmp_path.

    This prevents any writes to the live data/ directory during tests.
    """
    rg = RuleGenerator()
    rg.registry = MemoryRegistry(str(tmp_path / "reg.json"))
    rg.memory_md_path = tmp_path / "MEMORY.md"
    return rg


def _make_mock_analyst_agent(content: str = "analyst response") -> MagicMock:
    """Return a MagicMock agent whose .invoke() returns a single AIMessage."""
    fake_msg = AIMessage(content=content)
    mock = MagicMock()
    mock.invoke.return_value = {"messages": [fake_msg]}
    return mock


def _make_state(**overrides) -> dict:
    """Return a minimal SwarmState-compatible dict."""
    base = {
        "task_id": "test-mem03-integration",
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


# ---------------------------------------------------------------------------
# MC-01: Rule lifecycle — persist_rules() must promote rules to active
# ---------------------------------------------------------------------------


def test_persist_rules_promotes_to_active(isolated_rule_generator, temp_rule):
    """
    MEM-06: persist_rules() adds rules as proposed, then validator promotes
    passing rules to 'active'. With mocked backtest returning improved metrics,
    the rule must end up active.
    """
    rg = isolated_rule_generator
    audit_path = rg.memory_md_path.parent / "audit.jsonl"
    original_init = RuleValidator.__init__

    def patched_init(self_v, **kwargs):
        original_init(self_v, **kwargs)
        self_v.audit_path = audit_path

    # Mock backtest so validator promotes to active (2-of-3 metrics improve)
    with patch.object(RuleValidator, "__init__", patched_init):
        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=[
                {"sharpe_ratio": 1.0, "max_drawdown": -0.10, "win_rate": 0.50, "total_trades": 15},
                {"sharpe_ratio": 1.5, "max_drawdown": -0.05, "win_rate": 0.60, "total_trades": 15},
            ],
        ):
            rg.persist_rules([temp_rule])

    active_rules = rg.registry.get_active_rules()
    assert len(active_rules) > 0, (
        "MEM-06: persist_rules() + validator must promote passing rules to 'active'. "
        f"get_active_rules() returned {active_rules!r}. "
        "Validator runs after add_rule(); passing backtest promotes to active."
    )


def test_persist_rules_active_rules_accessible_across_registry_instances(
    isolated_rule_generator, temp_rule, tmp_path
):
    """
    MEM-06: After persist_rules() + validator promotion, a fresh MemoryRegistry
    at the same path must return the rule from get_active_rules() (durability).
    """
    rg = isolated_rule_generator
    reg_path = str(tmp_path / "reg.json")
    rg.registry = MemoryRegistry(reg_path)
    rg.memory_md_path = tmp_path / "MEMORY.md"
    audit_path = tmp_path / "audit.jsonl"
    original_init = RuleValidator.__init__

    def patched_init(self_v, **kwargs):
        original_init(self_v, **kwargs)
        self_v.audit_path = audit_path

    with patch.object(RuleValidator, "__init__", patched_init):
        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=[
                {"sharpe_ratio": 1.0, "max_drawdown": -0.10, "win_rate": 0.50, "total_trades": 15},
                {"sharpe_ratio": 1.5, "max_drawdown": -0.05, "win_rate": 0.60, "total_trades": 15},
            ],
        ):
            rg.persist_rules([temp_rule])

    fresh_registry = MemoryRegistry(reg_path)
    active_rules = fresh_registry.get_active_rules()

    assert len(active_rules) > 0, (
        "MEM-06: Validator promotion must be durable. "
        f"A fresh MemoryRegistry at the same path returned {active_rules!r}. "
        "Expected the rule to be persisted as 'active' to disk."
    )
    assert active_rules[0].title == temp_rule.title, (
        f"Expected rule title '{temp_rule.title}', got '{active_rules[0].title}'"
    )


# ---------------------------------------------------------------------------
# MC-02: Memory forwarding — analysts must receive memory as first message
# ---------------------------------------------------------------------------


def test_macro_analyst_receives_memory_as_first_message():
    """
    MC-02 RED: MacroAnalyst must forward the institutional memory message from
    state["messages"] as the FIRST element in the invoke() messages list.

    Currently FAILS because analysts.py line 133:
        result = _get_macro_agent().invoke({"messages": [HumanMessage(content=query)]})
    starts a fresh conversation — the memory_message from state["messages"] is ignored.

    Plan 02 fix: Prepend memory message to the invoke() messages list so the LLM
    sees the institutional context before the query.
    """
    memory_content = "INSTITUTIONAL MEMORY: PREFER: diversified assets"
    memory_message = {"role": "system", "content": memory_content}

    state = _make_state(messages=[memory_message])

    mock_agent = _make_mock_analyst_agent("macro analysis result")
    analysts_mod._macro_agent = mock_agent

    MacroAnalyst(state)

    assert mock_agent.invoke.called, "mock_agent.invoke must have been called"
    call_args = mock_agent.invoke.call_args
    # Positional arg 0 is the input dict; key "messages" is the messages list
    messages_sent = call_args[0][0]["messages"]

    assert len(messages_sent) >= 2, (
        f"MC-02 BROKEN: MacroAnalyst invoke() was called with {len(messages_sent)} message(s), "
        "expected at least 2 (memory message + query). "
        "Memory message is not being forwarded into the sub-graph invocation."
    )

    # Check the first message contains the institutional memory content
    first_msg = messages_sent[0]
    # Support both LangChain message objects (.content) and plain dicts ("content")
    first_content = (
        first_msg.content
        if hasattr(first_msg, "content")
        else first_msg.get("content", "")
    )
    assert "INSTITUTIONAL MEMORY" in first_content, (
        f"MC-02 BROKEN: First message in invoke() does not contain 'INSTITUTIONAL MEMORY'. "
        f"Got first message content: {first_content!r}. "
        "Memory message must be the first element so the LLM receives institutional context."
    )


def test_quant_modeler_receives_memory_as_first_message():
    """
    MC-02 RED: QuantModeler must forward the institutional memory message from
    state["messages"] as the FIRST element in the invoke() messages list.

    Currently FAILS because analysts.py line 191:
        result = _get_quant_agent().invoke({"messages": [HumanMessage(content=query)]})
    starts a fresh conversation — the memory_message from state["messages"] is ignored.

    Plan 02 fix: Same as MacroAnalyst — prepend memory message to invoke() list.
    """
    memory_content = "INSTITUTIONAL MEMORY: AVOID: high-beta momentum assets"
    memory_message = {"role": "system", "content": memory_content}

    state = _make_state(messages=[memory_message])

    mock_agent = _make_mock_analyst_agent("quant proposal result")
    analysts_mod._quant_agent = mock_agent

    QuantModeler(state)

    assert mock_agent.invoke.called, "mock_agent.invoke must have been called"
    call_args = mock_agent.invoke.call_args
    messages_sent = call_args[0][0]["messages"]

    assert len(messages_sent) >= 2, (
        f"MC-02 BROKEN: QuantModeler invoke() was called with {len(messages_sent)} message(s), "
        "expected at least 2 (memory message + query). "
        "Memory message is not being forwarded into the sub-graph invocation."
    )

    first_msg = messages_sent[0]
    first_content = (
        first_msg.content
        if hasattr(first_msg, "content")
        else first_msg.get("content", "")
    )
    assert "INSTITUTIONAL MEMORY" in first_content, (
        f"MC-02 BROKEN: First message in invoke() does not contain 'INSTITUTIONAL MEMORY'. "
        f"Got first message content: {first_content!r}. "
        "Memory message must be the first element so the LLM receives institutional context."
    )


# ---------------------------------------------------------------------------
# Regression guard — no memory state must not crash either analyst
# ---------------------------------------------------------------------------


def test_macro_analyst_no_memory_state_still_works():
    """
    Regression guard: MacroAnalyst with state["messages"] = [] (no memory injected)
    must still return a dict with a non-empty "messages" list.

    This PASSES both before AND after Plan 02 implementation — it guards against
    the fix breaking the no-memory code path.
    """
    state = _make_state(messages=[])

    mock_agent = _make_mock_analyst_agent("macro analysis: bullish, no memory context")
    analysts_mod._macro_agent = mock_agent

    result = MacroAnalyst(state)

    assert isinstance(result, dict), "MacroAnalyst must return a dict"
    assert "messages" in result, "Result must contain 'messages' key"
    assert isinstance(result["messages"], list), "'messages' must be a list"
    assert len(result["messages"]) > 0, (
        "MacroAnalyst must return non-empty messages list even with no institutional memory"
    )
