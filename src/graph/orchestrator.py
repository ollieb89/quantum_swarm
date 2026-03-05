import logging
import uuid
from datetime import datetime, timezone
from functools import partial
from typing import Any, Dict, Literal, Union

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

def risk_manager_node(state: SwarmState) -> dict:
    """RiskManager LangGraph node — final validation before execution.

    Reads debate_history and weighted_consensus_score from SwarmState.
    Performs final risk validation:
      1. Checks for conflicting hypotheses (both bullish and bearish sources present)
      2. Checks for missing provenance (empty debate_history)
      3. Validates that the consensus score is not anomalous (outside [0.0, 1.0])

    Returns:
        Partial state update with risk_approved (bool) and risk_notes (str).
    """
    logger.info("RiskManager node invoked (task_id=%s)", state.get("task_id"))

    debate_history = state.get("debate_history", [])
    score = state.get("weighted_consensus_score")

    notes: list[str] = []
    approved = True

    # Check for missing provenance
    if not debate_history:
        notes.append("No debate history found — provenance missing.")
        approved = False

    # Check for anomalous score
    if score is None:
        notes.append("weighted_consensus_score is None — cannot validate.")
        approved = False
    elif not (0.0 <= score <= 1.0):
        notes.append(f"Anomalous consensus score {score:.4f} outside [0.0, 1.0].")
        approved = False

    # Check for conflicting hypotheses (both bullish and bearish present is EXPECTED and healthy)
    sources = {entry.get("hypothesis") for entry in debate_history}
    if "bullish" in sources and "bearish" in sources:
        notes.append("Conflicting hypotheses detected (bullish + bearish) — normal adversarial debate.")
    elif not sources or sources == {"neutral"}:
        notes.append("No adversarial hypotheses found — debate may have been skipped.")
        approved = False

    risk_notes = " | ".join(notes) if notes else "All risk checks passed."

    logger.info(
        "RiskManager: approved=%s score=%s notes=%s",
        approved, score, risk_notes,
    )

    return {
        "risk_approved": approved,
        "risk_notes": risk_notes,
        "messages": [
            {
                "role": "assistant",
                "content": f"RiskManager: approved={approved} | {risk_notes}",
            }
        ],
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

def route_after_debate(state: SwarmState) -> str:
    """Conditional routing function after DebateSynthesizer.

    Routes to 'risk_manager' only if the weighted_consensus_score is STRICTLY
    greater than 0.6 — the minimum confidence threshold for execution.

    Falls back to 'hold' (END) when:
      - score is None (synthesizer did not run or output is missing)
      - score <= 0.6 (insufficient consensus, reject/hold)

    Returns:
        'risk_manager' or 'hold'
    """
    score = state.get("weighted_consensus_score")
    if score is not None and score > 0.6:
        logger.info("route_after_debate: score=%.4f → risk_manager", score)
        return "risk_manager"
    logger.info(
        "route_after_debate: score=%s → hold (threshold not met)", score
    )
    return "hold"


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
    # risk_manager_node takes only state (no config) — no partial needed
    workflow.add_node("risk_manager", risk_manager_node)
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

    # --- Risk gating: conditional edge from debate_synthesizer (Plan 02-04) ---
    # Routes to risk_manager only if weighted_consensus_score > 0.6; else hold (END).
    workflow.add_conditional_edges(
        "debate_synthesizer",
        route_after_debate,
        {
            "risk_manager": "risk_manager",
            "hold": END,
        },
    )

    # --- Downstream: risk_manager → synthesize → END (Phase 3 will add execute node) ---
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
            "risk_approved": None,
            "risk_notes": None,
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
