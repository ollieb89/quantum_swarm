"""
src.tools.data_sources.ccxt_client — ccxt async crypto OHLCV data client.

Provides:
    fetch_crypto_ohlcv(symbol, exchange_id, timeframe, limit) -> MarketData
    clear_cache()

Pattern:
    - Uses ccxt.async_support for non-blocking exchange calls.
    - In-memory cache keyed on (symbol, exchange_id, timeframe).
    - Maps the last OHLCV bar to MarketData fields.
    - Exchange session is explicitly closed after each fetch (resource cleanup).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import ccxt.async_support as ccxt  # type: ignore[import-untyped]

from src.models.data_models import MarketData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------

_data_cache: dict[tuple[str, str, str], MarketData] = {}


def clear_cache() -> None:
    """Clear the in-memory ccxt cache. Call at the start of each swarm run."""
    _data_cache.clear()
    logger.debug("ccxt cache cleared")


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------


async def fetch_crypto_ohlcv(
    symbol: str,
    exchange_id: str = "binance",
    timeframe: str = "1h",
    limit: int = 100,
) -> MarketData:
    """Fetch OHLCV bars for a crypto symbol from a ccxt-supported exchange.

    Results are cached in-memory by (symbol, exchange_id, timeframe). Calling
    this function twice with the same arguments returns the cached result.

    ccxt OHLCV bar format: [timestamp_ms, open, high, low, close, volume]

    Args:
        symbol:      Market symbol, e.g. "BTC/USDT", "ETH/USDT".
        exchange_id: ccxt exchange id, e.g. "binance", "bybit".
        timeframe:   Candlestick timeframe, e.g. "1h", "1d".
        limit:       Maximum number of bars to fetch.

    Returns:
        MarketData Pydantic model built from the most recent OHLCV bar,
        with source="ccxt".

    Raises:
        ValueError: If the exchange returns no OHLCV data.
        RuntimeError: If the exchange_id is not supported by ccxt.
    """
    cache_key = (symbol, exchange_id, timeframe)

    if cache_key in _data_cache:
        logger.debug("ccxt cache hit for %s/%s/%s", symbol, exchange_id, timeframe)
        return _data_cache[cache_key]

    # Instantiate the exchange — ccxt.async_support exposes exchanges as classes
    exchange_class = getattr(ccxt, exchange_id, None)
    if exchange_class is None:
        raise RuntimeError(f"ccxt does not support exchange: {exchange_id}")

    exchange = exchange_class()

    try:
        logger.info(
            "Fetching ccxt OHLCV for %s from %s (timeframe=%s, limit=%d)",
            symbol, exchange_id, timeframe, limit,
        )
        bars = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    finally:
        await exchange.close()

    if not bars:
        raise ValueError(
            f"ccxt returned no OHLCV data for {symbol} on {exchange_id}/{timeframe}"
        )

    # Use the most recent (last) OHLCV bar
    # Format: [timestamp_ms, open, high, low, close, volume]
    ts_ms, open_, high, low, close, volume = bars[-1]

    ts_dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)

    result = MarketData(
        symbol=symbol,
        price=float(close),
        volume=float(volume),
        open=float(open_),
        high=float(high),
        low=float(low),
        close=float(close),
        timestamp=ts_dt,
        source="ccxt",
        interval=timeframe,
    )

    _data_cache[cache_key] = result
    logger.debug("Cached ccxt result for %s/%s/%s", symbol, exchange_id, timeframe)
    return result
