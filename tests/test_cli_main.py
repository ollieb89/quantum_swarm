"""
Unit tests for src/main.py CLI entry point.

TDD RED phase: Tests written before implementation.
"""

import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.cycle_snapshot import CycleSnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_completed_state() -> dict:
    """Minimal SwarmState dict that CycleRunner would return after successful graph run."""
    return {
        "task_id": "test-task-id",
        "macro_report": {"summary": "bullish"},
        "quant_proposal": {"signal": "buy"},
        "bullish_thesis": {"thesis": "up"},
        "bearish_thesis": {"thesis": "down"},
        "debate_history": [{"round": 1}],
        "debate_resolution": {"winner": "bull"},
        "weighted_consensus_score": 0.85,
        "merit_scores": {"axiom": 0.9},
        "soul_sync_context": {"synced": True},
        "risk_approved": True,
        "risk_notes": "approved",
        "execution_result": {"filled": True},
        "decision_card_audit_ref": "ref-123",
        "decision_card_status": "approved",
    }


def _mock_snapshot(status: str = "completed") -> CycleSnapshot:
    """Build a minimal CycleSnapshot for mocking."""
    kwargs = {
        "cycle_id": 42,
        "task_id": "test-task-id",
        "symbol": "BTC",
        "status": status,
    }
    if status == "failed":
        kwargs["error_context"] = {"error_type": "RuntimeError", "message": "boom"}
    elif status == "completed":
        kwargs.update({
            "macro_report": {"s": 1},
            "quant_proposal": {"s": 1},
            "bullish_thesis": {"s": 1},
            "bearish_thesis": {"s": 1},
            "debate_history": [{}],
            "debate_resolution": {"w": "bull"},
            "weighted_consensus_score": 0.8,
            "merit_scores": {"a": 0.9},
            "soul_sync_context": {"ok": True},
            "execution_result": {"done": True},
            "decision_card": {"id": "c1"},
        })
    return CycleSnapshot(**kwargs)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMainCLI:
    """Tests for the main() CLI function."""

    @patch("src.main._try_get_pool", return_value=None)
    @patch("src.main.setup_persistence", new_callable=AsyncMock)
    @patch("src.main.create_orchestrator_graph")
    @patch("src.main.CycleRunner")
    def test_analyze_outputs_valid_json(
        self, mock_runner_cls, mock_graph, mock_persist, mock_pool, capsys, monkeypatch
    ):
        """CLI outputs valid CycleSnapshot JSON to stdout on success."""
        monkeypatch.setattr(sys, "argv", ["main.py", "analyze", "BTC", "--mode", "paper"])

        mock_runner = MagicMock()
        mock_runner.run_cycle = AsyncMock(return_value=_mock_snapshot("completed"))
        mock_runner_cls.return_value = mock_runner

        from src.main import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["cycle_id"] == 42
        assert data["symbol"] == "BTC"
        assert data["status"] == "completed"

    @patch("src.main._try_get_pool", return_value=None)
    @patch("src.main.setup_persistence", new_callable=AsyncMock)
    @patch("src.main.create_orchestrator_graph")
    @patch("src.main.CycleRunner")
    def test_failed_cycle_outputs_json_with_status_failed(
        self, mock_runner_cls, mock_graph, mock_persist, mock_pool, capsys, monkeypatch
    ):
        """Failed cycles output JSON with status='failed' and error_context."""
        monkeypatch.setattr(sys, "argv", ["main.py", "analyze", "BTC", "--mode", "paper"])

        mock_runner = MagicMock()
        mock_runner.run_cycle = AsyncMock(side_effect=RuntimeError("kaboom"))
        mock_runner_cls.return_value = mock_runner

        from src.main import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["status"] == "failed"
        assert "error_context" in data
        assert data["error_context"]["error_type"] == "RuntimeError"

    def test_no_args_exits_nonzero(self, capsys, monkeypatch):
        """Running with no arguments prints help and exits non-zero."""
        monkeypatch.setattr(sys, "argv", ["main.py"])

        from src.main import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code != 0

    @patch("src.main._try_get_pool", return_value=None)
    @patch("src.main.setup_persistence", new_callable=AsyncMock)
    @patch("src.main.create_orchestrator_graph")
    @patch("src.main.CycleRunner")
    @patch("src.main.reload_souls")
    def test_reload_souls_flag(
        self, mock_reload, mock_runner_cls, mock_graph, mock_persist, mock_pool, capsys, monkeypatch
    ):
        """--reload-souls flag calls reload_souls() before running."""
        monkeypatch.setattr(sys, "argv", ["main.py", "analyze", "BTC", "--reload-souls"])

        mock_runner = MagicMock()
        mock_runner.run_cycle = AsyncMock(return_value=_mock_snapshot("completed"))
        mock_runner_cls.return_value = mock_runner

        from src.main import main

        with pytest.raises(SystemExit):
            main()

        mock_reload.assert_called_once()

    @patch("src.main._try_get_pool", return_value=None)
    @patch("src.main.setup_persistence", new_callable=AsyncMock)
    @patch("src.main.create_orchestrator_graph")
    @patch("src.main.CycleRunner")
    def test_logs_go_to_stderr_not_stdout(
        self, mock_runner_cls, mock_graph, mock_persist, mock_pool, capsys, monkeypatch
    ):
        """Logs go to stderr, JSON goes to stdout (no mixing)."""
        monkeypatch.setattr(sys, "argv", ["main.py", "analyze", "BTC", "--mode", "paper"])

        mock_runner = MagicMock()
        mock_runner.run_cycle = AsyncMock(return_value=_mock_snapshot("completed"))
        mock_runner_cls.return_value = mock_runner

        from src.main import main

        with pytest.raises(SystemExit):
            main()

        captured = capsys.readouterr()
        # stdout should be valid JSON only
        json.loads(captured.out)
        # stderr should not contain JSON output
        assert '"cycle_id"' not in captured.err
