"""
src.graph.nodes.knowledge_base — KnowledgeBase LangGraph async node.

Queries local ChromaDB and DuckDB stores.
"""

from __future__ import annotations

import logging
from typing import Any

from src.graph.state import SwarmState
from src.tools.knowledge_base import get_kb

logger = logging.getLogger(__name__)

async def knowledge_base_node(state: SwarmState) -> dict[str, Any]:
    """KnowledgeBase node for RAG-enhanced context.

    State reads:
        state["quant_proposal"]  dict with "symbol"

    State writes:
        "knowledge_base_result"  dict with sentiment_context and historical_stats
        "messages"               list — one assistant message entry
    """
    quant_proposal = state.get("quant_proposal") or {}
    symbol: str = quant_proposal.get("symbol", "AAPL")
    
    logger.info("KnowledgeBase node: symbol=%s", symbol)
    
    # 1. Query historical price stats from DuckDB
    stats = get_kb().query_historical_stats(symbol)

    # 2. Query sentiment context from ChromaDB
    context = get_kb().query_sentiment_context(f"General market outlook and sentiment for {symbol}")
    
    result = {
        "historical_stats": stats,
        "sentiment_context": context,
    }
    
    msg = f"KnowledgeBase: Found {len(context)} historical sentiment samples. "
    if "error" not in stats:
        msg += f"Historical Avg Price: {stats['avg_price']:.2f}."
    else:
        msg += "No historical price data found."

    logger.info("KnowledgeBase node complete for %s", symbol)

    return {
        "knowledge_base_result": result,
        "messages": [
            {
                "role": "assistant",
                "content": msg,
            }
        ],
    }
