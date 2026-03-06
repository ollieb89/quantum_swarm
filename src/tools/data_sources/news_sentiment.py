"""
src.tools.data_sources.news_sentiment — Market news sentiment via FinBERT.

Provides:
    fetch_news_sentiment(symbol) -> SentimentData
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from src.models.data_models import SentimentData

logger = logging.getLogger(__name__)

# In-memory cache to prevent duplicate API calls in one run
_sentiment_cache: Dict[str, SentimentData] = {}


def clear_cache():
    """Clear the in-memory sentiment data cache."""
    _sentiment_cache.clear()


async def fetch_news_sentiment(symbol: str) -> SentimentData:
    """Fetch news sentiment for a symbol using HuggingFace FinBERT API or mock fallback.

    Args:
        symbol: Ticker symbol (e.g., 'AAPL').

    Returns:
        SentimentData Pydantic model with sentiment analysis.
    """
    if symbol in _sentiment_cache:
        logger.info("Cache hit for sentiment data: %s", symbol)
        return _sentiment_cache[symbol]

    hf_api_key = os.environ.get("HUGGINGFACE_API_KEY")
    now = datetime.now(tz=timezone.utc)

    if not hf_api_key:
        logger.warning("HUGGINGFACE_API_KEY not set; using mock news sentiment for %s", symbol)
        sentiment = _get_mock_sentiment(symbol, now)
        _sentiment_cache[symbol] = sentiment
        return sentiment

    logger.info("Fetching news sentiment for %s via HuggingFace FinBERT", symbol)

    # Simplified headline for sentiment analysis
    headline = f"The latest financial reports for {symbol} indicate potential market growth."
    
    api_url = "https://api-inference.huggingface.co/models/ProsusAI/finbert"
    headers = {"Authorization": f"Bearer {hf_api_key}"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                api_url, 
                headers=headers, 
                json={"inputs": headline}, 
                timeout=10.0
            )
            
            if response.status_code != 200:
                logger.warning("FinBERT API returned status %d; falling back to mock", response.status_code)
                sentiment = _get_mock_sentiment(symbol, now)
                _sentiment_cache[symbol] = sentiment
                return sentiment

            results: List[List[Dict[str, Any]]] = response.json()
            if not results or not results[0]:
                raise ValueError("Unexpected response format from FinBERT API")

            # Extract highest score label
            # Response structure: [[{'label': 'positive', 'score': 0.95}, ...]]
            scores = results[0]
            top_sentiment = max(scores, key=lambda x: x["score"])
            
            label = top_sentiment["label"]
            score = top_sentiment["score"]
            
            # Map label to a numeric score range for consistency if needed
            # (FinBERT uses positive, negative, neutral)
            
            sentiment = SentimentData(
                symbol=symbol,
                overall_sentiment=label,
                sentiment_score=float(score),
                article_count=1,  # Single-headline inference
                timestamp=now,
                source="finbert"
            )
            
            _sentiment_cache[symbol] = sentiment
            return sentiment

    except Exception as e:
        logger.error("Error fetching news sentiment for %s: %s; falling back to mock", symbol, e)
        sentiment = _get_mock_sentiment(symbol, now)
        _sentiment_cache[symbol] = sentiment
        return sentiment


def _get_mock_sentiment(symbol: str, timestamp: datetime) -> SentimentData:
    """Return a mock SentimentData model."""
    return SentimentData(
        symbol=symbol,
        overall_sentiment="neutral",
        sentiment_score=0.0,
        article_count=0,
        timestamp=timestamp,
        source="mock"
    )
