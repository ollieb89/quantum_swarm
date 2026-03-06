"""
src.core.blackboard — Session-based filesystem Blackboard for inter-agent communication.

Each session (keyed by task_id / session_id) gets its own subdirectory under
data/inter_agent_comms/.  Individual keys are stored as JSON files.  Writes are
protected by an exclusive fcntl advisory lock so concurrent agents cannot corrupt
a slot.

Usage::

    board = InterAgentBlackboard()
    board.write_state("abc123", "objective", {"user_input": "analyse BTC"})
    data = board.read_state("abc123", "objective")   # -> {"user_input": ...}
    keys = board.list_keys("abc123")                 # -> ["objective"]
"""

import fcntl
import json
from pathlib import Path
from typing import Any, List, Optional


class InterAgentBlackboard:
    """Filesystem-backed, session-scoped key-value store with file locking.

    Each session lives at ``<base_dir>/<session_id>/`` and each key is a
    ``<key>.json`` file inside that directory.  An ``fcntl.LOCK_EX`` advisory
    lock is acquired on a per-slot lock file before every read or write to
    ensure atomicity across concurrent processes.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = Path(__file__).resolve().parents[2] / "data" / "inter_agent_comms"
        self._base = Path(base_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _session_dir(self, session_id: str) -> Path:
        """Return the directory for a session."""
        return self._base / session_id

    def _slot_path(self, session_id: str, key: str) -> Path:
        return self._session_dir(session_id) / f"{key}.json"

    def _lock_path(self, session_id: str, key: str) -> Path:
        """Return a dedicated lock-file path (never used for data)."""
        return self._session_dir(session_id) / f".{key}.lock"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write_state(self, session_id: str, key: str, value: Any) -> None:
        """Persist *value* to *key* within *session_id*.

        Acquires an exclusive advisory lock for the duration of the write to
        prevent concurrent corruption.
        """
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        lock_path = self._lock_path(session_id, key)
        slot_path = self._slot_path(session_id, key)

        with open(lock_path, "w") as lock_fh:
            fcntl.flock(lock_fh, fcntl.LOCK_EX)
            try:
                slot_path.write_text(json.dumps(value), encoding="utf-8")
            finally:
                fcntl.flock(lock_fh, fcntl.LOCK_UN)

    def read_state(self, session_id: str, key: str) -> Optional[Any]:
        """Return the stored value for *key*, or ``None`` if it does not exist.

        Acquires a shared advisory lock to ensure a consistent read.
        """
        lock_path = self._lock_path(session_id, key)
        slot_path = self._slot_path(session_id, key)

        try:
            with open(lock_path, "a") as lock_fh:  # 'a' creates if missing
                fcntl.flock(lock_fh, fcntl.LOCK_SH)
                try:
                    if not slot_path.exists():
                        return None
                    return json.loads(slot_path.read_text(encoding="utf-8"))
                finally:
                    fcntl.flock(lock_fh, fcntl.LOCK_UN)
        except FileNotFoundError:
            # session_dir doesn't exist yet, so slot cannot exist
            return None

    def list_keys(self, session_id: str) -> List[str]:
        """Return all key names written to *session_id* (no locking needed)."""
        session_dir = self._base / session_id
        if not session_dir.exists():
            return []
        return [
            p.stem
            for p in session_dir.glob("*.json")
        ]
