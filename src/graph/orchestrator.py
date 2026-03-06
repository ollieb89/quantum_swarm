import logging
import os
import uuid
from datetime import datetime, timezone
from functools import partial
from typing import Any, Dict, Literal, Union

import yaml
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .models import GraphDecision
from .state import SwarmState
from .agents.analysts import MacroAnalyst, QuantModeler
from src.blackboard.board import Blackboard
from src.core.blackboard import InterAgentBlackboard
from src.core.budget_manager import BudgetManager
from src.tools.verification_wrapper import SafetyShutdown
from .agents.researchers import BullishResearcher, BearishResearcher
from .debate import DebateSynthesizer
from .agents.l3.data_fetcher import data_fetcher_node
from .nodes.knowledge_base import knowledge_base_node
from .nodes.l1 import risk_manager_node, synthesize_consensus, classify_intent_with_registry
from src.security.claw_guard import claw_guard_node
from .agents.l3.backtester import backtester_node
from .agents.l3.order_router import order_router_node
from .agents.l3.trade_logger import trade_logger_node

logger = logging.getLogger(__name__)

# risk_manager_node and synthesize_consensus imported from .nodes.l1

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
    board = Blackboard()
    inter_agent_board = InterAgentBlackboard()
    budget = BudgetManager(config=config)

    # --- L1 nodes ---
    workflow.add_node(
        "classify_intent",
        partial(classify_intent_with_registry, config=config, board=inter_agent_board, budget=budget),
    )

    # --- L2 Analyst nodes (Phase 2, Plan 02-01) ---
    workflow.add_node("macro_analyst", partial(MacroAnalyst, budget=budget))
    workflow.add_node("quant_modeler", partial(QuantModeler, budget=budget))

    # --- L2 Adversarial Researcher nodes (Phase 2, Plan 02-02) ---
    # Both run in PARALLEL after analysts (fan-out pattern)
    workflow.add_node("bullish_researcher", partial(BullishResearcher, budget=budget))
    workflow.add_node("bearish_researcher", partial(BearishResearcher, budget=budget))

    # --- L2 Debate Synthesis node (Phase 2, Plan 02-03) ---
    # Aggregates researcher outputs into weighted_consensus_score (fan-in)
    workflow.add_node("debate_synthesizer", DebateSynthesizer)

    # --- Existing downstream nodes (Plans 02-04+) ---
    workflow.add_node("risk_manager", partial(risk_manager_node, board=board))

    # --- ClawGuard (Phase 1, Deliverable 2) — between risk_manager and order_router ---
    workflow.add_node("claw_guard", partial(claw_guard_node, config=config))

    # --- L3 Executor nodes (Phase 3, Plan 03-04) ---
    workflow.add_node("data_fetcher", data_fetcher_node)
    workflow.add_node("knowledge_base", knowledge_base_node)
    workflow.add_node("backtester", backtester_node)
    workflow.add_node("order_router", order_router_node)
    workflow.add_node("trade_logger", trade_logger_node)

    workflow.add_node("synthesize", partial(synthesize_consensus, config=config, board=board))

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

    # --- Phase 3: risk_manager → claw_guard → L3 chain → synthesize → END ---
    workflow.add_edge("risk_manager", "claw_guard")
    workflow.add_edge("claw_guard", "data_fetcher")
    workflow.add_edge("data_fetcher", "knowledge_base")
    workflow.add_edge("knowledge_base", "backtester")
    workflow.add_edge("backtester", "order_router")
    workflow.add_edge("order_router", "trade_logger")
    workflow.add_edge("trade_logger", "synthesize")
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

        # Load YAML config for Phase 3 fields (execution_mode, etc.)
        config_path = os.path.join(
            os.path.dirname(__file__), "../../config/swarm_config.yaml"
        )
        try:
            with open(config_path) as f:
                self._yaml_config: Dict = yaml.safe_load(f) or {}
        except (FileNotFoundError, OSError):
            logger.warning("swarm_config.yaml not found at %s — using empty defaults", config_path)
            self._yaml_config = {}

        # Merge YAML config into runtime config so create_orchestrator_graph has it
        merged_config = {**self._yaml_config, **config}
        self.app = create_orchestrator_graph(merged_config)

    def run_task(self, user_input: str) -> GraphDecision:
        """Process user input through the LangGraph."""
        task_id = str(uuid.uuid4())[:8]

        # Resolve execution_mode from YAML config (safe default: "paper")
        execution_mode: str = (
            self._yaml_config.get("trading", {}).get("execution_mode", "paper")
            or "paper"
        )

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
            # Phase 1: Blackboard session (task_id is the session key)
            "blackboard_session": task_id,
            # Phase 1: Token budget tracking
            "total_tokens": 0,
            # Phase 3: L3 executor fields
            "trade_history": [],
            "execution_mode": execution_mode,
            "data_fetcher_result": None,
            "knowledge_base_result": None,
            "backtest_result": None,
            "execution_result": None,
        }

        # Configure the thread (required for checkpointing)
        config = {"configurable": {"thread_id": task_id}}

        try:
            final_state = self.app.invoke(initial_state, config=config)
        except SafetyShutdown as e:
            logger.warning("run_task: SafetyShutdown triggered: %s", e)
            return GraphDecision(
                task_id=task_id,
                decision="HOLD",
                consensus_score=0.0,
                rationale=f"Safety Shutdown: {e}",
            )

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
