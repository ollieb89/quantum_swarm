import logging
import os
import uuid
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
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
from src.core.memory_registry import MemoryRegistry
from src.core.decision_card import build_decision_card, canonical_json, verify_decision_card
from src.core.db import get_pool
from src.tools.verification_wrapper import SafetyShutdown
from .agents.researchers import BullishResearcher, BearishResearcher
from .debate import DebateSynthesizer
from .agents.l3.data_fetcher import data_fetcher_node
from .nodes.knowledge_base import knowledge_base_node
from .nodes.l1 import risk_manager_node, synthesize_consensus, classify_intent_with_registry
from src.security.claw_guard import claw_guard_node
from src.security.institutional_guard import institutional_guard_node
from .agents.l3.backtester import backtester_node
from .agents.l3.order_router import order_router_node
from .agents.l3.trade_logger import trade_logger_node
from .nodes.write_external_memory import write_external_memory_node
from .nodes.write_research_memory import write_research_memory_node
from .nodes.write_trade_memory import write_trade_memory_node

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


def route_after_order_router(state: SwarmState) -> str:
    """Route to decision_card_writer only for successful trade executions."""
    result = state.get("execution_result") or {}
    if result.get("success") is True:
        return "decision_card_writer"
    return "trade_logger"


def route_after_institutional_guard(state: SwarmState) -> str:
    """Conditional routing after InstitutionalGuard.

    Routes to 'data_fetcher' when the guard approves (risk_approved is not False).
    Routes to 'synthesize' when rejected (risk_approved is False), so the caller
    receives an explanatory summary rather than a silent END.

    Returns:
        'data_fetcher' or 'synthesize'
    """
    if state.get("risk_approved") is False:
        logger.info("route_after_institutional_guard: risk_approved=False → synthesize")
        return "synthesize"
    logger.info("route_after_institutional_guard: approved → data_fetcher")
    return "data_fetcher"


async def decision_card_writer_node(state: SwarmState) -> dict:
    """Generate and persist an immutable decision card for successful trade executions."""
    audit_path = Path("data/audit.jsonl")
    try:
        # Fetch prev_audit_hash from PostgreSQL audit_logs
        prev_audit_hash: Any = None
        try:
            pool = get_pool()
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT entry_hash FROM audit_logs ORDER BY id DESC LIMIT 1"
                    )
                    row = await cur.fetchone()
                    prev_audit_hash = row[0] if row else None
        except Exception as db_err:
            logger.warning("decision_card_writer: could not fetch prev_audit_hash: %s", db_err)
            prev_audit_hash = None

        # Load active rule IDs
        registry = MemoryRegistry()
        card = build_decision_card(state, registry=registry, prev_audit_hash=prev_audit_hash)

        line = canonical_json(card.model_dump(mode="json"))

        # Write with one retry on transient failure
        written = False
        last_err = None
        for attempt in range(2):
            try:
                audit_path.parent.mkdir(parents=True, exist_ok=True)
                with open(audit_path, "a") as f:
                    f.write(line + "\n")
                written = True
                break
            except Exception as write_err:
                last_err = write_err
                logger.warning(
                    "decision_card_writer: write attempt %d failed: %s", attempt + 1, write_err
                )

        if not written:
            logger.error(
                "COMPLIANCE INCIDENT: decision card write failed after retry for task_id=%s: %s",
                state.get("task_id"), last_err
            )
            return {
                "decision_card_status": "failed",
                "decision_card_error": str(last_err),
                "decision_card_audit_ref": None,
            }

        return {
            "decision_card_status": "written",
            "decision_card_error": None,
            "decision_card_audit_ref": card.card_id,
        }

    except Exception as e:
        logger.error(
            "COMPLIANCE INCIDENT: decision card generation failed for task_id=%s: %s",
            state.get("task_id"), e
        )
        return {
            "decision_card_status": "failed",
            "decision_card_error": str(e),
            "decision_card_audit_ref": None,
        }


# --- Graph Construction ---

from src.core.audit_logger import AuditLogger

# Global instance for the orchestrator session
audit_logger = AuditLogger()

def with_audit_logging(node_fn, node_id: str):
    """
    Decorator/Wrapper to automatically log node transitions with the AuditLogger.
    Ensures every node execution is recorded with its input, output, and hash chain.
    """
    async def wrapped_node(state: SwarmState, **kwargs):
        # Identify the task context
        task_id = state.get("task_id", "unknown")
        
        # In a real LangGraph node, input is the state.
        # We capture a snippet of the state for audit (avoiding massive binary blobs if any)
        input_snapshot = {k: v for k, v in state.items() if not k.startswith("_")}
        
        # Execute the actual node logic
        # Note: Some nodes might be sync, some async. 
        # Since we are in an async context (orchestrator), we handle both.
        if asyncio.iscoroutinefunction(node_fn):
            result = await node_fn(state, **kwargs)
        else:
            # Run sync nodes in a thread pool to avoid blocking the event loop
            result = await asyncio.to_thread(node_fn, state, **kwargs)
        
        # Capture the output (the state update)
        output_snapshot = result if isinstance(result, dict) else {}
        
        # Asynchronously log the transition
        try:
            await audit_logger.log_transition(
                task_id=task_id,
                node_id=node_id,
                input_data=input_snapshot,
                output_data=output_snapshot
            )
        except Exception as e:
            logger.error("Failed to log audit transition for node %s: %s", node_id, e)
            # In institutional compliance, a logging failure might require a halt.
            # For now, we log the error and continue.
            
        return result
        
    return wrapped_node

