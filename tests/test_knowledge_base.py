"""
tests.test_knowledge_base — Tests for the KnowledgeBase and its graph node.
"""

import pytest
from src.tools.knowledge_base import get_kb
from src.graph.nodes.knowledge_base import knowledge_base_node

@pytest.mark.asyncio
async def test_knowledge_base_node_basic():
    """Verify that the knowledge_base_node produces a result in SwarmState."""
    state = {
        "quant_proposal": {"symbol": "AAPL", "asset_class": "equity"},
        "messages": []
    }
    
    # We call the node directly
    result = await knowledge_base_node(state)
    
    assert "knowledge_base_result" in result
    assert "messages" in result
    assert isinstance(result["knowledge_base_result"]["sentiment_context"], list)
    # Even if DB is empty, it should return a structured dict (maybe with error/empty)
    assert "historical_stats" in result["knowledge_base_result"]

def test_kb_query_sentiment():
    """Test the low-level KB sentiment query."""
    context = get_kb().query_sentiment_context("market", n_results=1)
    assert isinstance(context, list)

def test_kb_query_stats_missing():
    """Test querying a symbol that doesn't exist in our current subset."""
    stats = get_kb().query_historical_stats("NON_EXISTENT_TICKER")
    assert "error" in stats
