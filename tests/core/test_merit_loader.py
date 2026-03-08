"""Merit loader node tests — Plan 02 implementation."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.kami import ALL_SOUL_HANDLES, DEFAULT_MERIT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pool_mock(rows=None):
    """Return a mock get_pool() that yields rows from agent_merit_scores query."""
    if rows is None:
        rows = []

    cur_mock = AsyncMock()

    # Simulate async for loop: __aiter__ / __anext__
    async def _aiter(self):
        for row in rows:
            yield row

    cur_mock.__aiter__ = _aiter
    cur_mock.execute = AsyncMock()

    # cursor context manager
    cur_ctx = AsyncMock()
    cur_ctx.__aenter__ = AsyncMock(return_value=cur_mock)
    cur_ctx.__aexit__ = AsyncMock(return_value=False)

    # connection context manager
    conn_mock = AsyncMock()
    conn_mock.cursor = MagicMock(return_value=cur_ctx)

    conn_ctx = AsyncMock()
    conn_ctx.__aenter__ = AsyncMock(return_value=conn_mock)
    conn_ctx.__aexit__ = AsyncMock(return_value=False)

    pool_mock = MagicMock()
    pool_mock.connection = MagicMock(return_value=conn_ctx)

    return pool_mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_merit_loader_cold_start():
    """merit_loader populates state from DB; cold-start defaults to 0.5 for all handles
    when DB returns no rows."""
    from src.graph.nodes.merit_loader import merit_loader_node

    pool_mock = _make_pool_mock(rows=[])  # DB empty → cold-start

    async def run():
        with patch("src.graph.nodes.merit_loader.get_pool", return_value=pool_mock):
            state = {"merit_scores": None}
            result = await merit_loader_node(state)
        return result

    result = asyncio.run(run())

    assert "merit_scores" in result
    scores = result["merit_scores"]

    # All soul handles must be present
    for handle in ALL_SOUL_HANDLES:
        assert handle in scores, f"Cold-start missing handle: {handle}"
        entry = scores[handle]
        assert entry["accuracy"] == DEFAULT_MERIT
        assert entry["recovery"] == DEFAULT_MERIT
        assert entry["consensus"] == DEFAULT_MERIT
        assert entry["fidelity"] == DEFAULT_MERIT
        assert entry["composite"] == DEFAULT_MERIT


def test_merit_scores_field_no_accumulation():
    """Calling merit_loader twice returns the same value — no list growth or dict merge."""
    from src.graph.nodes.merit_loader import merit_loader_node

    pool_mock = _make_pool_mock(rows=[])

    async def run():
        with patch("src.graph.nodes.merit_loader.get_pool", return_value=pool_mock):
            state = {"merit_scores": None}
            result1 = await merit_loader_node(state)
            # Second call: state still has None (simulating first call not yet applied)
            result2 = await merit_loader_node(state)
        return result1, result2

    result1, result2 = asyncio.run(run())

    # Both calls should return the same shape — no accumulation
    assert result1 == result2
    scores1 = result1["merit_scores"]
    scores2 = result2["merit_scores"]
    assert set(scores1.keys()) == set(scores2.keys())
    for handle in ALL_SOUL_HANDLES:
        assert scores1[handle] == scores2[handle]


def test_merit_loader_idempotent():
    """When state['merit_scores'] is already a non-None dict, merit_loader returns {}
    without making any DB call."""
    from src.graph.nodes.merit_loader import merit_loader_node

    pool_mock = _make_pool_mock(rows=[])

    async def run():
        with patch("src.graph.nodes.merit_loader.get_pool", return_value=pool_mock) as mock_get_pool:
            pre_populated = {"AXIOM": {"composite": 0.79, "accuracy": 0.7}}
            state = {"merit_scores": pre_populated}
            result = await merit_loader_node(state)
        return result, mock_get_pool

    result, mock_get_pool = asyncio.run(run())

    # Should return {} — idempotency guard fired
    assert result == {}
    # DB must NOT have been called
    pool_mock.connection.assert_not_called()


def test_merit_loader_reads_db_values():
    """When DB returns a row for AXIOM, that row's composite and dimensions are used."""
    from src.graph.nodes.merit_loader import merit_loader_node

    axiom_dims = {"accuracy": 0.71, "recovery": 0.94, "consensus": 0.63, "fidelity": 1.0}
    db_rows = [
        ("AXIOM", 0.79, axiom_dims),
    ]
    pool_mock = _make_pool_mock(rows=db_rows)

    async def run():
        with patch("src.graph.nodes.merit_loader.get_pool", return_value=pool_mock):
            state = {"merit_scores": None}
            result = await merit_loader_node(state)
        return result

    result = asyncio.run(run())

    scores = result["merit_scores"]
    assert "AXIOM" in scores
    axiom_entry = scores["AXIOM"]
    assert axiom_entry["composite"] == round(0.79, 4)
    # Other handles not in DB should get defaults
    for handle in ALL_SOUL_HANDLES:
        if handle != "AXIOM":
            assert scores[handle]["composite"] == DEFAULT_MERIT
