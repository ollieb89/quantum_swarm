import asyncio
import inspect
from unittest.mock import AsyncMock, patch
from src.security.institutional_guard import InstitutionalGuard, institutional_guard_node
import src.core.persistence as persistence_mod


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


# ---------------------------------------------------------------------------
# Phase 8 RED stubs — RISK-07: SQL columns, exit_time index, drawdown circuit breaker
# ---------------------------------------------------------------------------

def test_get_open_positions_correct_columns():
    """RISK-07: _get_open_positions SQL must use position_size and entry_price (Phase 6 schema rename)."""
    source = inspect.getsource(InstitutionalGuard._get_open_positions)
    assert "SELECT symbol, position_size" in source, (
        "SQL still uses old column names. Expected 'SELECT symbol, position_size' but got:\n" + source
    )
    assert "entry_price" in source, (
        "SQL must reference entry_price column (Phase 6 rename), not execution_price"
    )


def test_exit_time_index_exists():
    """RISK-07: setup_persistence() must create idx_trades_exit_time for open-position queries."""
    source = inspect.getsource(persistence_mod.setup_persistence)
    assert "idx_trades_exit_time" in source, (
        "idx_trades_exit_time index is missing from setup_persistence(). "
        "Open-position queries filter on exit_time IS NULL and need this index."
    )


def test_drawdown_circuit_breaker():
    """RISK-07: check_compliance must reject trades when daily loss exceeds max_daily_loss threshold."""
    config = {
        "risk_limits": {
            "starting_capital": 1000000.0,
            "max_notional_exposure": 500000.0,
            "max_asset_concentration_pct": 0.20,
            "max_concurrent_trades": 10,
            "max_daily_loss": 0.05,
            "max_drawdown": 0.15,
        }
    }
    guard = InstitutionalGuard(config)
    state = {
        "quant_proposal": {
            "symbol": "BTC/USDT",
            "entry_price": 50000.0,
            "quantity": 1.0,
            "stop_loss": 47500.0,
            "confidence": 0.8,
        }
    }
    # No open positions — only the drawdown check should block this trade.
    # _get_daily_pnl returns -60000.0 (6% of 1M capital, exceeds 5% max_daily_loss).
    with patch.object(InstitutionalGuard, "_get_open_positions",
                      new_callable=AsyncMock, return_value=[]):
        with patch.object(InstitutionalGuard, "_get_daily_pnl",
                          new_callable=AsyncMock, return_value=-60000.0):
            result = asyncio.run(guard.check_compliance(state))

    assert result["approved"] is False
    assert "drawdown" in result.get("violation", "").lower(), (
        f"violation message must mention 'drawdown', got: {result.get('violation')}"
    )


# ---------------------------------------------------------------------------
# Phase 8 GREEN confirmation — RISK-08: guard node metadata propagation
# ---------------------------------------------------------------------------

def test_guard_node_metadata_propagation():
    """RISK-08: institutional_guard_node approval path must populate metadata with risk metrics."""
    config = {
        "risk_limits": {
            "starting_capital": 1000000.0,
            "max_notional_exposure": 500000.0,
            "max_asset_concentration_pct": 0.20,
            "max_concurrent_trades": 10,
        }
    }
    state = {
        "quant_proposal": {
            "symbol": "BTC/USDT",
            "entry_price": 50000.0,
            "quantity": 1.0,
            "stop_loss": 47500.0,
            "confidence": 0.8,
        },
        "compliance_flags": [],
        "metadata": {},
    }
    with patch.object(InstitutionalGuard, "_get_open_positions",
                      new_callable=AsyncMock, return_value=[]):
        update = asyncio.run(institutional_guard_node(state, config))

    assert "metadata" in update, "metadata key missing from node output"
    assert isinstance(update["metadata"]["trade_risk_score"], float), \
        "trade_risk_score must be a float"
    assert isinstance(update["metadata"]["portfolio_heat"], float), \
        "portfolio_heat must be a float"
    assert 0.0 <= update["metadata"]["trade_risk_score"] <= 1.0
    assert 0.0 <= update["metadata"]["portfolio_heat"] <= 1.0
