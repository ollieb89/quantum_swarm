"""
MemoryService — sole interface to the ChromaDB vector store.

No other module imports chromadb directly. All reads, writes, and maintenance
operations go through this class.
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from src.memory.audit import AuditLog
from src.memory.config import (
    CHARS_PER_TOKEN,
    CHUNK_MAX_TOKENS,
    CHUNK_OVERLAP_TOKENS,
    CHUNK_SINGLE_THRESHOLD_TOKENS,
    COLLECTION_NAME,
    DEFAULT_SEARCH_K,
    MAX_HIT_CONTENT_CHARS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class MemorySource(str, Enum):
    TRADE = "trade"
    RESEARCH = "research"
    EXTERNAL_DATA = "external_data"


@dataclass
class MemoryHit:
    document_id: str
    chunk_id: str
    content: str
    source: MemorySource
    metadata: dict[str, Any]
    score: float  # normalized relevance; higher is better


@dataclass
class StoredDocument:
    document_id: str
    chunks: list[str]  # ordered by chunk_index
    source: MemorySource
    metadata: dict[str, Any]


@dataclass
class DeduplicationResult:
    duplicates_removed: int
    orphans_removed: int


# ---------------------------------------------------------------------------
# Required metadata keys per source
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS: dict[MemorySource, list[str]] = {
    MemorySource.TRADE: ["symbol", "timestamp", "run_id"],
    MemorySource.RESEARCH: ["symbol", "timestamp", "run_id", "agent"],
    MemorySource.EXTERNAL_DATA: ["timestamp", "data_type", "source_name", "title_or_url"],
}

_VALID_DATA_TYPES = {"news", "economic", "fundamental"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_content(text: str) -> str:
    """Normalize text for stable content hashing."""
    text = text.strip()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text)
    return text


def _content_hash(text: str) -> str:
    """SHA-256 hex of normalized content."""
    return hashlib.sha256(_normalize_content(text).encode("utf-8")).hexdigest()


def _approx_tokens(text: str) -> int:
    """Rough token count: chars / CHARS_PER_TOKEN."""
    return len(text) // CHARS_PER_TOKEN


def _make_document_id(source: MemorySource, metadata: dict[str, Any]) -> str:
    """Generate a deterministic, prefixed document ID from source-specific keys."""
    if source == MemorySource.TRADE:
        key = f"{metadata.get('symbol', '')}:{metadata.get('timestamp', '')}:{metadata.get('run_id', '')}"
    elif source == MemorySource.RESEARCH:
        key = f"{metadata.get('run_id', '')}:{metadata.get('agent', '')}:{metadata.get('timestamp', '')}"
    else:  # EXTERNAL_DATA
        key = (
            f"{metadata.get('source_name', '')}:{metadata.get('data_type', '')}:"
            f"{metadata.get('title_or_url', '')}:{metadata.get('timestamp', '')}"
        )
    hash_hex = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    prefix = source.value.replace("_", "-")
    return f"{prefix}_{hash_hex}"


def _split_into_chunks(content: str) -> list[str]:
    """
    Split content into chunks using the fallback chain:
      paragraph boundary → sentence boundary → hard character split.
    """
    max_chars = CHUNK_MAX_TOKENS * CHARS_PER_TOKEN
    overlap_chars = CHUNK_OVERLAP_TOKENS * CHARS_PER_TOKEN

    if _approx_tokens(content) <= CHUNK_SINGLE_THRESHOLD_TOKENS:
        return [content]

    # --- Step 1: paragraph split ---
    paragraphs = [p.strip() for p in re.split(r"\n\n+", content) if p.strip()]

    # Merge short adjacent paragraphs and split oversized ones
    segments: list[str] = []
    for para in paragraphs:
        if _approx_tokens(para) <= CHUNK_MAX_TOKENS:
            segments.append(para)
        else:
            # --- Step 2: sentence split ---
            sentences = re.split(r"(?<=[.!?])\s+", para)
            current = ""
            for sent in sentences:
                if _approx_tokens(current + " " + sent) <= CHUNK_MAX_TOKENS:
                    current = (current + " " + sent).strip()
                else:
                    if current:
                        segments.append(current)
                    if _approx_tokens(sent) <= CHUNK_MAX_TOKENS:
                        current = sent
                    else:
                        # --- Step 3: hard character split ---
                        for start in range(0, len(sent), max_chars):
                            segments.append(sent[start : start + max_chars])
                        current = ""
            if current:
                segments.append(current)

    # Combine segments into chunks with overlap
    chunks: list[str] = []
    current_chunk = ""
    for seg in segments:
        candidate = (current_chunk + "\n\n" + seg).strip() if current_chunk else seg
        if _approx_tokens(candidate) <= CHUNK_MAX_TOKENS:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # carry overlap from tail of previous chunk
            tail = current_chunk[-overlap_chars:] if overlap_chars and current_chunk else ""
            current_chunk = (tail + "\n\n" + seg).strip() if tail else seg

    if current_chunk:
        chunks.append(current_chunk)

    return chunks if chunks else [content]


def _validate_metadata(source: MemorySource, metadata: dict[str, Any]) -> None:
    required = _REQUIRED_FIELDS[source]
    for field_name in required:
        if not metadata.get(field_name):
            raise ValueError(f"Missing required metadata field '{field_name}' for source '{source.value}'")
    if source == MemorySource.EXTERNAL_DATA:
        dt = metadata.get("data_type", "")
        if dt not in _VALID_DATA_TYPES:
            raise ValueError(f"Invalid data_type '{dt}'; must be one of {_VALID_DATA_TYPES}")


# ---------------------------------------------------------------------------
# MemoryService
# ---------------------------------------------------------------------------


class MemoryService:
    """
    Sole interface to the ChromaDB vector store.

    Parameters
    ----------
    chroma_path:
        Directory for persistent ChromaDB storage. Ignored when ``collection``
        is provided (used primarily in tests).
    collection:
        Inject a pre-built ChromaDB collection. When given, ``chroma_path``
        is ignored and no ChromaDB client is created.
    audit_path:
        Override audit log path (useful in tests).
    """

    def __init__(
        self,
        chroma_path: str | None = None,
        collection: Any | None = None,
        audit_path: str | None = None,
    ) -> None:
        if collection is not None:
            self._collection = collection
        else:
            import chromadb  # lazy import — no key needed at module load time

            path = chroma_path or "data/chroma_db"
            client = chromadb.PersistentClient(path=path)
            self._collection = client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        self._audit = AuditLog(audit_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(
        self,
        content: str,
        source: MemorySource,
        metadata: dict[str, Any],
        document_id: str | None = None,
        node: str = "unknown",
    ) -> str:
        """
        Store or update a logical document and its chunks.

        Returns the document_id. Writes an audit event on success or failure.
        Never raises — failures are logged and audited.
        """
        ingested_at = _now_utc()
        ch = _content_hash(content)
        metadata = dict(metadata)  # don't mutate caller's dict

        try:
            _validate_metadata(source, metadata)
            doc_id = document_id or _make_document_id(source, metadata)

            chunks = _split_into_chunks(content)
            chunk_count = len(chunks)

            # Fetch existing chunk IDs for this document_id
            existing_ids = self._get_chunk_ids_for_document(doc_id)

            # Build new chunk IDs
            new_chunk_ids = [f"{doc_id}:{i:04d}" for i in range(chunk_count)]

            # Delete stale tail chunks not in the new set
            stale_ids = [cid for cid in existing_ids if cid not in new_chunk_ids]
            if stale_ids:
                self._collection.delete(ids=stale_ids)

            # Build shared metadata for each chunk
            base_meta = {
                "document_id": doc_id,
                "source": source.value,
                "content_hash": ch,
                "timestamp": metadata.get("timestamp", ingested_at),
                "ingested_at": ingested_at,
                "chunk_count": chunk_count,
                **{k: v for k, v in metadata.items() if k not in ("content_hash", "ingested_at")},
            }

            chunk_docs: list[str] = []
            chunk_ids: list[str] = []
            chunk_metas: list[dict[str, Any]] = []

            for i, chunk_text in enumerate(chunks):
                cid = f"{doc_id}:{i:04d}"
                chunk_ids.append(cid)
                chunk_docs.append(chunk_text[:MAX_HIT_CONTENT_CHARS])
                chunk_metas.append({**base_meta, "chunk_id": cid, "chunk_index": i})

            self._collection.upsert(
                ids=chunk_ids,
                documents=chunk_docs,
                metadatas=chunk_metas,
            )

            self._audit.store_success(
                document_id=doc_id,
                source=source.value,
                node=node,
                chunk_count=chunk_count,
                content_hash=ch,
                ingested_at=ingested_at,
            )
            return doc_id

        except Exception as exc:
            logger.error("MemoryService.store failed: %s", exc, exc_info=True)
            self._audit.store_error(
                source=source.value,
                node=node,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            raise

    def search(
        self,
        query: str,
        source_filter: MemorySource | None = None,
        k: int = DEFAULT_SEARCH_K,
    ) -> list[MemoryHit]:
        """
        Return ranked memory hits. score is normalized relevance (higher = better).
        ChromaDB cosine distance is converted: score = 1 - distance.
        Results are deduplicated by document_id.
        """
        where: dict[str, Any] | None = None
        if source_filter is not None:
            where = {"source": source_filter.value}

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(k * 2, max(1, self._collection.count())),  # over-fetch for dedup
                where=where,
                include=["documents", "distances", "metadatas"],
            )
        except Exception as exc:
            logger.warning("MemoryService.search failed: %s", exc)
            return []

        hits: list[MemoryHit] = []
        seen_doc_ids: set[str] = set()

        ids_list = (results.get("ids") or [[]])[0]
        docs_list = (results.get("documents") or [[]])[0]
        distances_list = (results.get("distances") or [[]])[0]
        metas_list = (results.get("metadatas") or [[]])[0]

        for chunk_id, doc_text, distance, meta in zip(ids_list, docs_list, distances_list, metas_list):
            if meta is None:
                meta = {}
            doc_id = meta.get("document_id", chunk_id)
            if doc_id in seen_doc_ids:
                continue
            seen_doc_ids.add(doc_id)

            score = max(0.0, 1.0 - float(distance))
            source_val = meta.get("source", "")
            try:
                source_enum = MemorySource(source_val)
            except ValueError:
                source_enum = MemorySource.EXTERNAL_DATA

            hits.append(
                MemoryHit(
                    document_id=doc_id,
                    chunk_id=chunk_id,
                    content=doc_text[:MAX_HIT_CONTENT_CHARS] if doc_text else "",
                    source=source_enum,
                    metadata=meta,
                    score=score,
                )
            )
            if len(hits) >= k:
                break

        self._audit.search_event(
            query=query,
            source_filter=source_filter.value if source_filter else None,
            k=k,
            hits_returned=len(hits),
            top_document_ids=[h.document_id for h in hits[:3]],
        )
        return hits

    def get(self, document_id: str) -> StoredDocument | None:
        """Fetch and reassemble a stored logical document from its chunks."""
        try:
            result = self._collection.get(
                where={"document_id": document_id},
                include=["documents", "metadatas"],
            )
        except Exception as exc:
            logger.warning("MemoryService.get failed for %s: %s", document_id, exc)
            return None

        ids = result.get("ids") or []
        docs = result.get("documents") or []
        metas = result.get("metadatas") or []

        if not ids:
            return None

        # Sort by chunk_index
        triples = sorted(
            zip(ids, docs, metas),
            key=lambda t: (t[2] or {}).get("chunk_index", 0),
        )

        chunks = [doc for _, doc, _ in triples]
        first_meta = triples[0][2] or {}
        source_val = first_meta.get("source", "")
        try:
            source_enum = MemorySource(source_val)
        except ValueError:
            source_enum = MemorySource.EXTERNAL_DATA

        return StoredDocument(
            document_id=document_id,
            chunks=chunks,
            source=source_enum,
            metadata=first_meta,
        )

    def delete(self, document_id: str, node: str = "unknown") -> None:
        """Delete all chunks for a document. Writes audit event."""
        chunk_ids = self._get_chunk_ids_for_document(document_id)
        if chunk_ids:
            # Get source for audit before deleting
            result = self._collection.get(ids=[chunk_ids[0]], include=["metadatas"])
            metas = result.get("metadatas") or [{}]
            source_val = (metas[0] or {}).get("source", "unknown")

            self._collection.delete(ids=chunk_ids)
            self._audit.delete_event(
                document_id=document_id,
                source=source_val,
                chunk_count=len(chunk_ids),
            )

    def deduplicate(self) -> DeduplicationResult:
        """Remove duplicate chunks (by content_hash) and orphaned chunks."""
        from src.memory.indexer import run_deduplication

        result = run_deduplication(self._collection)
        self._audit.deduplicate_event(
            duplicates_removed=result.duplicates_removed,
            orphans_removed=result.orphans_removed,
        )
        return result

    def health_check(self) -> bool:
        """Verify ChromaDB connectivity."""
        try:
            self._collection.count()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_chunk_ids_for_document(self, document_id: str) -> list[str]:
        """Return all chunk IDs belonging to a document_id."""
        try:
            result = self._collection.get(
                where={"document_id": document_id},
                include=[],
            )
            return list(result.get("ids") or [])
        except Exception:
            return []
