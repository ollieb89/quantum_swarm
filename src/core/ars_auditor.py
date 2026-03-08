"""Standalone ARS (Agent Reputation System) Drift Auditor.

Run as: python -m src.core.ars_auditor

Import Layer Law: must NOT import from src.graph.*

Computes five drift metrics from MEMORY.md evolution logs and soul proposal
data, enforces a 30-cycle warm-up period, uses flag-then-suspend breach
escalation with persistent breach counters, and appends structured audit
events to data/audit.jsonl.

Phase 19, Plan 01 (ARS-01).
"""
from __future__ import annotations

import json
import logging
import math
import re
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from src.core.kami import ALL_SOUL_HANDLES

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maps soul handle -> agent_id directory name under src/core/souls/
# Copied from memory_writer.py — do NOT import from src.graph.nodes (Import Layer Law).
HANDLE_TO_AGENT_ID: Dict[str, str] = {
    "AXIOM": "macro_analyst",
    "MOMENTUM": "bullish_researcher",
    "CASSANDRA": "bearish_researcher",
    "SIGMA": "quant_modeler",
    "GUARDIAN": "risk_manager",
}

IDENTITY_CRITICAL_SECTIONS = frozenset({
    "## Core Beliefs",
    "## Drift Guard",
    "## Core Wounds",
})

# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

_ARS_CONFIG: Dict = {}


