"""
Integration tests for CLI entry point (src/main.py).

Tests exercise main() in-process with mocked graph/DB to verify
end-to-end CLI behavior without requiring PostgreSQL or API keys.
"""

import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.cycle_snapshot import CycleSnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_snapshot(status: str = "completed") -> CycleSnapshot:
    """Build a minimal CycleSnapshot for mocking."""
    kwargs = {
        "cycle_id": 99,
        "task_id": "integration-test",
        "symbol": "BTC",
        "status": status,
    }
    if status == "failed":
        kwargs["error_context"] = {"error_type": "ValueError", "message": "test error"}
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
# Integration Tests
# ---------------------------------------------------------------------------


class TestCLIIntegration:
    """Integration tests exercising the full CLI flow with mocked backends."""

    @patch("src.main._try_get_pool", return_value=None)
    @patch("src.main.setup_persistence", new_callable=AsyncMock)
    @patch("src.main.create_orchestrator_graph")
    @patch("src.main.CycleRunner")
    def test_analyze_outputs_valid_json(
        self, mock_runner_cls, mock_graph, mock_persist, mock_pool, capsys, monkeypatch
    ):
        """Full CLI flow: analyze command outputs valid CycleSnapshot JSON."""
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
        assert "cycle_id" in data
        assert data["symbol"] == "BTC"
        assert data["status"] == "completed"

    @patch("src.main._try_get_pool", return_value=None)
    @patch("src.main.setup_persistence", new_callable=AsyncMock)
    @patch("src.main.create_orchestrator_graph")
    @patch("src.main.CycleRunner")
    def test_output_json_has_snapshot_fields(
        self, mock_runner_cls, mock_graph, mock_persist, mock_pool, capsys, monkeypatch
    ):
        """Output JSON contains key CycleSnapshot fields."""
        monkeypatch.setattr(sys, "argv", ["main.py", "analyze", "ETH", "--mode", "paper"])

        snapshot = _mock_snapshot("completed")
        snapshot_dict = snapshot.model_dump(mode="json")

        mock_runner = MagicMock()
        mock_runner.run_cycle = AsyncMock(return_value=snapshot)
        mock_runner_cls.return_value = mock_runner

        from src.main import main

        with pytest.raises(SystemExit):
            main()

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["cycle_id"] == 99
        assert data["task_id"] == "integration-test"
        assert data["symbol"] == "BTC"  # symbol comes from the snapshot mock
        assert "timestamp" in data
        assert "status" in data

    def test_no_args_exits_nonzero(self, capsys, monkeypatch):
        """Running with no subcommand exits non-zero."""
        monkeypatch.setattr(sys, "argv", ["main.py"])

        from src.main import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code != 0

    def test_help_flag_exits_zero(self, monkeypatch):
        """--help exits 0 and prints help text."""
        monkeypatch.setattr(sys, "argv", ["main.py", "analyze", "--help"])

        from src.main import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        # argparse exits 0 on --help
        assert exc_info.value.code == 0

    @patch("src.main._try_get_pool", return_value=None)
    @patch("src.main.setup_persistence", new_callable=AsyncMock)
    @patch("src.main.create_orchestrator_graph")
    @patch("src.main.CycleRunner")
    def test_failed_cycle_outputs_json(
        self, mock_runner_cls, mock_graph, mock_persist, mock_pool, capsys, monkeypatch
    ):
        """Failed graph execution outputs JSON with status='failed'."""
        monkeypatch.setattr(sys, "argv", ["main.py", "analyze", "BTC", "--mode", "paper"])

        mock_runner = MagicMock()
        mock_runner.run_cycle = AsyncMock(side_effect=RuntimeError("graph exploded"))
        mock_runner_cls.return_value = mock_runner

        from src.main import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["status"] == "failed"
        assert data["error_context"]["error_type"] == "RuntimeError"
        assert "graph exploded" in data["error_context"]["message"]

    @patch("src.main._try_get_pool", return_value=None)
    @patch("src.main.setup_persistence", new_callable=AsyncMock)
    @patch("src.main.create_orchestrator_graph")
    @patch("src.main.CycleRunner")
    @patch("src.main.reload_souls")
    def test_reload_souls_flag(
        self, mock_reload, mock_runner_cls, mock_graph, mock_persist, mock_pool, capsys, monkeypatch
    ):
        """--reload-souls invokes reload_souls() before pipeline execution."""
        monkeypatch.setattr(sys, "argv", ["main.py", "analyze", "BTC", "--reload-souls"])

        mock_runner = MagicMock()
        mock_runner.run_cycle = AsyncMock(return_value=_mock_snapshot("completed"))
        mock_runner_cls.return_value = mock_runner

        from src.main import main

        with pytest.raises(SystemExit):
            main()

        mock_reload.assert_called_once()
