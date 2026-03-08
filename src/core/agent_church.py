"""Standalone Agent Church proposal review script.

Run as: python -m src.core.agent_church

Import Layer Law: must NOT import from src.graph.*

Reads all pending SoulProposal JSON files from data/soul_proposals/, applies
structural heuristics to approve or reject each one, and mutates the agent's
SOUL.md in-place if approved.

Phase 17, Plan 03 (EVOL-03).

Approval criteria (all must pass):
  1. agent_id is in ALL_SOUL_HANDLES (L1 self-proposal guard — raises RequiresHumanApproval)
  2. target_section exists as an H2 heading in the agent's SOUL.md
  3. len(proposed_content) <= soul_autoapprove_max_chars (default 500)
  4. proposed_content is non-empty and non-whitespace
  5. proposal_reasons is non-empty

On approval: SOUL.md section is replaced in-place and soul cache is invalidated.
On rejection: proposal JSON is updated with status="rejected" and rejection_reason.
"""
from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, Optional

import yaml

from src.core.kami import ALL_SOUL_HANDLES
from src.core.soul_errors import RequiresHumanApproval
from src.core.soul_loader import load_soul, warmup_soul_cache
from src.core.soul_proposal import PROPOSALS_DIR, SoulProposal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maps soul handle → agent_id directory name under src/core/souls/
# Copied from memory_writer.py — do NOT import from src.graph.nodes (Import Layer Law).
HANDLE_TO_AGENT_ID: Dict[str, str] = {
    "AXIOM": "macro_analyst",
    "MOMENTUM": "bullish_researcher",
    "CASSANDRA": "bearish_researcher",
    "SIGMA": "quant_modeler",
    "GUARDIAN": "risk_manager",
}

_AUTOAPPROVE_MAX_CHARS: int = 500

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

_P17_CONFIG: Dict = {}


