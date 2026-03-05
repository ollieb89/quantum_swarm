from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class GraphDecision:
    """Immutable result from a LangGraph orchestration run."""

    task_id: str
    decision: str
    consensus_score: float = 0.0
    rationale: str = ""
    proposals: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
