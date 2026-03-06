"""
Write node: store confirmed trade outcomes into the memory knowledge store.

Placed in the graph between trade_logger and synthesize.
Only stores when execution_result is present and confirmed (not None).
Failures are caught and logged — they never interrupt the trading flow.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.memory.service import MemoryService

from src.graph.state import SwarmState
from src.memory.service import MemorySource

logger = logging.getLogger(__name__)


def write_trade_memory_node(state: SwarmState, memory: "MemoryService") -> SwarmState:
    """
    Store the confirmed trade execution result as trade memory.

    Includes execution details, consensus score, and quant proposal context
    so future agents can retrieve similar setups.
    """
    execution_result = state.get("execution_result")
    if not execution_result:
        return state

    task_id = state.get("task_id", "unknown")
    symbol = _extract_symbol(state, execution_result)

    try:
        content = _build_trade_content(state, execution_result)
        if not content.strip():
            return state

        metadata: dict = {
            "timestamp": _now_utc(),
            "run_id": task_id,
            "symbol": symbol,
            "direction": _extract_direction(execution_result),
        }

        # Add optional outcome fields if available
        pnl = execution_result.get("pnl") or execution_result.get("realized_pnl")
        if pnl is not None:
            metadata["pnl"] = float(pnl)

        score = state.get("weighted_consensus_score")
        if score is not None:
            metadata["weighted_consensus_score"] = score

        memory.store(
            content=content,
            source=MemorySource.TRADE,
            metadata=metadata,
            node="write_trade_memory",
        )
    except Exception as exc:
        logger.error("write_trade_memory: failed to store trade result: %s", exc)

    return {}  # no state changes; write is a side effect only


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_utc() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_symbol(state: SwarmState, execution_result: dict) -> str:
    for source in (execution_result, state.get("quant_proposal") or {}, state.get("macro_report") or {}):
        sym = source.get("symbol") or source.get("ticker", "")
        if sym:
            return str(sym).upper()
    return "UNKNOWN"


def _extract_direction(execution_result: dict) -> str:
    direction = execution_result.get("direction") or execution_result.get("side", "")
    return str(direction).upper() if direction else "UNKNOWN"


def _safe_serialize(data) -> str:
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data, default=str, indent=2)
    except Exception:
        return str(data)


def _build_trade_content(state: SwarmState, execution_result: dict) -> str:
    sections = []

    sections.append("=== Trade Execution Result ===")
    sections.append(_safe_serialize(execution_result))

    score = state.get("weighted_consensus_score")
    if score is not None:
        sections.append(f"Consensus Score at Execution: {score:.4f}")

    if state.get("quant_proposal"):
        sections.append("=== Quant Proposal Context ===")
        sections.append(_safe_serialize(state["quant_proposal"]))

    if state.get("debate_resolution"):
        sections.append("=== Debate Resolution ===")
        sections.append(_safe_serialize(state["debate_resolution"]))

    return "\n\n".join(sections)
