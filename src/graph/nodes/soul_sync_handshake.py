"""Phase 18: Theory of Mind Soul-Sync barrier node.

Runs after both BullishResearcher and BearishResearcher complete (LangGraph
multi-source barrier edge). Reads peer soul summaries from lru_cache into
SwarmState["soul_sync_context"]. Zero LLM calls. Zero filesystem I/O at runtime
(cache populated by warmup_soul_cache() at graph creation).
"""
import logging
from src.core.soul_loader import load_soul

logger = logging.getLogger(__name__)

# Maps peer-visible handle → soul directory name (agent_id)
_RESEARCHER_HANDLES: dict[str, str] = {
    "MOMENTUM": "bullish_researcher",
    "CASSANDRA": "bearish_researcher",
}


def soul_sync_handshake_node(state: dict) -> dict:
    """Barrier node: read peer soul summaries from lru_cache → soul_sync_context.

    Synchronous: all reads are lru_cache hits (warmed up at graph creation).
    Zero LLM calls. Zero filesystem I/O at runtime.

    Returns:
        {"soul_sync_context": {"MOMENTUM": "<summary>", "CASSANDRA": "<summary>"}}
    """
    soul_sync_context: dict[str, str] = {}
    for handle, agent_id in _RESEARCHER_HANDLES.items():
        try:
            soul = load_soul(agent_id)
            soul_sync_context[handle] = soul.public_soul_summary()
        except Exception as e:
            logger.error(
                "soul_sync_handshake: failed to load soul for %s (%s): %s",
                handle, agent_id, e,
            )
            soul_sync_context[handle] = ""
    return {"soul_sync_context": soul_sync_context}
