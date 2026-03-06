"""
src.tools.data_sources.news_sentiment — FinBERT news sentiment client (async).

Provides:
    fetch_news_sentiment(symbol) -> SentimentData

Primary path:
    - Calls the HuggingFace Inference API for ProsusAI/finbert with a simple
      headline about the symbol.
    - If HUGGINGFACE_API_KEY env var is set it is sent as a Bearer token.
    - Parses the JSON response and maps finbert labels to sentiment strings.

Fallback:
    - If HUGGINGFACE_API_KEY is absent OR if the API call fails for any reason,
      degrades to a mock SentimentData with source="mock" and sentiment_score=0.0.

Uses httpx for async HTTP requests.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from src.models.data_models import SentimentData

logger = logging.getLogger(__name__)

_FINBERT_ENDPOINT = (
    "https://api-inference.huggingface.co/models/ProsusAI/finbert"
)

# FinBERT label → canonical sentiment string
_LABEL_MAP = {
    "positive": "bullish",
    "negative": "bearish",
    "neutral": "neutral",
}

# FinBERT label → signed score contribution
_SCORE_SIGN = {
    "positive": 1.0,
    "negative": -1.0,
    "neutral": 0.0,
}


def _mock_sentiment(symbol: str) -> SentimentData:
    """Return a zeroed-out mock SentimentData when the real API is unavailable."""
    return SentimentData(
        symbol=symbol,
        overall_sentiment="neutral",
        sentiment_score=0.0,
        article_count=0,
        timestamp=datetime.now(tz=timezone.utc),
        source="mock",
    )


def _parse_finbert_response(symbol: str, payload: Any) -> SentimentData:
    """Parse the HuggingFace FinBERT response payload into SentimentData.

    HuggingFace returns a list of lists of dicts:
        [[{"label": "positive", "score": 0.98}, ...]]

    The label with the highest score is taken as the overall sentiment.
    The signed score is: score * sign(label).
    """
    if not payload or not isinstance(payload, list):
        return _mock_sentiment(symbol)

    # Unwrap outer list if present
    candidates = payload[0] if isinstance(payload[0], list) else payload

    if not candidates:
        return _mock_sentiment(symbol)

    # Sort by score descending and pick top
    sorted_candidates = sorted(candidates, key=lambda x: x.get("score", 0.0), reverse=True)
    top = sorted_candidates[0]

    label = top.get("label", "neutral").lower()
    score = float(top.get("score", 0.0))

    overall = _LABEL_MAP.get(label, "neutral")
    signed_score = score * _SCORE_SIGN.get(label, 0.0)

    return SentimentData(
        symbol=symbol,
        overall_sentiment=overall,
        sentiment_score=round(signed_score, 4),
        article_count=1,  # one synthetic headline submitted
        timestamp=datetime.now(tz=timezone.utc),
        source="finbert",
    )


async def fetch_news_sentiment(symbol: str) -> SentimentData:
    """Fetch FinBERT sentiment for *symbol* via HuggingFace Inference API.

    Degrades gracefully to mock if the API key is absent or the request fails.

    Args:
        symbol: Ticker symbol used to construct a synthetic headline.

    Returns:
        SentimentData Pydantic model.
    """
    api_key = os.environ.get("HUGGINGFACE_API_KEY", "")

    if not api_key:
        logger.debug("HUGGINGFACE_API_KEY not set — using mock sentiment for %s", symbol)
        return _mock_sentiment(symbol)

    headline = f"Latest news and market outlook for {symbol} stock performance"

    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {"inputs": headline}

    try:
        import httpx  # type: ignore[import-untyped]

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                _FINBERT_ENDPOINT,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        return _parse_finbert_response(symbol, data)

    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "FinBERT API call failed for %s: %s — falling back to mock", symbol, exc
        )
        return _mock_sentiment(symbol)
