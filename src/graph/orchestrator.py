import logging
import uuid
from datetime import datetime, timezone
from functools import partial
from typing import Any, Dict, Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .models import GraphDecision
from .state import SwarmState

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
    
    # Add Nodes
    workflow.add_node("classify_intent", partial(classify_intent, config=config))
    workflow.add_node("macro_analyst", partial(macro_analyst_node, config=config))
    workflow.add_node("quant_modeler", partial(quant_modeler_node, config=config))
    workflow.add_node("debate_synthesizer", partial(debate_synthesizer_node, config=config))
    workflow.add_node("risk_manager", partial(risk_manager_node, config=config))
    workflow.add_node("synthesize", partial(synthesize_consensus, config=config))
    
    # Set Entry Point
    workflow.set_entry_point("classify_intent")
    
    # Add Routing
    workflow.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "macro_analyst": "macro_analyst",
            "quant_modeler": "quant_modeler",
            "end": END
        }
    )
    
    # Internal Edges (Phase 1 Sequential Path for PoC)
    workflow.add_edge("macro_analyst", "debate_synthesizer")
    workflow.add_edge("quant_modeler", "debate_synthesizer")
    workflow.add_edge("debate_synthesizer", "risk_manager")
    workflow.add_edge("risk_manager", "synthesize")
    workflow.add_edge("synthesize", END)
    
    # Persistence
    memory = MemorySaver()
    
    return workflow.compile(checkpointer=memory)

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
