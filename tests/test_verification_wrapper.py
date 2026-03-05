"""
Unit tests for src/tools/verification_wrapper.py

Tests:
  1. test_budget_enforcement: 6th call on a budget-5 tool raises ToolBudgetExceeded
  2. test_hypothesis_required: calling without hypothesis raises ValueError
  3. test_cache_hit: identical args call underlying tool only once (cache deduplicates)
"""

from __future__ import annotations

import pytest

# Clear the module-level ToolCache before each test to avoid cross-test pollution
from src.tools.verification_wrapper import BudgetedTool, ToolCache, ToolBudgetExceeded, budgeted


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the shared ToolCache before each test to prevent cross-test pollution."""
    ToolCache.clear()
    yield
    ToolCache.clear()


# ---------------------------------------------------------------------------
# Test 1: Budget enforcement
# ---------------------------------------------------------------------------


def test_budget_enforcement():
    """BudgetedTool raises ToolBudgetExceeded on the call after budget is exhausted."""
    call_counter = {"n": 0}

    def mock_tool(value: str) -> dict:
        call_counter["n"] += 1
        return {"result": value, "call": call_counter["n"]}

    # Give it an explicit tool name so cache keys are stable
    mock_tool.__name__ = "mock_tool_budget"

    bt = BudgetedTool(tool_fn=mock_tool, max_calls=5)

    # 5 calls with unique args so cache doesn't short-circuit counting
    for i in range(5):
        bt(value=f"unique_arg_{i}", hypothesis="test hypothesis")

    assert bt.call_count == 5, "Expected exactly 5 underlying calls"

    # 6th call should raise ToolBudgetExceeded
    with pytest.raises(ToolBudgetExceeded):
        bt(value="unique_arg_5", hypothesis="test hypothesis")


# ---------------------------------------------------------------------------
# Test 2: Hypothesis required
# ---------------------------------------------------------------------------


def test_hypothesis_required():
    """BudgetedTool raises ValueError when hypothesis kwarg is missing or empty."""
    call_counter = {"n": 0}

    def mock_tool_h(value: str) -> dict:
        call_counter["n"] += 1
        return {"result": value}

    mock_tool_h.__name__ = "mock_tool_hypothesis"
    bt = BudgetedTool(tool_fn=mock_tool_h, max_calls=5)

    # Missing hypothesis entirely
    with pytest.raises(ValueError, match="hypothesis"):
        bt(value="some_value")

    # Empty string hypothesis
    with pytest.raises(ValueError, match="hypothesis"):
        bt(value="some_value", hypothesis="")

    # None hypothesis
    with pytest.raises(ValueError, match="hypothesis"):
        bt(value="some_value", hypothesis=None)

    # Underlying tool should not have been called
    assert call_counter["n"] == 0


# ---------------------------------------------------------------------------
# Test 3: Cache hit — identical calls only invoke underlying tool once
# ---------------------------------------------------------------------------


def test_cache_hit():
    """BudgetedTool serves repeated identical calls from cache, calling underlying tool once."""
    call_counter = {"n": 0}

    def mock_tool_cache(symbol: str, timeframe: str) -> dict:
        call_counter["n"] += 1
        return {"symbol": symbol, "timeframe": timeframe, "call": call_counter["n"]}

    mock_tool_cache.__name__ = "mock_tool_cache"
    bt = budgeted(mock_tool_cache, max_calls=5)

    # First call — cache miss, underlying tool invoked
    result1 = bt(symbol="BTC-USD", timeframe="1h", hypothesis="BTC is bullish")
    assert call_counter["n"] == 1, "Underlying tool should be called once on cache miss"
    assert result1["symbol"] == "BTC-USD"

    # Second call with identical args — cache hit, underlying tool NOT invoked again
    result2 = bt(symbol="BTC-USD", timeframe="1h", hypothesis="BTC is still bullish")
    assert call_counter["n"] == 1, "Underlying tool should NOT be called again on cache hit"

    # Results should be identical (same cached data)
    assert result1 == result2, "Cached result should equal original result"

    # Different args — cache miss again
    result3 = bt(symbol="ETH-USD", timeframe="1d", hypothesis="ETH is bullish")
    assert call_counter["n"] == 2, "Different args should bypass cache and call underlying tool"
    assert result3["symbol"] == "ETH-USD"
