"""
tests.test_inter_agent_blackboard — Tests for the inter-agent filesystem Blackboard.

Covers: write, read, session isolation, missing slot, and locking logic.
"""

import pytest
import concurrent.futures
from pathlib import Path
from src.core.blackboard import InterAgentBlackboard


def test_inter_agent_write_and_read(tmp_path):
    """Written data is retrievable within a session."""
    board = InterAgentBlackboard(base_dir=tmp_path)
    session_id = "test-session-1"
    key = "objective"
    value = {"task": "analyse BTC", "tokens": 100}

    board.write_state(session_id, key, value)
    result = board.read_state(session_id, key)

    assert result == value


def test_inter_agent_read_missing_slot_returns_none(tmp_path):
    """Reading a slot that was never written returns None."""
    board = InterAgentBlackboard(base_dir=tmp_path)
    session_id = "test-session-2"

    result = board.read_state(session_id, "missing")

    assert result is None


def test_inter_agent_session_isolation(tmp_path):
    """Sessions are isolated from each other."""
    board = InterAgentBlackboard(base_dir=tmp_path)
    key = "data"

    board.write_state("session-A", key, {"val": "A"})
    board.write_state("session-B", key, {"val": "B"})

    assert board.read_state("session-A", key) == {"val": "A"}
    assert board.read_state("session-B", key) == {"val": "B"}


def test_inter_agent_list_keys(tmp_path):
    """list_keys returns all key names written to a session."""
    board = InterAgentBlackboard(base_dir=tmp_path)
    session_id = "test-session-3"
    board.write_state(session_id, "key1", {})
    board.write_state(session_id, "key2", {})

    keys = board.list_keys(session_id)

    assert set(keys) == {"key1", "key2"}


def test_inter_agent_concurrent_writes(tmp_path):
    """Concurrent writes do not corrupt data (smoke test for locking)."""
    board = InterAgentBlackboard(base_dir=tmp_path)
    session_id = "concurrent-session"
    key = "counter"

    def write_val(i):
        board.write_state(session_id, key, {"val": i})
        return board.read_state(session_id, key)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(write_val, range(20)))

    # Each read should return a valid dict from one of the writes
    for res in results:
        assert isinstance(res, dict)
        assert "val" in res
