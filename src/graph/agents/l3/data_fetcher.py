"""
src.graph.agents.l3.data_fetcher — LangGraph node for multi-source data acquisition.

Provides:
    data_fetcher_node(state) -> dict
"""

import logging
from typing import Any, Dict, Optional

from src.graph.state import SwarmState
from src.core.parsing import parse_quant_proposal
from src.tools.data_sources.ccxt_client import fetch_crypto_ohlcv
from src.tools.data_sources.economic_calendar import fetch_economic_data
from src.tools.data_sources.news_sentiment import fetch_news_sentiment
from src.tools.data_sources.yfinance_client import fetch_equity_data
from src.tools.dexter_bridge import invoke_dexter_safe

logger = logging.getLogger(__name__)


async def data_fetcher_node(state: SwarmState) -> Dict[str, Any]:
    """LangGraph async node to fetch market, sentiment, and economic data.

    Args:
        state: Current LangGraph swarm state.

    Returns:
        State update dict with data_fetcher_result.
    """
    # Use shared parsing utility
    quant_parsed = parse_quant_proposal(state)
    symbol = quant_parsed.get("symbol", "BTC-USD")
    asset_class = quant_parsed.get("asset_class", "crypto" if "BTC" in symbol or "ETH" in symbol else "equity")
    
    metadata = state.get("metadata", {})
    fetch_fundamentals = metadata.get("fetch_fundamentals", False)

    logger.info("DataFetcher node triggered for %s (%s)", symbol, asset_class)

    # 1. Fetch Market Data
    try:
        if asset_class == "crypto":
            market_data = await fetch_crypto_ohlcv(symbol)
        else:
            market_data = await fetch_equity_data(symbol)
    except Exception as e:
        logger.error("Market data fetch failed for %s: %s", symbol, e)
        # Fallback to an empty MarketData object if possible, or raise
        raise

    # 2. Fetch News Sentiment
    sentiment_data = await fetch_news_sentiment(symbol)

    # 3. Fetch Economic Data
    economic_data = await fetch_economic_data()

    # 4. Fetch Fundamentals (Dexter) if requested
    fundamentals_data = None
    if fetch_fundamentals:
        query = f"Provide a comprehensive fundamental analysis report for {symbol} including valuation, risk factors, and growth prospects."
        fundamentals_data = await invoke_dexter_safe(query, symbol)

    # 5. Build Result
    result = {
        "market": market_data.model_dump(),
        "sentiment": sentiment_data.model_dump(),
        "economic": economic_data.model_dump(),
        "fundamentals": fundamentals_data.model_dump() if fundamentals_data else None,
    }

    logger.info("DataFetcher successfully retrieved context for %s", symbol)

    return {
        "data_fetcher_result": result,
        "messages": [
            {
                "role": "assistant", 
                "content": f"DataFetcher: Successfully retrieved market ({asset_class}), sentiment, and economic data for {symbol}."
            }
        ]
    }
