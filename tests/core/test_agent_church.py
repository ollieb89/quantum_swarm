"""Unit tests for src.core.agent_church (Agent Church proposal review script).

Phase 17, Plan 03 (EVOL-03).

Tests cover:
  - test_church_approves: valid proposal approved, SOUL.md mutated in-place
  - test_church_rejects_missing_section: nonexistent section → rejected
  - test_church_rejects_too_long: content > 500 chars → rejected
  - test_church_l1_raises: orchestrator agent_id → RequiresHumanApproval raised
  - test_church_cache_refresh: approved proposal triggers cache_clear then warmup_soul_cache
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from src.core.soul_errors import RequiresHumanApproval


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

MINIMAL_SOUL_MD = """\
# CASSANDRA — Soul

## Core Beliefs

Some content about core beliefs.

## Drift Guard

Other drift guard content.

"""


def _make_soul_dir(tmp_path: Path, agent_dir: str = "bearish_researcher") -> Path:
    """Create a minimal souls dir with a SOUL.md for the given agent directory."""
    souls_dir = tmp_path / "souls"
    agent_soul_dir = souls_dir / agent_dir
    agent_soul_dir.mkdir(parents=True)
    (agent_soul_dir / "SOUL.md").write_text(MINIMAL_SOUL_MD, encoding="utf-8")
    return souls_dir


def _make_proposal_json(
    tmp_path: Path,
    proposals_dir: Path,
    proposal_id: str = "cass_test001",
    agent_id: str = "CASSANDRA",
    target_section: str = "## Core Beliefs",
    proposed_content: str = "New content for core beliefs.",
    proposal_reasons: list[str] = None,
    status: str = "pending",
) -> Path:
    """Write a proposal JSON to proposals_dir and return its path."""
    proposals_dir.mkdir(parents=True, exist_ok=True)
    proposal = {
        "proposal_id": proposal_id,
        "agent_id": agent_id,
        "target_section": target_section,
        "proposed_content": proposed_content,
        "proposal_reasons": proposal_reasons or ["KAMI_SPIKE"],
        "rationale": "Merit changed sharply.",
        "proposed_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "rejection_reason": None,
    }
    path = proposals_dir / f"{proposal_id}.json"
    path.write_text(json.dumps(proposal, default=str), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAgentChurch:

    def test_church_approves(self, tmp_path):
        """Valid pending proposal → status='approved', SOUL.md section mutated."""
        from src.core import agent_church

        souls_dir = _make_soul_dir(tmp_path)
        proposals_dir = tmp_path / "proposals"
        proposal_path = _make_proposal_json(
            tmp_path,
            proposals_dir,
            proposal_id="cass_approve_001",
            agent_id="CASSANDRA",
            target_section="## Core Beliefs",
            proposed_content="Updated core beliefs content.",
        )

        with (
            patch.object(agent_church, "load_soul"),
            patch.object(agent_church, "warmup_soul_cache"),
        ):
            summary = agent_church.review_proposals(
                proposals_dir=proposals_dir,
                souls_dir=souls_dir,
            )

        # Proposal file updated to approved
        data = json.loads(proposal_path.read_text(encoding="utf-8"))
        assert data["status"] == "approved", f"Expected approved, got: {data['status']}"
        assert data["rejection_reason"] is None

        # SOUL.md contains the new content
        soul_path = souls_dir / "bearish_researcher" / "SOUL.md"
        soul_text = soul_path.read_text(encoding="utf-8")
        assert "Updated core beliefs content." in soul_text

        # Summary counts
        assert summary["approved"] == 1
        assert summary["rejected"] == 0

    def test_church_rejects_missing_section(self, tmp_path):
        """Proposal targeting nonexistent section → rejected, rejection_reason contains 'not found'."""
        from src.core import agent_church

        souls_dir = _make_soul_dir(tmp_path)
        proposals_dir = tmp_path / "proposals"
        proposal_path = _make_proposal_json(
            tmp_path,
            proposals_dir,
            proposal_id="cass_reject_section",
            agent_id="CASSANDRA",
            target_section="## Nonexistent Section",
            proposed_content="Some content.",
        )

        with (
            patch.object(agent_church, "load_soul"),
            patch.object(agent_church, "warmup_soul_cache"),
        ):
            summary = agent_church.review_proposals(
                proposals_dir=proposals_dir,
                souls_dir=souls_dir,
            )

        data = json.loads(proposal_path.read_text(encoding="utf-8"))
        assert data["status"] == "rejected"
        assert "not found" in (data["rejection_reason"] or "").lower(), (
            f"Expected 'not found' in rejection_reason, got: {data['rejection_reason']!r}"
        )

        # SOUL.md must be unchanged
        soul_path = souls_dir / "bearish_researcher" / "SOUL.md"
        assert soul_path.read_text(encoding="utf-8") == MINIMAL_SOUL_MD

        assert summary["rejected"] == 1

    def test_church_rejects_too_long(self, tmp_path):
        """Proposal with len(proposed_content) == 501 → rejected, reason mentions 'char limit'."""
        from src.core import agent_church

        souls_dir = _make_soul_dir(tmp_path)
        proposals_dir = tmp_path / "proposals"
        too_long = "x" * 501
        proposal_path = _make_proposal_json(
            tmp_path,
            proposals_dir,
            proposal_id="cass_reject_long",
            agent_id="CASSANDRA",
            target_section="## Core Beliefs",
            proposed_content=too_long,
        )

        with (
            patch.object(agent_church, "load_soul"),
            patch.object(agent_church, "warmup_soul_cache"),
        ):
            summary = agent_church.review_proposals(
                proposals_dir=proposals_dir,
                souls_dir=souls_dir,
            )

        data = json.loads(proposal_path.read_text(encoding="utf-8"))
        assert data["status"] == "rejected"
        assert "char limit" in (data["rejection_reason"] or "").lower(), (
            f"Expected 'char limit' in rejection_reason, got: {data['rejection_reason']!r}"
        )

        assert summary["rejected"] == 1

    def test_church_l1_raises(self, tmp_path):
        """Proposal with agent_id not in ALL_SOUL_HANDLES → RequiresHumanApproval raised."""
        from src.core import agent_church

        souls_dir = _make_soul_dir(tmp_path)
        proposals_dir = tmp_path / "proposals"
        _make_proposal_json(
            tmp_path,
            proposals_dir,
            proposal_id="orch_self_proposal",
            agent_id="orchestrator",
            target_section="## Core Beliefs",
            proposed_content="Attempting self-modification.",
        )

        with pytest.raises(RequiresHumanApproval):
            agent_church.review_proposals(
                proposals_dir=proposals_dir,
                souls_dir=souls_dir,
            )

    def test_church_cache_refresh(self, tmp_path):
        """After approval, load_soul.cache_clear is called before warmup_soul_cache."""
        from src.core import agent_church

        souls_dir = _make_soul_dir(tmp_path)
        proposals_dir = tmp_path / "proposals"
        _make_proposal_json(
            tmp_path,
            proposals_dir,
            proposal_id="cass_cache_test",
            agent_id="CASSANDRA",
            target_section="## Core Beliefs",
            proposed_content="Cache refresh test content.",
        )

        call_order = []

        mock_clear = MagicMock(side_effect=lambda: call_order.append("cache_clear"))
        mock_warmup = MagicMock(side_effect=lambda: call_order.append("warmup_soul_cache"))

        # load_soul is a cached function; patch .cache_clear on it
        with (
            patch.object(agent_church.load_soul, "cache_clear", mock_clear),
            patch.object(agent_church, "warmup_soul_cache", mock_warmup),
        ):
            agent_church.review_proposals(
                proposals_dir=proposals_dir,
                souls_dir=souls_dir,
            )

        assert call_order == ["cache_clear", "warmup_soul_cache"], (
            f"Expected cache_clear before warmup_soul_cache, got: {call_order}"
        )
