"""
Weekly deduplication and orphan-chunk cleanup for the MemoryService.

Called by MemoryService.deduplicate() and by the weekly systemd timer
via scripts/run_obsidian_tracking_update.sh.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from src.memory.service import DeduplicationResult

logger = logging.getLogger(__name__)


def run_deduplication(collection: Any) -> DeduplicationResult:
    """
    Scan the collection for:
      1. Duplicate content_hash values — keep earliest by ingested_at, delete the rest.
      2. Orphaned chunks — chunk indexes don't form a complete set 0..chunk_count-1.

    Returns a DeduplicationResult with counts.
    """
    duplicates_removed = 0
    orphans_removed = 0

    try:
        result = collection.get(include=["metadatas"])
        ids: list[str] = result.get("ids") or []
        metas: list[dict] = result.get("metadatas") or []

        if not ids:
            return DeduplicationResult(duplicates_removed=0, orphans_removed=0)

        # --- Step 1: Deduplicate by content_hash ---
        # Group chunk IDs by content_hash; keep earliest ingested_at
        hash_groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for chunk_id, meta in zip(ids, metas):
            if meta is None:
                continue
            ch = meta.get("content_hash", "")
            ingested_at = meta.get("ingested_at", "")
            if ch:
                hash_groups[ch].append((chunk_id, ingested_at))

        ids_to_delete: list[str] = []
        for ch, entries in hash_groups.items():
            if len(entries) <= 1:
                continue
            # Sort by ingested_at ascending; keep first (earliest)
            entries_sorted = sorted(entries, key=lambda t: t[1])
            stale = [cid for cid, _ in entries_sorted[1:]]
            ids_to_delete.extend(stale)

        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            duplicates_removed = len(ids_to_delete)
            logger.info("Deduplication: removed %d duplicate chunks", duplicates_removed)

        # --- Step 2: Orphan detection ---
        # Re-fetch after dedup to get fresh state
        result2 = collection.get(include=["metadatas"])
        ids2: list[str] = result2.get("ids") or []
        metas2: list[dict] = result2.get("metadatas") or []

        # Group by document_id
        doc_chunks: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
        for chunk_id, meta in zip(ids2, metas2):
            if meta is None:
                continue
            doc_id = meta.get("document_id", "")
            chunk_index = meta.get("chunk_index", -1)
            chunk_count = meta.get("chunk_count", -1)
            if doc_id:
                doc_chunks[doc_id].append((chunk_index, chunk_count, chunk_id))

        orphan_ids: list[str] = []
        for doc_id, entries in doc_chunks.items():
            # All chunk_count values should agree
            counts = {cc for _, cc, _ in entries}
            if len(counts) != 1:
                # Conflicting chunk_count — all chunks for this doc are suspect
                logger.warning("Conflicting chunk_count for document %s: %s", doc_id, counts)
                orphan_ids.extend(cid for _, _, cid in entries)
                continue

            expected_count = counts.pop()
            actual_indexes = sorted(ci for ci, _, _ in entries)
            expected_indexes = list(range(expected_count))

            if actual_indexes != expected_indexes:
                # Missing or duplicate indexes — mark all as orphans
                logger.warning(
                    "Orphaned chunks for document %s: expected %s, got %s",
                    doc_id,
                    expected_indexes,
                    actual_indexes,
                )
                orphan_ids.extend(cid for _, _, cid in entries)

        if orphan_ids:
            collection.delete(ids=orphan_ids)
            orphans_removed = len(orphan_ids)
            logger.info("Deduplication: removed %d orphaned chunks", orphans_removed)

    except Exception as exc:
        logger.error("run_deduplication failed: %s", exc, exc_info=True)

    return DeduplicationResult(
        duplicates_removed=duplicates_removed,
        orphans_removed=orphans_removed,
    )


if __name__ == "__main__":
    """Entry point for weekly systemd timer invocation."""
    import sys

    sys.path.insert(0, ".")

    from src.memory.service import MemoryService

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    svc = MemoryService()
    result = svc.deduplicate()
    print(f"Deduplication complete: {result.duplicates_removed} duplicates, {result.orphans_removed} orphans removed")
