"""Phase 3 smoke tests — environment and import verification."""

import pytest
import pathlib
import yaml


def test_data_models_import():
    """Pydantic data models import without error."""
    from src.models.data_models import MarketData, SentimentData, FundamentalsData, TradeRecord, EconomicData
    assert MarketData
    assert TradeRecord
    assert SentimentData
    assert FundamentalsData
    assert EconomicData


def test_dexter_bridge_import():
    """Dexter bridge exports invoke_dexter and invoke_dexter_safe."""
    from src.tools.dexter_bridge import invoke_dexter, invoke_dexter_safe
    assert callable(invoke_dexter)
    assert callable(invoke_dexter_safe)


def test_yfinance_client_import():
    """yfinance client exports fetch_equity_data and clear_cache."""
    from src.tools.data_sources.yfinance_client import fetch_equity_data, clear_cache
    assert callable(fetch_equity_data)
    assert callable(clear_cache)


def test_ccxt_client_import():
    """ccxt client exports fetch_crypto_ohlcv and clear_cache."""
    from src.tools.data_sources.ccxt_client import fetch_crypto_ohlcv, clear_cache
    assert callable(fetch_crypto_ohlcv)
    assert callable(clear_cache)


def test_news_sentiment_import():
    """News sentiment exports fetch_news_sentiment."""
    from src.tools.data_sources.news_sentiment import fetch_news_sentiment
    assert callable(fetch_news_sentiment)


def test_economic_calendar_import():
    """Economic calendar exports fetch_economic_data."""
    from src.tools.data_sources.economic_calendar import fetch_economic_data
    assert callable(fetch_economic_data)


def test_data_fetcher_node_import():
    """data_fetcher_node is importable from src.graph.agents.l3.data_fetcher."""
    from src.graph.agents.l3.data_fetcher import data_fetcher_node
    assert callable(data_fetcher_node)


def test_swarm_config_has_execution_mode():
    """config/swarm_config.yaml contains the trading.execution_mode key."""
    config_path = pathlib.Path(__file__).parent.parent / "config" / "swarm_config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    assert "trading" in config
    assert "execution_mode" in config["trading"]
    assert config["trading"]["execution_mode"] in ("paper", "live")
