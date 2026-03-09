"""Integration tests for CycleRunner post-cycle persona evaluation hook.

Phase 29, Plan 02, Task 1.
"""
import asyncio
import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.cycle_runner import CycleRunner
from src.core.cycle_snapshot import CycleSnapshot
from src.core.persona_scorer import PersonaScoreEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_runner(tmp_path: Path) -> CycleRunner:
    """Create a CycleRunner with a fake graph and no DB pool."""
    graph = AsyncMock()
    return CycleRunner(graph=graph, db_pool=None, base_dir=str(tmp_path))


def _make_snapshot(cycle_id: int = 42, status: str = "completed",
                   tmp_base: str = "/tmp/test_cycles") -> CycleSnapshot:
    return CycleSnapshot(
        cycle_id=cycle_id,
        task_id="task-abc",
        symbol="BTC/USD",
        status=status,
    )


def _make_final_state() -> dict:
    """Build a final_state dict with agent output fields."""
    return {
        "macro_report": {"summary": "bullish outlook"},
        "bullish_thesis": {"thesis": "buy BTC"},
        "bearish_thesis": {"thesis": "sell BTC"},
        "quant_proposal": {"signal": 0.8},
    }


def _make_score_entry(handle: str, composite: float = 0.75) -> PersonaScoreEntry:
    return PersonaScoreEntry(
        soul_handle=handle,
        consistency=composite,
        tone=composite,
        logic=composite,
        depth=composite,
        bias=composite,
        composite=composite,
        rationale="test",
    )


