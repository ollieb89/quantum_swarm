"""
tests/test_dexter_bridge.py — Unit tests for the Dexter CLI async bridge.

Tests converted from xfail stubs to real assertions after 03-01 implementation.
"""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Test 1: invoke_dexter returns STDOUT markdown on success
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dexter_success():
    """Mocked subprocess returns Markdown string."""
    expected_output = "# Report\nBullish"

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(
        return_value=(expected_output.encode(), b"")
    )

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch.dict(os.environ, {
            "FINANCIAL_DATASETS_API_KEY": "test-key",
            "EXASEARCH_API_KEY": "test-key",
            "ANTHROPIC_API_KEY": "test-key",
        }):
            from src.tools.dexter_bridge import invoke_dexter
            result = await invoke_dexter("test query")

    assert result == expected_output


# ---------------------------------------------------------------------------
# Test 2: invoke_dexter raises TimeoutError when proc takes too long
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dexter_timeout():
    """asyncio.wait_for raises TimeoutError after 90s (mocked)."""
    mock_proc = AsyncMock()
    mock_proc.returncode = None
    mock_proc.kill = MagicMock()

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with patch.dict(os.environ, {
            "FINANCIAL_DATASETS_API_KEY": "test-key",
            "EXASEARCH_API_KEY": "test-key",
            "ANTHROPIC_API_KEY": "test-key",
        }):
            with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
                from src.tools.dexter_bridge import invoke_dexter
                with pytest.raises(TimeoutError):
                    await invoke_dexter("slow query")


# ---------------------------------------------------------------------------
# Test 3: invoke_dexter_safe returns FundamentalsData when env vars are absent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dexter_missing_env_vars():
    """Returns graceful FundamentalsData with unavailable message when env vars missing."""
    env_without_keys = {
        k: v for k, v in os.environ.items()
        if k not in ("FINANCIAL_DATASETS_API_KEY", "EXASEARCH_API_KEY", "ANTHROPIC_API_KEY")
    }

    with patch.dict(os.environ, env_without_keys, clear=True):
        from src.tools.dexter_bridge import invoke_dexter_safe
        result = await invoke_dexter_safe(
            "fundamental analysis of AAPL", "AAPL"
        )

    assert result.symbol == "AAPL"
    assert "unavailable" in result.raw_markdown.lower()
    assert result.source == "dexter"
