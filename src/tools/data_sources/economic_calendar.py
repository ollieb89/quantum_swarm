"""
src.tools.data_sources.economic_calendar — Economic indicators via FRED.

Provides:
    fetch_economic_data() -> EconomicData
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional

from fredapi import Fred

from src.models.data_models import EconomicData

logger = logging.getLogger(__name__)

# In-memory cache to prevent duplicate API calls in one run
_economic_cache: Dict[str, EconomicData] = {}


def clear_cache():
    """Clear the in-memory economic data cache."""
    _economic_cache.clear()


async def fetch_economic_data() -> EconomicData:
    """Fetch key economic indicators from FRED or mock fallback.

    Args:

    Returns:
        EconomicData Pydantic model with VIX, DXY, and 10Y Yield.
    """
    cache_key = "global_economic_data"
    if cache_key in _economic_cache:
        logger.info("Cache hit for economic data")
        return _economic_cache[cache_key]

    fred_api_key = os.environ.get("FRED_API_KEY")
    now = datetime.now(tz=timezone.utc)

    if not fred_api_key:
        logger.warning("FRED_API_KEY not set; using mock economic data")
        economic = _get_mock_economic(now)
        _economic_cache[cache_key] = economic
        return economic

    logger.info("Fetching economic data via FRED")

    try:
        fred = Fred(api_key=fred_api_key)

        # Synchronous FRED calls; wrap in to_thread
        # VIXCLS = VIX Volatility Index
        # DTWEXBGS = USD Index (nominal Broad Dollar Index)
        # DGS10 = 10-Year Treasury Constant Maturity Rate
        
        vix = await asyncio.to_thread(fred.get_series, "VIXCLS")
        usd_index = await asyncio.to_thread(fred.get_series, "DTWEXBGS")
        yield_10y = await asyncio.to_thread(fred.get_series, "DGS10")

        # Get latest non-null values
        vix_val = float(vix.dropna().iloc[-1]) if not vix.dropna().empty else None
        usd_val = float(usd_index.dropna().iloc[-1]) if not usd_index.dropna().empty else None
        yield_val = float(yield_10y.dropna().iloc[-1]) if not yield_10y.dropna().empty else None

        economic = EconomicData(
            vix=vix_val,
            usd_index=usd_val,
            yield_10y=yield_val,
            next_event_name=None,  # Not directly from FRED
            next_event_date=None,
            timestamp=now,
            source="fred"
        )
        
        _economic_cache[cache_key] = economic
        return economic

    except Exception as e:
        logger.error("Error fetching economic data via FRED: %s; falling back to mock", e)
        economic = _get_mock_economic(now)
        _economic_cache[cache_key] = economic
        return economic


def _get_mock_economic(timestamp: datetime) -> EconomicData:
    """Return a mock EconomicData model."""
    return EconomicData(
        vix=18.5,
        usd_index=103.0,
        yield_10y=4.2,
        next_event_name="FOMC",
        next_event_date="2026-03-20",
        timestamp=timestamp,
        source="mock"
    )
