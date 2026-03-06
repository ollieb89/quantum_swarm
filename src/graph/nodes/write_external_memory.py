"""
Write node: store data_fetcher results into the memory knowledge store.

Placed in the graph between data_fetcher and knowledge_base.
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


def write_external_memory_node(state: SwarmState, memory: "MemoryService") -> SwarmState:
    """
    Store normalized data_fetcher results as external_data memory.

    Extracts each data sub-type (market, sentiment, economic) separately
    so they can be searched and retrieved independently.
    """
    result = state.get("data_fetcher_result")
    if not result:
        return state

    task_id = state.get("task_id", "unknown")
    symbol = _extract_symbol(result)

    sources_to_store = {
        "market": result.get("market_data"),
        "sentiment": result.get("sentiment_data"),
        "economic": result.get("economic_data"),
    }

    for data_type, data in sources_to_store.items():
        if not data:
            continue
        try:
            content = _serialize(data)
            if not content.strip():
                continue
            metadata = {
                "timestamp": _extract_timestamp(data) or _now_utc(),
                "data_type": _map_data_type(data_type),
                "source_name": data.get("source", f"data_fetcher_{data_type}"),
                "title_or_url": f"{symbol}:{data_type}:{task_id}",
                "run_id": task_id,
            }
            if symbol:
                metadata["symbol"] = symbol
            memory.store(
                content=content,
                source=MemorySource.EXTERNAL_DATA,
                metadata=metadata,
                node="write_external_memory",
            )
        except Exception as exc:
            logger.error(
                "write_external_memory: failed to store %s data: %s",
                data_type,
                exc,
            )

    return {}  # no state changes; write is a side effect only


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_utc() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_symbol(result: dict) -> str:
    for key in ("symbol", "ticker"):
        val = result.get(key) or (result.get("market_data") or {}).get(key, "")
        if val:
            return str(val).upper()
    return ""


def _extract_timestamp(data: dict) -> str | None:
    for key in ("timestamp", "date", "as_of"):
        val = data.get(key)
        if val:
            return str(val)
    return None


def _serialize(data: dict) -> str:
    try:
        return json.dumps(data, default=str, indent=2)
    except Exception:
        return str(data)


def _map_data_type(key: str) -> str:
    mapping = {
        "market": "news",
        "sentiment": "news",
        "economic": "economic",
    }
    return mapping.get(key, "news")
