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


# ---------------------------------------------------------------------------
# _build_entry: CYCLE_STATUS field tests
# ---------------------------------------------------------------------------


class TestBuildEntryCycleStatus:
    """_build_entry includes [CYCLE_STATUS:] field in correct position."""

    def test_cycle_status_success(self) -> None:
        from src.graph.nodes.memory_writer import _build_entry
        entry = _build_entry("AXIOM", 0.04, 0.81, "Thesis here.", cycle_status="success")
        lines = entry.strip().splitlines()
        field_lines = [l for l in lines if l.startswith("[")]
        labels = [l.split("]")[0] + "]" for l in field_lines]
        # CYCLE_STATUS must appear between DRIFT_FLAGS and THESIS_SUMMARY
        assert "[CYCLE_STATUS:]" in labels
        drift_idx = labels.index("[DRIFT_FLAGS:]")
        status_idx = labels.index("[CYCLE_STATUS:]")
        thesis_idx = labels.index("[THESIS_SUMMARY:]")
        assert drift_idx < status_idx < thesis_idx
        assert "[CYCLE_STATUS:] success" in entry

    def test_cycle_status_failed(self) -> None:
        from src.graph.nodes.memory_writer import _build_entry
        entry = _build_entry("CASSANDRA", -0.03, 0.78, "Bearish.", cycle_status="failed")
        assert "[CYCLE_STATUS:] failed" in entry

    def test_cycle_status_external_failure(self) -> None:
        from src.graph.nodes.memory_writer import _build_entry
        entry = _build_entry("SIGMA", 0.0, 0.50, "Neutral.", cycle_status="external_failure")
        assert "[CYCLE_STATUS:] external_failure" in entry

    def test_cycle_status_defaults_to_success(self) -> None:
        from src.graph.nodes.memory_writer import _build_entry
        entry = _build_entry("AXIOM", 0.0, 0.50, "Test.")
        assert "[CYCLE_STATUS:] success" in entry


# ---------------------------------------------------------------------------
# _process_agent: cycle_status determination tests
# ---------------------------------------------------------------------------


class TestProcessAgentCycleStatus:
    """_process_agent derives cycle_status from execution_result."""

    @patch("src.graph.nodes.memory_writer._get_souls_dir")
    @patch("src.graph.nodes.memory_writer._evaluate_drift_flags", return_value="none")
    @patch("src.graph.nodes.memory_writer.load_soul")
    def test_success_cycle_status(self, mock_soul, mock_drift, mock_dir, tmp_path) -> None:
        from src.graph.nodes.memory_writer import _process_agent
        mock_dir.return_value = tmp_path
        (tmp_path / "macro_analyst").mkdir()

        state = {
            "macro_report": "Inflation rising.",
            "merit_scores": {"AXIOM": {"composite": 0.80}},
            "execution_result": {"success": True, "failure_cause": None},
        }
        _process_agent("AXIOM", state)
        content = (tmp_path / "macro_analyst" / "MEMORY.md").read_text()
        assert "[CYCLE_STATUS:] success" in content

    @patch("src.graph.nodes.memory_writer._get_souls_dir")
    @patch("src.graph.nodes.memory_writer._evaluate_drift_flags", return_value="none")
    @patch("src.graph.nodes.memory_writer.load_soul")
    def test_failed_cycle_status_self_induced(self, mock_soul, mock_drift, mock_dir, tmp_path) -> None:
        from src.graph.nodes.memory_writer import _process_agent
        mock_dir.return_value = tmp_path
        (tmp_path / "macro_analyst").mkdir()

        state = {
            "macro_report": "Inflation rising.",
            "merit_scores": {"AXIOM": {"composite": 0.80}},
            "execution_result": {"success": False, "failure_cause": "RISK_RULE_VIOLATION"},
        }
        _process_agent("AXIOM", state)
        content = (tmp_path / "macro_analyst" / "MEMORY.md").read_text()
        assert "[CYCLE_STATUS:] failed" in content

    @patch("src.graph.nodes.memory_writer._get_souls_dir")
    @patch("src.graph.nodes.memory_writer._evaluate_drift_flags", return_value="none")
    @patch("src.graph.nodes.memory_writer.load_soul")
    def test_external_failure_cycle_status(self, mock_soul, mock_drift, mock_dir, tmp_path) -> None:
        from src.graph.nodes.memory_writer import _process_agent
        mock_dir.return_value = tmp_path
        (tmp_path / "macro_analyst").mkdir()

        state = {
            "macro_report": "Inflation rising.",
            "merit_scores": {"AXIOM": {"composite": 0.80}},
            "execution_result": {"success": False, "failure_cause": "EXCHANGE_DOWN"},
        }
        _process_agent("AXIOM", state)
        content = (tmp_path / "macro_analyst" / "MEMORY.md").read_text()
        assert "[CYCLE_STATUS:] external_failure" in content

    @patch("src.graph.nodes.memory_writer._get_souls_dir")
    @patch("src.graph.nodes.memory_writer._evaluate_drift_flags", return_value="none")
    @patch("src.graph.nodes.memory_writer.load_soul")
    def test_no_execution_result_defaults_success(self, mock_soul, mock_drift, mock_dir, tmp_path) -> None:
        from src.graph.nodes.memory_writer import _process_agent
        mock_dir.return_value = tmp_path
        (tmp_path / "macro_analyst").mkdir()

        state = {
            "macro_report": "Inflation rising.",
            "merit_scores": {"AXIOM": {"composite": 0.80}},
        }
        _process_agent("AXIOM", state)
        content = (tmp_path / "macro_analyst" / "MEMORY.md").read_text()
        assert "[CYCLE_STATUS:] success" in content


