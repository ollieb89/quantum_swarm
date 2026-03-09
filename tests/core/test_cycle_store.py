"""
Tests for src.core.cycle_store — read-only cycle data access layer.

Covers filesystem loading, DB listing, fallback, filters, and error cases.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.cycle_store import (
    list_cycles,
    list_cycles_db,
    list_cycles_filesystem,
    load_cycle,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_cycles_dir(tmp_path: Path) -> Path:
    """Create a temp directory with 3 fake cycle snapshots."""
    base = tmp_path / "cycles"
    base.mkdir()

    # Cycle 1 — completed, BTC
    c1 = base / "000001"
    c1.mkdir()
    (c1 / "snapshot.json").write_text(
        json.dumps(
            {
                "cycle_id": 1,
                "task_id": "task-aaa",
                "symbol": "BTC/USD",
                "timestamp": "2026-03-01T10:00:00+00:00",
                "status": "completed",
                "macro_report": {"data": "ok"},
                "quant_proposal": {"data": "ok"},
                "bullish_thesis": {"data": "ok"},
                "bearish_thesis": {"data": "ok"},
                "debate_history": [{"round": 1}],
                "debate_resolution": {"winner": "bull"},
                "weighted_consensus_score": 0.75,
                "merit_scores": {"AXIOM": 0.9},
                "soul_sync_context": {"sync": True},
                "execution_result": {"filled": True},
                "decision_card": {"action": "buy"},
            }
        )
    )

    # Cycle 2 — failed, ETH
    c2 = base / "000002"
    c2.mkdir()
    (c2 / "snapshot.json").write_text(
        json.dumps(
            {
                "cycle_id": 2,
                "task_id": "task-bbb",
                "symbol": "ETH/USD",
                "timestamp": "2026-03-02T12:00:00+00:00",
                "status": "failed",
                "error_context": {"reason": "timeout"},
            }
        )
    )

    # Cycle 3 — rejected, BTC
    c3 = base / "000003"
    c3.mkdir()
    (c3 / "snapshot.json").write_text(
        json.dumps(
            {
                "cycle_id": 3,
                "task_id": "task-ccc",
                "symbol": "BTC/USD",
                "timestamp": "2026-03-03T08:00:00+00:00",
                "status": "rejected",
                "weighted_consensus_score": 0.3,
                "risk_approved": False,
                "risk_notes": "Too risky",
            }
        )
    )

    return base


# ---------------------------------------------------------------------------
# load_cycle
# ---------------------------------------------------------------------------


class TestLoadCycle:
    def test_load_cycle_returns_valid_snapshot(self, tmp_cycles_dir: Path):
        snap = load_cycle(1, base_dir=str(tmp_cycles_dir))
        assert snap.cycle_id == 1
        assert snap.symbol == "BTC/USD"
        assert snap.status == "completed"
        assert snap.weighted_consensus_score == 0.75

    def test_load_cycle_raises_for_missing_id(self, tmp_cycles_dir: Path):
        with pytest.raises(FileNotFoundError, match="999"):
            load_cycle(999, base_dir=str(tmp_cycles_dir))

    def test_load_cycle_handles_failed_cycle(self, tmp_cycles_dir: Path):
        snap = load_cycle(2, base_dir=str(tmp_cycles_dir))
        assert snap.status == "failed"
        assert snap.error_context == {"reason": "timeout"}
        # Optional fields should be None
        assert snap.macro_report is None
        assert snap.decision_card is None

    def test_load_cycle_handles_rejected_cycle(self, tmp_cycles_dir: Path):
        snap = load_cycle(3, base_dir=str(tmp_cycles_dir))
        assert snap.status == "rejected"
        assert snap.risk_approved is False


# ---------------------------------------------------------------------------
# list_cycles_filesystem
# ---------------------------------------------------------------------------


class TestListCyclesFilesystem:
    def test_returns_sorted_newest_first(self, tmp_cycles_dir: Path):
        results = list_cycles_filesystem(base_dir=str(tmp_cycles_dir))
        assert len(results) == 3
        # Cycle 3 is newest (March 3), then 2 (March 2), then 1 (March 1)
        assert results[0]["cycle_id"] == 3
        assert results[1]["cycle_id"] == 2
        assert results[2]["cycle_id"] == 1

    def test_symbol_filter(self, tmp_cycles_dir: Path):
        results = list_cycles_filesystem(
            base_dir=str(tmp_cycles_dir), symbol="BTC/USD"
        )
        assert len(results) == 2
        assert all(r["symbol"] == "BTC/USD" for r in results)

    def test_status_filter(self, tmp_cycles_dir: Path):
        results = list_cycles_filesystem(
            base_dir=str(tmp_cycles_dir), status="failed"
        )
        assert len(results) == 1
        assert results[0]["cycle_id"] == 2

    def test_limit(self, tmp_cycles_dir: Path):
        results = list_cycles_filesystem(base_dir=str(tmp_cycles_dir), limit=2)
        assert len(results) == 2

    def test_empty_when_base_dir_missing(self, tmp_path: Path):
        results = list_cycles_filesystem(base_dir=str(tmp_path / "nonexistent"))
        assert results == []

    def test_metadata_keys(self, tmp_cycles_dir: Path):
        results = list_cycles_filesystem(base_dir=str(tmp_cycles_dir))
        expected_keys = {"cycle_id", "symbol", "status", "timestamp", "consensus_score"}
        for r in results:
            assert set(r.keys()) == expected_keys


# ---------------------------------------------------------------------------
# list_cycles_db
# ---------------------------------------------------------------------------


class TestListCyclesDb:
    def test_queries_db_with_no_filters(self):
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_pool.connection.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_cursor.fetchall = AsyncMock(
            return_value=[
                (1, "BTC/USD", "completed", datetime(2026, 3, 1, tzinfo=timezone.utc), 0.75),
            ]
        )
        mock_cursor.description = [
            ("cycle_id",), ("symbol",), ("status",), ("timestamp",), ("consensus_score",),
        ]

        result = asyncio.run(list_cycles_db(mock_pool))
        assert len(result) == 1
        assert result[0]["cycle_id"] == 1
        assert result[0]["symbol"] == "BTC/USD"

    def test_queries_db_with_filters(self):
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.connection.return_value.__aenter__ = AsyncMock(
            return_value=mock_conn
        )
        mock_pool.connection.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_cursor.fetchall = AsyncMock(return_value=[])
        mock_cursor.description = [
            ("cycle_id",), ("symbol",), ("status",), ("timestamp",), ("consensus_score",),
        ]

        result = asyncio.run(
            list_cycles_db(mock_pool, symbol="ETH/USD", status="failed", limit=5)
        )
        assert result == []
        # Verify SQL was called with params
        call_args = mock_conn.execute.call_args
        sql = call_args[0][0]
        assert "symbol" in sql
        assert "status" in sql
        assert "LIMIT" in sql


# ---------------------------------------------------------------------------
# list_cycles (unified)
# ---------------------------------------------------------------------------


class TestListCycles:
    def test_uses_filesystem_when_pool_is_none(self, tmp_cycles_dir: Path):
        result = asyncio.run(
            list_cycles(pool=None, base_dir=str(tmp_cycles_dir))
        )
        assert len(result) == 3

    def test_falls_back_to_filesystem_on_db_error(self, tmp_cycles_dir: Path):
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__aenter__ = AsyncMock(
            side_effect=Exception("DB down")
        )
        mock_pool.connection.return_value.__aexit__ = AsyncMock(return_value=False)

        result = asyncio.run(
            list_cycles(pool=mock_pool, base_dir=str(tmp_cycles_dir))
        )
        # Should fall back to filesystem
        assert len(result) == 3
