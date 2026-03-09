"""
Tests for src.core.cycle_runner — CycleRunner async wrapper.

Covers: completed/rejected/failed status paths, state isolation,
snapshot file writes, DB allocation/update, and field extraction.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.cycle_runner import CycleRunner
from src.core.cycle_snapshot import CycleSnapshot


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_completed_state() -> dict:
    """Return a dict mimicking a completed SwarmState after graph.ainvoke()."""
    return {
        "task_id": "test-task-001",
        "user_input": "Analyse BTC/USDT",
        "intent": "analysis",
        "messages": [{"role": "system", "content": "ok"}],
        "macro_report": {"summary": "bullish macro"},
        "quant_proposal": {"signal": "long", "confidence": 0.8},
        "bullish_thesis": {"thesis": "uptrend"},
        "bearish_thesis": {"thesis": "overextended"},
        "debate_resolution": {"winner": "bull", "margin": 0.6},
        "weighted_consensus_score": 0.72,
        "debate_history": [{"round": 1, "speaker": "bull"}],
        "risk_approval": {"approved": True},
        "consensus_score": 0.72,
        "compliance_flags": [],
        "risk_approved": True,
        "risk_notes": "Within limits",
        "final_decision": {"action": "buy"},
        "metadata": {"created_at": "2026-03-09"},
        "blackboard_session": "sess-001",
        "total_tokens": 500,
        "trade_history": [],
        "execution_mode": "paper",
        "data_fetcher_result": None,
        "knowledge_base_result": None,
        "backtest_result": None,
        "execution_result": {"fill": "BTC 0.1 @ 50000"},
        "decision_card_status": "written",
        "decision_card_error": None,
        "decision_card_audit_ref": "card-abc",
        "system_prompt": None,
        "active_persona": None,
        "merit_scores": {"AXIOM": {"composite": 0.65}},
        "soul_sync_context": {"AXIOM": "macro analyst"},
    }


def _make_mock_graph(return_state: dict | None = None, raise_exc: Exception | None = None) -> AsyncMock:
    """Create mock graph with ainvoke configured."""
    graph = AsyncMock()
    if raise_exc:
        graph.ainvoke.side_effect = raise_exc
    else:
        graph.ainvoke.return_value = return_state or _make_completed_state()
    return graph


def _make_mock_pool(cycle_id: int = 42) -> MagicMock:
    """Create mock db_pool that returns a cycle_id from INSERT RETURNING."""
    pool = MagicMock()
    conn = AsyncMock()
    cursor = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=(cycle_id,))
    conn.execute = AsyncMock(return_value=cursor)

    # pool.connection() is an async context manager
    conn_ctx = AsyncMock()
    conn_ctx.__aenter__ = AsyncMock(return_value=conn)
    conn_ctx.__aexit__ = AsyncMock(return_value=False)
    pool.connection = MagicMock(return_value=conn_ctx)

    return pool


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCycleRunnerCompleted:
    """run_cycle() with successful graph returns completed snapshot."""

    def test_completed_cycle_returns_snapshot(self, tmp_path):
        graph = _make_mock_graph()
        pool = _make_mock_pool(cycle_id=7)
        runner = CycleRunner(graph, db_pool=pool, base_dir=str(tmp_path / "cycles"))

        snapshot = asyncio.run(runner.run_cycle("Analyse BTC/USDT", "BTC/USDT"))

        assert isinstance(snapshot, CycleSnapshot)
        assert snapshot.status == "completed"
        assert snapshot.cycle_id == 7
        assert snapshot.symbol == "BTC/USDT"
        assert snapshot.macro_report is not None
        assert snapshot.execution_result is not None
        assert snapshot.merit_scores is not None
        assert snapshot.decision_card is not None


class TestCycleRunnerFailed:
    """run_cycle() with graph exception returns failed snapshot."""

    def test_failed_cycle_has_error_context(self, tmp_path):
        graph = _make_mock_graph(raise_exc=RuntimeError("Node exploded"))
        pool = _make_mock_pool(cycle_id=8)
        runner = CycleRunner(graph, db_pool=pool, base_dir=str(tmp_path / "cycles"))

        snapshot = asyncio.run(runner.run_cycle("Analyse ETH/USDT", "ETH/USDT"))

        assert snapshot.status == "failed"
        assert snapshot.error_context is not None
        assert "Node exploded" in snapshot.error_context["message"]
        assert snapshot.error_context["error_type"] == "RuntimeError"


class TestCycleRunnerRejected:
    """run_cycle() with risk_approved=False returns rejected snapshot."""

    def test_rejected_cycle_status(self, tmp_path):
        state = _make_completed_state()
        state["risk_approved"] = False
        state["execution_result"] = None
        state["decision_card_status"] = None
        state["decision_card_audit_ref"] = None
        graph = _make_mock_graph(return_state=state)
        pool = _make_mock_pool(cycle_id=9)
        runner = CycleRunner(graph, db_pool=pool, base_dir=str(tmp_path / "cycles"))

        snapshot = asyncio.run(runner.run_cycle("Analyse SOL/USDT", "SOL/USDT"))

        assert snapshot.status == "rejected"
        assert snapshot.risk_approved is False
        assert snapshot.macro_report is not None  # agent memos still present
        assert snapshot.execution_result is None
        assert snapshot.decision_card is None


class TestBuildInitialState:
    """_build_initial_state() produces fresh state each call."""

    def test_fresh_task_id_each_call(self):
        graph = _make_mock_graph()
        runner = CycleRunner(graph)

        state1 = runner._build_initial_state("input1")
        state2 = runner._build_initial_state("input2")

        assert state1["task_id"] != state2["task_id"]
        assert state1["user_input"] == "input1"
        assert state2["user_input"] == "input2"
        assert state1["messages"] == []
        assert state1["debate_history"] == []

    def test_has_all_swarm_state_keys(self):
        graph = _make_mock_graph()
        runner = CycleRunner(graph)

        state = runner._build_initial_state("test")

        required_keys = [
            "task_id", "user_input", "intent", "messages",
            "macro_report", "quant_proposal", "bullish_thesis",
            "bearish_thesis", "debate_resolution", "weighted_consensus_score",
            "debate_history", "risk_approval", "consensus_score",
            "compliance_flags", "risk_approved", "risk_notes",
            "final_decision", "metadata", "total_tokens",
            "trade_history", "execution_mode", "execution_result",
            "system_prompt", "active_persona", "merit_scores",
            "soul_sync_context",
        ]
        for key in required_keys:
            assert key in state, f"Missing key: {key}"


class TestExtractSnapshot:
    """_extract_snapshot() maps SwarmState fields to CycleSnapshot."""

    def test_completed_extraction(self):
        graph = _make_mock_graph()
        runner = CycleRunner(graph)
        final_state = _make_completed_state()

        snapshot = runner._extract_snapshot(
            cycle_id=1, task_id="t1", symbol="BTC/USDT",
            final_state=final_state, status="completed",
        )

        assert snapshot.macro_report == {"summary": "bullish macro"}
        assert snapshot.weighted_consensus_score == 0.72
        assert snapshot.merit_scores == {"AXIOM": {"composite": 0.65}}
        assert snapshot.decision_card is not None

    def test_failed_extraction_with_error(self):
        graph = _make_mock_graph()
        runner = CycleRunner(graph)

        snapshot = runner._extract_snapshot(
            cycle_id=2, task_id="t2", symbol="ETH/USDT",
            final_state={}, status="failed",
            error_ctx={"error_type": "RuntimeError", "message": "boom"},
        )

        assert snapshot.status == "failed"
        assert snapshot.error_context["message"] == "boom"


class TestWriteSnapshotFile:
    """_write_snapshot_file() creates directory and writes valid JSON."""

    def test_creates_directory_and_json(self, tmp_path):
        graph = _make_mock_graph()
        runner = CycleRunner(graph, base_dir=str(tmp_path / "cycles"))

        snapshot = CycleSnapshot(
            cycle_id=42, task_id="t-42", symbol="BTC/USDT",
            status="failed", error_context={"msg": "test"},
        )
        path = runner._write_snapshot_file(snapshot)

        assert path.exists()
        assert path.name == "snapshot.json"
        assert "000042" in str(path.parent)

        data = json.loads(path.read_text())
        assert data["cycle_id"] == 42
        assert data["status"] == "failed"


class TestValidateCompletedCalled:
    """validate_completed() is called for completed cycles."""

    def test_completed_calls_validate(self, tmp_path):
        # If a field were missing, validate_completed would raise
        graph = _make_mock_graph()
        pool = _make_mock_pool(cycle_id=10)
        runner = CycleRunner(graph, db_pool=pool, base_dir=str(tmp_path / "cycles"))

        # Should not raise since all fields are present
        snapshot = asyncio.run(runner.run_cycle("Analyse BTC/USDT", "BTC/USDT"))
        assert snapshot.status == "completed"


class TestAllocateCycleId:
    """_allocate_cycle_id() calls INSERT RETURNING on cycle_snapshots."""

    def test_allocate_with_db(self):
        graph = _make_mock_graph()
        pool = _make_mock_pool(cycle_id=99)
        runner = CycleRunner(graph, db_pool=pool)

        cid = asyncio.run(runner._allocate_cycle_id("BTC/USDT"))

        assert cid == 99
        # Verify INSERT was called
        conn_ctx = pool.connection.return_value
        conn = conn_ctx.__aenter__.return_value
        call_args = conn.execute.call_args[0][0]
        assert "INSERT" in call_args
        assert "cycle_snapshots" in call_args

    def test_allocate_without_db_returns_fallback(self):
        graph = _make_mock_graph()
        runner = CycleRunner(graph, db_pool=None)

        cid = asyncio.run(runner._allocate_cycle_id("BTC/USDT"))

        assert isinstance(cid, int)
        assert cid > 0


class TestUpdateCycleRow:
    """_update_cycle_row() calls UPDATE on cycle_snapshots."""

    def test_update_with_db(self):
        graph = _make_mock_graph()
        pool = _make_mock_pool()
        runner = CycleRunner(graph, db_pool=pool)

        snapshot = CycleSnapshot(
            cycle_id=42, task_id="t-42", symbol="BTC/USDT",
            status="completed", weighted_consensus_score=0.72,
        )
        asyncio.run(runner._update_cycle_row(snapshot))

        conn_ctx = pool.connection.return_value
        conn = conn_ctx.__aenter__.return_value
        call_args = conn.execute.call_args[0][0]
        assert "UPDATE" in call_args
        assert "cycle_snapshots" in call_args

    def test_update_without_db_is_noop(self):
        graph = _make_mock_graph()
        runner = CycleRunner(graph, db_pool=None)

        snapshot = CycleSnapshot(
            cycle_id=1, task_id="t-1", symbol="X",
            status="failed",
        )
        # Should not raise
        asyncio.run(runner._update_cycle_row(snapshot))


class TestStateIsolation:
    """Two consecutive run_cycle() calls produce independent states."""

    def test_no_accumulation(self, tmp_path):
        call_count = 0
        states_received = []

        async def capture_state(state, **kwargs):
            nonlocal call_count
            call_count += 1
            states_received.append(dict(state))
            result = _make_completed_state()
            result["task_id"] = state["task_id"]
            return result

        graph = AsyncMock()
        graph.ainvoke.side_effect = capture_state
        pool = _make_mock_pool(cycle_id=1)
        runner = CycleRunner(graph, db_pool=pool, base_dir=str(tmp_path / "cycles"))

        asyncio.run(runner.run_cycle("Run 1", "BTC/USDT"))
        asyncio.run(runner.run_cycle("Run 2", "BTC/USDT"))

        assert len(states_received) == 2
        assert states_received[0]["task_id"] != states_received[1]["task_id"]
        assert states_received[0]["messages"] == []
        assert states_received[1]["messages"] == []
        assert states_received[0]["user_input"] == "Run 1"
        assert states_received[1]["user_input"] == "Run 2"
