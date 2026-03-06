"""
src.tools.data_sources.yfinance_client — Equity market data via yfinance.

Provides:
    fetch_equity_data(symbol, period) -> MarketData
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Tuple

import pandas as pd
import yfinance as yf

from src.models.data_models import MarketData

logger = logging.getLogger(__name__)

# In-memory cache to prevent duplicate API calls in one run
_data_cache: Dict[Tuple[str, str], MarketData] = {}


def clear_cache():
    """Clear the in-memory market data cache."""
    _data_cache.clear()


async def fetch_equity_data(symbol: str, period: str = "6mo") -> MarketData:
    """Fetch equity OHLCV data from yfinance.

    Args:
        symbol: Ticker symbol (e.g., 'AAPL').
        period: Data period (e.g., '1mo', '6mo', '1y').

    Returns:
        MarketData Pydantic model with the latest bar.
    """
    cache_key = (symbol, period)
    if cache_key in _data_cache:
        logger.info("Cache hit for equity data: %s", symbol)
        return _data_cache[cache_key]

    logger.info("Fetching equity data for %s (%s)", symbol, period)

    # yfinance is synchronous; wrap in to_thread
    try:
        df = await asyncio.to_thread(yf.download, tickers=symbol, period=period, interval="1d", progress=False)
    except Exception as e:
        logger.error("Error downloading yfinance data for %s: %s", symbol, e)
        raise

    if df.empty:
        raise ValueError(f"No data returned from yfinance for {symbol}")

    # Normalize columns to lowercase (Pitfall 3)
    df.columns = [str(c).lower() for c in df.columns]

    # Handle multi-index columns if present (sometimes happens with yfinance)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    latest = df.iloc[-1]
    
    # Use index (timestamp) if available, otherwise now
    ts = df.index[-1]
    if hasattr(ts, "to_pydatetime"):
        timestamp = ts.to_pydatetime()
    else:
        timestamp = datetime.now(tz=timezone.utc)
    
    # Ensure timezone awareness
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    market_data = MarketData(
        symbol=symbol,
        price=float(latest["close"]),
        volume=float(latest["volume"]),
        open=float(latest["open"]),
        high=float(latest["high"]),
        low=float(latest["low"]),
        close=float(latest["close"]),
        timestamp=timestamp,
        source="yfinance",
        interval="1d"
    )

    _data_cache[cache_key] = market_data
    return market_data
