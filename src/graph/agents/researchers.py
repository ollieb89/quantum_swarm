"""
Researcher Agent Nodes — BullishResearcher and BearishResearcher as LangGraph ReAct agents.

These nodes create genuine adversarial pressure against analyst conclusions by
independently verifying claims from opposite directional hypotheses.

BullishResearcher seeks SUPPORTING evidence for a bullish thesis.
BearishResearcher seeks REFUTING evidence, looking for bearish signals.

Both agents:
  - Use gemini-2.0-flash (fast, cost-efficient)
  - Have a tool budget of 5 calls per invocation (via BudgetedTool)
  - Require a hypothesis= kwarg on every tool call (enforced by BudgetedTool)
  - Append tagged AIMessage findings to state["messages"] for DebateSynthesizer

IMPORTANT: Neither researcher has access to fetch_execute or any order-routing tools.
"""

from __future__ import annotations

import logging
import unittest.mock
from typing import Any, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool

from src.graph.state import SwarmState
from src.tools.analyst_tools import (
    fetch_economic_data,
    fetch_market_data,
    run_backtest,
)
from src.tools.verification_wrapper import BudgetedTool, budgeted
from src.graph.agents.l3.trade_logger import get_recent_trades, TRADE_HISTORY_WINDOW

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared LLM — gemini-2.5-flash
# ---------------------------------------------------------------------------

_MODEL_ID = "gemini-2.5-flash"

# Lazy singletons — deferred to first call so import never requires GOOGLE_API_KEY
_bullish_llm: "ChatGoogleGenerativeAI | None" = None
_bearish_llm: "ChatGoogleGenerativeAI | None" = None


def _get_bullish_llm() -> ChatGoogleGenerativeAI:
    global _bullish_llm
    if _bullish_llm is None:
        _bullish_llm = ChatGoogleGenerativeAI(model=_MODEL_ID)
    return _bullish_llm


def _get_bearish_llm() -> ChatGoogleGenerativeAI:
    global _bearish_llm
    if _bearish_llm is None:
        _bearish_llm = ChatGoogleGenerativeAI(model=_MODEL_ID)
    return _bearish_llm

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_BULLISH_SYSTEM = (
    "You are BullishResearcher, an adversarial agent whose sole purpose is to find "
    "SUPPORTING evidence for a BULLISH directional hypothesis. "
    "You receive analyst conclusions from previous messages and must independently "
    "verify or strengthen the bullish case using market and economic data. "
    "\n\n"
    "Rules:\n"
    "1. You have a LIMITED TOOL BUDGET: you may call tools at most 5 times total.\n"
    "2. Every tool call MUST include hypothesis='<your current hypothesis>' so your "
    "reasoning is logged.\n"
    "3. Focus only on market data, economic indicators, and backtests. "
    "You have NO access to execution or order-routing tools.\n"
    "4. Conclude with a structured JSON object with keys: "
    "hypothesis, supporting_evidence (list), confidence (0-1), "
    "recommended_action, rationale.\n"
)

_BEARISH_SYSTEM = (
    "You are BearishResearcher, an adversarial agent whose sole purpose is to find "
    "REFUTING evidence against the prevailing bullish thesis, making the BEARISH case. "
    "You receive analyst conclusions from previous messages and must independently "
    "challenge or undermine the bullish case using market and economic data. "
    "\n\n"
    "Rules:\n"
    "1. You have a LIMITED TOOL BUDGET: you may call tools at most 5 times total.\n"
    "2. Every tool call MUST include hypothesis='<your current hypothesis>' so your "
    "reasoning is logged.\n"
    "3. Focus only on market data, economic indicators, and backtests. "
    "You have NO access to execution or order-routing tools.\n"
    "4. Conclude with a structured JSON object with keys: "
    "hypothesis, refuting_evidence (list), confidence (0-1), "
    "recommended_action, rationale.\n"
)

# ---------------------------------------------------------------------------
# Helper: extract analyst context from state messages
# ---------------------------------------------------------------------------


