import logging
import uuid
from datetime import datetime, timezone
from functools import partial
from typing import Any, Dict, Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .models import GraphDecision
from .state import SwarmState
from .agents.analysts import MacroAnalyst, QuantModeler
from .agents.researchers import BullishResearcher, BearishResearcher
from .debate import DebateSynthesizer

logger = logging.getLogger(__name__)

# --- Node Implementations ---

def classify_intent(state: SwarmState, config: Dict):
    """
    Classifies the user intent using configured patterns or an LLM.
    """
    user_input = state["user_input"].lower()
    intent_patterns = config.get("orchestrator", {}).get("intent_patterns", {})
    
    intent = "unknown"
    for intent_name, patterns in intent_patterns.items():
        for pattern in patterns:
            if pattern in user_input:
                intent = intent_name
                break
        if intent != "unknown":
            break
            
    logger.info(f"Classified intent: {intent}")
    
    return {
        "intent": intent,
        "messages": [{"role": "assistant", "content": f"Classified intent: {intent}"}]
    }

def macro_analyst_node(state: SwarmState, config: Dict):
    """Placeholder for Macro Analyst (L2)."""
    # Phase 2 will implement the actual LLM agent here.
    return {
        "macro_report": {"status": "pending_implementation"},
        "messages": [{"role": "assistant", "content": "Macro Analyst: Analyzing global market conditions..."}]
    }

def quant_modeler_node(state: SwarmState, config: Dict):
    """Placeholder for Quant Modeler (L2)."""
    # Phase 2 will implement the actual LLM agent here.
    return {
        "quant_proposal": {"status": "pending_implementation"},
        "messages": [{"role": "assistant", "content": "Quant Modeler: Running technical analysis..."}]
    }

def debate_synthesizer_node(state: SwarmState, config: Dict):
    """Placeholder for Debate Synthesizer (L2)."""
    return {
        "debate_resolution": {"status": "pending_implementation"},
        "consensus_score": 0.5,
        "messages": [{"role": "assistant", "content": "Debate Synthesizer: Resolving analyst debate..."}]
    }

def risk_manager_node(state: SwarmState, config: Dict):
    """Placeholder for Risk Manager (L2)."""
    return {
        "risk_approval": {"approved": True, "risk_score": 0.1},
        "messages": [{"role": "assistant", "content": "Risk Manager: Validating against compliance limits..."}]
    }

def synthesize_consensus(state: SwarmState, config: Dict):
    """Final node to synthesize the result."""
    return {
        "final_decision": {
            "task_id": state["task_id"],
            "decision": "HOLD", # Default
            "rationale": "Phase 1 PoC: Execution node reached."
        },
        "messages": [{"role": "assistant", "content": "L1 Orchestrator: Final consensus synthesized."}]
    }

# --- Routing Logic ---

def route_by_intent(state: SwarmState) -> Literal["macro_analyst", "quant_modeler", "end"]:
    """Routes to appropriate nodes based on classified intent."""
    intent = state["intent"]
    
    if intent in ["trade", "analysis"]:
        return "quant_modeler"
    elif intent == "macro":
        return "macro_analyst"
    else:
        return "end"

# --- Graph Construction ---

def create_orchestrator_graph(config: Dict):
    """Builds the LangGraph orchestration graph."""

    workflow = StateGraph(SwarmState)

    # --- L1 nodes (existing) ---
    workflow.add_node("classify_intent", partial(classify_intent, config=config))

    # --- L2 Analyst nodes (Phase 2, Plan 02-01) ---
    # Real ReAct agents — do not accept config param (node functions take state only)
    workflow.add_node("macro_analyst", MacroAnalyst)
    workflow.add_node("quant_modeler", QuantModeler)

    # --- L2 Adversarial Researcher nodes (Phase 2, Plan 02-02) ---
    # Both run in PARALLEL after analysts (fan-out pattern)
    workflow.add_node("bullish_researcher", BullishResearcher)
    workflow.add_node("bearish_researcher", BearishResearcher)

    # --- L2 Debate Synthesis node (Phase 2, Plan 02-03) ---
    # Aggregates researcher outputs into weighted_consensus_score (fan-in)
    workflow.add_node("debate_synthesizer", DebateSynthesizer)

    # --- Existing downstream nodes (Plans 02-04+) ---
    workflow.add_node("risk_manager", partial(risk_manager_node, config=config))
    workflow.add_node("synthesize", partial(synthesize_consensus, config=config))

    # Set Entry Point
    workflow.set_entry_point("classify_intent")

    # --- Routing from intent classifier ---
    workflow.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "macro_analyst": "macro_analyst",
            "quant_modeler": "quant_modeler",
            "end": END
        }
    )

    # --- Fan-out: analysts → both researchers run in parallel ---
    # Each analyst fans out to both researchers; LangGraph executes parallel branches
    workflow.add_edge("macro_analyst", "bullish_researcher")
    workflow.add_edge("macro_analyst", "bearish_researcher")
    workflow.add_edge("quant_modeler", "bullish_researcher")
    workflow.add_edge("quant_modeler", "bearish_researcher")

    # --- Fan-in: both researchers must complete before debate_synthesizer ---
    workflow.add_edge(["bullish_researcher", "bearish_researcher"], "debate_synthesizer")

    # --- Downstream (Plans 02-04+: risk gating, final decision) ---
    workflow.add_edge("debate_synthesizer", "risk_manager")
    workflow.add_edge("risk_manager", "synthesize")
    workflow.add_edge("synthesize", END)

    # Persistence
    memory = MemorySaver()

    return workflow.compile(checkpointer=memory)


def build_graph():
    """Convenience entry point for smoke-testing the compiled graph.

    Returns the compiled LangGraph application using an empty config.
    Equivalent to create_orchestrator_graph({}).
    """
    return create_orchestrator_graph({})

class LangGraphOrchestrator:
    """Wrapper for the LangGraph orchestrator to match existing interface."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.app = create_orchestrator_graph(config)
        
    def run_task(self, user_input: str) -> GraphDecision:
        """Process user input through the LangGraph."""
        task_id = str(uuid.uuid4())[:8]

        initial_state: dict[str, Any] = {
            "task_id": task_id,
            "user_input": user_input,
            "intent": "unknown",
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
            "final_decision": None,
            "metadata": {"created_at": datetime.now(timezone.utc).isoformat()},
        }

        # Configure the thread (required for checkpointing)
        config = {"configurable": {"thread_id": task_id}}

        final_state = self.app.invoke(initial_state, config=config)

        # Handle early exit if intent is unknown or nodes skipped
        final_decision_data = final_state.get("final_decision")
        if not final_decision_data:
            final_decision_data = {
                "decision": "HOLD",
                "rationale": f"No analysis performed for intent: {final_state.get('intent', 'unknown')}",
            }

        return GraphDecision(
            task_id=final_state["task_id"],
            decision=final_decision_data["decision"],
            consensus_score=final_state.get("consensus_score", 0.0),
            rationale=final_decision_data["rationale"],
        )
