"""Tests for src.cli.replay — replay subcommand handlers."""

import io
import json
from argparse import Namespace
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from rich.console import Console

from src.core.cycle_snapshot import CycleSnapshot


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


def _make_snapshot(**overrides) -> dict:
    """Return a minimal valid CycleSnapshot dict with optional overrides."""
    base = {
        "cycle_id": 42,
        "task_id": "test-task",
        "symbol": "BTC",
        "timestamp": "2026-03-09T12:00:00+00:00",
        "status": "completed",
        "macro_report": {"analysis": "Macro looks bullish"},
        "quant_proposal": {"analysis": "Quant model suggests buy"},
        "bullish_thesis": {"analysis": "Strong momentum indicators"},
        "bearish_thesis": {"analysis": "Some risk factors present"},
        "debate_history": [
            {"round": 1, "speaker": "MOMENTUM", "argument": "Buy signal strong"},
            {"round": 2, "speaker": "CASSANDRA", "argument": "Caution warranted"},
        ],
        "debate_resolution": {"summary": "Consensus reached: moderate buy"},
        "weighted_consensus_score": 0.72,
        "merit_scores": {
            "AXIOM": {
                "accuracy": 0.5,
                "recovery": 0.5,
                "consensus": 0.5,
                "fidelity": 0.5,
                "composite": 0.50,
            },
            "MOMENTUM": {
                "accuracy": 0.5,
                "recovery": 0.62,
                "consensus": 0.48,
                "fidelity": 0.5,
                "composite": 0.52,
            },
            "CASSANDRA": {
                "accuracy": 0.5,
                "recovery": 0.45,
                "consensus": 0.55,
                "fidelity": 0.5,
                "composite": 0.50,
            },
        },
        "soul_sync_context": {
            "MOMENTUM": "MOMENTUM public summary",
        },
        "risk_approved": True,
        "risk_notes": "Within limits",
        "execution_result": {"order_id": "test-123"},
        "decision_card": {
            "action": "BUY",
            "confidence": 0.72,
            "symbol": "BTC",
        },
    }
    base.update(overrides)
    return base


def _make_snapshot_obj(**overrides) -> CycleSnapshot:
    """Return a CycleSnapshot model instance."""
    return CycleSnapshot.model_validate(_make_snapshot(**overrides))


@pytest.fixture
def tmp_cycles(tmp_path):
    """Write 2 snapshot.json files to tmp_path and return the base dir string."""
    import os

    for snap_data in [
        _make_snapshot(cycle_id=41, timestamp="2026-03-09T11:00:00+00:00"),
        _make_snapshot(cycle_id=42, timestamp="2026-03-09T12:00:00+00:00"),
        _make_snapshot(
            cycle_id=43,
            symbol="ETH",
            timestamp="2026-03-09T13:00:00+00:00",
            weighted_consensus_score=0.55,
        ),
    ]:
        cid = str(snap_data["cycle_id"]).zfill(6)
        d = tmp_path / cid
        d.mkdir()
        (d / "snapshot.json").write_text(json.dumps(snap_data))

    return str(tmp_path)


# ---------------------------------------------------------------------------
# handle_list tests
# ---------------------------------------------------------------------------


class TestHandleList:
    def test_list_json_returns_valid_array(self, tmp_cycles):
        from src.cli.replay import handle_list

        args = Namespace(
            symbol=None, status=None, limit=None, json=True
        )
        buf = io.StringIO()
        code = handle_list(args, base_dir=tmp_cycles, stdout=buf)
        assert code == 0
        data = json.loads(buf.getvalue())
        assert isinstance(data, list)
        assert len(data) == 3
        # Newest first
        assert data[0]["cycle_id"] == 43

    def test_list_rich_renders_table(self, tmp_cycles):
        from src.cli.replay import handle_list

        args = Namespace(
            symbol=None, status=None, limit=None, json=False
        )
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        code = handle_list(args, base_dir=tmp_cycles, console=console)
        assert code == 0
        output = buf.getvalue()
        assert "BTC" in output
        assert "ETH" in output
        assert "42" in output

    def test_list_filtered_by_symbol(self, tmp_cycles):
        from src.cli.replay import handle_list

        args = Namespace(
            symbol="BTC", status=None, limit=None, json=True
        )
        buf = io.StringIO()
        code = handle_list(args, base_dir=tmp_cycles, stdout=buf)
        assert code == 0
        data = json.loads(buf.getvalue())
        assert all(c["symbol"] == "BTC" for c in data)
        assert len(data) == 2


# ---------------------------------------------------------------------------
# handle_show tests
# ---------------------------------------------------------------------------


