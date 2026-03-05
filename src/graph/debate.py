"""
Debate Synthesis Node — DebateSynthesizer.

Aggregates bullish and bearish researcher outputs into a weighted consensus score.

The synthesizer is a PURE AGGREGATION step — it makes no LLM calls.
It reads the tagged AIMessage outputs produced by BullishResearcher and
BearishResearcher from SwarmState["messages"] and computes:

    weighted_consensus_score = bullish_strength / (bullish_strength + bearish_strength)

    where "strength" is a simple proxy: the character length of the researcher's
    final text output (longer, denser responses indicate more evidence gathered).
    This is deliberately lightweight and deterministic; future plans can swap in
    a more sophisticated scoring function without changing the interface.

Output fields written to SwarmState:
    - weighted_consensus_score: float in [0.0, 1.0]
    - debate_history: list of provenance dicts for downstream audit / risk gating
"""

from __future__ import annotations

import logging
from typing import Any

from src.graph.state import SwarmState

logger = logging.getLogger(__name__)

# Names used by researcher nodes to tag their AIMessage outputs
_BULLISH_SOURCE = "bullish_research"
_BEARISH_SOURCE = "bearish_research"


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

    # Strength proxy: character length of each side's output.
    # A researcher that produced more detailed findings has a longer response.
    bullish_strength = float(len(bullish_text)) if bullish_text else 0.0
    bearish_strength = float(len(bearish_text)) if bearish_text else 0.0

    total = bullish_strength + bearish_strength
    if total > 0.0:
        raw_score = bullish_strength / total
    else:
        # No researcher output at all — neutral default
        raw_score = 0.5

    # Clip to [0.0, 1.0] as a safety guard (should always be in range, but be explicit)
    weighted_consensus_score = max(0.0, min(1.0, raw_score))

    logger.info(
        "DebateSynthesizer: bullish_strength=%.0f bearish_strength=%.0f score=%.4f",
        bullish_strength,
        bearish_strength,
        weighted_consensus_score,
    )

    # Compile debate history with provenance metadata
    debate_history: list[dict] = []

    if bullish_text:
        debate_history.append(
            {
                "source": _BULLISH_SOURCE,
                "hypothesis": "bullish",
                "evidence": bullish_text,
                "strength": bullish_strength,
            }
        )

    if bearish_text:
        debate_history.append(
            {
                "source": _BEARISH_SOURCE,
                "hypothesis": "bearish",
                "evidence": bearish_text,
                "strength": bearish_strength,
            }
        )

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
    }
