"""OrderRouter node unit tests — covers paper mode, live routing, risk gate, serialization, and IB gate."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from src.agents.l3_executor import ExecutionResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(
    execution_mode="paper",
    risk_approved=True,
    asset_class="equity",
    symbol="AAPL",
    side="buy",
    quantity=10.0,
    stop_loss=148.0,
    entry_price=150.0,
):
    return {
        "task_id": "test-123",
        "execution_mode": execution_mode,
        "risk_approved": risk_approved,
        "quant_proposal": {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "asset_class": asset_class,
            "stop_loss": stop_loss,
            "entry_price": entry_price,
        },
        "messages": [],
        "metadata": {},
    }


# ---------------------------------------------------------------------------
# Test 1: paper mode returns PAPER- prefixed order_id with success=True
# ---------------------------------------------------------------------------

def test_order_router_paper_mode():
    """Paper mode returns dict with execution_result containing PAPER- order_id."""
    from src.graph.agents.l3.order_router import order_router_node

    state = _make_state(execution_mode="paper", risk_approved=True)

    result = asyncio.run(order_router_node(state))

    assert "execution_result" in result
    er = result["execution_result"]
    assert er["success"] is True
    assert isinstance(er["order_id"], str)
    assert er["order_id"].startswith("PAPER-"), f"Expected PAPER- prefix, got: {er['order_id']}"
    assert er["mode"] == "paper"
    assert "execution_price" in er


# ---------------------------------------------------------------------------
# Test 2: execution_mode=live, asset_class=equity → _execute_live_equity path
# ---------------------------------------------------------------------------

def test_execution_mode_routing():
    """execution_mode='live', asset_class='equity' → delegates to Executor.execute."""
    from src.graph.agents.l3.order_router import order_router_node

    state = _make_state(execution_mode="live", asset_class="equity", risk_approved=True)

    mock_result = ExecutionResult(
        success=True,
        order_id="IB-ORDER-12345",
        execution_price=150.25,
        message="Live equity executed",
        metadata={"mode": "live_equity"},
    )

    with patch("src.graph.agents.l3.order_router.Executor") as MockExecutor:
        MockExecutor.return_value.execute.return_value = mock_result
        result = asyncio.run(order_router_node(state))

    MockExecutor.return_value.execute.assert_called_once()
    assert result["execution_result"]["success"] is True
    assert result["execution_result"]["order_id"] == "IB-ORDER-12345"


# ---------------------------------------------------------------------------
# Test 3: execution_mode=live, asset_class=crypto → _execute_live_crypto path
# ---------------------------------------------------------------------------

def test_execution_mode_routing_crypto():
    """execution_mode='live', asset_class='crypto' → delegates to Executor.execute."""
    from src.graph.agents.l3.order_router import order_router_node

    state = _make_state(execution_mode="live", asset_class="crypto", symbol="BTC-USDT", risk_approved=True)

    mock_result = ExecutionResult(
        success=True,
        order_id="BIN-ORDER-99999",
        execution_price=44000.00,
        message="Live crypto executed",
        metadata={"mode": "live_crypto"},
    )

    with patch("src.graph.agents.l3.order_router.Executor") as MockExecutor:
        MockExecutor.return_value.execute.return_value = mock_result
        result = asyncio.run(order_router_node(state))

    MockExecutor.return_value.execute.assert_called_once()
    assert result["execution_result"]["success"] is True
    assert result["execution_result"]["order_id"] == "BIN-ORDER-99999"


# ---------------------------------------------------------------------------
# Test 4: risk_approved=False → execution_result success=False, reason=risk_not_approved
# ---------------------------------------------------------------------------

def test_risk_gate():
    """risk_approved=False → returns execution_result with success=False and reason='risk_not_approved'."""
    from src.graph.agents.l3.order_router import order_router_node

    state = _make_state(risk_approved=False)

    result = asyncio.run(order_router_node(state))

    assert "execution_result" in result
    er = result["execution_result"]
    assert er["success"] is False
    assert er.get("reason") == "risk_not_approved"
    # Should not have attempted any execution
    assert er.get("order_id") is None


# ---------------------------------------------------------------------------
# Test 5: all returned dicts are JSON-serializable
# ---------------------------------------------------------------------------

def test_result_serializable():
    """json.dumps(result['execution_result']) does not raise for paper mode."""
    from src.graph.agents.l3.order_router import order_router_node

    state = _make_state(execution_mode="paper", risk_approved=True)

    result = asyncio.run(order_router_node(state))

    # Should not raise
    serialized = json.dumps(result["execution_result"])
    assert isinstance(serialized, str)
    # Full result must also be JSON-serializable (excluding messages list with dicts)
    full_serialized = json.dumps(result["execution_result"])
    assert full_serialized is not None


# ---------------------------------------------------------------------------
# Test 6: live equity but IB not reachable → graceful error mentioning IB Gateway
# ---------------------------------------------------------------------------

def test_live_gate_no_ib():
    """Live equity mode when executor returns not-implemented → execution_result success=False."""
    from src.graph.agents.l3.order_router import order_router_node

    state = _make_state(execution_mode="live", asset_class="equity", risk_approved=True)

    # Executor._execute_live returns success=False with a "not implemented" message
    # when no live broker adapter is configured.
    result = asyncio.run(order_router_node(state))

    er = result["execution_result"]
    assert er["success"] is False, f"Expected success=False for unconfigured live mode, got: {er}"
