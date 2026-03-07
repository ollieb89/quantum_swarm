"""
Analyst Agent Nodes — MacroAnalyst and QuantModeler as LangGraph ReAct agents.

Both agents are implemented as LangGraph node functions with the signature:

    (state: SwarmState) -> dict

They use create_react_agent from langgraph.prebuilt to build compiled sub-graphs
that are invoked synchronously inside each node. Outputs are written back into
state["messages"] as AIMessage entries.

Model: gemini-2.0-flash (fast, cost-efficient for high-frequency analysis)
"""

import logging
import unittest.mock
from typing import Any, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from src.graph.state import SwarmState
from src.tools.analyst_tools import (
    fetch_economic_data,
    fetch_market_data,
    run_backtest,
    calculate_indicators,
    fetch_historical_data,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared LLM — gemini-2.0-flash
# ---------------------------------------------------------------------------

_MODEL_ID = "gemini-2.0-flash"

# Lazy singletons — deferred to first call so import never requires GOOGLE_API_KEY
_macro_agent = None
_quant_agent = None


def _get_macro_agent():
    global _macro_agent
    if _macro_agent is None:
        _macro_agent = create_react_agent(
            model=ChatGoogleGenerativeAI(model=_MODEL_ID),
            tools=[fetch_market_data, fetch_economic_data, calculate_indicators, fetch_historical_data],
            name="MacroAnalyst",
            prompt=(
                "You are MacroAnalyst, an expert in global macro-economics and market regime "
                "identification. Your job is to assess the current macroeconomic environment "
                "and produce a structured market report. "
                "IMPORTANT: Review the 'INSTITUTIONAL MEMORY' provided in the message history. "
                "Always adhere to the PREFER/AVOID/CAUTION rules derived from past performance. "
                "Use the fetch_market_data and fetch_economic_data tools to gather evidence. "
                "Use fetch_historical_data to get price series if you need to calculate indicators. "
                "Use calculate_indicators to compute technical indicators (RSI, MACD, etc.) if needed "
                "for regime identification before forming your conclusion. "
                "Return your final assessment as a JSON object with keys: "
                "phase, risk_on, confidence, sentiment, outlook, indicators."
            ),
        )
    return _macro_agent


def _get_quant_agent():
    global _quant_agent
    if _quant_agent is None:
        _quant_agent = create_react_agent(
            model=ChatGoogleGenerativeAI(model=_MODEL_ID),
            tools=[fetch_market_data, run_backtest, calculate_indicators, fetch_historical_data],
            name="QuantModeler",
            prompt=(
                "You are QuantModeler, an expert in quantitative finance and technical analysis. "
                "Your job is to identify precise entry and exit signals for a given symbol. "
                "IMPORTANT: Review the 'INSTITUTIONAL MEMORY' provided in the message history. "
                "Always adhere to the PREFER/AVOID/CAUTION rules derived from past performance. "
                "Use the fetch_market_data tool to get current price data. "
                "Use fetch_historical_data to retrieve the required price series for indicators. "
                "ALWAYS use calculate_indicators to compute RSI, MACD, Bollinger Bands, and ATR "
                "to justify your signals. "
                "MANDATORY: Every trade proposal MUST include a calculated stop_loss. "
                "Calculate the stop_loss using the ATR: "
                "For LONG: stop_loss = entry_price - (ATR * 2.0). "
                "For SHORT: stop_loss = entry_price + (ATR * 2.0). "
                "Use run_backtest to validate the strategy's historical performance "
                "before recommending a trade. "
                "Return your final recommendation as a JSON object with keys: "
                "signal, confidence, symbol, entry_price, stop_loss, "
                "atr_at_entry, stop_loss_multiplier, take_profit, "
                "position_size, rationale."
            ),
        )
    return _quant_agent


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


from src.core.budget_manager import BudgetManager

def MacroAnalyst(state: SwarmState, budget: Optional[BudgetManager] = None) -> dict[str, Any]:
    """LangGraph node: run the MacroAnalyst ReAct agent.

    Reads the current user_input and intent from SwarmState, invokes the
    MacroAnalyst sub-graph, and appends the agent's final response as an
    AIMessage to state["messages"].

    If budget is provided, records token usage from the AIMessage.

    Args:
        state: Current SwarmState shared across the graph.
        budget: Shared BudgetManager instance.

    Returns:
        Partial state update dict with ``messages`` key containing the agent
        response as an AIMessage, and ``total_tokens`` increment.
    """
    logger.info("MacroAnalyst node invoked (task_id=%s)", state.get("task_id"))

    user_input = state.get("user_input", "")
    intent = state.get("intent", "")

    query = (
        f"Perform a macro analysis. User intent: {intent}. Context: {user_input}"
    )

    result = _get_macro_agent().invoke({"messages": [HumanMessage(content=query)]})

    # Extract the final AI message from the sub-graph result
    agent_messages = result.get("messages", [])
    tokens_to_add = 0

    if agent_messages:
        last_msg = agent_messages[-1]
        content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        
        # Track token usage if available
        if hasattr(last_msg, "usage_metadata") and last_msg.usage_metadata and budget:
            usage = last_msg.usage_metadata
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            budget.record_usage(input_tokens=input_tokens, output_tokens=output_tokens)
            tokens_to_add = input_tokens + output_tokens
    else:
        content = "MacroAnalyst: no output produced"

    response = AIMessage(
        content=content,
        name="MacroAnalyst",
    )

    logger.info("MacroAnalyst node complete")
    return {"messages": [response], "total_tokens": tokens_to_add}


def QuantModeler(state: SwarmState, budget: Optional[BudgetManager] = None) -> dict[str, Any]:
    """LangGraph node: run the QuantModeler ReAct agent.

    Reads user_input, intent, and any available macro_report from SwarmState,
    invokes the QuantModeler sub-graph, and appends the agent's final response
    as an AIMessage to state["messages"].
    
    If budget is provided, records token usage from the AIMessage.

    Args:
        state: Current SwarmState shared across the graph.
        budget: Shared BudgetManager instance.

    Returns:
        Partial state update dict with ``messages`` key containing the agent
        response as an AIMessage, and ``total_tokens`` increment.
    """
    logger.info("QuantModeler node invoked (task_id=%s)", state.get("task_id"))

    user_input = state.get("user_input", "")
    intent = state.get("intent", "")
    macro_context = state.get("macro_report") or {}

    query = (
        f"Produce a quantitative trade proposal. "
        f"User intent: {intent}. Context: {user_input}. "
        f"Macro context: {macro_context}"
    )

    result = _get_quant_agent().invoke({"messages": [HumanMessage(content=query)]})

    agent_messages = result.get("messages", [])
    tokens_to_add = 0

    if agent_messages:
        last_msg = agent_messages[-1]
        content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

        # Track token usage if available
        if hasattr(last_msg, "usage_metadata") and last_msg.usage_metadata and budget:
            usage = last_msg.usage_metadata
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            budget.record_usage(input_tokens=input_tokens, output_tokens=output_tokens)
            tokens_to_add = input_tokens + output_tokens
    else:
        content = "QuantModeler: no output produced"

    response = AIMessage(
        content=content,
        name="QuantModeler",
    )

    logger.info("QuantModeler node complete")
    return {"messages": [response], "total_tokens": tokens_to_add}


# ---------------------------------------------------------------------------
# Smoke-test __main__ block (dev loop only — no real API calls)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    """Smoke-test: verify MacroAnalyst and QuantModeler instantiate and return
    the expected shape WITHOUT making live API calls."""

    import json

    print("Running smoke-test for analyst agents...")

    # Minimal SwarmState
    test_state: SwarmState = {  # type: ignore[assignment]
        "task_id": "smoke-test-001",
        "user_input": "Should I buy BTC today?",
        "intent": "analysis",
        "messages": [],
        "macro_report": None,
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

    # Patch ChatAnthropic.invoke at the langchain_anthropic level so no API
    # call is made.  The mock returns a realistic AIMessage.
    fake_ai_response = AIMessage(
        content=json.dumps(
            {
                "phase": "Bullish",
                "risk_on": True,
                "confidence": 0.78,
                "sentiment": "Risk-On",
                "outlook": "2-3 days",
                "indicators": {"vix": 14.5},
            }
        )
    )

    with unittest.mock.patch.object(
        _get_macro_agent(),
        "invoke",
        return_value={"messages": [fake_ai_response]},
    ):
        macro_result = MacroAnalyst(test_state)

    with unittest.mock.patch.object(
        _get_quant_agent(),
        "invoke",
        return_value={"messages": [fake_ai_response]},
    ):
        quant_result = QuantModeler(test_state)

    # Assertions
    assert isinstance(macro_result, dict), "MacroAnalyst must return a dict"
    assert "messages" in macro_result, "MacroAnalyst result must have 'messages' key"
    assert isinstance(macro_result["messages"], list), "'messages' must be a list"
    assert len(macro_result["messages"]) > 0, "'messages' must be non-empty"

    assert isinstance(quant_result, dict), "QuantModeler must return a dict"
    assert "messages" in quant_result, "QuantModeler result must have 'messages' key"
    assert isinstance(quant_result["messages"], list), "'messages' must be a list"
    assert len(quant_result["messages"]) > 0, "'messages' must be non-empty"

    print("MacroAnalyst result:", macro_result["messages"][0].content[:80], "...")
    print("QuantModeler result:", quant_result["messages"][0].content[:80], "...")
    print("Smoke-test PASSED: both agents return dict with 'messages' key.")
