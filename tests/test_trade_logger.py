"""TradeLogger node unit tests."""
import json
import pytest


@pytest.mark.asyncio
async def test_trade_logger_appends_record():
    """trade_logger_node appends one TradeRecord dict to trade_history."""
    from src.graph.agents.l3.trade_logger import trade_logger_node

    state = {
        "task_id": "test-001",
        "user_input": "buy AAPL",
        "intent": "trade",
        "messages": [],
        "macro_report": None,
        "quant_proposal": {"symbol": "AAPL", "side": "buy", "quantity": 10.0},
        "bullish_thesis": None,
        "bearish_thesis": None,
        "debate_resolution": None,
        "weighted_consensus_score": 0.75,
        "debate_history": [],
        "risk_approval": None,
        "consensus_score": 0.75,
        "compliance_flags": [],
        "risk_approved": True,
        "risk_notes": None,
        "final_decision": None,
        "metadata": {},
        "trade_history": [],
        "execution_mode": "paper",
        "data_fetcher_result": None,
        "backtest_result": None,
        "execution_result": {"success": True, "execution_price": 150.25, "order_id": "PAPER-ABC123"},
    }

    result = await trade_logger_node(state)

    assert "trade_history" in result
    assert isinstance(result["trade_history"], list)
    assert len(result["trade_history"]) == 1

    record = result["trade_history"][0]
    assert "symbol" in record
    assert "side" in record
    assert "trade_id" in record
    assert record["symbol"] == "AAPL"
    assert record["side"] == "buy"


def test_trade_history_window_enforced():
    """trade_history[-15:] slice enforces N=15 window in L2 agent read."""
    from src.graph.agents.l3.trade_logger import get_recent_trades, TRADE_HISTORY_WINDOW

    # Build a state with 20 entries in trade_history
    existing_trades = [
        {"trade_id": f"t{i:02d}", "symbol": "AAPL", "side": "buy",
         "entry_price": 100.0, "quantity": 1.0, "execution_mode": "paper",
         "strategy_context": {}, "entry_time": "2026-01-01T00:00:00"}
        for i in range(20)
    ]

    state = {
        "trade_history": existing_trades,
        "execution_mode": "paper",
    }

    recent = get_recent_trades(state)
    assert len(recent) == TRADE_HISTORY_WINDOW == 15
    # The most recent 15 should be indices 5-19
    assert recent[0]["trade_id"] == "t05"
    assert recent[-1]["trade_id"] == "t19"


@pytest.mark.asyncio
async def test_trade_record_is_serializable():
    """json.dumps(trade_history_entry) does not raise."""
    from src.graph.agents.l3.trade_logger import trade_logger_node

    state = {
        "task_id": "test-002",
        "user_input": "buy BTC",
        "intent": "trade",
        "messages": [],
        "macro_report": None,
        "quant_proposal": {"symbol": "BTC-USDT", "side": "buy", "quantity": 0.1},
        "bullish_thesis": None,
        "bearish_thesis": None,
        "debate_resolution": None,
        "weighted_consensus_score": 0.8,
        "debate_history": [],
        "risk_approval": None,
        "consensus_score": 0.8,
        "compliance_flags": [],
        "risk_approved": True,
        "risk_notes": None,
        "final_decision": None,
        "metadata": {},
        "trade_history": [],
        "execution_mode": "paper",
        "data_fetcher_result": None,
        "backtest_result": None,
        "execution_result": {"success": True, "execution_price": 45000.0, "order_id": "PAPER-XYZ"},
    }

    result = await trade_logger_node(state)
    record = result["trade_history"][0]

    # Should not raise
    serialized = json.dumps(record)
    assert serialized  # non-empty string


def test_state_has_phase3_fields():
    """SwarmState TypedDict has trade_history, execution_mode, data_fetcher_result,
    backtest_result, execution_result fields."""
    from src.graph.state import SwarmState

    annotations = SwarmState.__annotations__
    assert "trade_history" in annotations
    assert "execution_mode" in annotations
    assert "data_fetcher_result" in annotations
    assert "backtest_result" in annotations
    assert "execution_result" in annotations