def _load_p17_config() -> Dict:
    """Lazy-load phase17: block from config/swarm_config.yaml.

    Falls back to empty dict on any read/parse error so the module always
    imports successfully without a config file.
    """
    global _P17_CONFIG
    if not _P17_CONFIG:
        config_path = Path(__file__).parents[2] / "config" / "swarm_config.yaml"
        try:
            with open(config_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            _P17_CONFIG = cfg.get("phase17", {})
        except Exception as e:
            logger.warning("agent_church: could not load swarm_config.yaml: %s", e)
            _P17_CONFIG = {}
    return _P17_CONFIG


# ---------------------------------------------------------------------------
# Path helper
# ---------------------------------------------------------------------------


def _get_soul_path(handle: str, souls_dir: Path) -> Path:
    """Return the SOUL.md path for the given soul handle and souls_dir.

    Translates soul handle (e.g. "CASSANDRA") → agent directory name
    (e.g. "bearish_researcher") via HANDLE_TO_AGENT_ID.
    """
    agent_dir = HANDLE_TO_AGENT_ID[handle]
    return souls_dir / agent_dir / "SOUL.md"


# ---------------------------------------------------------------------------
# Guard helpers
# ---------------------------------------------------------------------------


def _is_l1_orchestrator(agent_id: str) -> bool:
    """Return True if agent_id is NOT in ALL_SOUL_HANDLES.

    Catches orchestrator self-proposals and any other non-standard agent IDs.
    """
    return agent_id not in ALL_SOUL_HANDLES


# ---------------------------------------------------------------------------
# H2 section replacement
# ---------------------------------------------------------------------------


def _replace_h2_section(soul_content: str, target_section: str, new_content: str) -> str:
    """Replace a single H2 section in SOUL.md content.

    target_section must be an exact H2 line e.g. '## Core Beliefs'.
    Raises ValueError if section not found.
    """
    replacement = new_content.rstrip("\n") + "\n\n"
    pattern = re.compile(
        r"(^" + re.escape(target_section) + r"\n)(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    if not pattern.search(soul_content):
        raise ValueError(f"Section not found in SOUL.md: {target_section!r}")
    return pattern.sub(replacement, soul_content, count=1)


# ---------------------------------------------------------------------------
# Atomic proposal JSON write
# ---------------------------------------------------------------------------


def _write_proposal_json_atomic(proposal: SoulProposal, proposals_dir: Path) -> None:
    """Overwrite the proposal JSON atomically via temp+rename.

    Uses the same atomic write pattern as write_proposal_atomic in soul_proposal.py.
    """
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


# ---------------------------------------------------------------------------
# Reject / approve helpers
# ---------------------------------------------------------------------------


def _reject_proposal(
    proposal: SoulProposal,
    reason: str,
    proposals_dir: Path,
) -> SoulProposal:
    """Set proposal status to 'rejected' and write back atomically."""
    # Pydantic v2 — model_copy with keyword update
    rejected = proposal.model_copy(update={"status": "rejected", "rejection_reason": reason})
    _write_proposal_json_atomic(rejected, proposals_dir)
    logger.info(
        "agent_church: rejected proposal %s for %s — %s",
        proposal.proposal_id,
        proposal.agent_id,
        reason,
    )
    return rejected


def _apply_proposal(
    proposal: SoulProposal,
    soul_path: Path,
    proposals_dir: Path,
) -> SoulProposal:
    """Apply an approved proposal: mutate SOUL.md, update proposal JSON, refresh cache."""
    # 1. Read current SOUL.md
    soul_content = soul_path.read_text(encoding="utf-8")

    # 2. Replace the target section (raises ValueError if section not found — caller must check first)
    updated_content = _replace_h2_section(
        soul_content,
        proposal.target_section,
        proposal.proposed_content,
    )

    # 3. Write updated SOUL.md back (single-writer; Agent Church is out-of-band)
    soul_path.write_text(updated_content, encoding="utf-8")

    # 4. Update proposal to approved
    approved = proposal.model_copy(update={"status": "approved", "rejection_reason": None})
    _write_proposal_json_atomic(approved, proposals_dir)

    # 5. Invalidate and re-warm soul cache (Phase 15 locked order: clear before warmup)
    load_soul.cache_clear()
    warmup_soul_cache()

    logger.info(
        "agent_church: approved proposal %s for %s — section %r updated",
        proposal.proposal_id,
        proposal.agent_id,
        proposal.target_section,
    )
    return approved


# ---------------------------------------------------------------------------
# Core review function
# ---------------------------------------------------------------------------


def review_proposals(
    proposals_dir: Optional[Path] = None,
    souls_dir: Optional[Path] = None,
) -> Dict[str, int]:
    """Process all pending SoulProposal JSON files in proposals_dir.

    Args:
        proposals_dir: Directory containing proposal JSON files.
                       Defaults to data/soul_proposals/ (PROPOSALS_DIR from soul_proposal).
        souls_dir:     Root directory containing per-agent soul subdirectories.
                       Defaults to SOULS_DIR from soul_loader.

    Returns:
        Summary dict {"approved": N, "rejected": N, "skipped": N}.

    Raises:
        RequiresHumanApproval: If any proposal targets an agent_id that is NOT in
                               ALL_SOUL_HANDLES (L1 self-proposal guard). This is raised
                               and NOT caught — it propagates to the __main__ caller.
    """
    from src.core.soul_loader import SOULS_DIR  # local import to allow default

    if proposals_dir is None:
        proposals_dir = PROPOSALS_DIR
    if souls_dir is None:
        souls_dir = SOULS_DIR

    cfg = _load_p17_config()
    max_chars: int = cfg.get("soul_autoapprove_max_chars", _AUTOAPPROVE_MAX_CHARS)

    summary: Dict[str, int] = {"approved": 0, "rejected": 0, "skipped": 0}

    proposal_files = sorted(proposals_dir.glob("*.json"))
    if not proposal_files:
        logger.info("agent_church: no proposal files found in %s", proposals_dir)
        return summary

    for p_file in proposal_files:
        try:
            data = json.loads(p_file.read_text(encoding="utf-8"))
            proposal = SoulProposal.model_validate(data)
        except Exception as e:
            logger.warning("agent_church: skipping malformed proposal file %s: %s", p_file, e)
            summary["skipped"] += 1
            continue

        # Skip non-pending
        if proposal.status != "pending":
            summary["skipped"] += 1
            continue

        # --- L1 self-proposal guard: RAISES (not caught) ---
        if _is_l1_orchestrator(proposal.agent_id):
            raise RequiresHumanApproval(
                f"L1 orchestrator proposal {proposal.proposal_id!r} requires human approval"
            )

        # --- Resolve SOUL.md path ---
        try:
            soul_path = _get_soul_path(proposal.agent_id, souls_dir)
        except KeyError:
            _reject_proposal(
                proposal,
                f"Unknown agent handle {proposal.agent_id!r} — no SOUL.md mapping",
                proposals_dir,
            )
            summary["rejected"] += 1
            continue

        # --- Reject conditions (checked in order; first match → reject) ---

        # 1. Content length check
        if len(proposal.proposed_content) > max_chars:
            _reject_proposal(
                proposal,
                f"Content exceeds char limit ({len(proposal.proposed_content)} > {max_chars})",
                proposals_dir,
            )
            summary["rejected"] += 1
            continue

        # 2. Empty proposed_content check
        if not proposal.proposed_content.strip():
            _reject_proposal(proposal, "Empty proposed_content", proposals_dir)
            summary["rejected"] += 1
            continue

        # 3. Empty proposal_reasons check
        if not proposal.proposal_reasons:
            _reject_proposal(proposal, "Empty proposal reasons", proposals_dir)
            summary["rejected"] += 1
            continue

        # 4. Section existence check (try replacement to validate)
        try:
            soul_content = soul_path.read_text(encoding="utf-8")
            _replace_h2_section(soul_content, proposal.target_section, proposal.proposed_content)
        except FileNotFoundError:
            _reject_proposal(
                proposal,
                f"SOUL.md not found at {soul_path}",
                proposals_dir,
            )
            summary["rejected"] += 1
            continue
        except ValueError:
            _reject_proposal(
                proposal,
                f"Section not found in SOUL.md: {proposal.target_section!r}",
                proposals_dir,
            )
            summary["rejected"] += 1
            continue

        # --- All checks passed: approve ---
        _apply_proposal(proposal, soul_path, proposals_dir)
        summary["approved"] += 1

    return summary


# ---------------------------------------------------------------------------
# __main__ entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    summary = review_proposals()
    print(f"Agent Church complete: {summary}")