def _extract_analyst_context(state: SwarmState) -> str:
    """Pull analyst conclusions from state messages for researcher context."""
    messages = state.get("messages", [])
    analyst_msgs: list[str] = []
    for msg in messages:
        # Handle both AIMessage objects and plain dicts
        if hasattr(msg, "name") and msg.name in ("MacroAnalyst", "QuantModeler"):
            content = msg.content if hasattr(msg, "content") else str(msg)
            analyst_msgs.append(f"[{msg.name}]: {content}")
        elif isinstance(msg, dict):
            source = msg.get("name") or msg.get("role", "")
            if source in ("MacroAnalyst", "QuantModeler"):
                analyst_msgs.append(f"[{source}]: {msg.get('content', '')}")

    macro_report = state.get("macro_report") or {}
    quant_proposal = state.get("quant_proposal") or {}

    context_parts: list[str] = analyst_msgs.copy()
    if macro_report:
        context_parts.append(f"[MacroReport]: {macro_report}")
    if quant_proposal:
        context_parts.append(f"[QuantProposal]: {quant_proposal}")

    return "\n".join(context_parts) if context_parts else "No analyst context available."


# ---------------------------------------------------------------------------
# Budgeted tool builders
# These are created inside node functions to reset the call counter per invocation.
# ---------------------------------------------------------------------------


def _make_budgeted_tools(max_calls: int = 5) -> list[BudgetedTool]:
    """Return fresh BudgetedTool instances for one researcher invocation."""
    return [
        budgeted(fetch_market_data, max_calls=max_calls),
        budgeted(fetch_economic_data, max_calls=max_calls),
        budgeted(run_backtest, max_calls=max_calls),
    ]


# ---------------------------------------------------------------------------
# Helper: invoke LLM with tool-use loop (simple ReAct pattern)
# ---------------------------------------------------------------------------


from src.core.budget_manager import BudgetManager

def _run_researcher_agent(
    llm: ChatGoogleGenerativeAI,
    system_prompt: str,
    query: str,
    budgeted_tools: list[BudgetedTool],
    budget: Optional[BudgetManager] = None,
) -> tuple[str, int]:
    """Run a simple ReAct loop with budgeted tools and return the final text and tokens used.

    We implement a lightweight manual ReAct loop here rather than using
    create_react_agent so that the BudgetedTool instances (with per-invocation
    call counters) are used directly without being re-wrapped by LangGraph
    internals.

    The loop:
      1. Send system + user message to LLM.
      2. If LLM produces text content, return it.
      3. If LLM produces a ToolBudgetExceeded or other stop, return last text.
    """
    messages: list[Any] = [HumanMessage(content=f"{system_prompt}\n\n{query}")]

    # Build a tool name → BudgetedTool map for dispatch
    tool_map: dict[str, BudgetedTool] = {t.tool_name: t for t in budgeted_tools}

    # Bind tools to LLM so it can generate tool call requests
    # We bind the original tool functions (for schema) but intercept calls below.
    original_tools = [t._tool_fn for t in budgeted_tools]
    bound_llm = llm.bind_tools(original_tools)

    MAX_ITERATIONS = 8  # safety cap on ReAct loop
    last_text: str = ""
    tokens_used: int = 0

    for _i in range(MAX_ITERATIONS):
        response = bound_llm.invoke(messages)
        messages.append(response)

        if budget and hasattr(response, "usage_metadata") and response.usage_metadata:
            u = response.usage_metadata
            inp = int(u.get("input_tokens", 0))
            out = int(u.get("output_tokens", 0))
            budget.record_usage(input_tokens=inp, output_tokens=out)
            tokens_used += inp + out

        # Check for tool calls
        tool_calls = getattr(response, "tool_calls", None) or []

        if not tool_calls:
            # No tool calls — final answer
            last_text = response.content if isinstance(response.content, str) else str(response.content)
            break

        # Execute each tool call via BudgetedTool
        for tc in tool_calls:
            tool_name = tc.get("name", "") if isinstance(tc, dict) else tc.name
            args = tc.get("args", {}) if isinstance(tc, dict) else tc.args
            tc_id = tc.get("id", tool_name) if isinstance(tc, dict) else tc.id

            bt = tool_map.get(tool_name)
            if bt is None:
                tool_result = {"error": f"Unknown tool: {tool_name}"}
            else:
                try:
                    # Extract hypothesis from args if LLM included it
                    hypothesis = args.pop("hypothesis", "unspecified hypothesis")
                    tool_result = bt(**args, hypothesis=hypothesis)
                except Exception as exc:  # includes ToolBudgetExceeded, ValueError
                    tool_result = {"error": str(exc)}

            # Append tool result as ToolMessage for the next LLM turn
            from langchain_core.messages import ToolMessage

            messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tc_id,
                )
            )

    return last_text or "No research output produced.", tokens_used


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