class TestHandleShow:
    def test_show_json_returns_full_snapshot(self, tmp_cycles):
        from src.cli.replay import handle_show

        args = Namespace(cycle_id=42, json=True)
        buf = io.StringIO()
        code = handle_show(args, base_dir=tmp_cycles, stdout=buf)
        assert code == 0
        data = json.loads(buf.getvalue())
        assert data["cycle_id"] == 42
        assert data["symbol"] == "BTC"
        assert "merit_scores" in data

    def test_show_missing_cycle_returns_1(self, tmp_cycles):
        from src.cli.replay import handle_show

        args = Namespace(cycle_id=999, json=False)
        buf = io.StringIO()
        err_console = Console(file=buf, force_terminal=False, width=120)
        code = handle_show(args, base_dir=tmp_cycles, console=err_console)
        assert code == 1

    def test_show_renders_merit_bars(self, tmp_cycles):
        from src.cli.replay import handle_show

        args = Namespace(cycle_id=42, json=False)
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        code = handle_show(args, base_dir=tmp_cycles, console=console)
        assert code == 0
        output = buf.getvalue()
        # Should contain agent names
        assert "AXIOM" in output
        assert "MOMENTUM" in output
        assert "CASSANDRA" in output
        # Should contain bar chars and numeric values
        assert "\u2588" in output  # block character
        assert "0.50" in output or "0.52" in output

    def test_show_renders_drift_annotation(self, tmp_cycles):
        from src.cli.replay import handle_show

        args = Namespace(cycle_id=42, json=False)
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        code = handle_show(args, base_dir=tmp_cycles, console=console)
        assert code == 0
        output = buf.getvalue()
        # MOMENTUM has soul_sync_context entry -> drift annotation
        assert "DRIFT" in output or "drift" in output.lower()

    def test_show_renders_token_usage(self, tmp_cycles):
        """handle_show renders token usage inline when present."""
        from src.cli.replay import handle_show
        import os

        # Write a cycle with token_usage
        snap_data = _make_snapshot(
            cycle_id=50,
            token_usage={
                "macro_analyst": {
                    "input_tokens": 500,
                    "output_tokens": 200,
                    "total_tokens": 700,
                    "usd_cost": 0.0975,
                },
                "quant_modeler": {
                    "input_tokens": 300,
                    "output_tokens": 100,
                    "total_tokens": 400,
                    "usd_cost": 0.0525,
                },
            },
        )
        d = os.path.join(tmp_cycles, "000050")
        os.makedirs(d)
        with open(os.path.join(d, "snapshot.json"), "w") as f:
            json.dump(snap_data, f)

        args = Namespace(cycle_id=50, json=False)
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        code = handle_show(args, base_dir=tmp_cycles, console=console)
        assert code == 0
        output = buf.getvalue()
        assert "Token Usage" in output
        assert "macro_analyst" in output
        assert "1,100" in output  # total tokens = 700 + 400

    def test_show_handles_failed_cycle(self, tmp_cycles):
        """Failed cycle with partial data should not crash."""
        from src.cli.replay import handle_show

        # Write a failed cycle with minimal data
        import os

        fail_dir = os.path.join(tmp_cycles, "000099")
        os.makedirs(fail_dir)
        fail_snap = {
            "cycle_id": 99,
            "task_id": "fail-task",
            "symbol": "BTC",
            "timestamp": "2026-03-09T14:00:00+00:00",
            "status": "failed",
            "error_context": {"error_type": "RuntimeError", "message": "boom"},
        }
        with open(os.path.join(fail_dir, "snapshot.json"), "w") as f:
            json.dump(fail_snap, f)

        args = Namespace(cycle_id=99, json=False)
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        code = handle_show(args, base_dir=tmp_cycles, console=console)
        assert code == 0
        output = buf.getvalue()
        assert "failed" in output.lower() or "Error" in output


# ---------------------------------------------------------------------------
# handle_compare tests
# ---------------------------------------------------------------------------


class TestHandleCompare:
    def test_compare_same_symbol_produces_deltas(self, tmp_cycles):
        from src.cli.replay import handle_compare

        args = Namespace(cycle_id_1=41, cycle_id_2=42, json=False)
        buf = io.StringIO()
        console = Console(file=buf, force_terminal=True, width=120)
        code = handle_compare(args, base_dir=tmp_cycles, console=console)
        assert code == 0
        output = buf.getvalue()
        # Should show directional arrows
        assert "\u25b2" in output or "\u25bc" in output or "0.00" in output

    def test_compare_different_symbol_returns_1(self, tmp_cycles):
        from src.cli.replay import handle_compare

        args = Namespace(cycle_id_1=42, cycle_id_2=43, json=False)
        buf = io.StringIO()
        err_buf = io.StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        err_console = Console(file=err_buf, force_terminal=False, width=120)
        code = handle_compare(
            args, base_dir=tmp_cycles, console=console, err_console=err_console
        )
        assert code == 1

    def test_compare_json_returns_structured_delta(self, tmp_cycles):
        from src.cli.replay import handle_compare

        args = Namespace(cycle_id_1=41, cycle_id_2=42, json=True)
        buf = io.StringIO()
        code = handle_compare(args, base_dir=tmp_cycles, stdout=buf)
        assert code == 0
        data = json.loads(buf.getvalue())
        assert "consensus" in data
        assert "from" in data["consensus"]
        assert "to" in data["consensus"]
        assert "delta" in data["consensus"]
        assert "merit_shifts" in data
