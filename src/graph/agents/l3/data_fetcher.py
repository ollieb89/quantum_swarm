"""
src.graph.agents.l3.data_fetcher — DataFetcher LangGraph async node.

Exports:
    data_fetcher_node(state: SwarmState) -> dict

This node replaces the stub DataFetcher class in src/agents/l3_executor.py with
a real async LangGraph node that dispatches to live data sources and returns
plain-dict serializable results suitable for LangGraph state.

Data sources:
    - Equity symbols  → yfinance_client.fetch_equity_data
    - Crypto symbols  → ccxt_client.fetch_crypto_ohlcv
    - Always fetched  → news_sentiment.fetch_news_sentiment
    - Always fetched  → economic_calendar.fetch_economic_data
    - Optional (fundamentals flag) → dexter_bridge.invoke_dexter_safe

All Pydantic models are serialised via .model_dump() before returning — no
raw Pydantic objects are stored in SwarmState.
"""

from __future__ import annotations

import logging
from typing import Any

from src.graph.state import SwarmState
from src.tools.data_sources.ccxt_client import fetch_crypto_ohlcv
from src.tools.data_sources.economic_calendar import fetch_economic_data
from src.tools.data_sources.news_sentiment import fetch_news_sentiment
from src.tools.data_sources.yfinance_client import fetch_equity_data
from src.tools.dexter_bridge import invoke_dexter_safe

logger = logging.getLogger(__name__)


async def data_fetcher_node(state: SwarmState) -> dict[str, Any]:
    """L3 DataFetcher LangGraph async node.

    Reads ``quant_proposal`` from SwarmState to determine symbol and asset class,
    fetches live market data, news sentiment, and economic indicators, then
    optionally invokes the Dexter fundamental research bridge.

    State reads:
        state["quant_proposal"]                           dict with "symbol" and "asset_class"
        state.get("metadata", {}).get("fetch_fundamentals", False)

    State writes:
        "data_fetcher_result"  dict — serialized MarketData, SentimentData, EconomicData
        "messages"             list — one assistant message entry

    Args:
        state: Current SwarmState shared across the LangGraph graph.

    Returns:
        Partial state update dict with ``data_fetcher_result`` and ``messages`` keys.
    """
    quant_proposal = state.get("quant_proposal") or {}
    symbol: str = quant_proposal.get("symbol", "AAPL")
    asset_class: str = quant_proposal.get("asset_class", "equity")
    fetch_fundamentals: bool = state.get("metadata", {}).get("fetch_fundamentals", False)

    logger.info(
        "DataFetcher node: symbol=%s, asset_class=%s, fetch_fundamentals=%s",
        symbol, asset_class, fetch_fundamentals,
    )

    # ------------------------------------------------------------------
    # 1. Dispatch to the appropriate market data source
    # ------------------------------------------------------------------
    if asset_class == "crypto":
        market_data = await fetch_crypto_ohlcv(symbol)
    else:
        # Default: treat as equity
        market_data = await fetch_equity_data(symbol)

    # ------------------------------------------------------------------
    # 2. Always fetch sentiment and economic data
    # ------------------------------------------------------------------
    sentiment = await fetch_news_sentiment(symbol)
    economic = await fetch_economic_data()

    # ------------------------------------------------------------------
    # 3. Optionally invoke Dexter for deep fundamental research
    # ------------------------------------------------------------------
    fundamentals = None
    if fetch_fundamentals:
        fundamentals = await invoke_dexter_safe(
            f"Fundamental analysis of {symbol}", symbol
        )

    # ------------------------------------------------------------------
    # 4. Serialise to plain dicts (Pydantic v2 .model_dump())
    # ------------------------------------------------------------------
    result: dict[str, Any] = {
        "market": market_data.model_dump(mode="json"),
        "sentiment": sentiment.model_dump(mode="json"),
        "economic": economic.model_dump(mode="json"),
        "fundamentals": fundamentals.model_dump(mode="json") if fundamentals else None,
    }

    logger.info("DataFetcher node complete for %s (%s)", symbol, asset_class)

    return {
        "data_fetcher_result": result,
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"DataFetcher: {symbol} ({asset_class}) data fetched — "
                    f"price={market_data.price:.2f}, "
                    f"sentiment={sentiment.overall_sentiment}, "
                    f"vix={economic.vix}"
                ),
            }
        ],
    }
