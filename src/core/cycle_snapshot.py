"""
src.core.cycle_snapshot — Canonical schema for cycle artifacts.

Pure data model: no I/O, no graph imports, no async.
Mirrors the DecisionCard pattern from src/core/decision_card.py.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CYCLE_ID_PAD_WIDTH = 6
"""Number of digits for zero-padded cycle IDs (e.g. 42 -> '000042')."""


# ---------------------------------------------------------------------------
# Fields required to be non-None for a completed cycle
# ---------------------------------------------------------------------------

_COMPLETED_REQUIRED_FIELDS: tuple[str, ...] = (
    "macro_report",
    "quant_proposal",
    "bullish_thesis",
    "bearish_thesis",
    "debate_history",
    "debate_resolution",
    "weighted_consensus_score",
    "merit_scores",
    "soul_sync_context",
    "execution_result",
    "decision_card",
)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class CycleSnapshot(BaseModel):
    """
    Immutable snapshot of a single orchestrator cycle.

    Manifest fields (cycle_id, task_id, symbol, timestamp, status) are always
    required.  All other fields are Optional and default to None, allowing
    partial snapshots for failed or rejected cycles.
    """

    # -- Manifest (always present) --
    cycle_id: int
    task_id: str
    symbol: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    status: Literal["completed", "rejected", "failed"]

    # -- Agent memos --
    macro_report: Optional[dict] = None
    quant_proposal: Optional[dict] = None
    bullish_thesis: Optional[dict] = None
    bearish_thesis: Optional[dict] = None

    # -- Debate --
    debate_history: Optional[list[dict]] = None
    debate_resolution: Optional[dict] = None

    # -- Consensus --
    weighted_consensus_score: Optional[float] = None

    # -- Merit / persona --
    merit_scores: Optional[dict] = None
    soul_sync_context: Optional[dict] = None

    # -- Risk gate --
    risk_approved: Optional[bool] = None
    risk_notes: Optional[str] = None

    # -- Post-risk (completed only) --
    execution_result: Optional[dict] = None
    decision_card: Optional[dict] = None

    # -- Failure context --
    error_context: Optional[dict] = None

    # -----------------------------------------------------------------------
    # Helper methods
    # -----------------------------------------------------------------------

    def padded_id(self) -> str:
        """Return zero-padded cycle ID string (e.g. 42 -> '000042')."""
        return str(self.cycle_id).zfill(CYCLE_ID_PAD_WIDTH)

    def snapshot_dir(self, base: str = "data/cycles") -> str:
        """Return the filesystem directory for this cycle's artifacts."""
        return str(Path(base) / self.padded_id())

    def validate_completed(self) -> None:
        """
        Raise ValueError if status is 'completed' but required fields are None.

        Only enforces for completed cycles — failed/rejected cycles may have
        partial data by design.
        """
        if self.status != "completed":
            return

        missing = [
            f for f in _COMPLETED_REQUIRED_FIELDS
            if getattr(self, f) is None
        ]
        if missing:
            raise ValueError(
                f"Completed cycle {self.cycle_id} has missing fields: "
                f"{', '.join(missing)}"
            )
