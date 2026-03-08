"""Post-execution node: per-agent MEMORY.md structured self-reflection log.

Phase 17, Plan 01 (EVOL-01) + Plan 02 (EVOL-02).

Writes one structured entry per active agent per cycle to:
    src/core/souls/{agent_id}/MEMORY.md

Entry format (fixed-field, deterministic — Phase 19 ARS parses by label):
    === 2026-03-08T12:34:56Z ===
    [AGENT:] AXIOM
    [KAMI_DELTA:] +0.04
    [MERIT_SCORE:] 0.81
    [DRIFT_FLAGS:] none
    [THESIS_SUMMARY:] Inflation surprise risk remains underpriced.

Rules:
- Silent node: always returns {} — no SwarmState mutation
- Non-blocking: on write failure, logs error and continues cycle
- Skip-on-no-output: if canonical state field is None, no entry written
- Cap: 50 entries max; oldest dropped when exceeded

Plan 02 additions (EVOL-02):
- _check_triggers: KAMI_SPIKE, DRIFT_STREAK, MERIT_FLOOR trigger evaluation
- _build_proposal_rationale: human-readable trigger summary string
- _process_agent: emits SoulProposal via write_proposal_atomic after trigger check
- Rate-limit guard: suppresses duplicate proposals for same (agent_id, target_section)

All I/O is synchronous (Path.read_text / Path.write_text).
Do NOT use asyncio.run() inside node functions — known project-breaking pattern.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from src.core.drift_eval import evaluate_drift
from src.core.kami import ALL_SOUL_HANDLES
from src.core.db import get_pool
from src.core.soul_loader import load_soul
from src.core.soul_proposal import (
    PROPOSALS_DIR,
    SoulProposal,
    build_proposal_id,
    check_rate_limit,
    write_proposal_atomic,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Evolution suspension check (ARS Plan 19-02)
# ---------------------------------------------------------------------------

async def _check_evolution_suspended(handle: str) -> bool:
    """Check if agent evolution is suspended via DB query. Non-blocking on failure.

    Queries the agent_merit_scores table for the evolution_suspended flag.
    Returns False on any error (DB down, missing row, etc.) so that
    memory writes proceed by default — fail-open for evolution, not trade execution.
    """
    try:
        pool = get_pool()
        async with pool.connection() as conn:
            result = await conn.execute(
                "SELECT evolution_suspended FROM agent_merit_scores WHERE soul_handle = %s",
                (handle,),
            )
            row = await result.fetchone()
            if row and row[0]:
                return True
    except Exception as e:
        logger.debug("memory_writer: could not check evolution_suspended for %s: %s", handle, e)
    return False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MEMORY_MAX_ENTRIES: int = 50

# Maps soul handle → agent_id directory name under src/core/souls/
HANDLE_TO_AGENT_ID: Dict[str, str] = {
    "AXIOM": "macro_analyst",
    "MOMENTUM": "bullish_researcher",
    "CASSANDRA": "bearish_researcher",
    "SIGMA": "quant_modeler",
    "GUARDIAN": "risk_manager",
}

# Maps soul handle → canonical SwarmState field name
_CANONICAL_FIELD_MAP: Dict[str, str] = {
    "AXIOM": "macro_report",
    "MOMENTUM": "bullish_thesis",
    "CASSANDRA": "bearish_thesis",
    "SIGMA": "quant_proposal",
    "GUARDIAN": "risk_approval",
}

# GUARDIAN stores reasoning under a nested key — handle transparently
_GUARDIAN_REASONING_KEY = "reasoning"

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

_P17_CONFIG: Dict = {}


def _load_p17_config() -> Dict:
    global _P17_CONFIG
    if not _P17_CONFIG:
        config_path = Path(__file__).parents[3] / "config" / "swarm_config.yaml"
        try:
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
            _P17_CONFIG = cfg.get("phase17", {})
        except Exception as e:
            logger.warning("memory_writer: could not load swarm_config.yaml: %s", e)
            _P17_CONFIG = {}
    return _P17_CONFIG


# ---------------------------------------------------------------------------
# Path helper
# ---------------------------------------------------------------------------

def _get_souls_dir() -> Path:
    """Return the souls/ directory. Monkeypatchable for test isolation."""
    return Path(__file__).parents[2] / "core" / "souls"


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

def _extract_thesis_summary(value: object, max_chars: int = 200) -> str:
    """Extract a one-line thesis summary from an agent's canonical output value.

    Handles dict (tries 'content', 'reasoning', 'summary', 'thesis' keys in order)
    and str. Returns first sentence truncated to max_chars; returns "" if not
    extractable.
    """
    text: str = ""

    if isinstance(value, dict):
        for key in ("content", "reasoning", "summary", "thesis"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                text = candidate.strip()
                break
    elif isinstance(value, str):
        text = value.strip()

    if not text:
        return ""

    # Extract first sentence (split on ". " or ".\n" or end of string)
    sentence_match = re.split(r"\.\s+|\.\n", text, maxsplit=1)
    first_sentence = sentence_match[0].strip()
    if not first_sentence.endswith("."):
        first_sentence = first_sentence + "."

    # Truncate to max_chars
    if len(first_sentence) > max_chars:
        first_sentence = first_sentence[:max_chars].rstrip() + "..."

    return first_sentence


# ---------------------------------------------------------------------------
# Entry parse / cap helpers
# ---------------------------------------------------------------------------

# Regex matching a MEMORY.md timestamp header line
_ENTRY_HEADER_RE = re.compile(r"^=== .+ ===$", re.MULTILINE)


def _parse_entries(content: str) -> list[str]:
    """Split MEMORY.md content into a list of entry blocks.

    Each block starts with "=== timestamp ===" and includes all lines until
    the next header (exclusive). Empty content → [].

    Uses header positions to extract each block preserving the header line.
    """
    if not content.strip():
        return []

    # Find all header positions
    headers = list(_ENTRY_HEADER_RE.finditer(content))
    if not headers:
        return []

    entries = []
    for i, match in enumerate(headers):
        start = match.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(content)
        block = content[start:end]
        entries.append(block)

    return entries


def _cap_entries(entries: list[str], max_entries: int = MEMORY_MAX_ENTRIES) -> list[str]:
    """Enforce the max_entries cap by dropping the oldest entries (front of list)."""
    if len(entries) > max_entries:
        return entries[-max_entries:]
    return entries


def _extract_prev_score(memory_path: Path) -> float:
    """Read MEMORY.md and return the [MERIT_SCORE:] from the last entry.

    Returns 0.5 (cold-start default) if the file is absent, empty, or parse fails.
    """
    if not memory_path.exists():
        return 0.5

    try:
        content = memory_path.read_text()
        entries = _parse_entries(content)
        if not entries:
            return 0.5

        last_entry = entries[-1]
        match = re.search(r"\[MERIT_SCORE:\]\s*([\d.]+)", last_entry)
        if match:
            return float(match.group(1))
    except Exception as e:
        logger.debug("memory_writer: could not parse prev score from %s: %s", memory_path, e)

    return 0.5


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _format_delta(delta: float) -> str:
    """Format a float with an explicit sign and 2 decimal places.

    Examples: +0.04, -0.02, +0.00
    """
    rounded = round(delta, 2)
    if rounded >= 0:
        return f"+{rounded:.2f}"
    return f"{rounded:.2f}"


def _build_entry(
    handle: str,
    kami_delta: float,
    merit_score: float,
    thesis_summary: str,
    drift_flags: str = "none",
) -> str:
    """Build a fixed-field MEMORY.md entry string with UTC timestamp header."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    delta_str = _format_delta(kami_delta)
    score_str = f"{round(merit_score, 4):.4f}"

    lines = [
        f"=== {timestamp} ===",
        f"[AGENT:] {handle}",
        f"[KAMI_DELTA:] {delta_str}",
        f"[MERIT_SCORE:] {score_str}",
        f"[DRIFT_FLAGS:] {drift_flags}",
        f"[THESIS_SUMMARY:] {thesis_summary}",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Drift evaluation helper (Plan 20-02)
# ---------------------------------------------------------------------------

def _evaluate_drift_flags(agent_id: str, canonical_output: str) -> str:
    """Evaluate drift rules for an agent against its canonical output.

    Returns:
        "none" -- no drift detected (or no rules defined)
        "flag1,flag2" -- comma-separated matched flag IDs
        "evaluation_failed" -- evaluator error (logged, non-blocking)
    """
    try:
        soul = load_soul(agent_id)
        if not soul.drift_rules:
            return "none"
        matched = evaluate_drift(soul.drift_rules, canonical_output)
        if not matched:
            return "none"
        return ",".join(matched)
    except Exception as e:
        logger.warning("memory_writer: drift evaluation failed for %s: %s", agent_id, e)
        return "evaluation_failed"


# ---------------------------------------------------------------------------
# Write helper
# ---------------------------------------------------------------------------

def _write_memory_entry(agent_id: str, entry_text: str) -> None:
    """Append entry_text to MEMORY.md, enforcing the 50-entry cap.

    Creates the parent directory if absent. Reads existing content, parses,
    appends new entry, caps to MEMORY_MAX_ENTRIES, writes back atomically.
    """
    souls_dir = _get_souls_dir()
    memory_path = souls_dir / agent_id / "MEMORY.md"

    # Ensure parent directory exists (mkdir on parent, not on MEMORY.md itself)
    memory_path.parent.mkdir(parents=True, exist_ok=True)

    existing_content = ""
    if memory_path.exists():
        existing_content = memory_path.read_text()

    entries = _parse_entries(existing_content)
    entries.append(entry_text)
    entries = _cap_entries(entries, MEMORY_MAX_ENTRIES)

    memory_path.write_text("".join(entries))


# ---------------------------------------------------------------------------
# Plan 02 (EVOL-02): Trigger helpers
# ---------------------------------------------------------------------------


def _extract_drift_flags(entry: str) -> str:
    """Parse a single entry block string; return the DRIFT_FLAGS value.

    Returns "" if no [DRIFT_FLAGS:] line is found.  Returns "" for the
    sentinel value "none" so callers can treat non-empty as "drift present".
    """
    match = re.search(r"\[DRIFT_FLAGS:\]\s*(.+)", entry)
    if not match:
        return ""
    value = match.group(1).strip()
    return "" if value.lower() == "none" else value


def _extract_merit_score_from_entry(entry: str) -> Optional[float]:
    """Find [MERIT_SCORE:] in an entry block; return float or None on failure."""
    match = re.search(r"\[MERIT_SCORE:\]\s*([\d.]+)", entry)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _check_triggers(
    handle: str,
    kami_delta: float,
    memory_path: Path,
    config: dict,
) -> list[str]:
    """Evaluate all three proposal triggers against the current MEMORY.md state.

    Checks (in order, independent — multiple can fire):
      KAMI_SPIKE   : |kami_delta| >= kami_delta_threshold (default 0.05)
      DRIFT_STREAK : last drift_streak_n entries all have non-empty DRIFT_FLAGS
      MERIT_FLOOR  : last merit_floor_k entries all have MERIT_SCORE <= merit_floor

    For DRIFT_STREAK and MERIT_FLOOR, if fewer than N/K entries exist in the file
    the trigger cannot fire (condition treated as False).

    Returns a list of matched trigger name strings (may be empty, 1, or more).
    """
    triggers: list[str] = []

    # --- KAMI_SPIKE ---
    threshold: float = config.get("kami_delta_threshold", 0.05)
    if abs(kami_delta) >= threshold:
        triggers.append("KAMI_SPIKE")

    # Read and parse entries for streak checks
    entries: list[str] = []
    if memory_path.exists():
        try:
            content = memory_path.read_text()
            entries = _parse_entries(content)
        except Exception as e:
            logger.debug("memory_writer: _check_triggers could not read %s: %s", memory_path, e)

    # --- DRIFT_STREAK ---
    streak_n: int = int(config.get("drift_streak_n", 3))
    if len(entries) >= streak_n:
        tail = entries[-streak_n:]
        if all(_extract_drift_flags(e) for e in tail):
            triggers.append("DRIFT_STREAK")

    # --- MERIT_FLOOR ---
    floor_k: int = int(config.get("merit_floor_k", 3))
    merit_floor: float = config.get("merit_floor", 0.40)
    if len(entries) >= floor_k:
        tail = entries[-floor_k:]
        scores = [_extract_merit_score_from_entry(e) for e in tail]
        if all(s is not None and s <= merit_floor for s in scores):
            triggers.append("MERIT_FLOOR")

    return triggers


def _build_proposal_rationale(triggers: list[str]) -> str:
    """Return a human-readable rationale string summarising which triggers fired."""
    parts = []
    if "KAMI_SPIKE" in triggers:
        parts.append("Merit changed sharply (KAMI_SPIKE)")
    if "DRIFT_STREAK" in triggers:
        parts.append("drift flags raised on consecutive cycles (DRIFT_STREAK)")
    if "MERIT_FLOOR" in triggers:
        parts.append("merit score below floor threshold (MERIT_FLOOR)")
    if not parts:
        return "Unknown trigger."
    return "; ".join(parts) + "."


# ---------------------------------------------------------------------------
# Per-agent processing
# ---------------------------------------------------------------------------

def _process_agent(handle: str, state: dict) -> None:
    """Write a MEMORY entry for one agent if its canonical output is non-None.

    Plan 02 extension: after writing the MEMORY entry, evaluate proposal
    triggers.  If any fire and the agent is not rate-limited, emit a
    SoulProposal via write_proposal_atomic.

    Raises on any exception (caller catches and logs).
    """
    canonical_field = _CANONICAL_FIELD_MAP.get(handle)
    if canonical_field is None:
        return

    value = state.get(canonical_field)
    if value is None:
        return  # Skip-on-no-output

    # Extract thesis summary
    thesis_summary = _extract_thesis_summary(value)

    # Get current composite merit score
    merit_scores: dict = state.get("merit_scores") or {}
    agent_scores: dict = merit_scores.get(handle) or {}
    current_composite: float = agent_scores.get("composite", 0.5)

    # Get previous score from MEMORY.md
    agent_id = HANDLE_TO_AGENT_ID[handle]
    souls_dir = _get_souls_dir()
    memory_path = souls_dir / agent_id / "MEMORY.md"
    prev_score = _extract_prev_score(memory_path)

    # Compute delta
    kami_delta = current_composite - prev_score

    # Evaluate drift flags (Plan 20-02)
    canonical_text = ""
    if isinstance(value, dict):
        for key in ("content", "reasoning", "summary", "thesis"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                canonical_text = candidate.strip()
                break
    elif isinstance(value, str):
        canonical_text = value.strip()
    drift_flags = _evaluate_drift_flags(agent_id, canonical_text)

    # Build and write entry
    entry_text = _build_entry(handle, kami_delta, current_composite, thesis_summary, drift_flags=drift_flags)
    _write_memory_entry(agent_id, entry_text)

    # --- Plan 02: Trigger evaluation and proposal emission ---
    try:
        cfg = _load_p17_config()
        triggers = _check_triggers(handle, kami_delta, memory_path, cfg)
        if not triggers:
            return

        # Rate-limit check — proposals_dir is patchable via module attribute
        rate_limited = check_rate_limit(
            agent_id=handle,  # use soul handle (consistent with Agent Church SOUL.md lookup)
            target_section="## Core Beliefs",
            proposals_dir=PROPOSALS_DIR,
            k=cfg.get("rate_limit_rejection_k", 3),
            window_days=cfg.get("rate_limit_window_days", 7),
        )

        if rate_limited:
            logger.warning("memory_writer: rate-limited proposal for %s", handle)
            return

        proposal = SoulProposal(
            proposal_id=build_proposal_id(agent_id),
            agent_id=handle,
            target_section="## Core Beliefs",
            proposed_content=(
                "[PENDING — Agent Church will draft content based on MEMORY.md context]"
            ),
            proposal_reasons=triggers,
            rationale=_build_proposal_rationale(triggers),
            proposed_at=datetime.now(timezone.utc),
            status="pending",
        )
        write_proposal_atomic(proposal)
        logger.info(
            "memory_writer: emitted proposal %s for %s (triggers: %s)",
            proposal.proposal_id,
            handle,
            triggers,
        )

    except Exception as exc:
        logger.error(
            "memory_writer: proposal trigger/emit error for %s: %s", handle, exc
        )


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

async def memory_writer_node(state: dict) -> dict:
    """Write per-agent MEMORY.md entries. Silent node (returns {}). Non-blocking.

    Iterates all 5 soul handles. For each, checks evolution_suspended flag
    in DB — if True, skips MEMORY.md write AND proposal emission (ARS-02).
    Then checks the canonical SwarmState field; writes a structured MEMORY
    entry if the field is non-None; skips silently otherwise.
    On any write failure, logs an error and continues — MEMORY is forensic
    infrastructure, not trade-critical.

    Returns:
        {} (no SwarmState mutation)
    """
    for handle in ALL_SOUL_HANDLES:
        try:
            if await _check_evolution_suspended(handle):
                logger.warning("memory_writer skipped due to evolution_suspended: %s", handle)
                continue
            _process_agent(handle, state)
        except Exception as e:
            logger.error("memory_writer: unhandled error for %s: %s", handle, e)
    return {}
