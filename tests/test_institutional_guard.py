import asyncio
from unittest.mock import AsyncMock, patch
from src.security.institutional_guard import InstitutionalGuard, institutional_guard_node


def test_institutional_guard_restricted_asset():
    config = {
        "risk_limits": {
            "restricted_assets": ["XRP/USDT", "DOGE/USDT"]
        }
    }
    guard = InstitutionalGuard(config)

    # Restricted asset path — fires before _get_open_positions(); no mock needed
    state = {"quant_proposal": {"symbol": "XRP/USDT"}}
    result = asyncio.run(guard.check_compliance(state))
    assert result["approved"] is False
    assert "restricted" in result["violation"]

    # Allowed asset path — _get_open_positions() IS called; mock to return empty list
    state = {"quant_proposal": {"symbol": "BTC/USDT"}}
    with patch.object(InstitutionalGuard, "_get_open_positions",
                      new_callable=AsyncMock, return_value=[]):
        result = asyncio.run(guard.check_compliance(state))
    assert result["approved"] is True


def test_institutional_guard_concurrent_trades():
    config = {"risk_limits": {"max_concurrent_trades": 10}}
    guard = InstitutionalGuard(config)
    state = {"quant_proposal": {"symbol": "BTC/USDT"}}

    # Exceeded path — 10 open positions triggers the limit (10 >= 10)
    ten_positions = [{"symbol": "ETH/USDT", "quantity": 1.0, "price": 1000.0}] * 10
    with patch.object(InstitutionalGuard, "_get_open_positions",
                      new_callable=AsyncMock, return_value=ten_positions):
        result = asyncio.run(guard.check_compliance(state))
    assert result["approved"] is False
    assert "Max concurrent trades" in result["violation"]

    # Under limit path — 0 open positions; should approve
    with patch.object(InstitutionalGuard, "_get_open_positions",
                      new_callable=AsyncMock, return_value=[]):
        result = asyncio.run(guard.check_compliance(state))
    assert result["approved"] is True


def test_institutional_guard_node_logic():
    config = {"risk_limits": {"restricted_assets": ["BAD/USDT"]}}

    # Violation path — BAD/USDT is restricted; fires before _get_open_positions()
    state = {
        "quant_proposal": {"symbol": "BAD/USDT"},
        "compliance_flags": ["PRE_EXISTING"],
        "risk_notes": "All good so far"
    }
    update = asyncio.run(institutional_guard_node(state, config))
    assert update["risk_approved"] is False
    assert any("INSTITUTIONAL_VIOLATION" in f for f in update["compliance_flags"])
    assert "Institutional Guard Block" in update["risk_notes"]

    # Approval path — GOOD/USDT is not restricted; _get_open_positions() IS called
    state = {"quant_proposal": {"symbol": "GOOD/USDT"}, "compliance_flags": []}
    with patch.object(InstitutionalGuard, "_get_open_positions",
                      new_callable=AsyncMock, return_value=[]):
        update = asyncio.run(institutional_guard_node(state, config))
    assert "INSTITUTIONAL_APPROVED" in update["compliance_flags"]
    assert "risk_approved" not in update  # node only sets risk_approved on violation
