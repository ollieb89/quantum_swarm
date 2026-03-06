"""Backtester node unit tests — Plan 03-02.

Tests cover:
    test_backtester_node_returns_sharpe         — node returns dict with sharpe_ratio key
    test_bar_data_wrangler_processes_dataframe  — BarDataWrangler processes lowercased DataFrame
    test_backtester_result_is_json_serializable — returned dict is JSON-serializable
    test_asyncio_to_thread_used                 — asyncio.to_thread is called (not engine.run directly)
    test_backtester_fallback                    — node returns fallback dict with fallback=True on engine error
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Test 1: backtester_node returns a dict with sharpe_ratio key
# ---------------------------------------------------------------------------

def test_backtester_node_returns_sharpe():
    """backtester_node returns dict with backtest_result containing sharpe_ratio."""
    from src.graph.agents.l3.backtester import backtester_node

    mock_result = {
        "sharpe_ratio": 1.5,
        "total_return": 0.12,
        "max_drawdown": -0.05,
        "total_trades": 10,
        "win_rate": 0.6,
        "period_days": 180,
    }

    state = {
        "quant_proposal": {"symbol": "AAPL", "strategy": {"type": "momentum"}},
        "data_fetcher_result": {},
        "messages": [],
    }

    with patch(
        "src.graph.agents.l3.backtester.asyncio.to_thread",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        result = asyncio.run(backtester_node(state))

    assert "backtest_result" in result
    assert result["backtest_result"]["sharpe_ratio"] == 1.5
    assert "messages" in result
    assert len(result["messages"]) >= 1


# ---------------------------------------------------------------------------
# Test 2: BarDataWrangler processes a yfinance-style DataFrame after lowercasing
# ---------------------------------------------------------------------------

def test_bar_data_wrangler_processes_dataframe():
    """BarDataWrangler.process(df) returns non-empty bar list after column lowercasing."""
    import numpy as np
    from nautilus_trader.model import BarType
    from nautilus_trader.model.currencies import USD
    from nautilus_trader.model.data import BarSpecification
    from nautilus_trader.model.enums import BarAggregation, PriceType
    from nautilus_trader.model.identifiers import InstrumentId, Symbol
    from nautilus_trader.model.instruments import Equity
    from nautilus_trader.model.objects import Price, Quantity
    from nautilus_trader.persistence.wranglers import BarDataWrangler

    # Build a 10-row yfinance-style DataFrame with UPPERCASE columns (raw yfinance output)
    dates = pd.date_range("2024-01-01", periods=10, freq="B", tz="UTC")
    df = pd.DataFrame(
        {
            "Open": [150.0 + i for i in range(10)],
            "High": [155.0 + i for i in range(10)],
            "Low": [148.0 + i for i in range(10)],
            "Close": [152.0 + i for i in range(10)],
            "Volume": [1_000_000 + i * 10_000 for i in range(10)],
        },
        index=dates,
    )

    # CRITICAL: lowercase before BarDataWrangler (Pitfall 3 from RESEARCH.md)
    df.columns = [c.lower() for c in df.columns]

    # Build instrument using NT 1.223.0 API (raw_symbol, ts_event, ts_init required)
    symbol = "AAPL"
    venue_name = "SIM"
    instrument = Equity(
        instrument_id=InstrumentId.from_str(f"{symbol}.{venue_name}"),
        raw_symbol=Symbol(symbol),
        currency=USD,
        price_precision=2,
        price_increment=Price(0.01, 2),
        lot_size=Quantity(1, 0),
        ts_event=0,
        ts_init=0,
    )
    bar_type = BarType(
        instrument_id=instrument.id,
        bar_spec=BarSpecification(1, BarAggregation.DAY, PriceType.LAST),
    )
    wrangler = BarDataWrangler(bar_type=bar_type, instrument=instrument)
    bars = wrangler.process(df)

    assert len(bars) > 0, "BarDataWrangler should produce non-empty bar list from 10-row DataFrame"


# ---------------------------------------------------------------------------
# Test 3: The returned backtest_result is JSON-serializable
# ---------------------------------------------------------------------------

def test_backtester_result_is_json_serializable():
    """backtest_result dict is JSON-serializable (no NautilusTrader internal objects)."""
    from src.graph.agents.l3.backtester import backtester_node

    mock_result = {
        "sharpe_ratio": 1.2,
        "total_return": 0.08,
        "max_drawdown": -0.03,
        "total_trades": 5,
        "win_rate": 0.6,
        "period_days": 90,
    }

    state = {
        "quant_proposal": {"symbol": "TSLA", "strategy": {}},
        "data_fetcher_result": {},
        "messages": [],
    }

    with patch(
        "src.graph.agents.l3.backtester.asyncio.to_thread",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        result = asyncio.run(backtester_node(state))

    # Must not raise TypeError
    serialized = json.dumps(result["backtest_result"])
    assert serialized  # non-empty JSON string


# ---------------------------------------------------------------------------
# Test 4: asyncio.to_thread is called (engine.run not called directly)
# ---------------------------------------------------------------------------

def test_asyncio_to_thread_used():
    """asyncio.to_thread is called when backtester_node is invoked."""
    from src.graph.agents.l3.backtester import backtester_node

    state = {
        "quant_proposal": {"symbol": "AAPL", "strategy": {}},
        "data_fetcher_result": {},
        "messages": [],
    }

    mock_result = {
        "sharpe_ratio": 0.5,
        "total_return": 0.02,
        "max_drawdown": -0.01,
        "total_trades": 3,
        "win_rate": 0.33,
        "period_days": 180,
    }

    call_recorder = []

    async def mock_to_thread(fn, *args, **kwargs):
        call_recorder.append({"fn": fn, "args": args})
        return mock_result

    with patch("src.graph.agents.l3.backtester.asyncio.to_thread", side_effect=mock_to_thread):
        asyncio.run(backtester_node(state))

    assert len(call_recorder) == 1, "asyncio.to_thread should have been called exactly once"
    # The function passed to to_thread should be the synchronous worker
    recorded_fn = call_recorder[0]["fn"]
    assert callable(recorded_fn), "asyncio.to_thread should be called with a callable"


# ---------------------------------------------------------------------------
# Test 5: Fallback path — when _run_nautilus_backtest raises, node returns fallback dict
# ---------------------------------------------------------------------------

def test_backtester_fallback():
    """When _run_nautilus_backtest raises, backtester_node returns fallback dict with fallback=True."""
    from src.graph.agents.l3.backtester import backtester_node

    state = {
        "quant_proposal": {"symbol": "FAIL", "strategy": {}},
        "data_fetcher_result": {},
        "messages": [],
    }

    async def raise_on_thread(fn, *args, **kwargs):
        raise RuntimeError("NautilusTrader engine exploded")

    with patch("src.graph.agents.l3.backtester.asyncio.to_thread", side_effect=raise_on_thread):
        result = asyncio.run(backtester_node(state))

    assert "backtest_result" in result
    bt = result["backtest_result"]
    assert bt.get("fallback") is True, "Fallback dict must have fallback=True"
    assert "error" in bt, "Fallback dict must include error message"
    assert bt["sharpe_ratio"] == 0.0
    assert bt["total_return"] == 0.0
    assert bt["max_drawdown"] == 0.0
    assert bt["total_trades"] == 0
    # Ensure the fallback is still JSON-serializable
    json.dumps(bt)  # must not raise