def BullishResearcher(state: SwarmState, budget: Optional[BudgetManager] = None) -> dict[str, Any]:
    """LangGraph node: run the BullishResearcher adversarial agent.

    Reads analyst conclusions from SwarmState messages, then seeks SUPPORTING
    evidence for a bullish directional hypothesis using budgeted research tools.

    Args:
        state: Current SwarmState shared across the graph.
        budget: Shared BudgetManager instance.

    Returns:
        Partial state update dict with ``messages`` key containing the agent
        findings as an AIMessage tagged with name="bullish_research".
    """
    logger.info("BullishResearcher node invoked (task_id=%s)", state.get("task_id"))

    analyst_context = _extract_analyst_context(state)
    user_input = state.get("user_input", "")
    intent = state.get("intent", "")

    # Self-improvement: inject recent trade history as context (Phase 3, Plan 03-04)
    recent_trades = get_recent_trades(state)
    trade_history_block = ""
    if recent_trades:
        trade_history_block = (
            f"\n[Trade History — last {len(recent_trades)} trades]\n"
        )
        for t in recent_trades:
            pnl_str = f"P&L: {t.get('pnl_pct')}%" if t.get("pnl_pct") else "P&L: open"
            trade_history_block += (
                f"  - {t['symbol']} {t['side']} @ {t['entry_price']} ({pnl_str})\n"
            )

    query = (
        f"User intent: {intent}. Query: {user_input}\n\n"
        f"Analyst conclusions to verify/support:\n{analyst_context}\n"
        f"{trade_history_block}\n"
        "Find SUPPORTING evidence for a BULLISH thesis. "
        "Use available tools and include hypothesis= in each call. "
        "Conclude with your structured JSON findings."
    )

    budgeted_tools = _make_budgeted_tools(max_calls=5)
    tokens_to_add = 0

    try:
        content, tokens_to_add = _run_researcher_agent(
            llm=_get_bullish_llm(),
            system_prompt=_BULLISH_SYSTEM,
            query=query,
            budgeted_tools=budgeted_tools,
            budget=budget,
        )
    except Exception as exc:
        logger.warning("BullishResearcher encountered error: %s", exc)
        content = f"BullishResearcher error: {exc}"

    logger.info(
        "BullishResearcher complete (tools used: %d)",
        sum(t.call_count for t in budgeted_tools),
    )

    response = AIMessage(
        content=content,
        name="bullish_research",
    )
    return {"messages": [response], "total_tokens": tokens_to_add, "bullish_thesis": {"text": content}}