def _load_ars_config() -> Dict:
    """Lazy-load ars: block from config/swarm_config.yaml.

    Falls back to empty dict on any read/parse error so the module always
    imports successfully without a config file.
    """
    global _ARS_CONFIG
    if not _ARS_CONFIG:
        config_path = Path(__file__).parents[2] / "config" / "swarm_config.yaml"
        try:
            with open(config_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            _ARS_CONFIG = cfg.get("ars", {})
        except Exception as e:
            logger.warning("ars_auditor: could not load swarm_config.yaml: %s", e)
            _ARS_CONFIG = {}
    return _ARS_CONFIG


# ---------------------------------------------------------------------------
# Path helpers (monkeypatchable for test isolation)
# ---------------------------------------------------------------------------


def _get_souls_dir() -> Path:
    """Return the souls/ directory."""
    return Path(__file__).parent / "souls"


def _get_proposals_dir() -> Path:
    """Return the soul proposals directory."""
    return Path("data/soul_proposals")


def _get_audit_path() -> Path:
    """Return the audit.jsonl path."""
    return Path("data/audit.jsonl")


# ---------------------------------------------------------------------------
# MEMORY.md parsing (re-implemented locally — Import Layer Law)
# ---------------------------------------------------------------------------

_ENTRY_HEADER_RE = re.compile(r"^=== .+ ===$", re.MULTILINE)


def _parse_entries(content: str) -> List[str]:
    """Split MEMORY.md content into a list of entry blocks."""
    if not content.strip():
        return []
    headers = list(_ENTRY_HEADER_RE.finditer(content))
    if not headers:
        return []
    entries = []
    for i, match in enumerate(headers):
        start = match.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(content)
        entries.append(content[start:end])
    return entries


def _extract_field(entry: str, field: str) -> str:
    """Generic [FIELD:] extractor from a MEMORY.md entry block."""
    pattern = re.compile(rf"\[{re.escape(field)}:\]\s*(.+)")
    match = pattern.search(entry)
    return match.group(1).strip() if match else ""


# ---------------------------------------------------------------------------
# Metric 1a: Proposal Rejection Rate
# ---------------------------------------------------------------------------


def _compute_proposal_rejection_rate(
    handle: str, proposals_dir: Path, window: int
) -> float:
    """Return rejected/total ratio of proposals for this agent."""
    if not proposals_dir.exists():
        return 0.0

    total = 0
    rejected = 0
    for f in proposals_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("agent_id") != handle:
            continue
        total += 1
        if data.get("status") == "rejected":
            rejected += 1

    return rejected / total if total > 0 else 0.0


# ---------------------------------------------------------------------------
# Metric 1b: Drift Flag Frequency
# ---------------------------------------------------------------------------


def _compute_drift_flag_frequency(entries: List[str], window: int) -> float:
    """Return ratio of entries with non-empty DRIFT_FLAGS over trailing window."""
    tail = entries[-window:] if len(entries) > window else entries
    if not tail:
        return 0.0

    flagged = 0
    for entry in tail:
        flags = _extract_field(entry, "DRIFT_FLAGS")
        if flags and flags.lower() != "none":
            flagged += 1

    return flagged / len(tail)


# ---------------------------------------------------------------------------
# Metric 2: KAMI Dimension Variance
# ---------------------------------------------------------------------------


def _compute_kami_dimension_variance(dimensions: Dict[str, float]) -> float:
    """Compute cross-dimension variance from KAMI dimensions dict."""
    values = [
        dimensions.get("accuracy", 0.5),
        dimensions.get("recovery", 0.5),
        dimensions.get("consensus", 0.5),
        dimensions.get("fidelity", 0.5),
    ]
    return statistics.variance(values)


# ---------------------------------------------------------------------------
# Metric 3: Alignment Section Mutation Count
# ---------------------------------------------------------------------------


def _compute_alignment_mutation_count(handle: str, proposals_dir: Path) -> int:
    """Count approved proposals targeting identity-critical sections for this agent."""
    if not proposals_dir.exists():
        return 0

    count = 0
    for f in proposals_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("agent_id") != handle:
            continue
        if data.get("status") != "approved":
            continue
        if data.get("target_section") in IDENTITY_CRITICAL_SECTIONS:
            count += 1

    return count


# ---------------------------------------------------------------------------
# Metric 4: Self-Reflection Sentiment Shift
# ---------------------------------------------------------------------------


def _tokenize_lower(text: str) -> List[str]:
    """Tokenize text to lowercase words."""
    return re.findall(r"[a-z]+", text.lower())


def _build_sentiment_vector(
    text: str,
    bullish_terms: List[str],
    bearish_terms: List[str],
    uncertainty_terms: List[str],
) -> Tuple[Dict[str, float], float]:
    """Build normalized 3-dim sentiment vector + signed polarity from text.

    Returns (vector_dict, polarity).
    vector_dict has keys: bullish, bearish, uncertainty (normalized by token count).
    polarity = (bullish_hits - bearish_hits) / tokens.
    """
    tokens = _tokenize_lower(text)
    total = len(tokens) if tokens else 1

    bullish_set = set(bullish_terms)
    bearish_set = set(bearish_terms)
    uncertainty_set = set(uncertainty_terms)

    bullish_hits = sum(1 for t in tokens if t in bullish_set)
    bearish_hits = sum(1 for t in tokens if t in bearish_set)
    uncertainty_hits = sum(1 for t in tokens if t in uncertainty_set)

    vector = {
        "bullish": bullish_hits / total,
        "bearish": bearish_hits / total,
        "uncertainty": uncertainty_hits / total,
    }
    polarity = (bullish_hits - bearish_hits) / total

    return vector, polarity


def _cosine_distance(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Compute cosine distance between two dicts (1 - cosine_similarity)."""
    keys = set(a) | set(b)
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in keys)
    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return 1.0 - dot / (mag_a * mag_b)


def _compute_sentiment_shift(
    entries: List[str], config: Dict
) -> Tuple[float, float]:
    """Compute (cosine_distance, polarity_delta) from baseline to latest entry.

    Returns (0.0, 0.0) if fewer entries than baseline window + 1.
    """
    baseline_window = config.get("sentiment_baseline_window", 10)
    bullish_terms = config.get("bullish_terms", [])
    bearish_terms = config.get("bearish_terms", [])
    uncertainty_terms = config.get("uncertainty_terms", [])

    if len(entries) < baseline_window + 1:
        return 0.0, 0.0

    # Build baseline from window before the latest entry
    baseline_entries = entries[-(baseline_window + 1):-1]
    baseline_vectors = []
    baseline_polarities = []
    for entry in baseline_entries:
        thesis = _extract_field(entry, "THESIS_SUMMARY")
        vec, pol = _build_sentiment_vector(thesis, bullish_terms, bearish_terms, uncertainty_terms)
        baseline_vectors.append(vec)
        baseline_polarities.append(pol)

    # Mean baseline vector
    mean_vec: Dict[str, float] = {}
    for key in ("bullish", "bearish", "uncertainty"):
        mean_vec[key] = sum(v.get(key, 0.0) for v in baseline_vectors) / len(baseline_vectors)
    mean_polarity = sum(baseline_polarities) / len(baseline_polarities)

    # Latest entry
    latest_thesis = _extract_field(entries[-1], "THESIS_SUMMARY")
    latest_vec, latest_polarity = _build_sentiment_vector(
        latest_thesis, bullish_terms, bearish_terms, uncertainty_terms
    )

    distance = _cosine_distance(mean_vec, latest_vec)
    polarity_delta = latest_polarity - mean_polarity

    return distance, polarity_delta


# ---------------------------------------------------------------------------
# Metric 5: Role Boundary Vocabulary Violations
# ---------------------------------------------------------------------------


def _compute_role_boundary_violations(
    entries: List[str], handle: str, config: Dict
) -> float:
    """Compute context-aware role boundary violation score.

    For each forbidden term found in THESIS_SUMMARY, check a 5-token window
    before and after. Count as violation only if assertion marker present
    and NO negation marker in that window.

    Returns max weighted_score across entries in trailing window.
    """
    forbidden_vocab = config.get("forbidden_vocabulary", {})
    forbidden_terms = set(forbidden_vocab.get(handle, []))
    if not forbidden_terms:
        return 0.0

    assertion_markers = set(config.get("assertion_markers", []))
    negation_markers = set(config.get("negation_markers", []))
    trailing_window = config.get("trailing_window", 20)

    tail = entries[-trailing_window:] if len(entries) > trailing_window else entries
    max_score = 0.0

    for entry in tail:
        thesis = _extract_field(entry, "THESIS_SUMMARY")
        tokens = _tokenize_lower(thesis)
        total = len(tokens) if tokens else 1
        weighted_hits = 0

        for i, token in enumerate(tokens):
            if token not in forbidden_terms:
                continue

            # Check context window (5 tokens before and after)
            window_start = max(0, i - 5)
            window_end = min(len(tokens), i + 6)
            context = set(tokens[window_start:window_end])

            has_negation = bool(context & negation_markers)
            has_assertion = bool(context & assertion_markers)

            if has_negation:
                continue  # Negation context — not a violation
            if has_assertion:
                weighted_hits += 1  # Assertion context — violation

        score = weighted_hits / total
        if score > max_score:
            max_score = score

    return max_score


# ---------------------------------------------------------------------------
# Breach state management (DB operations — mocked in tests)
# ---------------------------------------------------------------------------


async def _load_breach_counts(handle: str) -> Dict[str, int]:
    """Load breach counts for all metrics for a given agent from ars_state table."""
    from src.core.db import get_pool

    pool = get_pool()
    counts: Dict[str, int] = {}
    async with pool.connection() as conn:
        rows = await conn.execute(
            "SELECT metric_name, breach_count FROM ars_state WHERE soul_handle = %s",
            (handle,),
        )
        async for row in rows:
            counts[row[0]] = row[1]
    return counts


async def _update_breach_count(handle: str, metric: str, new_count: int) -> None:
    """Upsert breach count for (handle, metric) in ars_state."""
    from src.core.db import get_pool

    pool = get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            """
            INSERT INTO ars_state (soul_handle, metric_name, breach_count, last_audit_ts)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (soul_handle, metric_name)
            DO UPDATE SET breach_count = %s, last_audit_ts = CURRENT_TIMESTAMP
            """,
            (handle, metric, new_count, new_count),
        )


async def _suspend_agent(handle: str) -> None:
    """Set evolution_suspended=TRUE for agent in agent_merit_scores."""
    from src.core.db import get_pool

    pool = get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE agent_merit_scores SET evolution_suspended = TRUE WHERE soul_handle = %s",
            (handle,),
        )


async def _unsuspend_agent(handle: str) -> None:
    """Set evolution_suspended=FALSE for agent, reset all breach counts."""
    from src.core.db import get_pool

    pool = get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE agent_merit_scores SET evolution_suspended = FALSE WHERE soul_handle = %s",
            (handle,),
        )
        await conn.execute(
            "DELETE FROM ars_state WHERE soul_handle = %s",
            (handle,),
        )
    _append_audit_event({
        "event": "ARS_UNSUSPEND",
        "agent": handle,
        "metric": "all",
        "value": 0,
        "threshold": 0,
        "breach_count": 0,
        "action": "unsuspend",
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    logger.info("ars_auditor: unsuspended %s — breach counters reset", handle)


async def _load_merit_dimensions(handle: str) -> Dict[str, float]:
    """Load KAMI dimensions from agent_merit_scores for KAMI variance metric."""
    from src.core.db import get_pool

    pool = get_pool()
    async with pool.connection() as conn:
        row = await conn.execute(
            "SELECT dimensions FROM agent_merit_scores WHERE soul_handle = %s",
            (handle,),
        )
        result = await row.fetchone()
        if result and result[0]:
            return result[0]
    return {"accuracy": 0.5, "recovery": 0.5, "consensus": 0.5, "fidelity": 0.5}


# ---------------------------------------------------------------------------
# Audit event writer
# ---------------------------------------------------------------------------


def _append_audit_event(event: dict) -> None:
    """Append a JSON line to the audit file."""
    audit_path = _get_audit_path()
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, default=str) + "\n")


# ---------------------------------------------------------------------------
# Core audit function
# ---------------------------------------------------------------------------


async def audit_agent(
    handle: str,
    config: Dict,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Audit a single agent for drift across all 5 metrics.

    Returns a dict with status and per-metric results.
    """
    agent_id = HANDLE_TO_AGENT_ID.get(handle)
    if not agent_id:
        return {"status": "error", "message": f"Unknown handle: {handle}"}

    # Read MEMORY.md
    souls_dir = _get_souls_dir()
    memory_path = souls_dir / agent_id / "MEMORY.md"

    entries: List[str] = []
    if memory_path.exists():
        content = memory_path.read_text(encoding="utf-8")
        entries = _parse_entries(content)

    # Warm-up check
    warmup_min = config.get("warmup_min_entries", 30)
    if len(entries) < warmup_min:
        return {"status": "warmup", "entries": len(entries)}

    # Load proposals dir
    proposals_dir = _get_proposals_dir()

    # Compute all 5 metrics
    trailing_window = config.get("trailing_window", 20)

    m1a = _compute_proposal_rejection_rate(handle, proposals_dir, trailing_window)
    m1b = _compute_drift_flag_frequency(entries, trailing_window)

    # KAMI variance — load from DB (or mock)
    dimensions = await _load_merit_dimensions(handle)
    m2 = _compute_kami_dimension_variance(dimensions)

    m3 = _compute_alignment_mutation_count(handle, proposals_dir)
    m4_dist, m4_polarity = _compute_sentiment_shift(entries, config)
    m5 = _compute_role_boundary_violations(entries, handle, config)

    # Build threshold checks
    thresholds = {
        "proposal_rejection_rate": (m1a, config.get("proposal_rejection_rate_threshold", 0.5)),
        "drift_flag_frequency": (m1b, config.get("drift_flag_frequency_threshold", 0.3)),
        "kami_dimension_variance": (m2, config.get("kami_variance_threshold", 0.04)),
        "alignment_mutation_count": (m3, config.get("alignment_mutation_count_threshold", 3)),
        "role_boundary_violations": (m5, config.get("role_boundary_score_threshold", 0.02)),
    }

    # Sentiment shift: flags when BOTH distance AND polarity exceed thresholds
    sentiment_distance_threshold = config.get("sentiment_distance_threshold", 0.3)
    sentiment_polarity_threshold = config.get("sentiment_polarity_threshold", 0.15)
    sentiment_breached = (
        m4_dist > sentiment_distance_threshold
        and abs(m4_polarity) > sentiment_polarity_threshold
    )

    # Role boundary: also check min_hits
    role_min_hits = config.get("role_boundary_min_hits", 3)

    # Load existing breach counts (skip in dry_run)
    if not dry_run:
        breach_counts = await _load_breach_counts(handle)
    else:
        breach_counts = {}

    consecutive_to_suspend = config.get("consecutive_breaches_to_suspend", 3)

    metrics_result: Dict[str, Any] = {}

    # Process each metric
    for metric_name, (value, threshold) in thresholds.items():
        # Special handling for alignment_mutation_count (>= threshold, integer)
        if metric_name == "alignment_mutation_count":
            breached = value >= threshold
        else:
            breached = value > threshold

        # Special override for role_boundary: also needs min_hits
        # (the score is weighted_hits/tokens, but we re-check conceptually)
        # For role_boundary, already using score threshold

        action = "clean"
        new_breach_count = 0

        if breached:
            old_count = breach_counts.get(metric_name, 0)
            new_breach_count = old_count + 1

            if new_breach_count >= consecutive_to_suspend:
                action = "suspend"
                logger.critical(
                    "ARS: %s metric %s — %d consecutive breaches — SUSPENDING",
                    handle, metric_name, new_breach_count,
                )
                if not dry_run:
                    await _update_breach_count(handle, metric_name, new_breach_count)
                    await _suspend_agent(handle)
            else:
                action = "flag"
                logger.warning(
                    "ARS: %s metric %s — breach %d/%d (value=%.4f threshold=%.4f)",
                    handle, metric_name, new_breach_count, consecutive_to_suspend,
                    float(value), float(threshold),
                )
                if not dry_run:
                    await _update_breach_count(handle, metric_name, new_breach_count)

            # Write audit event
            _append_audit_event({
                "event": "ARS_BREACH",
                "agent": handle,
                "metric": metric_name,
                "value": value,
                "threshold": threshold,
                "breach_count": new_breach_count,
                "action": action,
                "ts": datetime.now(timezone.utc).isoformat(),
            })
        else:
            # Clean cycle — reset breach counter if it was >0
            old_count = breach_counts.get(metric_name, 0)
            if old_count > 0 and not dry_run:
                await _update_breach_count(handle, metric_name, 0)

        metrics_result[metric_name] = {
            "value": value,
            "threshold": threshold,
            "breached": breached,
            "breach_count": new_breach_count if breached else 0,
            "action": action,
        }

    # Handle sentiment shift separately (dual threshold)
    old_sentiment_count = breach_counts.get("sentiment_shift", 0)
    if sentiment_breached:
        new_count = old_sentiment_count + 1
        if new_count >= consecutive_to_suspend:
            action = "suspend"
            logger.critical(
                "ARS: %s sentiment_shift — %d consecutive breaches — SUSPENDING",
                handle, new_count,
            )
            if not dry_run:
                await _update_breach_count(handle, "sentiment_shift", new_count)
                await _suspend_agent(handle)
        else:
            action = "flag"
            logger.warning(
                "ARS: %s sentiment_shift — breach %d/%d (dist=%.4f polarity=%.4f)",
                handle, new_count, consecutive_to_suspend, m4_dist, m4_polarity,
            )
            if not dry_run:
                await _update_breach_count(handle, "sentiment_shift", new_count)

        _append_audit_event({
            "event": "ARS_BREACH",
            "agent": handle,
            "metric": "sentiment_shift",
            "value": {"distance": m4_dist, "polarity_delta": m4_polarity},
            "threshold": {"distance": sentiment_distance_threshold, "polarity": sentiment_polarity_threshold},
            "breach_count": new_count,
            "action": action,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        metrics_result["sentiment_shift"] = {
            "value": {"distance": m4_dist, "polarity_delta": m4_polarity},
            "threshold": {"distance": sentiment_distance_threshold, "polarity": sentiment_polarity_threshold},
            "breached": True,
            "breach_count": new_count,
            "action": action,
        }
    else:
        if old_sentiment_count > 0 and not dry_run:
            await _update_breach_count(handle, "sentiment_shift", 0)
        metrics_result["sentiment_shift"] = {
            "value": {"distance": m4_dist, "polarity_delta": m4_polarity},
            "threshold": {"distance": sentiment_distance_threshold, "polarity": sentiment_polarity_threshold},
            "breached": False,
            "breach_count": 0,
            "action": "clean",
        }

    return {
        "status": "audited",
        "handle": handle,
        "entries": len(entries),
        "metrics": metrics_result,
    }


async def audit_all(
    config: Dict,
    agent_filter: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Audit all agents (or single if agent_filter set).

    Returns dict keyed by soul handle with audit results.
    """
    handles = [agent_filter] if agent_filter else ALL_SOUL_HANDLES
    results: Dict[str, Any] = {}

    for handle in handles:
        try:
            result = await audit_agent(handle, config, dry_run=dry_run)
            results[handle] = result
        except Exception as e:
            logger.error("ars_auditor: error auditing %s: %s", handle, e)
            results[handle] = {"status": "error", "message": str(e)}

    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import asyncio

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="ARS Drift Auditor")
    parser.add_argument("--agent", type=str, help="Audit single agent (e.g. MOMENTUM)")
    parser.add_argument("--dry-run", action="store_true", help="Compute metrics without DB writes")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--unsuspend", type=str, help="Unsuspend agent (e.g. MOMENTUM)")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = _load_ars_config()

    if args.unsuspend:
        asyncio.run(_unsuspend_agent(args.unsuspend))
    else:
        result = asyncio.run(audit_all(config, agent_filter=args.agent, dry_run=args.dry_run))
        print(json.dumps(result, indent=2, default=str))
