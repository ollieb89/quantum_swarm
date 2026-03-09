"""Integration tests for circuit breaker wired into with_audit_logging.

Tests the single integration point: all LLM nodes gain circuit breaker
protection through the with_audit_logging wrapper.
"""

import asyncio
import operator
import os
from typing import Annotated, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai.errors import ServerError

from src.core.circuit_breaker import CircuitBreaker, CircuitState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_circuit_breaker_singleton():
    """Reset the module-level _circuit_breaker between tests."""
    import src.graph.orchestrator as orch_mod
    original = getattr(orch_mod, "_circuit_breaker", None)
    orch_mod._circuit_breaker = None
    yield
    orch_mod._circuit_breaker = original


@pytest.fixture
def mock_audit_logger():
    """Patch the global audit_logger in orchestrator to avoid DB calls."""
    with patch("src.graph.orchestrator.audit_logger") as mock_al:
        mock_al.log_transition = AsyncMock()
        yield mock_al


def _make_server_error(code: int) -> ServerError:
    """Create a ServerError with the given HTTP status code."""
    err = ServerError.__new__(ServerError)
    err.code = code
    err.message = f"HTTP {code}"
    err.args = (f"HTTP {code}",)
    return err


# ---------------------------------------------------------------------------
# Task 1 tests: with_audit_logging circuit breaker behavior
# ---------------------------------------------------------------------------


class TestLLMNodeCircuitBreaker:
    """Verify with_audit_logging checks circuit breaker for LLM nodes."""

    def test_llm_nodes_constant_exists(self):
        """LLM_NODES frozenset is importable and contains expected nodes."""
        from src.graph.orchestrator import LLM_NODES

        assert isinstance(LLM_NODES, frozenset)
        assert "macro_analyst" in LLM_NODES
        assert "quant_modeler" in LLM_NODES
        assert "bullish_researcher" in LLM_NODES
        assert "bearish_researcher" in LLM_NODES
        # debate_synthesizer is NOT an LLM node (pure aggregation)
        assert "debate_synthesizer" not in LLM_NODES

    def test_llm_node_calls_circuit_breaker(self, mock_audit_logger):
        """with_audit_logging checks cb.check() for LLM nodes before executing."""
        from src.graph.orchestrator import with_audit_logging

        cb = CircuitBreaker(threshold=3)
        node_fn = AsyncMock(return_value={"result": "ok"})

        with patch("src.graph.orchestrator._get_circuit_breaker", return_value=cb):
            wrapped = with_audit_logging(node_fn, "macro_analyst")
            state = {"task_id": "test-1", "soft_failed_nodes": []}
            result = asyncio.run(wrapped(state))

        node_fn.assert_called_once()
        assert result == {"result": "ok"}

    def test_non_llm_node_bypasses_circuit_breaker(self, mock_audit_logger):
        """Non-LLM node executes without circuit breaker check."""
        from src.graph.orchestrator import with_audit_logging

        cb = CircuitBreaker(threshold=3)
        # Force circuit open
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

        node_fn = AsyncMock(return_value={"data": "fetched"})

        with patch("src.graph.orchestrator._get_circuit_breaker", return_value=cb):
            wrapped = with_audit_logging(node_fn, "data_fetcher")
            state = {"task_id": "test-2"}
            result = asyncio.run(wrapped(state))

        # Node still executes despite open circuit (not an LLM node)
        node_fn.assert_called_once()
        assert result == {"data": "fetched"}

    def test_open_circuit_returns_empty_dict(self, mock_audit_logger):
        """When cb.check() returns False, node returns soft_failed_nodes without calling node_fn."""
        from src.graph.orchestrator import with_audit_logging

        cb = CircuitBreaker(threshold=3)
        # Trip the breaker
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

        node_fn = AsyncMock(return_value={"should": "not-reach"})

        with patch("src.graph.orchestrator._get_circuit_breaker", return_value=cb):
            wrapped = with_audit_logging(node_fn, "macro_analyst")
            state = {"task_id": "test-3", "soft_failed_nodes": []}
            result = asyncio.run(wrapped(state))

        node_fn.assert_not_called()
        assert result == {"soft_failed_nodes": ["macro_analyst"]}

    def test_transient_error_records_failure(self, mock_audit_logger):
        """When LLM node raises transient error, cb.record_failure() is called and node returns soft_failed_nodes."""
        from src.graph.orchestrator import with_audit_logging

        cb = CircuitBreaker(threshold=5)
        node_fn = AsyncMock(side_effect=_make_server_error(503))

        with patch("src.graph.orchestrator._get_circuit_breaker", return_value=cb):
            wrapped = with_audit_logging(node_fn, "quant_modeler")
            state = {"task_id": "test-4", "soft_failed_nodes": []}
            result = asyncio.run(wrapped(state))

        assert result == {"soft_failed_nodes": ["quant_modeler"]}
        # Failure was recorded
        assert cb._failure_count == 1

    def test_non_transient_error_still_raises(self, mock_audit_logger):
        """When LLM node raises non-transient error (ValueError), error re-raises."""
        from src.graph.orchestrator import with_audit_logging

        cb = CircuitBreaker(threshold=3)
        node_fn = AsyncMock(side_effect=ValueError("bad input"))

        with patch("src.graph.orchestrator._get_circuit_breaker", return_value=cb):
            wrapped = with_audit_logging(node_fn, "macro_analyst")
            state = {"task_id": "test-5"}

            with pytest.raises(ValueError, match="bad input"):
                asyncio.run(wrapped(state))

    def test_success_records_success(self, mock_audit_logger):
        """When LLM node succeeds, cb.record_success() is called."""
        from src.graph.orchestrator import with_audit_logging

        cb = CircuitBreaker(threshold=3)
        # Record one failure first to verify it resets
        cb.record_failure()
        assert cb._failure_count == 1

        node_fn = AsyncMock(return_value={"analysis": "done"})

        with patch("src.graph.orchestrator._get_circuit_breaker", return_value=cb):
            wrapped = with_audit_logging(node_fn, "bullish_researcher")
            state = {"task_id": "test-6", "soft_failed_nodes": []}
            result = asyncio.run(wrapped(state))

        assert result == {"analysis": "done"}
        assert cb._failure_count == 0  # reset by record_success

    def test_soft_failed_nodes_in_state(self, mock_audit_logger):
        """When circuit opens, soft_failed_nodes list in returned state update includes node_id."""
        from src.graph.orchestrator import with_audit_logging

        cb = CircuitBreaker(threshold=1)
        node_fn = AsyncMock(side_effect=_make_server_error(429))

        with patch("src.graph.orchestrator._get_circuit_breaker", return_value=cb):
            wrapped = with_audit_logging(node_fn, "bearish_researcher")
            state = {"task_id": "test-7", "soft_failed_nodes": []}
            result = asyncio.run(wrapped(state))

        assert "soft_failed_nodes" in result
        assert "bearish_researcher" in result["soft_failed_nodes"]

    def test_audit_hash_chain_preserved(self, mock_audit_logger):
        """Soft-failed nodes still produce audit log entries (output={})."""
        from src.graph.orchestrator import with_audit_logging

        cb = CircuitBreaker(threshold=3)
        for _ in range(3):
            cb.record_failure()

        with patch("src.graph.orchestrator._get_circuit_breaker", return_value=cb):
            wrapped = with_audit_logging(AsyncMock(), "macro_analyst")
            state = {"task_id": "test-8", "soft_failed_nodes": []}
            asyncio.run(wrapped(state))

        # audit_logger.log_transition was called even for soft-failed node
        mock_audit_logger.log_transition.assert_called_once()
        call_kwargs = mock_audit_logger.log_transition.call_args
        assert call_kwargs.kwargs.get("output_data") == {} or call_kwargs[1].get("output_data") == {}


