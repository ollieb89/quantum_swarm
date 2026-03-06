"""
Tests for the three memory write nodes.

Each node is tested in isolation: verify it calls memory.store() with the
correct source and required metadata, and that it never raises on store failure.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.graph.nodes.write_external_memory import write_external_memory_node
from src.graph.nodes.write_research_memory import write_research_memory_node
from src.graph.nodes.write_trade_memory import write_trade_memory_node
from src.memory.service import MemorySource


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mock_memory(return_value="doc_id_123"):
    mem = MagicMock()
    mem.store.return_value = return_value
    return mem


def _base_state(**kwargs) -> dict:
    base = {
        "task_id": "test_run_001",
        "user_input": "Analyze NVDA",
        "intent": "trade",
        "messages": [],
        "macro_report": None,
        "quant_proposal": {"symbol": "NVDA", "signal": "BUY"},
        "bullish_thesis": None,
        "bearish_thesis": None,
        "debate_resolution": None,
        "weighted_consensus_score": None,
        "debate_history": [],
        "risk_approval": None,
        "consensus_score": 0.0,
        "compliance_flags": [],
        "risk_approved": None,
        "risk_notes": None,
        "final_decision": None,
        "metadata": {},
        "blackboard_session": "test_run_001",
        "total_tokens": 0,
        "trade_history": [],
        "execution_mode": "paper",
        "data_fetcher_result": None,
        "knowledge_base_result": None,
        "backtest_result": None,
        "execution_result": None,
    }
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# write_trade_memory_node tests
# ---------------------------------------------------------------------------


class TestWriteTradeMemoryNode:
    def test_calls_store_with_trade_source(self):
        memory = _mock_memory()
        state = _base_state(
            execution_result={
                "symbol": "NVDA",
                "direction": "LONG",
                "fill_price": 850.0,
                "status": "filled",
            },
            weighted_consensus_score=0.78,
        )
        write_trade_memory_node(state, memory)
        memory.store.assert_called_once()
        call_kwargs = memory.store.call_args.kwargs
        assert call_kwargs["source"] == MemorySource.TRADE
        assert call_kwargs["node"] == "write_trade_memory"

    def test_store_metadata_contains_required_fields(self):
        memory = _mock_memory()
        state = _base_state(
            execution_result={
                "symbol": "AAPL",
                "direction": "SHORT",
                "fill_price": 175.0,
                "status": "filled",
            }
        )
        write_trade_memory_node(state, memory)
        meta = memory.store.call_args.kwargs["metadata"]
        assert "symbol" in meta
        assert "timestamp" in meta
        assert "run_id" in meta
        assert meta["run_id"] == "test_run_001"

    def test_does_not_store_when_execution_result_is_none(self):
        memory = _mock_memory()
        state = _base_state(execution_result=None)
        write_trade_memory_node(state, memory)
        memory.store.assert_not_called()

    def test_does_not_raise_on_store_failure(self):
        memory = _mock_memory()
        memory.store.side_effect = RuntimeError("chroma unavailable")
        state = _base_state(
            execution_result={"symbol": "NVDA", "direction": "LONG", "status": "filled"}
        )
        # Should not raise — failure is caught and logged
        result = write_trade_memory_node(state, memory)
        assert result == {}  # no state changes; write is a side effect only


# ---------------------------------------------------------------------------
# write_research_memory_node tests
# ---------------------------------------------------------------------------


class TestWriteResearchMemoryNode:
    def test_calls_store_with_research_source(self):
        memory = _mock_memory()
        state = _base_state(
            debate_resolution={
                "decision": "BUY",
                "rationale": "Strong bullish thesis prevailed.",
                "symbol": "NVDA",
            },
            bullish_thesis={"summary": "Earnings beat expected"},
            bearish_thesis={"summary": "Macro headwinds"},
            weighted_consensus_score=0.72,
        )
        write_research_memory_node(state, memory)
        memory.store.assert_called_once()
        call_kwargs = memory.store.call_args.kwargs
        assert call_kwargs["source"] == MemorySource.RESEARCH
        assert call_kwargs["node"] == "write_research_memory"

    def test_store_metadata_contains_required_fields(self):
        memory = _mock_memory()
        state = _base_state(
            debate_resolution={"decision": "HOLD", "symbol": "TSLA"},
        )
        write_research_memory_node(state, memory)
        meta = memory.store.call_args.kwargs["metadata"]
        assert "symbol" in meta
        assert "timestamp" in meta
        assert "run_id" in meta
        assert "agent" in meta
        assert meta["agent"] == "debate_synthesizer"

    def test_does_not_store_when_debate_resolution_is_none(self):
        memory = _mock_memory()
        state = _base_state(debate_resolution=None)
        write_research_memory_node(state, memory)
        memory.store.assert_not_called()

    def test_does_not_raise_on_store_failure(self):
        memory = _mock_memory()
        memory.store.side_effect = RuntimeError("chroma unavailable")
        state = _base_state(
            debate_resolution={"decision": "BUY", "symbol": "NVDA"}
        )
        result = write_research_memory_node(state, memory)
        assert result == {}


# ---------------------------------------------------------------------------
# write_external_memory_node tests
# ---------------------------------------------------------------------------


class TestWriteExternalMemoryNode:
    def test_calls_store_with_external_data_source(self):
        memory = _mock_memory()
        state = _base_state(
            data_fetcher_result={
                "symbol": "NVDA",
                "market_data": {
                    "price": 850.0,
                    "volume": 1_000_000,
                    "source": "yfinance",
                    "timestamp": "2026-03-06T12:00:00Z",
                },
            }
        )
        write_external_memory_node(state, memory)
        assert memory.store.called
        # At least one call should have EXTERNAL_DATA source
        sources = [c.kwargs["source"] for c in memory.store.call_args_list]
        assert MemorySource.EXTERNAL_DATA in sources

    def test_store_metadata_contains_required_fields(self):
        memory = _mock_memory()
        state = _base_state(
            data_fetcher_result={
                "symbol": "AAPL",
                "economic_data": {
                    "indicator": "CPI",
                    "value": 3.1,
                    "source": "fred",
                    "timestamp": "2026-03-06T00:00:00Z",
                },
            }
        )
        write_external_memory_node(state, memory)
        assert memory.store.called
        meta = memory.store.call_args.kwargs["metadata"]
        assert "timestamp" in meta
        assert "data_type" in meta
        assert "source_name" in meta
        assert "title_or_url" in meta

    def test_does_not_store_when_data_fetcher_result_is_none(self):
        memory = _mock_memory()
        state = _base_state(data_fetcher_result=None)
        write_external_memory_node(state, memory)
        memory.store.assert_not_called()

    def test_does_not_raise_on_store_failure(self):
        memory = _mock_memory()
        memory.store.side_effect = RuntimeError("chroma unavailable")
        state = _base_state(
            data_fetcher_result={
                "market_data": {"price": 100.0, "source": "yfinance", "timestamp": "2026-03-06T12:00:00Z"}
            }
        )
        result = write_external_memory_node(state, memory)
        assert result == {}

    def test_returns_state_unchanged(self):
        memory = _mock_memory()
        state = _base_state(
            data_fetcher_result={
                "market_data": {"price": 100.0, "source": "yfinance"}
            }
        )
        result = write_external_memory_node(state, memory)
        assert result == {}
