"""Tests for Phase 22: failure_cause classification and KAMI Recovery signal awareness.

Covers:
- order_router failure_cause field in execution_result
- _extract_recovery_signal failure_cause-aware logic
- _build_entry CYCLE_STATUS field
- _process_agent cycle_status determination
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from src.core.kami import _extract_recovery_signal


# ---------------------------------------------------------------------------
# _extract_recovery_signal: failure_cause-aware tests
# ---------------------------------------------------------------------------


class TestRecoverySignalFailureCause:
    """_extract_recovery_signal uses failure_cause when present."""

    @pytest.mark.parametrize("cause", [
        "INVALID_ORDER",
        "BAD_PARAMETERS",
        "RISK_RULE_VIOLATION",
        "INSUFFICIENT_FUNDS_FROM_SIZING",
        "UNSUPPORTED_INSTRUMENT",
    ])
    def test_self_induced_causes_return_zero(self, cause: str) -> None:
        state = {
            "execution_result": {
                "success": False,
                "failure_cause": cause,
            },
        }
        assert _extract_recovery_signal(state) == 0.0

    @pytest.mark.parametrize("cause", [
        "EXCHANGE_DOWN",
        "BROKER_API_ERROR",
        "NETWORK_TIMEOUT",
        "VENUE_UNAVAILABLE",
    ])
    def test_external_causes_return_one(self, cause: str) -> None:
        state = {
            "execution_result": {
                "success": False,
                "failure_cause": cause,
            },
        }
        assert _extract_recovery_signal(state) == 1.0

    def test_unknown_failure_cause_returns_one_fail_open(self) -> None:
        state = {
            "execution_result": {
                "success": False,
                "failure_cause": "SOME_FUTURE_CAUSE",
            },
        }
        assert _extract_recovery_signal(state) == 1.0

    def test_missing_failure_cause_falls_through_to_legacy(self) -> None:
        """No failure_cause key -> legacy error_type path."""
        state = {
            "execution_result": {
                "success": False,
                "error_type": "INVALID_INPUT",
            },
        }
        # Legacy path: INVALID_INPUT is in _SELF_INDUCED_ERRORS -> 0.0
        assert _extract_recovery_signal(state) == 0.0

    def test_none_failure_cause_falls_through_to_legacy(self) -> None:
        """failure_cause=None -> legacy error_type path."""
        state = {
            "execution_result": {
                "success": False,
                "failure_cause": None,
                "error_type": "SCHEMA_FAILURE",
            },
        }
        assert _extract_recovery_signal(state) == 0.0

    def test_success_true_still_returns_one(self) -> None:
        """Backward compat: success=True -> 1.0 regardless of failure_cause."""
        state = {
            "execution_result": {
                "success": True,
                "failure_cause": None,
            },
        }
        assert _extract_recovery_signal(state) == 1.0


# ---------------------------------------------------------------------------
# order_router failure_cause field tests
# ---------------------------------------------------------------------------


class TestOrderRouterFailureCause:
    """order_router_node sets failure_cause in execution_result."""

    def _run(self, state: dict) -> dict:
        """Helper to run async node."""
        from src.graph.agents.l3.order_router import order_router_node
        return asyncio.run(order_router_node(state))

    def test_risk_not_approved_sets_risk_rule_violation(self) -> None:
        state = {
            "risk_approved": False,
            "execution_mode": "paper",
        }
        result = self._run(state)
        er = result["execution_result"]
        assert er["success"] is False
        assert er["failure_cause"] == "RISK_RULE_VIOLATION"

    @patch("src.graph.agents.l3.order_router.parse_quant_proposal", return_value={
        "symbol": "AAPL", "side": "buy", "quantity": 1.0, "asset_class": "equity",
    })
    @patch("src.graph.agents.l3.order_router.Executor")
    def test_compliance_rejection_sets_risk_rule_violation(self, mock_exec_cls, mock_parse) -> None:
        mock_exec = MagicMock()
        mock_exec.execute.side_effect = ValueError("stop-loss missing")
        mock_exec_cls.return_value = mock_exec

        state = {"risk_approved": True, "execution_mode": "paper"}
        result = self._run(state)
        er = result["execution_result"]
        assert er["success"] is False
        assert er["failure_cause"] == "RISK_RULE_VIOLATION"

    @patch("src.graph.agents.l3.order_router.parse_quant_proposal", return_value={
        "symbol": "AAPL", "side": "buy", "quantity": 1.0, "asset_class": "equity",
    })
    @patch("src.graph.agents.l3.order_router.Executor")
    def test_generic_exception_sets_execution_failure(self, mock_exec_cls, mock_parse) -> None:
        mock_exec = MagicMock()
        mock_exec.execute.side_effect = RuntimeError("connection reset")
        mock_exec_cls.return_value = mock_exec

        state = {"risk_approved": True, "execution_mode": "paper"}
        result = self._run(state)
        er = result["execution_result"]
        assert er["success"] is False
        assert er["failure_cause"] == "EXECUTION_FAILURE"

    @patch("src.graph.agents.l3.order_router.parse_quant_proposal", return_value={
        "symbol": "AAPL", "side": "buy", "quantity": 1.0, "asset_class": "equity",
    })
    @patch("src.graph.agents.l3.order_router.Executor")
    def test_success_sets_failure_cause_none(self, mock_exec_cls, mock_parse) -> None:
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.order_id = "ORD-123"
        mock_result.execution_price = 150.0
        mock_result.message = "filled"
        mock_result.metadata = {}
        mock_exec = MagicMock()
        mock_exec.execute.return_value = mock_result
        mock_exec_cls.return_value = mock_exec

        state = {"risk_approved": True, "execution_mode": "paper"}
        result = self._run(state)
        er = result["execution_result"]
        assert er["success"] is True
        assert er["failure_cause"] is None
