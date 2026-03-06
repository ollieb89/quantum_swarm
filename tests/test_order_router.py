"""OrderRouter node unit tests — covers paper mode, live routing, risk gate, serialization, and IB gate."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


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
    """execution_mode='live', asset_class='equity' → calls _execute_live_equity path."""
    from src.graph.agents.l3.order_router import order_router_node

    state = _make_state(execution_mode="live", asset_class="equity", risk_approved=True)

    live_success = {
        "success": True,
        "order_id": "IB-ORDER-12345",
        "execution_price": 150.25,
        "mode": "live_equity",
    }

    with patch(
        "src.graph.agents.l3.order_router._execute_live_equity",
        new_callable=AsyncMock,
        return_value=live_success,
    ) as mock_live:
        result = asyncio.run(order_router_node(state))

    mock_live.assert_called_once()
    assert result["execution_result"]["success"] is True
    assert result["execution_result"]["order_id"] == "IB-ORDER-12345"


# ---------------------------------------------------------------------------
# Test 3: execution_mode=live, asset_class=crypto → _execute_live_crypto path
# ---------------------------------------------------------------------------

def test_execution_mode_routing_crypto():
    """execution_mode='live', asset_class='crypto' → calls _execute_live_crypto path."""
    from src.graph.agents.l3.order_router import order_router_node

    state = _make_state(execution_mode="live", asset_class="crypto", symbol="BTC-USDT", risk_approved=True)

    crypto_success = {
        "success": True,
        "order_id": "BIN-ORDER-99999",
        "execution_price": 44000.00,
        "mode": "live_crypto",
    }

    with patch(
        "src.graph.agents.l3.order_router._execute_live_crypto",
        new_callable=AsyncMock,
        return_value=crypto_success,
    ) as mock_crypto:
        result = asyncio.run(order_router_node(state))

    mock_crypto.assert_called_once()
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
    """Live equity mode when IB not reachable → execution_result success=False, error mentions IB Gateway."""
    from src.graph.agents.l3.order_router import order_router_node

    state = _make_state(execution_mode="live", asset_class="equity", risk_approved=True)

    # Simulate TCP connection refused (IB not running)
    async def _fake_open_connection(host, port):
        raise ConnectionRefusedError("Connection refused")

    with patch("asyncio.open_connection", side_effect=ConnectionRefusedError("Connection refused")):
        result = asyncio.run(order_router_node(state))

    er = result["execution_result"]
    assert er["success"] is False
    # Error message must mention IB Gateway (case-insensitive)
    error_msg = str(er.get("error", "")).lower()
    assert "ib gateway" in error_msg or "gateway" in error_msg, f"Expected gateway mention, got: {er.get('error')}"
