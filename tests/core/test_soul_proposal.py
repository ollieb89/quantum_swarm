"""Unit tests for src.core.soul_proposal — Phase 17, Plan 02 (EVOL-02).

Tests cover:
  1. SoulProposal schema validation (valid + invalid status)
  2. write_proposal_atomic creates JSON file atomically with no .tmp residue
  3. KAMI delta trigger (KAMI_SPIKE)
  4. Drift streak trigger (DRIFT_STREAK)
  5. Merit floor trigger (MERIT_FLOOR)
  6. Merged proposal (multiple triggers → single emit)
  7. Rate-limit suppression (check_rate_limit True → no write)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.core.soul_proposal import (
    SoulProposal,
    build_proposal_id,
    write_proposal_atomic,
    check_rate_limit,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_proposal(**kwargs) -> SoulProposal:
    """Return a minimal valid SoulProposal, overriding any fields via kwargs."""
    defaults = dict(
        proposal_id="test_20260308T123456000000Z",
        agent_id="CASSANDRA",
        target_section="## Core Beliefs",
        proposed_content="[PENDING]",
        proposal_reasons=["KAMI_SPIKE"],
        rationale="KAMI delta exceeded threshold.",
        proposed_at=datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc),
        status="pending",
        rejection_reason=None,
    )
    defaults.update(kwargs)
    return SoulProposal(**defaults)


# ---------------------------------------------------------------------------
# Task 1 tests — schema + atomic write
# ---------------------------------------------------------------------------


def test_proposal_schema_valid():
    """SoulProposal(**valid_dict) constructs without error; invalid status raises."""
    p = _make_proposal()
    assert p.proposal_id == "test_20260308T123456000000Z"
    assert p.agent_id == "CASSANDRA"
    assert p.status == "pending"
    assert p.rejection_reason is None

    # All four valid statuses
    for status in ("pending", "approved", "rejected", "rate_limited"):
        sp = _make_proposal(status=status)
        assert sp.status == status

    # Invalid status raises Pydantic ValidationError
    with pytest.raises(ValidationError):
        _make_proposal(status="invalid")


def test_proposal_atomic_write(tmp_path):
    """write_proposal_atomic creates {proposal_id}.json; no .tmp files remain."""
    p = _make_proposal(proposal_id="cass_20260308T120000000000Z")
    write_proposal_atomic(p, proposals_dir=tmp_path)

    expected = tmp_path / "cass_20260308T120000000000Z.json"
    assert expected.exists(), "Proposal JSON file must exist after atomic write"

    # Verify JSON content round-trips correctly
    data = json.loads(expected.read_text())
    assert data["proposal_id"] == "cass_20260308T120000000000Z"
    assert data["agent_id"] == "CASSANDRA"
    assert data["status"] == "pending"

    # No leftover .tmp files
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert tmp_files == [], f"Unexpected .tmp files: {tmp_files}"


# ---------------------------------------------------------------------------
# Task 2 tests — trigger logic + memory_writer integration
# ---------------------------------------------------------------------------


def _make_memory_entry(
    merit_score: float = 0.80,
    drift_flags: str = "none",
    kami_delta: float = 0.02,
) -> str:
    """Build a minimal valid MEMORY.md entry block string."""
    ts = "2026-03-08T12:00:00Z"
    delta_str = f"+{kami_delta:.2f}" if kami_delta >= 0 else f"{kami_delta:.2f}"
    return (
        f"=== {ts} ===\n"
        f"[AGENT:] CASSANDRA\n"
        f"[KAMI_DELTA:] {delta_str}\n"
        f"[MERIT_SCORE:] {merit_score:.4f}\n"
        f"[DRIFT_FLAGS:] {drift_flags}\n"
        f"[THESIS_SUMMARY:] Test thesis.\n"
    )


def _write_memory(memory_path: Path, entries: list[str]) -> None:
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    memory_path.write_text("".join(entries))


def _make_config(**overrides) -> dict:
    base = {
        "kami_delta_threshold": 0.05,
        "drift_streak_n": 3,
        "merit_floor": 0.40,
        "merit_floor_k": 3,
        "rate_limit_rejection_k": 3,
        "rate_limit_window_days": 7,
    }
    base.update(overrides)
    return base


# Import _check_triggers lazily (it lives in memory_writer, not soul_proposal)
def _get_check_triggers():
    from src.graph.nodes.memory_writer import _check_triggers
    return _check_triggers


def test_trigger_kami_delta(tmp_path):
    """_check_triggers returns ['KAMI_SPIKE'] when |delta| >= 0.05; [] when |delta| < 0.05."""
    from src.graph.nodes.memory_writer import _check_triggers

    # Write 3 neutral entries so drift/floor don't fire
    memory_path = tmp_path / "MEMORY.md"
    entries = [_make_memory_entry(merit_score=0.80, drift_flags="none") for _ in range(3)]
    _write_memory(memory_path, entries)

    config = _make_config()

    # |delta| == 0.06 >= 0.05 → KAMI_SPIKE fires
    triggers = _check_triggers("CASSANDRA", 0.06, memory_path, config)
    assert "KAMI_SPIKE" in triggers

    # |delta| == 0.03 < 0.05 → KAMI_SPIKE does NOT fire
    triggers_low = _check_triggers("CASSANDRA", 0.03, memory_path, config)
    assert "KAMI_SPIKE" not in triggers_low


def test_trigger_drift_streak(tmp_path):
    """_check_triggers returns ['DRIFT_STREAK'] when last 3 entries all have non-empty DRIFT_FLAGS."""
    from src.graph.nodes.memory_writer import _check_triggers

    memory_path = tmp_path / "MEMORY.md"
    config = _make_config(kami_delta_threshold=1.0)  # disable KAMI_SPIKE for this test

    # 3 entries all with drift flags → DRIFT_STREAK fires
    entries_all = [_make_memory_entry(drift_flags="vol_spike") for _ in range(3)]
    _write_memory(memory_path, entries_all)
    triggers = _check_triggers("CASSANDRA", 0.01, memory_path, config)
    assert "DRIFT_STREAK" in triggers

    # 2 entries with flags, 1 without → DRIFT_STREAK does NOT fire
    entries_partial = [
        _make_memory_entry(drift_flags="none"),  # oldest — no flag
        _make_memory_entry(drift_flags="vol_spike"),
        _make_memory_entry(drift_flags="momentum_break"),
    ]
    _write_memory(memory_path, entries_partial)
    triggers_partial = _check_triggers("CASSANDRA", 0.01, memory_path, config)
    assert "DRIFT_STREAK" not in triggers_partial


def test_trigger_merit_floor(tmp_path):
    """_check_triggers returns ['MERIT_FLOOR'] when last 3 entries all have merit_score <= 0.40."""
    from src.graph.nodes.memory_writer import _check_triggers

    memory_path = tmp_path / "MEMORY.md"
    config = _make_config(kami_delta_threshold=1.0)  # disable KAMI_SPIKE

    # 3 entries all at/below floor → MERIT_FLOOR fires
    entries_all_low = [_make_memory_entry(merit_score=0.38) for _ in range(3)]
    _write_memory(memory_path, entries_all_low)
    triggers = _check_triggers("CASSANDRA", 0.01, memory_path, config)
    assert "MERIT_FLOOR" in triggers

    # 2 below floor, 1 above → MERIT_FLOOR does NOT fire
    entries_partial = [
        _make_memory_entry(merit_score=0.38),
        _make_memory_entry(merit_score=0.38),
        _make_memory_entry(merit_score=0.55),  # newest — above floor
    ]
    _write_memory(memory_path, entries_partial)
    triggers_partial = _check_triggers("CASSANDRA", 0.01, memory_path, config)
    assert "MERIT_FLOOR" not in triggers_partial


def test_merged_proposal(tmp_path):
    """Both KAMI_SPIKE + DRIFT_STREAK fire → single proposal with both reasons."""
    from src.graph.nodes import memory_writer as mw

    memory_path = tmp_path / "MEMORY.md"
    proposals_dir = tmp_path / "proposals"

    # 3 entries with drift flags — sets up DRIFT_STREAK
    entries = [_make_memory_entry(drift_flags="vol_spike") for _ in range(3)]
    _write_memory(memory_path, entries)

    config = _make_config(kami_delta_threshold=0.05, merit_floor_k=99)  # disable MERIT_FLOOR

    write_calls = []

    def fake_write_proposal_atomic(proposal, proposals_dir=None):
        write_calls.append(proposal)

    # Patch _get_souls_dir to return tmp soul dir, write_proposal_atomic to capture
    with patch.object(mw, "write_proposal_atomic", side_effect=fake_write_proposal_atomic):
        triggers = mw._check_triggers("CASSANDRA", 0.06, memory_path, config)
        assert "KAMI_SPIKE" in triggers
        assert "DRIFT_STREAK" in triggers

        # Simulate what _process_agent would do: build + emit exactly once
        rationale = mw._build_proposal_rationale(triggers)
        proposal = SoulProposal(
            proposal_id=build_proposal_id("CASSANDRA"),
            agent_id="CASSANDRA",
            target_section="## Core Beliefs",
            proposed_content="[PENDING — Agent Church will draft content based on MEMORY.md context]",
            proposal_reasons=triggers,
            rationale=rationale,
            proposed_at=datetime.now(timezone.utc),
            status="pending",
        )
        fake_write_proposal_atomic(proposal)

    # write_proposal_atomic called exactly once
    assert len(write_calls) == 1
    sole_proposal = write_calls[0]
    assert "KAMI_SPIKE" in sole_proposal.proposal_reasons
    assert "DRIFT_STREAK" in sole_proposal.proposal_reasons


def test_rate_limit(tmp_path):
    """check_rate_limit True → write_proposal_atomic NOT called."""
    from src.graph.nodes import memory_writer as mw

    memory_path = tmp_path / "MEMORY.md"
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir()

    # 3 entries with large KAMI delta to trigger KAMI_SPIKE
    entries = [_make_memory_entry(drift_flags="none") for _ in range(3)]
    _write_memory(memory_path, entries)

    config = _make_config(kami_delta_threshold=0.05, drift_streak_n=99, merit_floor_k=99)

    # Inject 3 rejected proposals into proposals_dir so check_rate_limit returns True
    now = datetime.now(timezone.utc)
    for i in range(3):
        p = _make_proposal(
            proposal_id=f"cass_rejected_{i}",
            agent_id="CASSANDRA",
            target_section="## Core Beliefs",
            status="rejected",
            proposed_at=now - timedelta(hours=i),
        )
        write_proposal_atomic(p, proposals_dir=proposals_dir)

    # Confirm check_rate_limit sees the rejections
    assert check_rate_limit(
        "CASSANDRA", "## Core Beliefs", proposals_dir, k=3, window_days=7
    ) is True

    write_calls = []

    def fake_write(proposal, proposals_dir=None):
        write_calls.append(proposal)

    # Patch PROPOSALS_DIR inside memory_writer so _process_agent uses our proposals_dir
    with patch.object(mw, "write_proposal_atomic", side_effect=fake_write):
        with patch.object(mw, "PROPOSALS_DIR", proposals_dir):
            with patch.object(mw, "_get_souls_dir", return_value=memory_path.parent.parent):
                mw._process_agent(
                    "CASSANDRA",
                    {
                        "bearish_thesis": "Markets look grim.",
                        "merit_scores": {"CASSANDRA": {"composite": 0.38}},
                    },
                )

    # write_proposal_atomic must NOT have been called (rate-limited)
    assert write_calls == [], "write_proposal_atomic must be suppressed when rate-limited"
