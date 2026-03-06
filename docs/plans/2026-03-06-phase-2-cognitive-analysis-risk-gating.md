# Phase 2: Cognitive Analysis & Risk Gating (L2) — Completion Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete Phase 2 — add missing unit tests for the analyst and researcher nodes, verify all P2 tests pass, and update the ROADMAP to reflect Phase 2 as complete.

**Architecture:** Most Phase 2 code already exists (see status below). The remaining work is purely testing and state tracking. Tests use mocked LLMs so no API key is required. Test pattern: create a fake AIMessage response, patch the lazy-init LLM singleton, call the node function, assert shape.

**Tech Stack:** Python 3.12, pytest, `unittest.mock`, LangGraph `SwarmState`, Gemini lazy-init pattern (patch `bind_tools` + `invoke` on the LLM singleton), `scripts/state_engine.py` for ROADMAP update.

---

## Phase 2 Inventory — What Already Exists

| Component | File | Status |
|-----------|------|--------|
| MacroAnalyst, QuantModeler nodes | `src/graph/agents/analysts.py` | ✅ Complete |
| BullishResearcher, BearishResearcher nodes | `src/graph/agents/researchers.py` | ✅ Complete |
| BudgetedTool, ToolCache, budgeted() | `src/tools/verification_wrapper.py` | ✅ Complete |
| fetch_market_data, run_backtest, fetch_economic_data | `src/tools/analyst_tools.py` | ✅ Complete |
| DebateSynthesizer node | `src/graph/debate.py` | ✅ Complete |
| Fan-out/fan-in + route_after_debate | `src/graph/orchestrator.py` | ✅ Complete |
| Adversarial debate integration tests (Scenarios A/B/C) | `tests/test_adversarial_debate.py` | ✅ Passing |
| Verification wrapper unit tests | `tests/test_verification_wrapper.py` | ✅ Passing |
| Risk gating routing tests | `tests/test_risk_gating.py` | ✅ Passing |
| **Analyst node unit tests** | `tests/test_analysts.py` | ❌ Missing |
| **Researcher node unit tests** | `tests/test_researchers.py` | ❌ Missing |
| **ROADMAP P2 state** | `.planning/ROADMAP.md` | ❌ Not updated |

**Remaining work: 2 test files + 1 ROADMAP update.**

---

## Lazy-Init Patching Pattern

The analyst and researcher nodes use lazy singletons with this pattern:

```python
_macro_agent = None
def _get_macro_agent():
    global _macro_agent
    if _macro_agent is None:
        _macro_agent = create_react_agent(...)
    return _macro_agent
```

**To patch without an API key**, force the singleton to init with a mock, then patch `invoke`:

```python
from unittest.mock import MagicMock, patch
import src.graph.agents.analysts as analysts_mod

# Force singleton init with a mock agent
mock_agent = MagicMock()
analysts_mod._macro_agent = mock_agent
mock_agent.invoke.return_value = {"messages": [fake_ai_msg]}
```

For researchers, the LLM is a raw `ChatGoogleGenerativeAI` (not a compiled agent). Patch both `bind_tools` and `invoke`:

```python
import src.graph.agents.researchers as researchers_mod

mock_llm = MagicMock()
researchers_mod._bullish_llm = mock_llm
bound_mock = MagicMock()
mock_llm.bind_tools.return_value = bound_mock
# invoke returns an AIMessage with no tool_calls (terminates the ReAct loop)
bound_mock.invoke.return_value = fake_ai_msg  # no .tool_calls attr
```

---

## Task 1: Unit Tests for Analyst Nodes

**Files:**
- Create: `tests/test_analysts.py`

**Step 1: Write the test file**

Create `tests/test_analysts.py` with this content:

```python
"""
Unit tests for src/graph/agents/analysts.py

Tests:
  1. MacroAnalyst node returns dict with "messages" key containing AIMessage
  2. QuantModeler node returns dict with "messages" key containing AIMessage
  3. MacroAnalyst AIMessage has name="MacroAnalyst"
  4. QuantModeler AIMessage has name="QuantModeler"
  5. Empty agent output handled gracefully (returns fallback content)
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage

import src.graph.agents.analysts as analysts_mod
from src.graph.agents.analysts import MacroAnalyst, QuantModeler


@pytest.fixture(autouse=True)
def reset_analyst_singletons():
    """Reset lazy singletons before each test to prevent cross-test contamination."""
    analysts_mod._macro_agent = None
    analysts_mod._quant_agent = None
    yield
    analysts_mod._macro_agent = None
    analysts_mod._quant_agent = None


def _make_state(**overrides) -> dict:
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


def _fake_macro_content() -> str:
    return json.dumps({
        "phase": "Bullish",
        "risk_on": True,
        "confidence": 0.78,
        "sentiment": "Risk-On",
        "outlook": "2-3 days",
        "indicators": {"vix": 14.5},
    })


def _fake_quant_content() -> str:
    return json.dumps({
        "signal": "BUY",
        "confidence": 0.72,
        "symbol": "BTC-USD",
        "entry_price": 95000.0,
        "stop_loss": 92000.0,
        "take_profit": 102000.0,
        "position_size": 0.05,
        "rationale": "RSI momentum breakout",
    })


def _make_mock_agent(content: str) -> MagicMock:
    """Return a mock agent whose invoke() returns a realistic message list."""
    fake_msg = AIMessage(content=content)
    mock = MagicMock()
    mock.invoke.return_value = {"messages": [fake_msg]}
    return mock


# ---------------------------------------------------------------------------
# Test 1 & 3: MacroAnalyst returns correct shape and name
# ---------------------------------------------------------------------------


def test_macro_analyst_returns_messages_dict():
    """MacroAnalyst node must return {"messages": [...]} with a non-empty list."""
    mock_agent = _make_mock_agent(_fake_macro_content())
    analysts_mod._macro_agent = mock_agent

    result = MacroAnalyst(_make_state())

    assert isinstance(result, dict), "Must return a dict"
    assert "messages" in result, "Must have 'messages' key"
    assert isinstance(result["messages"], list), "'messages' must be a list"
    assert len(result["messages"]) > 0, "'messages' must be non-empty"


def test_macro_analyst_message_name():
    """MacroAnalyst AIMessage must have name='MacroAnalyst'."""
    mock_agent = _make_mock_agent(_fake_macro_content())
    analysts_mod._macro_agent = mock_agent

    result = MacroAnalyst(_make_state())

    msg = result["messages"][0]
    assert hasattr(msg, "name"), "AIMessage must have 'name' attribute"
    assert msg.name == "MacroAnalyst", f"Expected name='MacroAnalyst', got '{msg.name}'"


def test_macro_analyst_empty_agent_output():
    """MacroAnalyst returns fallback string when agent returns empty messages."""
    mock_agent = MagicMock()
    mock_agent.invoke.return_value = {"messages": []}
    analysts_mod._macro_agent = mock_agent

    result = MacroAnalyst(_make_state())

    assert len(result["messages"]) > 0, "Must produce a message even on empty agent output"
    msg = result["messages"][0]
    assert "no output" in msg.content.lower() or len(msg.content) > 0


# ---------------------------------------------------------------------------
# Test 2 & 4: QuantModeler returns correct shape and name
# ---------------------------------------------------------------------------


def test_quant_modeler_returns_messages_dict():
    """QuantModeler node must return {"messages": [...]} with a non-empty list."""
    mock_agent = _make_mock_agent(_fake_quant_content())
    analysts_mod._quant_agent = mock_agent

    result = QuantModeler(_make_state())

    assert isinstance(result, dict)
    assert "messages" in result
    assert len(result["messages"]) > 0


def test_quant_modeler_message_name():
    """QuantModeler AIMessage must have name='QuantModeler'."""
    mock_agent = _make_mock_agent(_fake_quant_content())
    analysts_mod._quant_agent = mock_agent

    result = QuantModeler(_make_state())

    msg = result["messages"][0]
    assert msg.name == "QuantModeler", f"Expected name='QuantModeler', got '{msg.name}'"


def test_quant_modeler_uses_macro_context():
    """QuantModeler reads macro_report from state without crashing."""
    mock_agent = _make_mock_agent(_fake_quant_content())
    analysts_mod._quant_agent = mock_agent

    state = _make_state(macro_report={"phase": "Bullish", "risk_on": True})
    result = QuantModeler(state)

    # The agent was invoked exactly once
    mock_agent.invoke.assert_called_once()
    assert len(result["messages"]) > 0
```

