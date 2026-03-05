import operator
from typing import Annotated, List, TypedDict, Union, Optional
import json

from langgraph.graph import StateGraph, END

# --- 1. Define State ---

class SwarmState(TypedDict):
    # Standard task tracking
    task_id: str
    user_input: str
    intent: str
    
    # Message history
    messages: Annotated[List[str], operator.add]
    
    # Analyst Outputs
    macro_report: Optional[dict]
    quant_proposal: Optional[dict]
    
    # Adversarial Debate
    bullish_thesis: Optional[dict]
    bearish_thesis: Optional[dict]
    debate_resolution: Optional[dict]
    
    # Final Gating
    risk_approval: Optional[dict]
    consensus_score: float
    final_decision: Optional[str]

# --- 2. Define Nodes (Mocked for PoC) ---

def supervisor_node(state: SwarmState):
    """L1 Supervisor: Classifies intent and routes to analysts."""
    print("--- L1 Supervisor ---")
    # In a real scenario, this would use an LLM to classify intent
    intent = "trade" # Mocked
    return {
        "intent": intent,
        "messages": [f"Supervisor: Classified intent as {intent}. Routing to analysts."]
    }

def macro_analyst_node(state: SwarmState):
    """L2 Macro Analyst: Analyzes macro environment."""
    print("--- Macro Analyst ---")
    report = {
        "signal": "bullish",
        "vix": 14.5,
        "sentiment": "Risk-On"
    }
    return {
        "macro_report": report,
        "messages": ["Macro Analyst: Environment looks Risk-On. Low VIX."]
    }

def quant_modeler_node(state: SwarmState):
    """L2 Quant Modeler: Analyzes technical indicators."""
    print("--- Quant Modeler ---")
    proposal = {
        "signal": "buy",
        "rsi": 42.0,
        "stop_loss": 65000.0
    }
    return {
        "quant_proposal": proposal,
        "messages": ["Quant Modeler: RSI is neutral-bullish. Recommending buy."]
    }

def bullish_researcher_node(state: SwarmState):
    """L2 Bullish Researcher: Argues FOR the trade."""
    print("--- Bullish Researcher ---")
    thesis = {
        "arguments": ["Macro is favorable", "Technical setup is solid"],
        "confidence": 0.85
    }
    return {
        "bullish_thesis": thesis,
        "messages": ["Bullish Researcher: Strong arguments for entry."]
    }

def bearish_researcher_node(state: SwarmState):
    """L2 Bearish Researcher: Argues AGAINST the trade."""
    print("--- Bearish Researcher ---")
    thesis = {
        "arguments": ["Resistance at 70k", "Potential divergence on RSI"],
        "confidence": 0.3
    }
    return {
        "bearish_thesis": thesis,
        "messages": ["Bearish Researcher: identified overhead resistance."]
    }

def debate_synthesizer_node(state: SwarmState):
    """Resolves the debate."""
    print("--- Debate Synthesizer ---")
    # Weighted resolution
    bull = state["bullish_thesis"]["confidence"]
    bear = state["bearish_thesis"]["confidence"]
    
    consensus = (bull + (1 - bear)) / 2
    resolution = "approved" if consensus > 0.7 else "rejected"
    
    return {
        "consensus_score": consensus,
        "debate_resolution": {"status": resolution},
        "messages": [f"Synthesizer: Debate resolved. Consensus score: {consensus:.2f}"]
    }

def risk_manager_node(state: SwarmState):
    """Final Risk Gating."""
    print("--- Risk Manager ---")
    approval = {
        "approved": True,
        "risk_score": 0.2
    }
    return {
        "risk_approval": approval,
        "final_decision": "EXECUTE" if approval["approved"] else "REJECT",
        "messages": ["Risk Manager: Risk parameters within limits. Approved."]
    }

# --- 3. Build Graph ---

def build_graph():
    """Construct and compile the LangGraph orchestration graph."""
    workflow = StateGraph(SwarmState)

    # Add Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("macro_analyst", macro_analyst_node)
    workflow.add_node("quant_modeler", quant_modeler_node)
    workflow.add_node("bullish_researcher", bullish_researcher_node)
    workflow.add_node("bearish_researcher", bearish_researcher_node)
    workflow.add_node("debate_synthesizer", debate_synthesizer_node)
    workflow.add_node("risk_manager", risk_manager_node)

    # Add Edges
    workflow.set_entry_point("supervisor")

    # Routing from supervisor (simplified for PoC)
    workflow.add_edge("supervisor", "macro_analyst")
    workflow.add_edge("supervisor", "quant_modeler")

    # Both analysts must finish before debate
    workflow.add_edge("macro_analyst", "bullish_researcher")
    workflow.add_edge("macro_analyst", "bearish_researcher")
    workflow.add_edge("quant_modeler", "bullish_researcher")
    workflow.add_edge("quant_modeler", "bearish_researcher")

    # Debate researchers feed synthesizer
    workflow.add_edge("bullish_researcher", "debate_synthesizer")
    workflow.add_edge("bearish_researcher", "debate_synthesizer")

    # Synthesizer feeds risk
    workflow.add_edge("debate_synthesizer", "risk_manager")

    # Final step
    workflow.add_edge("risk_manager", END)

    return workflow.compile()


# --- 4. Run PoC ---

if __name__ == "__main__":
    app = build_graph()

    initial_state = {
        "task_id": "poc-123",
        "user_input": "Should I buy BTC now?",
        "messages": [],
        "consensus_score": 0.0,
    }

    print("Starting LangGraph PoC...")
    final_state = app.invoke(initial_state)

    print("\n--- PoC Result ---")
    print(f"Task ID: {final_state['task_id']}")
    print(f"Final Decision: {final_state['final_decision']}")
    print(f"Consensus Score: {final_state['consensus_score']:.2f}")
    print("\nMessage Log:")
    for msg in final_state["messages"]:
        print(f"  - {msg}")
