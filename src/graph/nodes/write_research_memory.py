"""
Write node: store debate synthesis output into the memory knowledge store.

Placed in the graph between debate_synthesizer and the risk-gate conditional edge,
so research is always stored regardless of whether the trade passes the threshold.
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


def write_research_memory_node(state: SwarmState, memory: "MemoryService") -> SwarmState:
    """
    Store the debate resolution (plus bullish/bearish theses) as research memory.

    Uses a composite content string so the full adversarial context is searchable
    in a single document.
    """
    debate_resolution = state.get("debate_resolution")
    if not debate_resolution:
        return state

    task_id = state.get("task_id", "unknown")
    symbol = _extract_symbol(state)

    try:
        content = _build_research_content(state)
        if not content.strip():
            return state

        metadata = {
            "timestamp": _now_utc(),
            "run_id": task_id,
            "agent": "debate_synthesizer",
            "symbol": symbol,
            "weighted_consensus_score": state.get("weighted_consensus_score"),
        }
        memory.store(
            content=content,
            source=MemorySource.RESEARCH,
            metadata=metadata,
            node="write_research_memory",
        )
    except Exception as exc:
        logger.error("write_research_memory: failed to store debate result: %s", exc)

    return {}  # no state changes; write is a side effect only


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_utc() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_symbol(state: SwarmState) -> str:
    for key in ("quant_proposal", "macro_report", "debate_resolution"):
        data = state.get(key) or {}
        if isinstance(data, dict):
            sym = data.get("symbol") or data.get("ticker", "")
            if sym:
                return str(sym).upper()
    return state.get("user_input", "UNKNOWN")[:20].upper()


def _safe_serialize(data) -> str:
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data, default=str, indent=2)
    except Exception:
        return str(data)


def _build_research_content(state: SwarmState) -> str:
    sections = []

    score = state.get("weighted_consensus_score")
    if score is not None:
        sections.append(f"Weighted Consensus Score: {score:.4f}")

    if state.get("debate_resolution"):
        sections.append("=== Debate Resolution ===")
        sections.append(_safe_serialize(state["debate_resolution"]))

    if state.get("bullish_thesis"):
        sections.append("=== Bullish Thesis ===")
        sections.append(_safe_serialize(state["bullish_thesis"]))

    if state.get("bearish_thesis"):
        sections.append("=== Bearish Thesis ===")
        sections.append(_safe_serialize(state["bearish_thesis"]))

    return "\n\n".join(sections)