**Step 2: Run the tests to verify they fail (file doesn't exist yet)**

```bash
cd /home/ollie/Development/Tools/quantum_swarm
.venv/bin/pytest tests/test_analysts.py -v 2>&1 | head -20
```

Expected: `ERROR: not found: tests/test_analysts.py`

**Step 3: Create the file**

Write the content above to `tests/test_analysts.py`.

**Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_analysts.py -v
```

Expected output:
```
tests/test_analysts.py::test_macro_analyst_returns_messages_dict PASSED
tests/test_analysts.py::test_macro_analyst_message_name PASSED
tests/test_analysts.py::test_macro_analyst_empty_agent_output PASSED
tests/test_analysts.py::test_quant_modeler_returns_messages_dict PASSED
tests/test_analysts.py::test_quant_modeler_message_name PASSED
tests/test_analysts.py::test_quant_modeler_uses_macro_context PASSED
6 passed
```

**Step 5: Commit**

```bash
git add tests/test_analysts.py
git commit -m "test: add unit tests for MacroAnalyst and QuantModeler nodes (P2 Task 1)"
```

---

## Task 2: Unit Tests for Researcher Nodes

**Files:**
- Create: `tests/test_researchers.py`

**Step 1: Write the test file**

Create `tests/test_researchers.py` with this content:

```python
"""
Unit tests for src/graph/agents/researchers.py

Tests:
  1. BullishResearcher returns {"messages": [...]} with name="bullish_research"
  2. BearishResearcher returns {"messages": [...]} with name="bearish_research"
  3. Both researchers inject trade_history context without crashing
  4. Both researchers handle empty messages state (no analyst context)
  5. BullishResearcher message content is non-empty string
  6. BearishResearcher message content is non-empty string

Mocking strategy:
  - Force singleton LLM init by setting _bullish_llm / _bearish_llm to MagicMock
  - Patch bind_tools to return a bound mock
  - Patch bound mock's invoke to return a plain AIMessage (no tool_calls)
    so the ReAct loop terminates immediately on the first iteration
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage

import src.graph.agents.researchers as researchers_mod
from src.graph.agents.researchers import BullishResearcher, BearishResearcher
from src.tools.verification_wrapper import ToolCache


@pytest.fixture(autouse=True)
def reset_researcher_singletons():
    """Reset lazy LLM singletons and ToolCache before each test."""
    ToolCache.clear()
    researchers_mod._bullish_llm = None
    researchers_mod._bearish_llm = None
    yield
    ToolCache.clear()
    researchers_mod._bullish_llm = None
    researchers_mod._bearish_llm = None


def _make_state(**overrides) -> dict:
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


def _make_mock_llm(content: str) -> tuple[MagicMock, MagicMock]:
    """Return (mock_llm, bound_mock) where bound_mock.invoke returns a non-tool AIMessage."""
    # AIMessage with no tool_calls attribute → ReAct loop terminates on first pass
    fake_msg = AIMessage(content=content)
    # Ensure no tool_calls so the loop exits
    fake_msg.tool_calls = []

    bound_mock = MagicMock()
    bound_mock.invoke.return_value = fake_msg

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = bound_mock

    return mock_llm, bound_mock


_BULLISH_CONTENT = json.dumps({
    "hypothesis": "BTC momentum breakout",
    "supporting_evidence": ["RSI > 65", "Volume surge 2x avg"],
    "confidence": 0.72,
    "recommended_action": "BUY",
    "rationale": "Strong momentum with macro tailwind",
})

_BEARISH_CONTENT = json.dumps({
    "hypothesis": "macro_refutation",
    "refuting_evidence": ["PMI < 50 for 3 months", "Yield curve inverted"],
    "confidence": 0.68,
    "recommended_action": "HOLD",
    "rationale": "Macro headwinds override quant signal",
})


# ---------------------------------------------------------------------------
# Tests for BullishResearcher
# ---------------------------------------------------------------------------


def test_bullish_researcher_returns_messages_dict():
    """BullishResearcher must return {"messages": [...]} with a non-empty list."""
    mock_llm, _ = _make_mock_llm(_BULLISH_CONTENT)
    researchers_mod._bullish_llm = mock_llm

    result = BullishResearcher(_make_state())

    assert isinstance(result, dict)
    assert "messages" in result
    assert isinstance(result["messages"], list)
    assert len(result["messages"]) > 0


def test_bullish_researcher_message_name():
    """BullishResearcher AIMessage must have name='bullish_research'."""
    mock_llm, _ = _make_mock_llm(_BULLISH_CONTENT)
    researchers_mod._bullish_llm = mock_llm

    result = BullishResearcher(_make_state())

    msg = result["messages"][0]
    assert hasattr(msg, "name"), "AIMessage must have 'name' attribute"
    assert msg.name == "bullish_research", (
        f"Expected name='bullish_research', got '{msg.name}'"
    )


def test_bullish_researcher_content_is_string():
    """BullishResearcher message content must be a non-empty string."""
    mock_llm, _ = _make_mock_llm(_BULLISH_CONTENT)
    researchers_mod._bullish_llm = mock_llm

    result = BullishResearcher(_make_state())

    content = result["messages"][0].content
    assert isinstance(content, str) and len(content) > 0, (
        f"Expected non-empty string content, got: {content!r}"
    )


def test_bullish_researcher_with_trade_history():
    """BullishResearcher handles non-empty trade_history without crashing."""
    mock_llm, _ = _make_mock_llm(_BULLISH_CONTENT)
    researchers_mod._bullish_llm = mock_llm

    trade_history = [
        {"symbol": "BTC-USD", "side": "BUY", "entry_price": 90000.0, "pnl_pct": 5.2},
        {"symbol": "ETH-USD", "side": "SELL", "entry_price": 3200.0, "pnl_pct": -1.1},
    ]
    state = _make_state(trade_history=trade_history)
    result = BullishResearcher(state)

    assert len(result["messages"]) > 0


def test_bullish_researcher_empty_messages():
    """BullishResearcher handles state with no analyst messages (no prior context)."""
    mock_llm, _ = _make_mock_llm(_BULLISH_CONTENT)
    researchers_mod._bullish_llm = mock_llm

    state = _make_state(messages=[], macro_report=None, quant_proposal=None)
    result = BullishResearcher(state)

    assert len(result["messages"]) > 0


# ---------------------------------------------------------------------------
# Tests for BearishResearcher
# ---------------------------------------------------------------------------


def test_bearish_researcher_returns_messages_dict():
    """BearishResearcher must return {"messages": [...]} with a non-empty list."""
    mock_llm, _ = _make_mock_llm(_BEARISH_CONTENT)
    researchers_mod._bearish_llm = mock_llm

    result = BearishResearcher(_make_state())

    assert isinstance(result, dict)
    assert "messages" in result
    assert len(result["messages"]) > 0


def test_bearish_researcher_message_name():
    """BearishResearcher AIMessage must have name='bearish_research'."""
    mock_llm, _ = _make_mock_llm(_BEARISH_CONTENT)
    researchers_mod._bearish_llm = mock_llm

    result = BearishResearcher(_make_state())

    msg = result["messages"][0]
    assert msg.name == "bearish_research", (
        f"Expected name='bearish_research', got '{msg.name}'"
    )


def test_bearish_researcher_content_is_string():
    """BearishResearcher message content must be a non-empty string."""
    mock_llm, _ = _make_mock_llm(_BEARISH_CONTENT)
    researchers_mod._bearish_llm = mock_llm

    result = BearishResearcher(_make_state())

    content = result["messages"][0].content
    assert isinstance(content, str) and len(content) > 0


def test_bearish_researcher_with_trade_history():
    """BearishResearcher handles non-empty trade_history without crashing."""
    mock_llm, _ = _make_mock_llm(_BEARISH_CONTENT)
    researchers_mod._bearish_llm = mock_llm

    trade_history = [
        {"symbol": "BTC-USD", "side": "BUY", "entry_price": 90000.0, "pnl_pct": -2.5},
    ]
    state = _make_state(trade_history=trade_history)
    result = BearishResearcher(state)

    assert len(result["messages"]) > 0
```

**Step 2: Run to verify they fail (before file exists)**

```bash
.venv/bin/pytest tests/test_researchers.py -v 2>&1 | head -5
```

Expected: file not found error.

**Step 3: Create the file**

Write the content above to `tests/test_researchers.py`.

**Step 4: Run tests**

```bash
.venv/bin/pytest tests/test_researchers.py -v
```

Expected:
```
tests/test_researchers.py::test_bullish_researcher_returns_messages_dict PASSED
tests/test_researchers.py::test_bullish_researcher_message_name PASSED
tests/test_researchers.py::test_bullish_researcher_content_is_string PASSED
tests/test_researchers.py::test_bullish_researcher_with_trade_history PASSED
tests/test_researchers.py::test_bullish_researcher_empty_messages PASSED
tests/test_researchers.py::test_bearish_researcher_returns_messages_dict PASSED
tests/test_researchers.py::test_bearish_researcher_message_name PASSED
tests/test_researchers.py::test_bearish_researcher_content_is_string PASSED
tests/test_researchers.py::test_bearish_researcher_with_trade_history PASSED
9 passed
```

> **Debugging tip:** If `tool_calls` causes the ReAct loop to continue, ensure `fake_msg.tool_calls = []` is set after constructing the AIMessage. LangChain may add this attribute dynamically.

**Step 5: Commit**

```bash
git add tests/test_researchers.py
git commit -m "test: add unit tests for BullishResearcher and BearishResearcher nodes (P2 Task 2)"
```

---

## Task 3: Full P2 Test Suite Verification

**Files:**
- Read: all P2 test files (no modifications expected)

**Step 1: Run all P2 tests together**

```bash
.venv/bin/pytest tests/test_analysts.py tests/test_researchers.py \
  tests/test_adversarial_debate.py tests/test_verification_wrapper.py \
  tests/test_risk_gating.py -v
```

Expected: all tests pass (target: 6 + 9 + 3 + 3 + 3 = 24 P2-specific tests).

**Step 2: Run the full suite to confirm no regressions**

```bash
.venv/bin/pytest --tb=short -q
```

Expected: all existing tests still pass (previously 46; now 46 + 15 = 61 total).

**Step 3: If any test fails**

Check for these common issues:

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `GOOGLE_API_KEY` validation error at import | Lazy init not working — singleton initialized at module load | Verify the `_macro_agent = None` pattern is respected; ensure fixture resets it BEFORE the test calls the node |
| `AttributeError: 'AIMessage' has no attribute 'tool_calls'` | ReAct loop reads `.tool_calls` but mock doesn't have it | Add `fake_msg.tool_calls = []` after creating the mock AIMessage |
| Researcher test hangs (loop runs 8 iterations) | `bound_mock.invoke` keeps returning responses that trigger tool calls | Ensure `fake_msg.tool_calls = []` not `None`; LangGraph checks truthiness |
| `TypeError: _make_budgeted_tools got unexpected kwarg` | Import chain triggering real tool init | Check `src/tools/analyst_tools.py` — it creates `_data_fetcher` at module level; this is fine (no API call) |

**Step 4: No commit needed** (tests already committed in Tasks 1 and 2)

---

## Task 4: Update ROADMAP to Reflect P2 Complete

**Files:**
- Modify: `.planning/ROADMAP.md` (via state_engine.py)

**Step 1: Transition P2 status to in_progress**

```bash
cd /home/ollie/Development/Tools/quantum_swarm
python scripts/state_engine.py transition 2 in_progress
```

**Step 2: Check what command marks deliverables (inspect state_engine help)**

```bash
python scripts/state_engine.py --help
```

**Step 3: Transition P2 to complete**

```bash
python scripts/state_engine.py transition 2 complete
```

**Step 4: Verify ROADMAP.md updated**

```bash
grep -A 10 "Phase 2" .planning/ROADMAP.md
```

Expected: Phase 2 shows `status: complete` and `completed: 2026-03-06`.

> **Note:** If state_engine.py doesn't support adding deliverables via CLI, edit `.planning/ROADMAP.md` YAML frontmatter directly — add deliverables under phase 2:
>
> ```yaml
> - number: 2
>   name: Cognitive Analysis & Risk Gating (L2)
>   status: complete
>   started: 2026-03-06
>   completed: 2026-03-06
>   plan_file: 02-cognitive-analysis-risk-gating
>   deliverables:
>   - MacroAnalyst & QuantModeler ReAct Agents (analysts.py)
>   - BullishResearcher & BearishResearcher Adversarial Nodes (researchers.py)
>   - BudgetedTool & ToolCache Verification Wrapper (verification_wrapper.py)
>   - DebateSynthesizer & weighted_consensus_score (debate.py)
>   - Risk Gating Conditional Routing — threshold > 0.6 (orchestrator.py)
>   - Full P2 test suite — 24 tests passing
> ```
>
> Then regenerate the markdown body:
> ```bash
> python scripts/state_engine.py regenerate
> ```

**Step 5: Commit**

```bash
git add .planning/ROADMAP.md .planning/STATE.md
git commit -m "chore: mark Phase 2 complete in ROADMAP — all P2 tests passing"
```

---

## Summary: P2 Completion Checklist

- [ ] `tests/test_analysts.py` created with 6 tests (Task 1)
- [ ] `tests/test_researchers.py` created with 9 tests (Task 2)
- [ ] All P2 tests pass (24 total across 5 test files)
- [ ] Full suite passes (no regressions)
- [ ] `.planning/ROADMAP.md` Phase 2 status = complete
- [ ] `.planning/ROADMAP.md` Phase 2 deliverables populated

---

## Key Architecture Reference

```
classify_intent
      │
      ├─ intent=trade/analysis → quant_modeler ─┐
      └─ intent=macro → macro_analyst ──────────┤
                                                 │ (fan-out)
                                    ┌────────────┴────────────┐
                              bullish_researcher      bearish_researcher
                                    └────────────┬────────────┘
                                                 │ (fan-in)
                                        debate_synthesizer
                                                 │
                              consensus > 0.6 ───┤─── hold → END
                                                 │
                                          risk_manager
                                                 │
                                          claw_guard
                                                 │
                                      [L3 chain → END]
```