def create_orchestrator_graph(config: Dict, checkpointer: Any = None, memory: Any = None):
    """Builds the LangGraph orchestration graph.

    Args:
        config: Dict containing agent and runtime settings.
        checkpointer: Optional LangGraph checkpointer (e.g. MemorySaver, PostgresSaver).
    """

    workflow = StateGraph(SwarmState)
    board = Blackboard()
    inter_agent_board = InterAgentBlackboard()
    budget = BudgetManager(config=config)

    # Memory service — constructed lazily if not provided
    if memory is None:
        from src.memory.service import MemoryService
        memory = MemoryService(chroma_path="data/chroma_db")

    # --- L1 nodes ---
    workflow.add_node(
        "classify_intent",
        with_audit_logging(
            partial(classify_intent_with_registry, config=config, board=inter_agent_board, budget=budget),
            "classify_intent"
        ),
    )

    # --- L2 Analyst nodes ---
    workflow.add_node("macro_analyst", with_audit_logging(partial(MacroAnalyst, budget=budget), "macro_analyst"))
    workflow.add_node("quant_modeler", with_audit_logging(partial(QuantModeler, budget=budget), "quant_modeler"))

    # --- L2 Adversarial Researcher nodes ---
    workflow.add_node("bullish_researcher", with_audit_logging(partial(BullishResearcher, budget=budget), "bullish_researcher"))
    workflow.add_node("bearish_researcher", with_audit_logging(partial(BearishResearcher, budget=budget), "bearish_researcher"))

    # --- L2 Debate Synthesis node ---
    workflow.add_node("debate_synthesizer", with_audit_logging(DebateSynthesizer, "debate_synthesizer"))

    # --- Existing downstream nodes ---
    workflow.add_node("risk_manager", with_audit_logging(partial(risk_manager_node, board=board), "risk_manager"))

    # --- ClawGuard ---
    workflow.add_node("claw_guard", with_audit_logging(partial(claw_guard_node, config=config), "claw_guard"))

    # --- Institutional Guard (Phase 4) ---
    workflow.add_node("institutional_guard", with_audit_logging(partial(institutional_guard_node, config=config), "institutional_guard"))

    # --- L3 Executor nodes ---
    workflow.add_node("data_fetcher", with_audit_logging(data_fetcher_node, "data_fetcher"))
    workflow.add_node("knowledge_base", with_audit_logging(knowledge_base_node, "knowledge_base"))
    workflow.add_node("backtester", with_audit_logging(backtester_node, "backtester"))
    workflow.add_node("order_router", with_audit_logging(order_router_node, "order_router"))
    workflow.add_node("decision_card_writer", with_audit_logging(decision_card_writer_node, "decision_card_writer"))
    workflow.add_node("trade_logger", with_audit_logging(trade_logger_node, "trade_logger"))

    workflow.add_node("synthesize", with_audit_logging(partial(synthesize_consensus, config=config, board=board), "synthesize"))

    # --- Phase 4: Memory write nodes ---
    workflow.add_node("write_external_memory", partial(write_external_memory_node, memory=memory))
    workflow.add_node("write_research_memory", partial(write_research_memory_node, memory=memory))
    workflow.add_node("write_trade_memory", partial(write_trade_memory_node, memory=memory))

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
    workflow.add_edge("macro_analyst", "bullish_researcher")
    workflow.add_edge("macro_analyst", "bearish_researcher")
    workflow.add_edge("quant_modeler", "bullish_researcher")
    workflow.add_edge("quant_modeler", "bearish_researcher")

    # --- Fan-in: both researchers must complete before debate_synthesizer ---
    workflow.add_edge(["bullish_researcher", "bearish_researcher"], "debate_synthesizer")

    # --- Phase 4: research memory written after debate, before risk gate ---
    workflow.add_edge("debate_synthesizer", "write_research_memory")

    # --- Risk gating: conditional edge from write_research_memory ---
    workflow.add_conditional_edges(
        "write_research_memory",
        route_after_debate,
        {
            "risk_manager": "risk_manager",
            "hold": END,
        },
    )

    # --- Phase 3+4: risk_manager → claw_guard → L3 chain → synthesize → END ---
    workflow.add_edge("risk_manager", "claw_guard")
    workflow.add_edge("claw_guard", "institutional_guard")
    workflow.add_conditional_edges(
        "institutional_guard",
        route_after_institutional_guard,
        {"data_fetcher": "data_fetcher", "synthesize": "synthesize"},
    )
    workflow.add_edge("data_fetcher", "write_external_memory")   # Phase 4: store market data
    workflow.add_edge("write_external_memory", "knowledge_base")
    workflow.add_edge("knowledge_base", "backtester")
    workflow.add_edge("backtester", "order_router")
    workflow.add_conditional_edges(
        "order_router",
        route_after_order_router,
        {"decision_card_writer": "decision_card_writer", "trade_logger": "trade_logger"},
    )
    workflow.add_edge("decision_card_writer", "trade_logger")
    workflow.add_edge("trade_logger", "write_trade_memory")      # Phase 4: store trade outcome
    workflow.add_edge("write_trade_memory", "synthesize")
    workflow.add_edge("synthesize", END)

    # Default to memory persistence if none provided
    if checkpointer is None:
        checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


