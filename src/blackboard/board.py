"""
src.blackboard.board — Filesystem blackboard for inter-agent communication.

Agents write named slots (JSON files) to data/blackboard/.
Each slot is an isolated file; reads return None for missing slots.
"""

import json
from pathlib import Path
from typing import Any, List, Optional


class Blackboard:
    """Filesystem-backed key-value store for SwarmState slots."""

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = Path(__file__).resolve().parents[2] / "data" / "blackboard"
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, slot: str) -> Path:
        return self._base / f"{slot}.json"

    def write(self, slot: str, data: Any) -> None:
        """Persist data to the named slot, replacing any existing content."""
        self._path(slot).write_text(json.dumps(data), encoding="utf-8")

    def read(self, slot: str) -> Optional[Any]:
        """Return the slot's content, or None if the slot does not exist."""
        p = self._path(slot)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def clear(self, slot: str) -> None:
        """Delete the slot file if it exists."""
        p = self._path(slot)
        if p.exists():
            p.unlink()

    def list_slots(self) -> List[str]:
        """Return names of all currently written slots."""
        return [p.stem for p in self._base.glob("*.json")]