def BearishResearcher(state: SwarmState, budget: Optional[BudgetManager] = None) -> dict[str, Any]:
    """LangGraph node: run the BearishResearcher adversarial agent.

    Reads analyst conclusions from SwarmState messages, then seeks REFUTING
    evidence against the bullish thesis, building the bearish case using
    budgeted research tools.

    Args:
        state: Current SwarmState shared across the graph.
        budget: Shared BudgetManager instance.

    Returns:
        Partial state update dict with ``messages`` key containing the agent
        findings as an AIMessage tagged with name="bearish_research".
    """
    logger.info("BearishResearcher node invoked (task_id=%s)", state.get("task_id"))

    analyst_context = _extract_analyst_context(state)
    user_input = state.get("user_input", "")
    intent = state.get("intent", "")

    # Self-improvement: inject recent trade history as context (Phase 3, Plan 03-04)
    recent_trades = get_recent_trades(state)
    trade_history_block = ""
    if recent_trades:
        trade_history_block = (
            f"\n[Trade History — last {len(recent_trades)} trades]\n"
        )
        for t in recent_trades:
            pnl_str = f"P&L: {t.get('pnl_pct')}%" if t.get("pnl_pct") else "P&L: open"
            trade_history_block += (
                f"  - {t['symbol']} {t['side']} @ {t['entry_price']} ({pnl_str})\n"
            )

    query = (
        f"User intent: {intent}. Query: {user_input}\n\n"
        f"Analyst conclusions to challenge:\n{analyst_context}\n"
        f"{trade_history_block}\n"
        "Find REFUTING evidence for a BEARISH thesis — challenge or undermine the bullish case. "
        "Use available tools and include hypothesis= in each call. "
        "Conclude with your structured JSON findings."
    )

    budgeted_tools = _make_budgeted_tools(max_calls=5)
    tokens_to_add = 0

    try:
        content, tokens_to_add = _run_researcher_agent(
            llm=_get_bearish_llm(),
            system_prompt=_BEARISH_SYSTEM,
            query=query,
            budgeted_tools=budgeted_tools,
            budget=budget,
        )
    except Exception as exc:
        logger.warning("BearishResearcher encountered error: %s", exc)
        content = f"BearishResearcher error: {exc}"

    logger.info(
        "BearishResearcher complete (tools used: %d)",
        sum(t.call_count for t in budgeted_tools),
    )

    response = AIMessage(
        content=content,
        name="bearish_research",
    )
    return {"messages": [response], "total_tokens": tokens_to_add, "bearish_thesis": {"text": content}}


# ---------------------------------------------------------------------------
# Smoke-test __main__ block (dev loop only — no real API calls)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    """Smoke-test: verify BullishResearcher and BearishResearcher instantiate
    and return the expected shape WITHOUT making live API calls."""

    import json

    print("Running smoke-test for researcher agents...")

    test_state: SwarmState = {  # type: ignore[assignment]
        "task_id": "smoke-test-002",
        "user_input": "Should I buy BTC today?",
        "intent": "analysis",
        "messages": [
            AIMessage(
                content=json.dumps({"phase": "Bullish", "risk_on": True, "confidence": 0.78}),
                name="MacroAnalyst",
            )
        ],
        "macro_report": {"phase": "Bullish", "risk_on": True},
        "quant_proposal": None,
        "bullish_thesis": None,
        "bearish_thesis": None,
        "debate_resolution": None,
        "risk_approval": None,
        "consensus_score": 0.0,
        "compliance_flags": [],
        "final_decision": None,
        "metadata": {},
    }

    fake_response = AIMessage(
        content=json.dumps(
            {
                "hypothesis": "BTC is in a bullish trend",
                "supporting_evidence": ["RSI > 60", "Volume increasing"],
                "confidence": 0.75,
                "recommended_action": "BUY",
                "rationale": "Strong momentum signals",
            }
        )
    )

    _bl = _get_bullish_llm()
    _br = _get_bearish_llm()

    with unittest.mock.patch.object(
        _bl, "bind_tools", return_value=_bl
    ), unittest.mock.patch.object(
        _bl, "invoke", return_value=fake_response
    ):
        bullish_result = BullishResearcher(test_state)

    with unittest.mock.patch.object(
        _br, "bind_tools", return_value=_br
    ), unittest.mock.patch.object(
        _br, "invoke", return_value=fake_response
    ):
        bearish_result = BearishResearcher(test_state)

    assert isinstance(bullish_result, dict), "BullishResearcher must return a dict"
    assert "messages" in bullish_result, "BullishResearcher result must have 'messages' key"
    assert bullish_result["messages"][0].name == "bullish_research"

    assert isinstance(bearish_result, dict), "BearishResearcher must return a dict"
    assert "messages" in bearish_result, "BearishResearcher result must have 'messages' key"
    assert bearish_result["messages"][0].name == "bearish_research"

    print("BullishResearcher result:", bullish_result["messages"][0].content[:80], "...")
    print("BearishResearcher result:", bearish_result["messages"][0].content[:80], "...")
    print("Smoke-test PASSED: both researchers return dict with 'messages' key.")
