"""Tests for yfinance retry logic and disk cache (Phase 25, Plan 01)."""

import asyncio
import json
import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestFetchWithRetry:
    """Verify exponential backoff retry on yfinance failures."""

    def test_retries_three_times_on_exception(self):
        """After 3 failures, exception should propagate."""
        import src.tools.data_sources.yfinance_client as mod

        mock_download = MagicMock(side_effect=RuntimeError("network error"))

        with patch.object(mod, "yf") as mock_yf, \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_yf.download = mock_download
            # Clear caches to avoid stale data
            mod.clear_cache()

            with pytest.raises(RuntimeError, match="network error"):
                asyncio.run(mod._fetch_with_retry("AAPL", "6mo"))

            assert mock_download.call_count == 3

    def test_retry_delays_are_exponential(self):
        """Delays should follow BASE_DELAY * 2^attempt pattern."""
        import src.tools.data_sources.yfinance_client as mod

        mock_download = MagicMock(side_effect=RuntimeError("fail"))
        sleep_delays = []

        async def capture_sleep(delay):
            sleep_delays.append(delay)

        with patch.object(mod, "yf") as mock_yf, \
             patch("asyncio.sleep", side_effect=capture_sleep):
            mock_yf.download = mock_download

            with pytest.raises(RuntimeError):
                asyncio.run(mod._fetch_with_retry("AAPL", "6mo"))

        # Should have 2 sleeps (after attempt 0 and 1; attempt 2 raises immediately)
        assert len(sleep_delays) == 2
        # First delay ~1s base, second ~2s base (plus jitter up to 0.5)
        assert 1.0 <= sleep_delays[0] <= 1.5
        assert 2.0 <= sleep_delays[1] <= 2.5

    def test_success_on_first_try_no_retry(self):
        """Successful download should not retry."""
        import pandas as pd
        import src.tools.data_sources.yfinance_client as mod

        df = pd.DataFrame({
            "open": [100.0], "high": [105.0], "low": [99.0],
            "close": [103.0], "volume": [1000000.0],
        }, index=pd.to_datetime(["2026-01-01"]))
        mock_download = MagicMock(return_value=df)

        with patch.object(mod, "yf") as mock_yf:
            mock_yf.download = mock_download
            result = asyncio.run(mod._fetch_with_retry("AAPL", "6mo"))

        assert not result.empty
        assert mock_download.call_count == 1


