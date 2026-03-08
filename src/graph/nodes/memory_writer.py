"""Post-execution node: per-agent MEMORY.md structured self-reflection log.

Phase 17, Plan 01 (EVOL-01).

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

from src.core.kami import ALL_SOUL_HANDLES

logger = logging.getLogger(__name__)

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
        "[DRIFT_FLAGS:] none",
        f"[THESIS_SUMMARY:] {thesis_summary}",
        "",
    ]
    return "\n".join(lines)


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
# Per-agent processing
# ---------------------------------------------------------------------------

def _process_agent(handle: str, state: dict) -> None:
    """Write a MEMORY entry for one agent if its canonical output is non-None.

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

    # Build and write entry
    entry_text = _build_entry(handle, kami_delta, current_composite, thesis_summary)
    _write_memory_entry(agent_id, entry_text)


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

async def memory_writer_node(state: dict) -> dict:
    """Write per-agent MEMORY.md entries. Silent node (returns {}). Non-blocking.

    Iterates all 5 soul handles. For each, checks the canonical SwarmState field;
    writes a structured MEMORY entry if the field is non-None; skips silently otherwise.
    On any write failure, logs an error and continues — MEMORY is forensic infrastructure,
    not trade-critical.

    Returns:
        {} (no SwarmState mutation)
    """
    for handle in ALL_SOUL_HANDLES:
        try:
            _process_agent(handle, state)
        except Exception as e:
            logger.error("memory_writer: unhandled error for %s: %s", handle, e)
    return {}
