"""
src.tools.data_sources.economic_calendar — FRED economic data client (async).

Provides:
    fetch_economic_data() -> EconomicData

Primary path:
    - Uses the fredapi library with FRED_API_KEY env var to fetch:
        VIXCLS  — CBOE Volatility Index (VIX)
        DXY     — US Dollar Index (USD index)
        DGS10   — 10-Year Treasury Constant Maturity Rate
    - fredapi is synchronous; wrapped in asyncio.to_thread.

Fallback:
    - If FRED_API_KEY is not set OR if any fredapi call fails, returns a mock
      EconomicData with source="mock" and None values for all indicators.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

from src.models.data_models import EconomicData

logger = logging.getLogger(__name__)

# FRED series IDs
_VIX_SERIES = "VIXCLS"
_USD_SERIES = "DTWEXBGS"   # Broad US Dollar Index (DXY-equivalent; FRED standard)
_YIELD_SERIES = "DGS10"    # 10-Year Treasury Constant Maturity Rate


def _mock_economic() -> EconomicData:
    """Return a zeroed-out mock EconomicData when FRED is unavailable."""
    return EconomicData(
        vix=None,
        usd_index=None,
        yield_10y=None,
        next_event_name=None,
        next_event_date=None,
        timestamp=datetime.now(tz=timezone.utc),
        source="mock",
    )


def _fetch_fred_data_sync(api_key: str) -> EconomicData:
    """Synchronous FRED data fetch — called via asyncio.to_thread.

    Fetches the most recent observation for VIX, USD index, and 10Y yield.
    Handles missing series data gracefully.
    """
    try:
        import fredapi  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("fredapi not installed — falling back to mock economic data")
        return _mock_economic()

    fred = fredapi.Fred(api_key=api_key)

    def _get_latest(series_id: str) -> float | None:
        """Return the most recent non-null float value for a FRED series."""
        try:
            series = fred.get_series(series_id)
            # Drop NaN values and return the last one
            valid = series.dropna()
            if valid.empty:
                return None
            return float(valid.iloc[-1])
        except Exception as exc:  # noqa: BLE001
            logger.debug("FRED series %s fetch failed: %s", series_id, exc)
            return None

    vix = _get_latest(_VIX_SERIES)
    usd_index = _get_latest(_USD_SERIES)
    yield_10y = _get_latest(_YIELD_SERIES)

    return EconomicData(
        vix=vix,
        usd_index=usd_index,
        yield_10y=yield_10y,
        next_event_name=None,   # FRED does not provide forward event calendar
        next_event_date=None,
        timestamp=datetime.now(tz=timezone.utc),
        source="fred",
    )


async def fetch_economic_data() -> EconomicData:
    """Fetch macro-economic snapshot from FRED.

    Degrades gracefully to mock if FRED_API_KEY is absent or any request fails.

    Returns:
        EconomicData Pydantic model with VIX, USD index, and 10Y yield.
    """
    api_key = os.environ.get("FRED_API_KEY", "")

    if not api_key:
        logger.debug("FRED_API_KEY not set — using mock economic data")
        return _mock_economic()

    try:
        result = await asyncio.to_thread(_fetch_fred_data_sync, api_key)
        return result
    except Exception as exc:  # noqa: BLE001
        logger.warning("FRED data fetch failed: %s — falling back to mock", exc)
        return _mock_economic()
