"""
src.core.decision_card — Immutable audit artifact for executed trades.

Pure Python service: no LLM, no I/O, no async at module level.
All hashing uses SHA-256 over a deterministic canonical JSON payload.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class AgentContributions(BaseModel):
    """Snapshot of every agent's output that influenced the trade decision."""

    macro_report: Optional[dict] = None
    quant_proposal: Optional[dict] = None
    bullish_thesis: Optional[dict] = None
    bearish_thesis: Optional[dict] = None
    debate_resolution: Optional[dict] = None


class RiskSnapshot(BaseModel):
    """Risk and compliance fields captured at execution time."""

    consensus_score: float
    risk_approval: dict
    compliance_flags: list[str]
    portfolio_risk_score: Optional[float] = None


class DecisionCard(BaseModel):
    """
    Immutable, self-verifying audit artifact for a single executed trade.

    The content_hash field is a SHA-256 digest of the canonical JSON of all
    other fields (sort_keys=True, ensure_ascii=False).  Altering any field
    after signing breaks the hash.
    """

    card_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str = "1.0"
    event_type: str = "decision_card_created"
    task_id: str
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    execution_result: dict
    agent_contributions: AgentContributions
    applied_rule_ids: list[str]
    risk_snapshot: RiskSnapshot
    prev_audit_hash: Optional[str] = None
    hash_algorithm: str = "sha256"
    content_hash: str = ""  # populated by build_decision_card()


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def canonical_json(payload: dict) -> str:
    """
    Return a deterministic JSON string for *payload*.

    Rules:
    - Keys sorted alphabetically (sort_keys=True)
    - Non-ASCII characters preserved (ensure_ascii=False)
    - Non-serialisable objects rendered via str()
    """
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)


def _compute_hash(card_dict: dict) -> str:
    """
    Compute SHA-256 of the canonical JSON of *card_dict* with 'content_hash' excluded.

    This is the canonical hashing path used by both builder and verifier.
    """
    payload = {k: v for k, v in card_dict.items() if k != "content_hash"}
    raw = canonical_json(payload)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------


def verify_decision_card(card_dict: dict) -> bool:
    """
    Return True iff the stored content_hash matches the recomputed hash.

    Never mutates *card_dict*.
    """
    expected = card_dict.get("content_hash", "")
    recomputed = _compute_hash(card_dict)
    return recomputed == expected


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_decision_card(
    state: dict,
    registry=None,
    prev_audit_hash: Optional[str] = None,
) -> DecisionCard:
    """
    Construct and sign a DecisionCard from a SwarmState dict.

    Args:
        state: SwarmState-compatible dict (at minimum: task_id, execution_result,
               consensus_score, compliance_flags; other fields may be None/absent).
        registry: Optional MemoryRegistry instance.  If provided,
                  get_active_rules() is called and .id fields collected.
        prev_audit_hash: Optional SHA-256 hash of the most-recent PostgreSQL
                         audit_logs row.  None is an explicit, valid value.

    Returns:
        DecisionCard with content_hash populated.
    """
    # --- Agent contributions ---
    agent_contributions = AgentContributions(
        macro_report=state.get("macro_report"),
        quant_proposal=state.get("quant_proposal"),
        bullish_thesis=state.get("bullish_thesis"),
        bearish_thesis=state.get("bearish_thesis"),
        debate_resolution=state.get("debate_resolution"),
    )

    # --- Risk snapshot ---
    # portfolio_risk_score lives at state["metadata"]["trade_risk_score"] (Phase 8)
    portfolio_risk_score: Optional[float] = state.get("metadata", {}).get(
        "trade_risk_score"
    )

    risk_snapshot = RiskSnapshot(
        consensus_score=state.get("consensus_score", 0.0),
        risk_approval=state.get("risk_approval") or {},
        compliance_flags=state.get("compliance_flags") or [],
        portfolio_risk_score=portfolio_risk_score,
    )

    # --- Applied rule IDs ---
    applied_rule_ids: list[str] = []
    if registry is not None:
        applied_rule_ids = [r.id for r in registry.get_active_rules()]

    # --- Build card (content_hash empty at construction) ---
    card = DecisionCard(
        task_id=state["task_id"],
        execution_result=state.get("execution_result") or {},
        agent_contributions=agent_contributions,
        applied_rule_ids=applied_rule_ids,
        risk_snapshot=risk_snapshot,
        prev_audit_hash=prev_audit_hash,
    )

    # --- Compute and attach content_hash ---
    card_dict = card.model_dump(mode="json")
    card.content_hash = _compute_hash(card_dict)

    return card