class TestDiskCache:
    """Verify disk cache write-always, read-only-with-QS_DEV_CACHE."""

    def test_successful_fetch_writes_disk_cache(self, tmp_path, monkeypatch):
        """Every successful fetch should write to data/cache/{symbol}.json."""
        import pandas as pd
        import src.tools.data_sources.yfinance_client as mod

        monkeypatch.setattr(mod, "CACHE_DIR", tmp_path)
        mod.clear_cache()

        df = pd.DataFrame({
            "open": [100.0], "high": [105.0], "low": [99.0],
            "close": [103.0], "volume": [1000000.0],
        }, index=pd.to_datetime(["2026-01-01"]))

        with patch.object(mod, "yf") as mock_yf, \
             patch("asyncio.sleep", new_callable=AsyncMock):
            mock_yf.download = MagicMock(return_value=df)
            asyncio.run(mod.fetch_equity_data("TEST", "6mo"))

        cache_file = tmp_path / "TEST.json"
        assert cache_file.exists()
        data = json.loads(cache_file.read_text())
        assert data["symbol"] == "TEST"
        assert "_cached_at" in data

    def test_disk_cache_read_with_dev_cache_env(self, tmp_path, monkeypatch):
        """With QS_DEV_CACHE=1, disk cache is read before hitting yfinance."""
        import src.tools.data_sources.yfinance_client as mod

        monkeypatch.setattr(mod, "CACHE_DIR", tmp_path)
        monkeypatch.setenv("QS_DEV_CACHE", "1")
        mod.clear_cache()

        # Write a valid cache file
        cache_data = {
            "symbol": "CACHED",
            "price": 150.0,
            "volume": 500000.0,
            "open": 148.0,
            "high": 152.0,
            "low": 147.0,
            "close": 150.0,
            "timestamp": "2026-01-01T00:00:00+00:00",
            "source": "yfinance",
            "interval": "1d",
            "_cached_at": time.time(),  # Fresh
        }
        cache_file = tmp_path / "CACHED.json"
        cache_file.write_text(json.dumps(cache_data))

        mock_download = MagicMock()
        with patch.object(mod, "yf") as mock_yf:
            mock_yf.download = mock_download
            result = asyncio.run(mod.fetch_equity_data("CACHED", "6mo"))

        # yfinance should NOT have been called
        mock_download.assert_not_called()
        assert result.symbol == "CACHED"
        assert result.price == 150.0

    def test_disk_cache_not_read_without_dev_cache_env(self, tmp_path, monkeypatch):
        """Without QS_DEV_CACHE=1, disk cache is written but never read."""
        import pandas as pd
        import src.tools.data_sources.yfinance_client as mod

        monkeypatch.setattr(mod, "CACHE_DIR", tmp_path)
        monkeypatch.delenv("QS_DEV_CACHE", raising=False)
        mod.clear_cache()

        # Write a cache file that would be used if cache reading was active
        cache_data = {
            "symbol": "NOCACHE",
            "price": 999.0,
            "volume": 1.0,
            "open": 999.0,
            "high": 999.0,
            "low": 999.0,
            "close": 999.0,
            "timestamp": "2026-01-01T00:00:00+00:00",
            "source": "yfinance",
            "interval": "1d",
            "_cached_at": time.time(),
        }
        cache_file = tmp_path / "NOCACHE.json"
        cache_file.write_text(json.dumps(cache_data))

        df = pd.DataFrame({
            "open": [100.0], "high": [105.0], "low": [99.0],
            "close": [103.0], "volume": [1000000.0],
        }, index=pd.to_datetime(["2026-01-01"]))

        with patch.object(mod, "yf") as mock_yf, \
             patch("asyncio.sleep", new_callable=AsyncMock):
            mock_yf.download = MagicMock(return_value=df)
            result = asyncio.run(mod.fetch_equity_data("NOCACHE", "6mo"))

        # Should have fetched from yfinance, not cache
        assert result.price == 103.0  # from df, not 999.0 from cache

    def test_expired_disk_cache_ignored(self, tmp_path, monkeypatch):
        """Expired TTL disk cache should be ignored even with QS_DEV_CACHE=1."""
        import pandas as pd
        import src.tools.data_sources.yfinance_client as mod

        monkeypatch.setattr(mod, "CACHE_DIR", tmp_path)
        monkeypatch.setenv("QS_DEV_CACHE", "1")
        mod.clear_cache()

        # Write a cache file with old _cached_at
        cache_data = {
            "symbol": "EXPIRED",
            "price": 999.0,
            "volume": 1.0,
            "open": 999.0,
            "high": 999.0,
            "low": 999.0,
            "close": 999.0,
            "timestamp": "2026-01-01T00:00:00+00:00",
            "source": "yfinance",
            "interval": "1d",
            "_cached_at": time.time() - 7200,  # 2 hours old (TTL is 1 hour)
        }
        cache_file = tmp_path / "EXPIRED.json"
        cache_file.write_text(json.dumps(cache_data))

        df = pd.DataFrame({
            "open": [100.0], "high": [105.0], "low": [99.0],
            "close": [103.0], "volume": [1000000.0],
        }, index=pd.to_datetime(["2026-01-01"]))

        with patch.object(mod, "yf") as mock_yf, \
             patch("asyncio.sleep", new_callable=AsyncMock):
            mock_yf.download = MagicMock(return_value=df)
            result = asyncio.run(mod.fetch_equity_data("EXPIRED", "6mo"))

        # Should have fetched from yfinance because cache is expired
        assert result.price == 103.0
