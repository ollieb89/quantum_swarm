"""
Debate Synthesis Node — DebateSynthesizer.

Aggregates bullish and bearish researcher outputs into a weighted consensus score.

The synthesizer is a PURE AGGREGATION step — it makes no LLM calls.
It reads the tagged AIMessage outputs produced by BullishResearcher and
BearishResearcher from SwarmState["messages"] and computes:

    weighted_consensus_score = bull_w / (bull_w + bear_w)

    where bull_w and bear_w are the KAMI merit composite scores for each side's
    soul handle (MOMENTUM and CASSANDRA respectively), read from
    SwarmState["merit_scores"]. Character-length proxy removed in Phase 16.
    Cold-start fallback: both sides default to DEFAULT_MERIT=0.5 → score=0.5.

Output fields written to SwarmState:
    - weighted_consensus_score: float in [0.0, 1.0]
    - debate_history: list of provenance dicts for downstream audit / risk gating
"""

from __future__ import annotations

import logging
from typing import Any

from src.graph.state import SwarmState
from src.core.kami import RESEARCHER_HANDLE_MAP, DEFAULT_MERIT

logger = logging.getLogger(__name__)

# Names used by researcher nodes to tag their AIMessage outputs
_BULLISH_SOURCE = "bullish_research"
_BEARISH_SOURCE = "bearish_research"

# Phase 21: maps debate source → opponent soul handle for peer summary lookup
_OPPONENT_MAP: dict[str, str] = {
    _BULLISH_SOURCE: "CASSANDRA",
    _BEARISH_SOURCE: "MOMENTUM",
}


def _extract_researcher_text(messages: list[Any], source_name: str) -> str:
    """Return concatenated content from all messages tagged with *source_name*.

    Messages may be AIMessage objects (have a ``.name`` attribute) or plain dicts
    (have a ``"name"`` key). Both are handled.
    """
    parts: list[str] = []
    for msg in messages:
        name = None
        content = None

        if hasattr(msg, "name"):
            # LangChain AIMessage / BaseMessage object
            name = getattr(msg, "name", None)
            content = getattr(msg, "content", None)
            if content is None:
                content = str(msg)
        elif isinstance(msg, dict):
            name = msg.get("name") or msg.get("role", "")
            content = msg.get("content", "")

        if name == source_name and content:
            parts.append(content if isinstance(content, str) else str(content))

    return "\n".join(parts)


def DebateSynthesizer(state: SwarmState) -> dict[str, Any]:
    """LangGraph node: aggregate adversarial researcher outputs into consensus score.

    Reads all messages in SwarmState, extracts bullish_research and bearish_research
    AIMessages by their ``name`` tag, computes a weighted consensus score from the
    relative text strength of each side, and compiles the full debate provenance
    into ``debate_history``.

    Args:
        state: Current SwarmState shared across the graph.

    Returns:
        Partial state update dict with:
            - ``weighted_consensus_score``: float in [0.0, 1.0]
            - ``debate_history``: list of dicts with provenance metadata
    """
    logger.info("DebateSynthesizer node invoked (task_id=%s)", state.get("task_id"))

    messages = state.get("messages", [])

    bullish_text = _extract_researcher_text(messages, _BULLISH_SOURCE)
    bearish_text = _extract_researcher_text(messages, _BEARISH_SOURCE)

    # Phase 16: KAMI merit-based consensus weighting.
    # Character-length proxy removed — len(text) is no longer used for strength.
    # Merit key: soul handles from RESEARCHER_HANDLE_MAP (stable per-role mapping).
    # Extension point: future phases with multiple agents per side sum their merits.
    merit_scores = state.get("merit_scores") or {}
    bullish_handle = RESEARCHER_HANDLE_MAP.get(_BULLISH_SOURCE, "")
    bearish_handle = RESEARCHER_HANDLE_MAP.get(_BEARISH_SOURCE, "")

    bullish_entry = merit_scores.get(bullish_handle, {})
    bearish_entry = merit_scores.get(bearish_handle, {})

    bull_w = float(bullish_entry.get("composite", DEFAULT_MERIT)) if bullish_entry else DEFAULT_MERIT
    bear_w = float(bearish_entry.get("composite", DEFAULT_MERIT)) if bearish_entry else DEFAULT_MERIT

    # Both sides missing or zero → neutral
    total = bull_w + bear_w
    if total > 0.0:
        raw_score = bull_w / total
    else:
        # No merit data at all — neutral default
        raw_score = 0.5

    # Clip to [0.0, 1.0] as a safety guard (should always be in range, but be explicit)
    weighted_consensus_score = max(0.0, min(1.0, raw_score))

    logger.info(
        "DebateSynthesizer: bull_merit=%.4f bear_merit=%.4f score=%.4f",
        bull_w,
        bear_w,
        weighted_consensus_score,
    )

    # Phase 21: read soul_sync_context for peer summary enrichment
    soul_sync_context = state.get("soul_sync_context") or {}
    logger.info("DebateSynthesizer: soul_sync_context consumed (%d peer summaries)", len(soul_sync_context))

    # Compile debate history with provenance metadata
    debate_history: list[dict] = []

    if bullish_text:
        entry: dict[str, Any] = {
            "source": _BULLISH_SOURCE,
            "hypothesis": "bullish",
            "evidence": bullish_text,
            "strength": bull_w,   # merit composite, not len(text)
        }
        opponent_summary = soul_sync_context.get(_OPPONENT_MAP[_BULLISH_SOURCE], "")
        if opponent_summary:
            entry["peer_soul_summary"] = opponent_summary
        debate_history.append(entry)

    if bearish_text:
        entry = {
            "source": _BEARISH_SOURCE,
            "hypothesis": "bearish",
            "evidence": bearish_text,
            "strength": bear_w,   # merit composite, not len(text)
        }
        opponent_summary = soul_sync_context.get(_OPPONENT_MAP[_BEARISH_SOURCE], "")
        if opponent_summary:
            entry["peer_soul_summary"] = opponent_summary
        debate_history.append(entry)

    # If neither researcher ran, add a placeholder so debate_history is never empty
    if not debate_history:
        debate_history.append(
            {
                "source": "synthesizer",
                "hypothesis": "neutral",
                "evidence": "No researcher outputs found; defaulting to neutral score.",
                "strength": 0.0,
            }
        )

    return {
        "weighted_consensus_score": weighted_consensus_score,
        "debate_history": debate_history,
        "debate_resolution": {
            "weighted_consensus_score": weighted_consensus_score,
            "debate_history": debate_history,
        },
    }
