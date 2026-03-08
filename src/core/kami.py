"""KAMI Merit Index — arithmetic core for earned dynamic merit scoring.

Phase 16, Plan 01.

This module contains only pure functions and frozen dataclasses. No LLM calls,
no asyncio, no module-level state. All functions are synchronous.

Import layer: may import from src.core.* (core-to-core is permitted).
Must NOT import from src.graph.* — enforced by Import Layer Law.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from src.core.soul_errors import SoulNotFoundError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MERIT: float = 0.5
MERIT_FLOOR: float = 0.1
MERIT_CEIL: float = 1.0

# Default composite formula weights — must sum to 1.0.
# Matching config/swarm_config.yaml kami: section.
DEFAULT_WEIGHTS: Dict[str, float] = {
    "alpha": 0.30,  # Accuracy weight
    "beta": 0.35,   # Recovery weight
    "gamma": 0.25,  # Consensus weight
    "delta": 0.10,  # Fidelity weight
}

# All authoritative soul handles in this system.
ALL_SOUL_HANDLES = ["AXIOM", "MOMENTUM", "CASSANDRA", "SIGMA", "GUARDIAN"]

# Maps LangGraph node / agent_id strings to canonical soul handles.
RESEARCHER_HANDLE_MAP: Dict[str, str] = {
    "bullish_research": "MOMENTUM",
    "bearish_research": "CASSANDRA",
}

# Error types that indicate self-induced failure (not upstream).
# Legacy: used by error_type fallback path (pre-Phase 22).
_SELF_INDUCED_ERRORS = frozenset({
    "INVALID_INPUT",
    "SCHEMA_FAILURE",
    "MALFORMED_OUTPUT",
    "TOOL_ERROR",
})

# Phase 22: failure_cause classification taxonomy.
# Self-induced causes penalise Recovery (signal -> 0.0).
_SELF_INDUCED_CAUSES = frozenset({
    "INVALID_ORDER",
    "BAD_PARAMETERS",
    "RISK_RULE_VIOLATION",
    "INSUFFICIENT_FUNDS_FROM_SIZING",
    "UNSUPPORTED_INSTRUMENT",
})

# External causes spare Recovery (signal -> 1.0, no penalty).
_EXTERNAL_CAUSES = frozenset({
    "EXCHANGE_DOWN",
    "BROKER_API_ERROR",
    "NETWORK_TIMEOUT",
    "VENUE_UNAVAILABLE",
})


# ---------------------------------------------------------------------------
# KAMIDimensions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KAMIDimensions:
    """Immutable snapshot of one agent's four merit dimensions.

    Frozen for hashability and concurrent fan-out read safety.
    Default values are DEFAULT_MERIT (0.5) representing cold-start neutral.

    Attributes:
        accuracy:  How often the agent's signals align with eventual outcomes.
        recovery:  Ability to self-correct after errors (penalises self-induced failures).
        consensus: Contribution to debate convergence (CASSANDRA protected — see extractor).
        fidelity:  Adherence to authorised soul identity (non-empty IDENTITY.md).
    """
    accuracy: float = field(default=DEFAULT_MERIT)
    recovery: float = field(default=DEFAULT_MERIT)
    consensus: float = field(default=DEFAULT_MERIT)
    fidelity: float = field(default=DEFAULT_MERIT)


# ---------------------------------------------------------------------------
# Core arithmetic
# ---------------------------------------------------------------------------

def compute_merit(dims: KAMIDimensions, weights: Dict[str, float]) -> float:
    """Compute the composite merit score from dimension values and weights.

    Formula: alpha*accuracy + beta*recovery + gamma*consensus + delta*fidelity
    Result is clamped to [MERIT_FLOOR, MERIT_CEIL].

    Args:
        dims:    Frozen KAMIDimensions snapshot.
        weights: Dict with keys 'alpha', 'beta', 'gamma', 'delta'. Must sum to 1.0.

    Returns:
        Float in [0.1, 1.0].
    """
    raw = (
        weights["alpha"] * dims.accuracy
        + weights["beta"] * dims.recovery
        + weights["gamma"] * dims.consensus
        + weights["delta"] * dims.fidelity
    )
    # Round to 10 decimal places to eliminate IEEE 754 float jitter before clamping.
    raw = round(raw, 10)
    return max(MERIT_FLOOR, min(MERIT_CEIL, raw))


def apply_ema(prev: float, signal: float, lam: float) -> float:
    """Exponential Moving Average update.

    Formula: lam * signal + (1.0 - lam) * prev

    Args:
        prev:   Previous EMA value.
        signal: New signal reading.
        lam:    Decay rate in [0.0, 1.0]. Higher = more weight on recent signal.

    Returns:
        Updated EMA float.
    """
    return lam * signal + (1.0 - lam) * prev


# ---------------------------------------------------------------------------
# Signal extractors (private — called by merit_updater in Plan 02)
# ---------------------------------------------------------------------------

def _extract_recovery_signal(state: dict) -> float:
    """Derive the recovery dimension signal from execution_result in state.

    Phase 22 update: checks ``failure_cause`` field FIRST for classified
    failure taxonomy.  Falls through to legacy ``error_type`` logic when
    ``failure_cause`` is absent or None (backward compatibility).

    Rules (evaluated in order):
    - No execution_result key -> no execution occurred -> 1.0 (no penalty).
    - success=True -> 1.0.
    - failure_cause in _SELF_INDUCED_CAUSES -> 0.0.
    - failure_cause in _EXTERNAL_CAUSES -> 1.0 (no penalty).
    - failure_cause is some other non-None string -> 1.0 (fail-open).
    - failure_cause is None/missing -> fall through to legacy error_type path:
      - producer_agent_id present and != active_persona -> 1.0.
      - error_type in _SELF_INDUCED_ERRORS -> 0.0.
      - Catch-all -> 0.0.

    Args:
        state: SwarmState dict (or dict with same keys).

    Returns:
        Float 0.0 or 1.0.
    """
    result = state.get("execution_result")
    if result is None:
        # No execution attempted — no penalty.
        return 1.0

    if result.get("success") is True:
        return 1.0

    # --- Phase 22: failure_cause classification ---
    failure_cause = result.get("failure_cause")
    if failure_cause is not None:
        if failure_cause in _SELF_INDUCED_CAUSES:
            return 0.0
        # External or unknown cause — fail-open (no penalty).
        return 1.0

    # --- Legacy path (pre-Phase 22 execution_results without failure_cause) ---

    # Check if error was upstream (not self-induced).
    producer = result.get("producer_agent_id")
    active = state.get("active_persona")
    if producer is not None and producer != active:
        return 1.0

    # Self-induced or unknown failure.
    error_type = result.get("error_type")
    if error_type in _SELF_INDUCED_ERRORS:
        return 0.0

    # Catch-all: unknown failure → penalise.
    return 0.0


def _extract_consensus_signal(state: dict) -> float:
    """Derive the consensus dimension signal from weighted_consensus_score.

    Uses normalised distance from neutral (0.5) to reward strong directional
    signals without penalising contrarians (CASSANDRA protection).

    Formula: min(1.0, abs(score - 0.5) * 2.0)

    Args:
        state: SwarmState dict.

    Returns:
        Float in [0.0, 1.0]. 0.0 if score missing.
    """
    score = state.get("weighted_consensus_score")
    if score is None:
        return 0.0
    return min(1.0, abs(score - 0.5) * 2.0)


def _extract_fidelity_signal(agent_id: str) -> float:
    """Derive the fidelity dimension signal by inspecting the agent's soul.

    Uses Option A from RESEARCH.md: call load_soul(agent_id) and check whether
    soul.identity has non-empty content. An empty or absent IDENTITY.md indicates
    a skeleton agent that has not been authored — fidelity 0.0.

    Args:
        agent_id: Agent directory name under src/core/souls/ (e.g. 'macro_analyst').

    Returns:
        1.0 if soul.identity.strip() is non-empty, otherwise 0.0.
    """
    # Lazy import inside function to avoid circular-import risk at module load time.
    from src.core.soul_loader import load_soul  # noqa: PLC0415

    try:
        soul = load_soul(agent_id)
    except (SoulNotFoundError, Exception):
        return 0.0

    return 1.0 if soul.identity.strip() else 0.0
