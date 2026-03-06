"""
tests/test_data_fetcher.py — Unit tests for data source clients and the
data_fetcher_node LangGraph async node.

Tests converted from xfail stubs to real assertions after 03-01 implementation.
"""

import asyncio
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd


# ---------------------------------------------------------------------------
# Helper: build a minimal yfinance-like DataFrame
# ---------------------------------------------------------------------------

def _make_mock_df(symbol: str = "AAPL") -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=5, freq="D")
    df = pd.DataFrame({
        "open": [100.0, 101.0, 102.0, 103.0, 104.0],
        "high": [105.0, 106.0, 107.0, 108.0, 109.0],
        "low":  [99.0, 100.0, 101.0, 102.0, 103.0],
        "close": [103.0, 104.0, 105.0, 106.0, 107.0],
        "volume": [1_000_000.0, 1_100_000.0, 1_200_000.0, 1_300_000.0, 1_400_000.0],
    }, index=dates)
    df.index.name = "Date"
    return df


# ---------------------------------------------------------------------------
# Test 1: yfinance client returns MarketData for equity symbol
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_data_fetcher_yfinance():
    """Node returns dict with data_fetcher_result containing MarketData for 'AAPL'."""
    from src.models.data_models import SentimentData, EconomicData

    mock_df = _make_mock_df("AAPL")
    now = datetime.now(tz=timezone.utc)

    mock_sentiment = SentimentData(
        symbol="AAPL", overall_sentiment="neutral", sentiment_score=0.0,
        article_count=0, timestamp=now, source="mock"
    )
    mock_economic = EconomicData(
        vix=None, usd_index=None, yield_10y=None,
        next_event_name=None, next_event_date=None, timestamp=now, source="mock"
    )

    state = {
        "quant_proposal": {"symbol": "AAPL", "asset_class": "equity"},
        "execution_mode": "paper",
        "metadata": {},
        "messages": [],
    }

    with patch("yfinance.download", return_value=mock_df):
        with patch("src.graph.agents.l3.data_fetcher.fetch_news_sentiment",
                   return_value=mock_sentiment):
            with patch("src.graph.agents.l3.data_fetcher.fetch_economic_data",
                       return_value=mock_economic):
                from src.tools.data_sources.yfinance_client import clear_cache
                clear_cache()
                from src.graph.agents.l3.data_fetcher import data_fetcher_node
                result = await data_fetcher_node(state)

    assert "data_fetcher_result" in result
    assert result["data_fetcher_result"]["market"]["symbol"] == "AAPL"
    assert result["data_fetcher_result"]["market"]["source"] == "yfinance"


# ---------------------------------------------------------------------------
# Test 2: ccxt client returns MarketData for crypto symbol
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_data_fetcher_ccxt():
    """data_fetcher_node with crypto quant_proposal uses the ccxt path."""
    from src.models.data_models import MarketData, SentimentData, EconomicData

    now = datetime.now(tz=timezone.utc)

    # ccxt OHLCV format: [ts_ms, open, high, low, close, volume]
    mock_bars = [
        [1704067200000, 42000.0, 43000.0, 41000.0, 42500.0, 100.0],
        [1704153600000, 42500.0, 44000.0, 42000.0, 43800.0, 120.0],
    ]

    mock_exchange = AsyncMock()
    mock_exchange.fetch_ohlcv = AsyncMock(return_value=mock_bars)
    mock_exchange.close = AsyncMock()

    mock_sentiment = SentimentData(
        symbol="BTC/USDT", overall_sentiment="neutral", sentiment_score=0.0,
        article_count=0, timestamp=now, source="mock"
    )
    mock_economic = EconomicData(
        vix=None, usd_index=None, yield_10y=None,
        next_event_name=None, next_event_date=None, timestamp=now, source="mock"
    )

    state = {
        "quant_proposal": {"symbol": "BTC/USDT", "asset_class": "crypto"},
        "execution_mode": "paper",
        "metadata": {},
        "messages": [],
    }

    with patch("ccxt.async_support.binance", return_value=mock_exchange):
        with patch("src.graph.agents.l3.data_fetcher.fetch_news_sentiment",
                   return_value=mock_sentiment):
            with patch("src.graph.agents.l3.data_fetcher.fetch_economic_data",
                       return_value=mock_economic):
                from src.tools.data_sources.ccxt_client import clear_cache
                clear_cache()
                from src.graph.agents.l3.data_fetcher import data_fetcher_node
                result = await data_fetcher_node(state)

    assert result["data_fetcher_result"]["market"]["source"] == "ccxt"
    assert result["data_fetcher_result"]["market"]["symbol"] == "BTC/USDT"