# ---------------------------------------------------------------------------
# Phase 22 Plan 02: Orchestrator rewiring + failure-aware decision_card_writer
# ---------------------------------------------------------------------------


class TestOrchestratorDirectEdge:
    """Graph topology: order_router -> decision_card_writer is a direct (unconditional) edge."""

    def test_order_router_has_direct_edge_to_decision_card_writer(self) -> None:
        """After compilation, order_router's next node is always decision_card_writer —
        no conditional routing function in the path."""
        from src.graph.orchestrator import create_orchestrator_graph
        graph = create_orchestrator_graph({})
        # The compiled graph exposes its structure. Walk the graph to confirm
        # order_router has a direct edge to decision_card_writer.
        # In LangGraph, compiled graph.graph stores the underlying StateGraph.
        # We check that no conditional edge map exists for order_router.
        g = graph.get_graph()
        # Find the edge from order_router
        order_router_edges = [
            e for e in g.edges if e.source == "order_router"
        ]
        assert len(order_router_edges) == 1, (
            f"Expected exactly 1 edge from order_router, got {len(order_router_edges)}: {order_router_edges}"
        )
        assert order_router_edges[0].target == "decision_card_writer"

    def test_route_after_order_router_deleted(self) -> None:
        """The route_after_order_router function must not exist in orchestrator module."""
        import src.graph.orchestrator as orch_mod
        assert not hasattr(orch_mod, "route_after_order_router"), (
            "route_after_order_router should be deleted from orchestrator.py"
        )


class TestDecisionCardWriterFailure:
    """decision_card_writer_node produces valid cards for failed executions."""

    def test_failure_card_returns_written_status(self) -> None:
        """decision_card_writer_node with execution_result.success=False should
        still call build_decision_card and return decision_card_status='written'."""
        from src.graph.orchestrator import decision_card_writer_node

        state = {
            "task_id": "fail-test-001",
            "execution_result": {
                "success": False,
                "failure_cause": "RISK_RULE_VIOLATION",
                "error": "Position limit exceeded",
            },
            "consensus_score": 0.0,
            "weighted_consensus_score": None,
            "compliance_flags": [],
            "risk_approval": {},
            "macro_report": None,
            "quant_proposal": None,
            "bullish_thesis": None,
            "bearish_thesis": None,
            "debate_resolution": None,
            "metadata": {},
        }
        result = asyncio.run(decision_card_writer_node(state))
        assert result["decision_card_status"] == "written"
        assert result["decision_card_audit_ref"] is not None

    def test_build_decision_card_handles_failure(self) -> None:
        """build_decision_card produces a valid card when execution_result.success=False."""
        from src.core.decision_card import build_decision_card, verify_decision_card

        state = {
            "task_id": "fail-card-001",
            "execution_result": {
                "success": False,
                "failure_cause": "BAD_PARAMETERS",
                "error": "Invalid quantity",
            },
            "consensus_score": 0.7,
            "compliance_flags": [],
            "risk_approval": {},
            "metadata": {},
        }
        card = build_decision_card(state)
        assert card.task_id == "fail-card-001"
        assert card.execution_result["success"] is False
        assert card.content_hash  # non-empty hash
        assert verify_decision_card(card.model_dump(mode="json"))


class TestMeritUpdaterFailurePath:
    """merit_updater_node processes failed execution_results (does not early-return)."""

    @patch("src.graph.nodes.merit_updater._persist_merit")
    def test_merit_updater_processes_failed_execution(self, mock_persist) -> None:
        """When execution_result.success=False, merit_updater should still run
        (execution_result is truthy dict), not skip via the aborted-cycle guard."""
        from src.graph.nodes.merit_updater import merit_updater_node

        # Make persist a no-op async
        async def noop(*a, **kw):
            pass
        mock_persist.side_effect = noop

        state = {
            "execution_result": {
                "success": False,
                "failure_cause": "RISK_RULE_VIOLATION",
            },
            "active_persona": "AXIOM",
            "merit_scores": {
                "AXIOM": {
                    "accuracy": 0.5,
                    "recovery": 0.5,
                    "consensus": 0.5,
                    "fidelity": 0.5,
                    "composite": 0.5,
                },
            },
            "weighted_consensus_score": 0.7,
        }
        result = asyncio.run(merit_updater_node(state))
        # Should NOT return {} (aborted cycle guard)
        assert result != {}, "merit_updater should process failed execution_result, not skip it"
        assert "merit_scores" in result
        # Recovery should be penalised (self-induced cause -> 0.0 signal)
        updated = result["merit_scores"]["AXIOM"]
        assert updated["recovery"] < 0.5, "Recovery should decrease for self-induced failure"