# ---------------------------------------------------------------------------
# State model tests
# ---------------------------------------------------------------------------


class TestSwarmStateSoftFailedNodes:
    """Verify soft_failed_nodes field in SwarmState."""

    def test_soft_failed_nodes_field_exists(self):
        """SwarmState has soft_failed_nodes field."""
        from src.graph.state import SwarmState
        assert "soft_failed_nodes" in SwarmState.__annotations__


class TestCycleSnapshotDegraded:
    """Verify degraded and soft_failed_nodes fields in CycleSnapshot."""

    def test_degraded_field_defaults_false(self):
        from src.core.cycle_snapshot import CycleSnapshot
        snap = CycleSnapshot(
            cycle_id=1, task_id="t", symbol="BTC", status="completed",
        )
        assert snap.degraded is False
        assert snap.soft_failed_nodes == []

    def test_degraded_field_set_true(self):
        from src.core.cycle_snapshot import CycleSnapshot
        snap = CycleSnapshot(
            cycle_id=1, task_id="t", symbol="BTC", status="completed",
            degraded=True, soft_failed_nodes=["macro_analyst"],
        )
        assert snap.degraded is True
        assert snap.soft_failed_nodes == ["macro_analyst"]


class TestAuditExcludedFields:
    """Verify soft_failed_nodes is excluded from audit hash."""

    def test_soft_failed_nodes_excluded(self):
        from src.core.audit_logger import AUDIT_EXCLUDED_FIELDS
        assert "soft_failed_nodes" in AUDIT_EXCLUDED_FIELDS


class TestCycleRunnerDegraded:
    """Verify CycleRunner propagates degraded state."""

    def test_build_initial_state_has_soft_failed_nodes(self):
        from src.core.cycle_runner import CycleRunner
        runner = CycleRunner(graph=MagicMock())
        state = runner._build_initial_state("test input")
        assert "soft_failed_nodes" in state
        assert state["soft_failed_nodes"] == []

    def test_extract_snapshot_propagates_degraded(self):
        from src.core.cycle_runner import CycleRunner
        runner = CycleRunner(graph=MagicMock())
        final_state = {
            "soft_failed_nodes": ["macro_analyst", "quant_modeler"],
            "macro_report": None,
        }
        snapshot = runner._extract_snapshot(
            cycle_id=1, task_id="t", symbol="BTC",
            final_state=final_state, status="completed",
        )
        assert snapshot.degraded is True
        assert snapshot.soft_failed_nodes == ["macro_analyst", "quant_modeler"]

    def test_extract_snapshot_not_degraded_when_empty(self):
        from src.core.cycle_runner import CycleRunner
        runner = CycleRunner(graph=MagicMock())
        final_state = {"soft_failed_nodes": []}
        snapshot = runner._extract_snapshot(
            cycle_id=1, task_id="t", symbol="BTC",
            final_state=final_state, status="completed",
        )
        assert snapshot.degraded is False
        assert snapshot.soft_failed_nodes == []


class TestCircuitBreakerDisabled:
    """Verify kill switch disables circuit breaker."""

    def test_circuit_breaker_disabled_env_var(self, mock_audit_logger, monkeypatch):
        """When CIRCUIT_BREAKER_ENABLED=false, transient errors still raise."""
        from src.graph.orchestrator import with_audit_logging

        monkeypatch.setenv("CIRCUIT_BREAKER_ENABLED", "false")

        node_fn = AsyncMock(side_effect=_make_server_error(503))

        wrapped = with_audit_logging(node_fn, "macro_analyst")
        state = {"task_id": "test-disabled"}

        with pytest.raises(ServerError):
            asyncio.run(wrapped(state))