def _dummy_scores() -> dict:
    return {
        "AXIOM": _make_score_entry("AXIOM"),
        "MOMENTUM": _make_score_entry("MOMENTUM"),
        "CASSANDRA": _make_score_entry("CASSANDRA"),
        "SIGMA": _make_score_entry("SIGMA"),
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPostCycleHookFires:
    """Post-cycle hook fires for completed and rejected cycles."""

    def test_hook_fires_for_completed_cycle(self, tmp_path):
        """evaluate_all_agents is called with correct agent outputs for completed cycles."""
        runner = _make_runner(tmp_path)
        snapshot = _make_snapshot(status="completed", tmp_base=str(tmp_path))
        final_state = _make_final_state()

        mock_evaluate = AsyncMock(return_value=_dummy_scores())
        mock_persist = AsyncMock()

        async def run():
            with patch("src.core.cycle_runner.evaluate_all_agents", mock_evaluate), \
                 patch("src.core.cycle_runner.persist_persona_scores", mock_persist):
                # Write initial snapshot file so the update can read it
                runner._write_snapshot_file(snapshot)
                await runner._evaluate_persona_scores(snapshot, final_state)

        asyncio.run(run())

        mock_evaluate.assert_called_once()
        call_args = mock_evaluate.call_args
        agent_outputs = call_args[0][0]
        assert agent_outputs["AXIOM"] == {"summary": "bullish outlook"}
        assert agent_outputs["MOMENTUM"] == {"thesis": "buy BTC"}
        assert call_args[0][1] == 42  # cycle_id

    def test_hook_fires_for_rejected_cycle(self, tmp_path):
        """Post-cycle hook also fires for rejected cycles (agent memos exist)."""
        runner = _make_runner(tmp_path)
        snapshot = _make_snapshot(status="rejected", tmp_base=str(tmp_path))
        final_state = _make_final_state()

        mock_evaluate = AsyncMock(return_value=_dummy_scores())
        mock_persist = AsyncMock()

        async def run():
            with patch("src.core.cycle_runner.evaluate_all_agents", mock_evaluate), \
                 patch("src.core.cycle_runner.persist_persona_scores", mock_persist):
                runner._write_snapshot_file(snapshot)
                await runner._evaluate_persona_scores(snapshot, final_state)

        asyncio.run(run())

        mock_evaluate.assert_called_once()


class TestPostCycleHookSkipsFailed:
    """Post-cycle hook is skipped for failed cycles."""

    def test_hook_skipped_for_failed_cycle(self, tmp_path):
        """run_cycle does not call _evaluate_persona_scores for failed cycles."""
        runner = _make_runner(tmp_path)

        # Make graph.ainvoke raise to trigger failed status
        runner._graph.ainvoke = AsyncMock(side_effect=RuntimeError("graph boom"))

        mock_eval_method = AsyncMock()

        async def run():
            with patch.object(runner, "_evaluate_persona_scores", mock_eval_method):
                snapshot = await runner.run_cycle("test input", "BTC/USD")
            return snapshot

        snapshot = asyncio.run(run())

        assert snapshot.status == "failed"
        mock_eval_method.assert_not_called()


class TestPostCycleHookPersists:
    """Post-cycle hook persists scores to DB and updates snapshot file."""

    def test_hook_persists_scores(self, tmp_path):
        """persist_persona_scores is called with cycle_id and scores."""
        runner = _make_runner(tmp_path)
        snapshot = _make_snapshot(status="completed", tmp_base=str(tmp_path))
        final_state = _make_final_state()
        scores = _dummy_scores()

        mock_evaluate = AsyncMock(return_value=scores)
        mock_persist = AsyncMock()

        async def run():
            with patch("src.core.cycle_runner.evaluate_all_agents", mock_evaluate), \
                 patch("src.core.cycle_runner.persist_persona_scores", mock_persist):
                runner._write_snapshot_file(snapshot)
                await runner._evaluate_persona_scores(snapshot, final_state)

        asyncio.run(run())

        mock_persist.assert_called_once_with(42, scores)

    def test_hook_updates_snapshot_file(self, tmp_path):
        """After evaluation, snapshot.json is updated with persona_scores dict."""
        runner = _make_runner(tmp_path)
        snapshot = _make_snapshot(status="completed", tmp_base=str(tmp_path))
        final_state = _make_final_state()
        scores = _dummy_scores()

        mock_evaluate = AsyncMock(return_value=scores)
        mock_persist = AsyncMock()

        async def run():
            with patch("src.core.cycle_runner.evaluate_all_agents", mock_evaluate), \
                 patch("src.core.cycle_runner.persist_persona_scores", mock_persist):
                runner._write_snapshot_file(snapshot)
                await runner._evaluate_persona_scores(snapshot, final_state)

        asyncio.run(run())

        # Re-read snapshot file and check persona_scores
        snap_dir = Path(snapshot.snapshot_dir(base=str(tmp_path)))
        snap_file = snap_dir / "snapshot.json"
        data = json.loads(snap_file.read_text())
        assert "persona_scores" in data
        assert "AXIOM" in data["persona_scores"]


class TestPostCycleHookNeverCrashes:
    """Post-cycle hook catches all exceptions without crashing."""

    def test_evaluate_all_agents_raises(self, tmp_path):
        """If evaluate_all_agents raises, the hook logs but does not re-raise."""
        runner = _make_runner(tmp_path)
        snapshot = _make_snapshot(status="completed", tmp_base=str(tmp_path))
        final_state = _make_final_state()

        mock_evaluate = AsyncMock(side_effect=RuntimeError("eval boom"))

        async def run():
            with patch("src.core.cycle_runner.evaluate_all_agents", mock_evaluate), \
                 patch("src.core.cycle_runner.persist_persona_scores", AsyncMock()):
                runner._write_snapshot_file(snapshot)
                await runner._evaluate_persona_scores(snapshot, final_state)

        # Must not raise
        asyncio.run(run())

    def test_persist_raises(self, tmp_path):
        """If persist_persona_scores raises, the hook logs but does not re-raise."""
        runner = _make_runner(tmp_path)
        snapshot = _make_snapshot(status="completed", tmp_base=str(tmp_path))
        final_state = _make_final_state()

        mock_evaluate = AsyncMock(return_value=_dummy_scores())
        mock_persist = AsyncMock(side_effect=RuntimeError("DB boom"))

        async def run():
            with patch("src.core.cycle_runner.evaluate_all_agents", mock_evaluate), \
                 patch("src.core.cycle_runner.persist_persona_scores", mock_persist):
                runner._write_snapshot_file(snapshot)
                await runner._evaluate_persona_scores(snapshot, final_state)

        # Must not raise
        asyncio.run(run())


class TestPostCycleHookExtractsOutputs:
    """Post-cycle hook extracts agent outputs using HANDLE_TO_OUTPUT_FIELD."""

    def test_extracts_correct_fields(self, tmp_path):
        """Agent outputs are mapped from HANDLE_TO_OUTPUT_FIELD keys."""
        runner = _make_runner(tmp_path)
        snapshot = _make_snapshot(status="completed", tmp_base=str(tmp_path))
        final_state = _make_final_state()

        captured_outputs = {}

        async def capture_evaluate(agent_outputs, cycle_id):
            captured_outputs.update(agent_outputs)
            return _dummy_scores()

        async def run():
            with patch("src.core.cycle_runner.evaluate_all_agents", side_effect=capture_evaluate), \
                 patch("src.core.cycle_runner.persist_persona_scores", AsyncMock()):
                runner._write_snapshot_file(snapshot)
                await runner._evaluate_persona_scores(snapshot, final_state)

        asyncio.run(run())

        assert captured_outputs["AXIOM"] == {"summary": "bullish outlook"}
        assert captured_outputs["SIGMA"] == {"signal": 0.8}
        assert captured_outputs["CASSANDRA"] == {"thesis": "sell BTC"}
        assert captured_outputs["MOMENTUM"] == {"thesis": "buy BTC"}
