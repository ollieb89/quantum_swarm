"""
src.graph.nodes.l1 — L1 orchestrator node implementations.

These nodes are intentionally kept dependency-light so they can be imported
and tested without the heavy agent/LLM stack.
"""

import logging
from typing import Any, Dict, Optional

from src.blackboard.board import Blackboard
from src.core.blackboard import InterAgentBlackboard
from src.core.budget_manager import BudgetManager
from src.skills.registry import SkillRegistry

_registry: Optional[SkillRegistry] = None


def _get_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
        _registry.discover()
    return _registry

logger = logging.getLogger(__name__)


def risk_manager_node(state: dict, board: Optional[Blackboard] = None) -> dict:
    """RiskManager LangGraph node — final validation before execution.

    Reads debate_history and weighted_consensus_score from SwarmState.
    Performs final risk validation:
      1. Checks for conflicting hypotheses (both bullish and bearish sources present)
      2. Checks for missing provenance (empty debate_history)
      3. Validates that the consensus score is not anomalous (outside [0.0, 1.0])

    If board is provided, writes the risk_approval slot to the blackboard.

    Returns:
        Partial state update with risk_approved (bool) and risk_notes (str).
    """
    logger.info("RiskManager node invoked (task_id=%s)", state.get("task_id"))

    debate_history = state.get("debate_history", [])
    score = state.get("weighted_consensus_score")

    notes: list[str] = []
    approved = True

    if not debate_history:
        notes.append("No debate history found — provenance missing.")
        approved = False

    if score is None:
        notes.append("weighted_consensus_score is None — cannot validate.")
        approved = False
    elif not (0.0 <= score <= 1.0):
        notes.append(f"Anomalous consensus score {score:.4f} outside [0.0, 1.0].")
        approved = False

    sources = {entry.get("hypothesis") for entry in debate_history}
    if "bullish" in sources and "bearish" in sources:
        notes.append("Conflicting hypotheses detected (bullish + bearish) — normal adversarial debate.")
    elif not sources or sources == {"neutral"}:
        notes.append("No adversarial hypotheses found — debate may have been skipped.")
        approved = False

    risk_notes = " | ".join(notes) if notes else "All risk checks passed."

    logger.info("RiskManager: approved=%s score=%s notes=%s", approved, score, risk_notes)

    if board is not None:
        board.write("risk_approval", {"approved": approved, "notes": risk_notes})

    return {
        "risk_approved": approved,
        "risk_notes": risk_notes,
        "messages": [
            {"role": "assistant", "content": f"RiskManager: approved={approved} | {risk_notes}"}
        ],
    }


def synthesize_consensus(state: dict, config: dict, board: Optional[Blackboard] = None) -> dict:
    """Final node to synthesize the result.

    If board is provided, writes the final_decision slot to the blackboard.
    """
    decision = {
        "task_id": state["task_id"],
        "decision": "HOLD",
        "rationale": "Phase 1 PoC: Execution node reached.",
    }

    if board is not None:
        board.write("final_decision", decision)

    return {
        "final_decision": decision,
        "messages": [{"role": "assistant", "content": "L1 Orchestrator: Final consensus synthesized."}],
    }


def classify_intent_with_registry(
    state: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
    board: Optional[InterAgentBlackboard] = None,
    budget: Optional[BudgetManager] = None,
) -> Dict[str, Any]:
    """Classify intent, routing deterministically to a skill if one matches.

    Checks the SkillRegistry first. If the user_input contains a known
    SKILL_INTENT token, calls the handler directly (bypassing the graph).
    Falls through to pattern-based intent classification otherwise.

    If *board* is provided, writes the delegation objective to the blackboard
    so that child agents can pick it up via the session_id.

    If *budget* is provided, checks budget ceilings before proceeding.
    Raises SafetyShutdown (propagated from BudgetManager) if limits are hit.
    """
    if config is None:
        config = {}

    # --- Budget gate (runs before any LLM work) ---
    if budget is not None:
        budget.check_budget()
        # Record a dummy cost for intent classification (e.g. 50 input tokens)
        budget.record_usage(input_tokens=50, output_tokens=0)

    user_input = state.get("user_input", "")
    registry = _get_registry()

    # Get cumulative tokens from budget if available
    tokens_to_add = 50 if budget is not None else 0

    # Deterministic bypass: check each registered intent against user input
    for intent in registry.intents:
        if intent in user_input.lower():
            skill_result = registry.route(intent, state)
            if skill_result is not None:
                logger.info("classify_intent_with_registry: bypassing graph for skill=%r", intent)
                _write_objective(board, state, intent)
                return {
                    "intent": intent,
                    "skill_result": skill_result,
                    "blackboard_session": state.get("task_id"),
                    "total_tokens": tokens_to_add,
                    "messages": [
                        {"role": "assistant", "content": f"Skill bypass: {intent}"}
                    ],
                }

    # Fall through: pattern-based classification
    intent_patterns = config.get("orchestrator", {}).get("intent_patterns", {})
    intent = "unknown"
    for intent_name, patterns in intent_patterns.items():
        for pattern in patterns:
            if pattern in user_input.lower():
                intent = intent_name
                break
        if intent != "unknown":
            break

    logger.info("classify_intent_with_registry: pattern intent=%r", intent)
    _write_objective(board, state, intent)
    return {
        "intent": intent,
        "blackboard_session": state.get("task_id"),
        "total_tokens": tokens_to_add,
        "messages": [{"role": "assistant", "content": f"Classified intent: {intent}"}],
    }


def _write_objective(
    board: Optional[InterAgentBlackboard],
    state: Dict[str, Any],
    intent: str,
) -> None:
    """Write the current task objective to the blackboard if board is provided."""
    if board is None:
        return
    session_id = state.get("task_id")
    if not session_id:
        return
    objective = {
        "task_id": session_id,
        "user_input": state.get("user_input", ""),
        "intent": intent,
    }
    board.write_state(session_id, "objective", objective)
    logger.info("classify_intent_with_registry: objective written to blackboard session=%s", session_id)
