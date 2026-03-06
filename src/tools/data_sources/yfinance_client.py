"""
src.tools.data_sources.yfinance_client — Yahoo Finance async equity data client.

Provides:
    fetch_equity_data(symbol, period) -> MarketData   (async, asyncio.to_thread)
    clear_cache()                                      — reset in-memory cache

Pattern:
    - yfinance.download is synchronous; wrapped in asyncio.to_thread to avoid
      blocking the LangGraph event loop (Pattern 1 from Phase 3 RESEARCH.md).
    - In-memory cache keyed on (symbol, period) prevents duplicate API calls
      within a swarm run (CONTEXT.md decision).
    - Column names normalised to lowercase before access (Pitfall 3 from RESEARCH.md).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import yfinance as yf

from src.models.data_models import MarketData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------

_data_cache: dict[tuple[str, str], MarketData] = {}


def clear_cache() -> None:
    """Clear the in-memory yfinance cache. Call at the start of each swarm run."""
    _data_cache.clear()
    logger.debug("yfinance cache cleared")


# ---------------------------------------------------------------------------
# Synchronous helper (runs in thread pool)
# ---------------------------------------------------------------------------


def _download_equity(symbol: str, period: str) -> MarketData:
    """Synchronous yfinance download and MarketData construction.

    Called via asyncio.to_thread — must not use async primitives.
    """
    # Fetch OHLCV data
    df = yf.download(symbol, period=period, interval="1d", auto_adjust=True, progress=False)

    if df.empty:
        raise ValueError(f"yfinance returned empty DataFrame for symbol: {symbol}")

    # Normalise column names to lowercase (Pitfall 3 from RESEARCH.md)
    # yfinance may return a MultiIndex with ticker in columns — flatten first
    if hasattr(df.columns, "levels"):
        # MultiIndex: flatten to single level using the first level (field names)
        df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]

    # Use the most recent row
    latest = df.iloc[-1]
    ts = df.index[-1]

    # Convert index timestamp to timezone-aware datetime
    if hasattr(ts, "to_pydatetime"):
        ts_dt = ts.to_pydatetime()
        if ts_dt.tzinfo is None:
            ts_dt = ts_dt.replace(tzinfo=timezone.utc)
    else:
        ts_dt = datetime.now(tz=timezone.utc)

    return MarketData(
        symbol=symbol,
        price=float(latest.get("close", latest.get("adj close", 0.0))),
        volume=float(latest.get("volume", 0.0)),
        open=float(latest.get("open", 0.0)),
        high=float(latest.get("high", 0.0)),
        low=float(latest.get("low", 0.0)),
        close=float(latest.get("close", latest.get("adj close", 0.0))),
        timestamp=ts_dt,
        source="yfinance",
        interval="1d",
    )


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------


async def fetch_equity_data(symbol: str, period: str = "6mo") -> MarketData:
    """Fetch equity OHLCV data for *symbol* from Yahoo Finance.

    Results are cached in-memory by (symbol, period). Calling this function
    twice with the same arguments within a swarm run returns the cached result
    without making a second API call.

    Args:
        symbol: Ticker symbol, e.g. "AAPL", "MSFT".
        period:  yfinance period string, e.g. "6mo", "1y", "3mo".

    Returns:
        MarketData Pydantic model with source="yfinance".

    Raises:
        ValueError: If yfinance returns an empty DataFrame for the symbol.
    """
    cache_key = (symbol, period)

    if cache_key in _data_cache:
        logger.debug("yfinance cache hit for %s/%s", symbol, period)
        return _data_cache[cache_key]

    logger.info("Fetching yfinance data for %s (period=%s)", symbol, period)
    result = await asyncio.to_thread(_download_equity, symbol, period)

    _data_cache[cache_key] = result
    logger.debug("Cached yfinance result for %s/%s", symbol, period)
    return result
