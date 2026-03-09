"""
src.tools.data_sources.yfinance_client -- Equity market data via yfinance.

Provides:
    fetch_equity_data(symbol, period) -> MarketData

Retry: 3 attempts with exponential backoff (1s, 2s base + jitter).
Disk cache: Always writes on successful fetch. Reads only when QS_DEV_CACHE=1.
"""

import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
import yfinance as yf

from src.models.data_models import MarketData

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 1.0

# Disk cache configuration
CACHE_DIR = Path("data/cache")
CACHE_TTL_SECONDS = 3600  # 1 hour

# In-memory cache to prevent duplicate API calls in one run
_data_cache: Dict[Tuple[str, str], MarketData] = {}


def clear_cache():
    """Clear the in-memory market data cache."""
    _data_cache.clear()


async def _fetch_with_retry(symbol: str, period: str) -> pd.DataFrame:
    """Fetch yfinance data with exponential backoff retry.

    Args:
        symbol: Ticker symbol.
        period: Data period string.

    Returns:
        DataFrame with OHLCV data.

    Raises:
        Last exception after MAX_RETRIES attempts.
    """
    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            df = await asyncio.to_thread(
                yf.download, tickers=symbol, period=period,
                interval="1d", progress=False,
            )
            return df
        except Exception as e:
            last_exc = e
            logger.warning(
                "yfinance attempt %d/%d failed for %s: %s",
                attempt + 1, MAX_RETRIES, symbol, e,
            )
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt) + random.uniform(0, 0.5)
                await asyncio.sleep(delay)

    raise last_exc  # type: ignore[misc]


def _read_disk_cache(symbol: str) -> Optional[MarketData]:
    """Read cached MarketData from disk if QS_DEV_CACHE=1 and TTL is valid.

    Returns None if:
        - QS_DEV_CACHE is not "1"
        - Cache file does not exist
        - Cache TTL has expired
    """
    if os.environ.get("QS_DEV_CACHE") != "1":
        return None

    cache_file = CACHE_DIR / f"{symbol}.json"
    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Disk cache read failed for %s: %s", symbol, e)
        return None

    cached_at = data.get("_cached_at", 0)
    if time.time() - cached_at > CACHE_TTL_SECONDS:
        logger.info("Disk cache expired for %s", symbol)
        return None

    # Strip internal field before constructing MarketData
    data.pop("_cached_at", None)
    try:
        return MarketData(**data)
    except Exception as e:
        logger.warning("Disk cache parse failed for %s: %s", symbol, e)
        return None


def _write_disk_cache(symbol: str, market_data: MarketData) -> None:
    """Write MarketData to disk cache with _cached_at timestamp."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{symbol}.json"
        data = market_data.model_dump(mode="json")
        data["_cached_at"] = time.time()
        cache_file.write_text(json.dumps(data))
    except OSError as e:
        logger.warning("Disk cache write failed for %s: %s", symbol, e)


async def fetch_equity_data(symbol: str, period: str = "6mo") -> MarketData:
    """Fetch equity OHLCV data from yfinance.

    Checks in-memory cache, then disk cache (if QS_DEV_CACHE=1), then fetches
    from yfinance with retry. Writes disk cache on every successful fetch.

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

    # Check disk cache (only reads when QS_DEV_CACHE=1)
    cached = _read_disk_cache(symbol)
    if cached is not None:
        logger.info("Disk cache hit for %s", symbol)
        _data_cache[cache_key] = cached
        return cached

    logger.info("Fetching equity data for %s (%s)", symbol, period)

    df = await _fetch_with_retry(symbol, period)

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
    _write_disk_cache(symbol, market_data)
    return market_data
