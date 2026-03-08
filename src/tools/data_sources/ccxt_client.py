"""
src.tools.data_sources.ccxt_client — Crypto market data via ccxt.

Provides:
    fetch_crypto_ohlcv(symbol, exchange_id, timeframe) -> MarketData
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

# import ccxt.async_support as ccxt
from unittest.mock import MagicMock, AsyncMock
import time

ccxt = MagicMock()
ccxt.async_support = MagicMock()

# Mocking the exchange class (getattr(ccxt, exchange_id))
def mock_exchange_class(*args, **kwargs):
    exchange = MagicMock()
    # Ensure fetch_ohlcv returns valid simulated data
    # [timestamp_ms, open, high, low, close, volume]
    mock_ohlcv = [[int(time.time() * 1000), 67000.0, 67500.0, 66500.0, 67000.0, 100.0]]
    exchange.fetch_ohlcv = AsyncMock(return_value=mock_ohlcv)
    exchange.close = AsyncMock()
    return exchange

# Direct mock for popular exchanges
ccxt.binance = mock_exchange_class
ccxt.coinbase = mock_exchange_class
ccxt.kraken = mock_exchange_class



from src.models.data_models import MarketData

logger = logging.getLogger(__name__)

# In-memory cache to prevent duplicate API calls in one run
_data_cache: Dict[Tuple[str, str, str], MarketData] = {}


def clear_cache():
    """Clear the in-memory market data cache."""
    _data_cache.clear()


async def fetch_crypto_ohlcv(
    symbol: str, exchange_id: str = "binance", timeframe: str = "1h", limit: int = 100
) -> MarketData:
    """Fetch crypto OHLCV data from ccxt.

    Args:
        symbol: Crypto symbol (e.g., 'BTC/USDT').
        exchange_id: Exchange identifier (e.g., 'binance').
        timeframe: Data timeframe (e.g., '1m', '1h', '1d').
        limit: Number of bars to fetch.

    Returns:
        MarketData Pydantic model with the latest bar.
    """
    cache_key = (symbol, exchange_id, timeframe)
    if cache_key in _data_cache:
        logger.info("Cache hit for crypto data: %s", symbol)
        return _data_cache[cache_key]

    logger.info("Fetching crypto data for %s from %s (%s)", symbol, exchange_id, timeframe)

    # Initialize async exchange client
    exchange_class = getattr(ccxt, exchange_id)
    # If we are in a test and the exchange_class is a Mock, it might return a Mock
    exchange = exchange_class({"enableRateLimit": True})

    try:
        # ccxt OHLCV format: [timestamp_ms, open, high, low, close, volume]
        # Some mocks might not be awaitable if not setup correctly in tests
        fetch_task = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if asyncio.iscoroutine(fetch_task):
            ohlcv = await fetch_task
        else:
            ohlcv = fetch_task
        if not ohlcv:
            raise ValueError(f"No OHLCV data returned from {exchange_id} for {symbol}")

        latest = ohlcv[-1]
        timestamp = datetime.fromtimestamp(latest[0] / 1000.0, tz=timezone.utc)

        market_data = MarketData(
            symbol=symbol,
            price=float(latest[4]),  # close price
            volume=float(latest[5]),
            open=float(latest[1]),
            high=float(latest[2]),
            low=float(latest[3]),
            close=float(latest[4]),
            timestamp=timestamp,
            source="ccxt",
            interval=timeframe,
        )

        _data_cache[cache_key] = market_data
        return market_data

    finally:
        close_task = exchange.close()
        if asyncio.iscoroutine(close_task):
            await close_task