def build_graph():
    """Convenience entry point for smoke-testing the compiled graph.

    Returns the compiled LangGraph application using an empty config.
    Equivalent to create_orchestrator_graph({}).
    """
    return create_orchestrator_graph({})

import asyncio

class LangGraphOrchestrator:
    """Wrapper for the LangGraph orchestrator to match existing interface."""

    def __init__(self, config: Dict, checkpointer: Any = None):
        self.config = config
        self.checkpointer = checkpointer

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

        # Phase 4: Memory service — constructed once, shared across all graph runs
        from src.memory.service import MemoryService
        self._memory = MemoryService(chroma_path="data/chroma_db")

        self.app = create_orchestrator_graph(merged_config, checkpointer=self.checkpointer, memory=self._memory)

    def run_task(self, user_input: str) -> GraphDecision:
        """Process user input through the LangGraph (Synchronous wrapper)."""
        return asyncio.run(self.run_task_async(user_input))

    def _load_institutional_memory(self) -> str:
        """Load institutional memory from the structured registry and MEMORY.md.

        Combines two sources:
        1. Structured MemoryRegistry (data/memory_registry.json) — active governed rules.
        2. data/MEMORY.md — markdown rules file written by the RuleGenerator pipeline.

        This allows rules generated by the /review command (written to MEMORY.md) to
        be injected into agent prompts alongside formally governed registry rules.
        """
        sections: list[str] = []

        # Source 1: Structured JSON registry
        try:
            registry = MemoryRegistry()
            rules = registry.get_active_rules()
            if rules:
                formatted = []
                for r in rules:
                    formatted.append(f"- [{r.id}] {r.type.upper()}: {r.title}")
                    if r.condition:
                        formatted.append(f"  When: {str(r.condition)}")
                    if r.action:
                        formatted.append(f"  Action: {str(r.action)}")
                sections.append("\n".join(formatted))
        except Exception as e:
            logger.error("Failed to load institutional memory registry: %s", e)

        # Source 2: MEMORY.md flat-file rules (written by RuleGenerator)
        memory_md_path = Path("data/MEMORY.md")
        try:
            if memory_md_path.exists():
                content = memory_md_path.read_text().strip()
                if content:
                    sections.append(content)
        except Exception as e:
            logger.error("Failed to read data/MEMORY.md: %s", e)

        if not sections:
            return "No active institutional rules."

        return "\n\n".join(sections)

    async def run_task_async(self, user_input: str) -> GraphDecision:
        """Process user input through the LangGraph (Asynchronous)."""
        task_id = str(uuid.uuid4())[:8]

        # Resolve execution_mode from YAML config (safe default: "paper")
        execution_mode: str = (
            self._yaml_config.get("trading", {}).get("execution_mode", "paper")
            or "paper"
        )

        # Phase 7: Load and inject institutional memory
        institutional_memory = self._load_institutional_memory()
        memory_message = {
            "role": "system",
            "content": f"INSTITUTIONAL MEMORY (Prior Lessons):\n{institutional_memory}"
        }

        initial_state: dict[str, Any] = {
            "task_id": task_id,
            "user_input": user_input,
            "intent": "unknown",
            "messages": [memory_message],
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
            # Phase 11: Decision Card fields
            "decision_card_status": None,
            "decision_card_error": None,
            "decision_card_audit_ref": None,
        }

        # Configure the thread (required for checkpointing)
        config = {"configurable": {"thread_id": task_id}}

        try:
            # LangGraph application contains async nodes (e.g. within with_audit_logging),
            # so we MUST use ainvoke even without an async checkpointer.
            final_state = await self.app.ainvoke(initial_state, config=config)

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
