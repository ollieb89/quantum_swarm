"""Session-start node: load persisted merit scores from PostgreSQL into SwarmState."""
import logging
from typing import Any, Dict

from src.core.db import get_pool
from src.core.kami import ALL_SOUL_HANDLES, DEFAULT_MERIT
from src.graph.state import SwarmState

logger = logging.getLogger(__name__)


async def merit_loader_node(state: SwarmState) -> dict:
    """Load agent_merit_scores from DB into SwarmState["merit_scores"].

    Idempotency guard: if merit_scores is already populated (not None), skip DB load.
    This prevents re-invoking this session-start node from overwriting mid-session updates.
    """
    if state.get("merit_scores") is not None:
        return {}  # Already loaded — idempotency guard

    scores: Dict[str, Any] = {}
    try:
        pool = get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT soul_handle, composite, dimensions FROM agent_merit_scores"
                )
                async for row in cur:
                    soul_handle, composite, dimensions = row
                    scores[soul_handle] = {
                        **(dimensions if isinstance(dimensions, dict) else {}),
                        "composite": round(float(composite), 4),
                    }
    except Exception as e:
        logger.warning("merit_loader: DB read failed, using cold-start defaults: %s", e)

    # Cold-start defaults for any soul not yet persisted
    cold_start = {
        "accuracy": DEFAULT_MERIT,
        "recovery": DEFAULT_MERIT,
        "consensus": DEFAULT_MERIT,
        "fidelity": DEFAULT_MERIT,
        "composite": DEFAULT_MERIT,
    }
    for handle in ALL_SOUL_HANDLES:
        if handle not in scores:
            scores[handle] = cold_start.copy()

    return {"merit_scores": scores}
