"""
Append-only JSONL audit log writer.

Called only by MemoryService — never imported directly by graph nodes or agents.
Every store/search/delete operation writes a structured event here.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_AUDIT_PATH = Path("data/audit.jsonl")


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class AuditLog:
    """Append-only JSONL audit writer."""

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path else _DEFAULT_AUDIT_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: dict[str, Any]) -> None:
        """Append a single event dict as a JSON line. Never raises."""
        try:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, default=str) + "\n")
        except Exception as exc:
            logger.error("audit write failed: %s", exc)

    def store_success(
        self,
        *,
        document_id: str,
        source: str,
        node: str,
        chunk_count: int,
        content_hash: str,
        ingested_at: str,
    ) -> None:
        self.write(
            {
                "timestamp": _now_utc(),
                "event": "store",
                "status": "success",
                "document_id": document_id,
                "source": source,
                "node": node,
                "chunk_count": chunk_count,
                "content_hash": content_hash,
                "ingested_at": ingested_at,
            }
        )

    def store_error(
        self,
        *,
        source: str,
        node: str,
        error_type: str,
        error_message: str,
    ) -> None:
        self.write(
            {
                "timestamp": _now_utc(),
                "event": "store",
                "status": "error",
                "source": source,
                "node": node,
                "error_type": error_type,
                "error_message": error_message,
            }
        )

    def search_event(
        self,
        *,
        query: str,
        source_filter: str | None,
        k: int,
        hits_returned: int,
        top_document_ids: list[str],
    ) -> None:
        self.write(
            {
                "timestamp": _now_utc(),
                "event": "search",
                "status": "success",
                "query": query,
                "source_filter": source_filter,
                "k": k,
                "hits_returned": hits_returned,
                "top_document_ids": top_document_ids,
            }
        )

    def delete_event(self, *, document_id: str, source: str, chunk_count: int) -> None:
        self.write(
            {
                "timestamp": _now_utc(),
                "event": "delete",
                "status": "success",
                "document_id": document_id,
                "source": source,
                "chunk_count": chunk_count,
            }
        )

    def deduplicate_event(
        self,
        *,
        duplicates_removed: int,
        orphans_removed: int,
    ) -> None:
        self.write(
            {
                "timestamp": _now_utc(),
                "event": "deduplicate",
                "status": "success",
                "duplicates_removed": duplicates_removed,
                "orphans_removed": orphans_removed,
            }
        )
