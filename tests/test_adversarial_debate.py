"""
Integration tests for the adversarial debate layer — Phase 2 validation scenarios.

Scenario A: Overfitting detection
  - BearishResearcher produces more (longer) macro counter-evidence than BullishResearcher
  - DebateSynthesizer produces weighted_consensus_score < 0.5 (bearish dominates)
  - BearishResearcher's hypothesis appears in debate_history

Scenario B: Budget enforcement
  - BudgetedTool enforces max_calls=5; the 6th call raises ToolBudgetExceeded
  - Calls 1-5 succeed

Scenario C: Provenance tracking
  - Every researcher-sourced entry in debate_history has a non-empty "hypothesis" field
  - No entry from a researcher has hypothesis == None or hypothesis == ""

Plan: 02-05 — Adversarial Debate Integration Tests
"""

from __future__ import annotations

import pytest

from src.graph.debate import DebateSynthesizer
from src.tools.verification_wrapper import BudgetedTool, ToolBudgetExceeded, ToolCache


# ---------------------------------------------------------------------------
# Shared fixture: clear ToolCache between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_tool_cache():
    """Prevent cross-test cache pollution."""
    ToolCache.clear()
    yield
    ToolCache.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_base_state(**overrides) -> dict:
    """Return a minimal SwarmState-compatible dict."""
    base = {
        "task_id": "test-task-02-05",
        "user_input": "Should I buy BTC?",
        "intent": "trade",
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
# Scenario A: Overfitting detection
# ---------------------------------------------------------------------------


def test_scenario_a_overfitting():
    """
    When MacroAnalyst shows high-confidence quant signal but weak macro data:
    - BullishResearcher produces short supporting evidence (low quality)
    - BearishResearcher produces long macro counter-evidence (high quality)

    Expected outcome after DebateSynthesizer:
    - weighted_consensus_score < 0.5  (bearish evidence dominates by length)
    - debate_history contains an entry from "bearish_research" with hypothesis "macro_refutation"
    """
    # Build state messages: MacroAnalyst flags weak macro but strong quant signal
    # BullishResearcher produces short low-quality output
    bullish_short_content = "Bullish: RSI high."  # deliberately short

    # BearishResearcher produces long counter-evidence with macro_refutation hypothesis
    bearish_long_content = (
        "Bearish macro refutation: "
        "GDP growth is slowing significantly — Q3 fell to 1.2% annualised from 3.8%. "
        "PMI is below 50 for the third consecutive month signalling contraction. "
        "Unemployment has risen from 3.5% to 4.2% in the last two quarters. "
        "Core inflation remains elevated at 4.1% constraining Fed policy space. "
        "Credit spreads are widening; HY spreads +180 bps since last month. "
        "Consumer confidence index dropped to 62 — lowest since 2020. "
        "The macro backdrop does NOT support the bullish quant signal. "
        "hypothesis=macro_refutation"
    )

    # Create plain dict messages (DebateSynthesizer handles dict messages with "name" key)
    state = _make_base_state(
        messages=[
            # MacroAnalyst output (context only — not used by synthesizer scoring)
            {
                "role": "assistant",
                "name": "MacroAnalyst",
                "content": '{"phase": "Neutral", "risk_on": False, "confidence": 0.45}',
            },
            # BullishResearcher output — short content → low bullish strength
            {
                "role": "assistant",
                "name": "bullish_research",
                "content": bullish_short_content,
            },
            # BearishResearcher output — long content → high bearish strength
            {
                "role": "assistant",
                "name": "bearish_research",
                "content": bearish_long_content,
            },
        ]
    )

    result = DebateSynthesizer(state)

    score = result["weighted_consensus_score"]
    history = result["debate_history"]

    # Assertion 1: bearish evidence dominates → score < 0.5
    assert score < 0.5, (
        f"Expected weighted_consensus_score < 0.5 when bearish evidence dominates, "
        f"got {score:.4f} (bullish_len={len(bullish_short_content)}, "
        f"bearish_len={len(bearish_long_content)})"
    )

    # Assertion 2: debate_history contains bearish_research entry
    bearish_entries = [e for e in history if e.get("source") == "bearish_research"]
    assert len(bearish_entries) >= 1, (
        "Expected at least one bearish_research entry in debate_history"
    )

    # Verify the bearish entry records a hypothesis
    for entry in bearish_entries:
        assert entry.get("hypothesis"), (
            f"bearish_research entry in debate_history must have non-empty hypothesis, "
            f"got: {entry}"
        )


# ---------------------------------------------------------------------------
# Scenario B: Budget enforcement
# ---------------------------------------------------------------------------


def test_scenario_b_budget_enforcement():
    """
    BudgetedTool wrapping a mock fetch_market_data with max_calls=5:
    - Calls 1-5 succeed and return the mock result
    - The 6th call raises ToolBudgetExceeded
    """
    mock_result = {"price": 50000.0, "volume": 1234567, "symbol": "BTC-USD"}
    call_counter = {"n": 0}

    def mock_fetch_market_data(symbol: str, timeframe: str = "1h") -> dict:
        call_counter["n"] += 1
        return {**mock_result, "call_number": call_counter["n"]}

    mock_fetch_market_data.__name__ = "fetch_market_data"

    bt = BudgetedTool(tool_fn=mock_fetch_market_data, max_calls=5)

    # Calls 1-5 must succeed (use unique args to bypass cache)
    for i in range(5):
        result = bt(symbol=f"BTC-USD-{i}", timeframe="1h", hypothesis="budget_test")
        assert result is not None, f"Call {i + 1} should succeed, got None"
        assert result["price"] == 50000.0, f"Call {i + 1} returned unexpected result"

    assert bt.call_count == 5, f"Expected call_count=5 after 5 calls, got {bt.call_count}"

    # 6th call must raise ToolBudgetExceeded
    with pytest.raises(ToolBudgetExceeded):
        bt(symbol="BTC-USD-5", timeframe="1h", hypothesis="budget_test")

    # Underlying tool should still only have been called 5 times
    assert call_counter["n"] == 5, (
        f"Underlying tool should be called exactly 5 times; got {call_counter['n']}"
    )


# ---------------------------------------------------------------------------
# Scenario C: Provenance tracking
# ---------------------------------------------------------------------------


def test_scenario_c_provenance():
    """
    Every researcher-sourced entry in debate_history must have a non-empty
    "hypothesis" field. This verifies that the hypothesis gating from
    verification_wrapper propagates into the state correctly.
    """
    # Build state with researcher messages that include hypothesis metadata
    state = _make_base_state(
        messages=[
            # BullishResearcher output with explicit hypothesis metadata in content
            {
                "role": "assistant",
                "name": "bullish_research",
                "content": (
                    "Bullish thesis confirmed. "
                    '{"hypothesis": "BTC momentum breakout", '
                    '"supporting_evidence": ["RSI > 65", "Volume surge"], '
                    '"confidence": 0.72}'
                ),
            },
            # BearishResearcher output with hypothesis metadata
            {
                "role": "assistant",
                "name": "bearish_research",
                "content": (
                    "Bearish thesis: macro headwinds. "
                    '{"hypothesis": "macro_refutation", '
                    '"refuting_evidence": ["PMI < 50", "Yield curve inverted"], '
                    '"confidence": 0.68}'
                ),
            },
        ]
    )

    result = DebateSynthesizer(state)
    history = result["debate_history"]

    # All researcher entries must have a non-empty "hypothesis" field
    researcher_sources = {"bullish_research", "bearish_research"}
    researcher_entries = [e for e in history if e.get("source") in researcher_sources]

    assert len(researcher_entries) >= 1, (
        "Expected at least one researcher entry in debate_history"
    )

    for entry in researcher_entries:
        hypothesis = entry.get("hypothesis")
        assert hypothesis is not None, (
            f"Entry from '{entry.get('source')}' has hypothesis=None in debate_history"
        )
        assert hypothesis != "", (
            f"Entry from '{entry.get('source')}' has hypothesis='' in debate_history"
        )
        # The hypothesis field must be a non-empty string
        assert isinstance(hypothesis, str) and hypothesis.strip(), (
            f"Entry from '{entry.get('source')}' has blank/non-string hypothesis: "
            f"'{hypothesis}'"
        )


# ---------------------------------------------------------------------------
# Bug 1: DebateSynthesizer must write debate_resolution to state
# ---------------------------------------------------------------------------


def test_debate_synthesizer_writes_debate_resolution_to_state():
    """Bug 1: DebateSynthesizer must return debate_resolution key so DecisionCard can read it."""
    state = _make_base_state(
        messages=[
            {
                "role": "assistant",
                "name": "bullish_research",
                "content": "Bullish: strong momentum. hypothesis=bullish_momentum",
            },
            {
                "role": "assistant",
                "name": "bearish_research",
                "content": "Bearish: macro headwinds. hypothesis=bearish_macro",
            },
        ]
    )

    result = DebateSynthesizer(state)

    assert "debate_resolution" in result, (
        "DebateSynthesizer must include 'debate_resolution' in its returned state dict; "
        f"got keys: {list(result.keys())}"
    )
    assert result["debate_resolution"] is not None, "debate_resolution must not be None"
