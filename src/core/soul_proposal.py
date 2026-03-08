"""Soul proposal schema and atomic write helpers.

Phase 17, Plan 02 (EVOL-02).
Import layer: src.core only — must NOT import from src.graph.*

Provides:
  SoulProposal  — Pydantic v2 model for agent self-evolution proposals
  build_proposal_id(agent_id) — deterministic unique proposal ID
  write_proposal_atomic(proposal, proposals_dir) — atomic JSON write via temp+rename
  check_rate_limit(agent_id, target_section, proposals_dir, k, window_days) — rate-limit scan
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Default proposals directory (created on first write — NOT at import time)
PROPOSALS_DIR = Path("data/soul_proposals")


# ---------------------------------------------------------------------------
# Pydantic model
# ---------------------------------------------------------------------------


class SoulProposal(BaseModel):
    """Immutable-ish proposal record for an agent's requested soul evolution.

    Fields
    ------
    proposal_id     : unique ID, e.g. "cass_20260308T124122123456Z"
    agent_id        : soul handle, e.g. "CASSANDRA"
    target_section  : SOUL.md section heading, e.g. "## Core Beliefs"
    proposed_content: replacement text; sentinel "[PENDING …]" until Agent Church drafts
    proposal_reasons: list of trigger names, e.g. ["KAMI_SPIKE", "DRIFT_STREAK"]
    rationale       : human-readable explanation of why triggers fired
    proposed_at     : UTC datetime of proposal creation
    status          : one of pending | approved | rejected | rate_limited
    rejection_reason: optional human or Church rejection note
    """

    proposal_id: str
    agent_id: str
    target_section: str
    proposed_content: str
    proposal_reasons: list[str]
    rationale: str
    proposed_at: datetime
    status: Literal["pending", "approved", "rejected", "rate_limited"]
    rejection_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# ID builder
# ---------------------------------------------------------------------------


def build_proposal_id(agent_id: str) -> str:
    """Return a deterministic, unique proposal ID.

    Format: <first-4-chars-of-agent_id-lowercase>_<UTC-timestamp-with-microseconds>Z
    Example: "cass_20260308T124122123456Z"

    The microsecond component makes collisions within the same second astronomically
    unlikely.  Prefix is lowercased and truncated to 4 chars for compactness.
    """
    prefix = agent_id[:4].lower()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + "Z"
    return f"{prefix}_{ts}"


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------


def write_proposal_atomic(
    proposal: SoulProposal,
    proposals_dir: Path = PROPOSALS_DIR,
) -> None:
    """Write a SoulProposal to proposals_dir as {proposal_id}.json atomically.

    Uses NamedTemporaryFile + os.rename to ensure no partial writes are visible.
    Creates proposals_dir (parents=True, exist_ok=True) if it does not exist.
    No .tmp files are left behind on success or failure (NamedTemporaryFile with
    delete=False is cleaned up by the rename; if rename fails the .tmp persists,
    which is the safe/honest failure mode).
    """
    proposals_dir.mkdir(parents=True, exist_ok=True)
    target = proposals_dir / f"{proposal.proposal_id}.json"

    payload = proposal.model_dump(mode="json")

    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=proposals_dir,
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    ) as f:
        json.dump(payload, f, indent=2, default=str)
        tmp_path = f.name

    os.rename(tmp_path, target)
    logger.debug("soul_proposal: wrote %s", target)


# ---------------------------------------------------------------------------
# Rate-limit scan
# ---------------------------------------------------------------------------


def check_rate_limit(
    agent_id: str,
    target_section: str,
    proposals_dir: Path,
    k: int,
    window_days: int,
) -> bool:
    """Return True if (agent_id, target_section) is rate-limited.

    Rate-limited means: at least k proposals for this (agent_id, target_section)
    pair with status == "rejected" exist in proposals_dir with proposed_at >=
    (now - window_days days).

    Malformed JSON files are silently skipped.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    count = 0

    for p_file in proposals_dir.glob("*.json"):
        try:
            data = json.loads(p_file.read_text(encoding="utf-8"))
            if (
                data.get("agent_id") == agent_id
                and data.get("target_section") == target_section
                and data.get("status") == "rejected"
            ):
                proposed_at_raw = data.get("proposed_at")
                if proposed_at_raw is None:
                    continue
                proposed_at = datetime.fromisoformat(proposed_at_raw)
                # Ensure timezone-aware for comparison
                if proposed_at.tzinfo is None:
                    proposed_at = proposed_at.replace(tzinfo=timezone.utc)
                if proposed_at >= cutoff:
                    count += 1
        except Exception:
            continue

    return count >= k