# ---------------------------------------------------------------------------
# Test 3: Cache hit — second fetch_equity_data call doesn't invoke yf.download
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_data_fetcher_cache():
    """Same ticker queried twice returns cached result (one yfinance.download call)."""
    mock_df = _make_mock_df("MSFT")

    with patch("yfinance.download", return_value=mock_df) as mock_dl:
        from src.tools.data_sources.yfinance_client import fetch_equity_data, clear_cache
        clear_cache()

        result1 = await fetch_equity_data("MSFT", period="6mo")
        result2 = await fetch_equity_data("MSFT", period="6mo")

    # yf.download should only have been called ONCE
    assert mock_dl.call_count == 1
    assert result1.symbol == result2.symbol == "MSFT"
    assert result1.source == "yfinance"


# ---------------------------------------------------------------------------
# Test 4: data_fetcher_node result includes sentiment field
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_data_fetcher_news_sentiment():
    """data_fetcher_node result contains a sentiment field with SentimentData-like dict."""
    from src.models.data_models import SentimentData, EconomicData

    now = datetime.now(tz=timezone.utc)
    mock_df = _make_mock_df("AAPL")

    mock_sentiment = SentimentData(
        symbol="AAPL", overall_sentiment="bullish", sentiment_score=0.65,
        article_count=10, timestamp=now, source="finbert"
    )
    mock_economic = EconomicData(
        vix=14.5, usd_index=104.2, yield_10y=4.25,
        next_event_name=None, next_event_date=None, timestamp=now, source="fred"
    )

    state = {
        "quant_proposal": {"symbol": "AAPL", "asset_class": "equity"},
        "execution_mode": "paper",
        "metadata": {},
        "messages": [],
    }

    with patch("yfinance.download", return_value=mock_df):
        with patch("src.graph.agents.l3.data_fetcher.fetch_news_sentiment",
                   return_value=mock_sentiment) as mock_sent:
            with patch("src.graph.agents.l3.data_fetcher.fetch_economic_data",
                       return_value=mock_economic):
                from src.tools.data_sources.yfinance_client import clear_cache
                clear_cache()
                from src.graph.agents.l3.data_fetcher import data_fetcher_node
                result = await data_fetcher_node(state)

    mock_sent.assert_called_once_with("AAPL")
    assert "sentiment" in result["data_fetcher_result"]
    assert result["data_fetcher_result"]["sentiment"]["overall_sentiment"] == "bullish"


# ---------------------------------------------------------------------------
# Test 5: data_fetcher_node result includes economic field
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_data_fetcher_economic():
    """data_fetcher_node result contains an economic field with EconomicData-like dict."""
    from src.models.data_models import SentimentData, EconomicData

    now = datetime.now(tz=timezone.utc)
    mock_df = _make_mock_df("AAPL")

    mock_sentiment = SentimentData(
        symbol="AAPL", overall_sentiment="neutral", sentiment_score=0.0,
        article_count=0, timestamp=now, source="mock"
    )
    mock_economic = EconomicData(
        vix=18.5, usd_index=103.0, yield_10y=4.1,
        next_event_name="FOMC", next_event_date="2026-03-20",
        timestamp=now, source="fred"
    )

    state = {
        "quant_proposal": {"symbol": "AAPL", "asset_class": "equity"},
        "execution_mode": "paper",
        "metadata": {},
        "messages": [],
    }

    with patch("yfinance.download", return_value=mock_df):
        with patch("src.graph.agents.l3.data_fetcher.fetch_news_sentiment",
                   return_value=mock_sentiment):
            with patch("src.graph.agents.l3.data_fetcher.fetch_economic_data",
                       return_value=mock_economic) as mock_econ:
                from src.tools.data_sources.yfinance_client import clear_cache
                clear_cache()
                from src.graph.agents.l3.data_fetcher import data_fetcher_node
                result = await data_fetcher_node(state)

    mock_econ.assert_called_once()
    assert "economic" in result["data_fetcher_result"]
    assert result["data_fetcher_result"]["economic"]["vix"] == 18.5
