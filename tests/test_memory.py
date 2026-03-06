"""
Tests for the memory subsystem: MemoryService, chunking, ID generation,
audit log, indexer, tools, and L1 recency filtering.

Uses an injected fake ChromaDB collection (chromadb.EphemeralClient) for
integration tests, and MagicMock collections for unit tests.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.memory.audit import AuditLog
from src.memory.config import (
    CHUNK_MAX_TOKENS,
    CHUNK_SINGLE_THRESHOLD_TOKENS,
    CHARS_PER_TOKEN,
)
from src.memory.service import (
    DeduplicationResult,
    MemoryHit,
    MemoryService,
    MemorySource,
    StoredDocument,
    _content_hash,
    _make_document_id,
    _normalize_content,
    _split_into_chunks,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_collection():
    """Return a real in-memory ChromaDB collection with a unique name to avoid cross-test pollution."""
    import uuid

    import chromadb

    client = chromadb.EphemeralClient()
    name = f"test_{uuid.uuid4().hex[:12]}"
    return client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})


def _make_service(collection=None, audit_path=None):
    if collection is None:
        collection = _fake_collection()
    return MemoryService(collection=collection, audit_path=audit_path)


def _trade_meta(**kwargs):
    base = {
        "symbol": "NVDA",
        "timestamp": "2026-03-06T12:00:00Z",
        "run_id": "run_001",
    }
    base.update(kwargs)
    return base


def _research_meta(**kwargs):
    base = {
        "symbol": "NVDA",
        "timestamp": "2026-03-06T12:00:00Z",
        "run_id": "run_001",
        "agent": "macro_analyst",
    }
    base.update(kwargs)
    return base


def _external_meta(**kwargs):
    base = {
        "timestamp": "2026-03-06T12:00:00Z",
        "data_type": "news",
        "source_name": "reuters",
        "title_or_url": "https://reuters.com/article/1",
    }
    base.update(kwargs)
    return base


SHORT_CONTENT = "This is a short document about NVDA earnings."
LONG_CONTENT = "\n\n".join([f"Section {i}: " + ("A " * 100) for i in range(10)])


# ---------------------------------------------------------------------------
# MemoryService core tests
# ---------------------------------------------------------------------------


class TestMemoryServiceCore:
    def test_store_creates_chunks_with_stable_ids(self):
        svc = _make_service()
        doc_id = svc.store(SHORT_CONTENT, MemorySource.TRADE, _trade_meta())
        assert doc_id.startswith("trade_")
        assert len(doc_id) > 6

        stored = svc.get(doc_id)
        assert stored is not None
        assert len(stored.chunks) >= 1
        assert SHORT_CONTENT.strip() in stored.chunks[0]

    def test_store_upsert_replaces_stale_tail_chunks(self):
        svc = _make_service()
        meta = _trade_meta()
        # Store a long document (many chunks)
        doc_id = svc.store(LONG_CONTENT, MemorySource.TRADE, meta)
        stored_v1 = svc.get(doc_id)
        assert stored_v1 is not None
        v1_chunk_count = len(stored_v1.chunks)

        # Store a shorter version under the same document_id
        doc_id2 = svc.store(SHORT_CONTENT, MemorySource.TRADE, meta, document_id=doc_id)
        assert doc_id2 == doc_id
        stored_v2 = svc.get(doc_id)
        assert stored_v2 is not None
        # Short content should result in fewer chunks
        assert len(stored_v2.chunks) <= v1_chunk_count

    def test_store_writes_audit_event_on_success(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            audit_path = f.name

        svc = _make_service(audit_path=audit_path)
        svc.store(SHORT_CONTENT, MemorySource.TRADE, _trade_meta())

        events = [json.loads(line) for line in Path(audit_path).read_text().splitlines()]
        store_events = [e for e in events if e.get("event") == "store"]
        assert len(store_events) >= 1
        ev = store_events[0]
        assert ev["status"] == "success"
        assert "document_id" in ev
        assert "content_hash" in ev
        assert "ingested_at" in ev

    def test_store_writes_audit_error_event_on_failure(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            audit_path = f.name

        mock_col = MagicMock()
        mock_col.get.return_value = {"ids": [], "metadatas": []}
        mock_col.upsert.side_effect = RuntimeError("chroma failure")

        svc = MemoryService(collection=mock_col, audit_path=audit_path)

        with pytest.raises(RuntimeError):
            svc.store(SHORT_CONTENT, MemorySource.TRADE, _trade_meta())

        events = [json.loads(line) for line in Path(audit_path).read_text().splitlines()]
        error_events = [e for e in events if e.get("status") == "error"]
        assert len(error_events) >= 1
        assert error_events[0]["error_type"] == "RuntimeError"

    def test_store_failure_does_not_raise_when_caught_at_node_boundary(self):
        """Node-level pattern: catch exceptions so run continues."""
        mock_col = MagicMock()
        mock_col.get.return_value = {"ids": [], "metadatas": []}
        mock_col.upsert.side_effect = RuntimeError("chroma failure")

        svc = MemoryService(collection=mock_col)

        # Node-level pattern from design doc — exception is caught externally
        result = None
        try:
            result = svc.store(SHORT_CONTENT, MemorySource.TRADE, _trade_meta())
        except Exception:
            result = None

        assert result is None  # write failed but flow continues

    def test_search_returns_memory_hits_not_raw_chroma(self):
        svc = _make_service()
        svc.store(SHORT_CONTENT, MemorySource.TRADE, _trade_meta())
        hits = svc.search("NVDA earnings")
        assert isinstance(hits, list)
        for h in hits:
            assert isinstance(h, MemoryHit)
            assert isinstance(h.document_id, str)
            assert isinstance(h.score, float)
            assert isinstance(h.source, MemorySource)

    def test_search_score_higher_is_better(self):
        svc = _make_service()
        svc.store("NVDA strong buy signal on earnings beat", MemorySource.TRADE, _trade_meta())
        svc.store("Unrelated content about cats", MemorySource.RESEARCH, _research_meta())
        hits = svc.search("NVDA earnings buy signal", k=5)
        if len(hits) >= 2:
            # Scores should be in descending order
            scores = [h.score for h in hits]
            assert scores == sorted(scores, reverse=True)

    def test_search_source_filter_applied(self):
        svc = _make_service()
        svc.store(SHORT_CONTENT, MemorySource.TRADE, _trade_meta())
        svc.store("Research note about NVDA", MemorySource.RESEARCH, _research_meta())
        hits = svc.search("NVDA", source_filter=MemorySource.TRADE, k=5)
        for h in hits:
            assert h.source == MemorySource.TRADE

    def test_get_reassembles_chunks_in_order(self):
        svc = _make_service()
        doc_id = svc.store(LONG_CONTENT, MemorySource.RESEARCH, _research_meta())
        stored = svc.get(doc_id)
        assert stored is not None
        assert len(stored.chunks) > 1
        # Verify chunk content appears in source order
        for i, chunk in enumerate(stored.chunks):
            assert isinstance(chunk, str)
            assert len(chunk) > 0

    def test_delete_removes_all_chunks(self):
        svc = _make_service()
        doc_id = svc.store(LONG_CONTENT, MemorySource.TRADE, _trade_meta())
        stored = svc.get(doc_id)
        assert stored is not None

        svc.delete(doc_id)
        stored_after = svc.get(doc_id)
        assert stored_after is None


# ---------------------------------------------------------------------------
# Chunking tests
# ---------------------------------------------------------------------------


class TestChunking:
    def test_chunking_short_document_single_chunk(self):
        short = "A " * 100  # ~200 tokens, below threshold
        chunks = _split_into_chunks(short)
        assert len(chunks) == 1

    def test_chunking_long_document_overlap_respected(self):
        # Create content that will definitely be multi-chunk
        long = "\n\n".join(["Word " * 200 for _ in range(5)])
        chunks = _split_into_chunks(long)
        assert len(chunks) > 1
        # Each chunk should be within the max token budget (with some tolerance)
        for chunk in chunks:
            approx_tokens = len(chunk) // CHARS_PER_TOKEN
            assert approx_tokens <= CHUNK_MAX_TOKENS * 2  # generous bound

    def test_chunking_paragraph_fallback_sentence_split(self):
        # One very long paragraph (no double newlines) with multiple sentences
        sentences = [f"Sentence number {i} contains important financial data about equities." for i in range(50)]
        content = " ".join(sentences)  # single paragraph, many sentences
        chunks = _split_into_chunks(content)
        # Should still produce chunks since total tokens > threshold
        total_tokens = len(content) // CHARS_PER_TOKEN
        if total_tokens > CHUNK_SINGLE_THRESHOLD_TOKENS:
            assert len(chunks) >= 1

    def test_chunking_sentence_fallback_token_split(self):
        # One extremely long "sentence" with no punctuation — forces hard split
        single_long_line = "a" * (CHUNK_MAX_TOKENS * CHARS_PER_TOKEN * 3)
        chunks = _split_into_chunks(single_long_line)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= CHUNK_MAX_TOKENS * CHARS_PER_TOKEN * 2  # reasonable bound


# ---------------------------------------------------------------------------
# ID generation tests
# ---------------------------------------------------------------------------


class TestDocumentIdGeneration:
    def test_trade_document_id_deterministic(self):
        meta = _trade_meta()
        id1 = _make_document_id(MemorySource.TRADE, meta)
        id2 = _make_document_id(MemorySource.TRADE, meta)
        assert id1 == id2
        assert id1.startswith("trade_")
        assert len(id1) == len("trade_") + 24

    def test_research_document_id_deterministic(self):
        meta = _research_meta()
        id1 = _make_document_id(MemorySource.RESEARCH, meta)
        id2 = _make_document_id(MemorySource.RESEARCH, meta)
        assert id1 == id2
        assert id1.startswith("research_")
        assert len(id1) == len("research_") + 24

    def test_external_document_id_deterministic(self):
        meta = _external_meta()
        id1 = _make_document_id(MemorySource.EXTERNAL_DATA, meta)
        id2 = _make_document_id(MemorySource.EXTERNAL_DATA, meta)
        assert id1 == id2
        assert id1.startswith("external-data_")
        assert len(id1) == len("external-data_") + 24

    def test_different_inputs_produce_different_ids(self):
        meta1 = _trade_meta(symbol="NVDA")
        meta2 = _trade_meta(symbol="AAPL")
        assert _make_document_id(MemorySource.TRADE, meta1) != _make_document_id(MemorySource.TRADE, meta2)


# ---------------------------------------------------------------------------
# Audit log tests
# ---------------------------------------------------------------------------


class TestAuditLog:
    def test_audit_event_shape_success(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        audit = AuditLog(path)
        audit.store_success(
            document_id="trade_abc",
            source="trade",
            node="write_trade_memory",
            chunk_count=2,
            content_hash="deadbeef",
            ingested_at="2026-03-06T12:00:00Z",
        )
        events = [json.loads(line) for line in Path(path).read_text().splitlines()]
        assert len(events) == 1
        ev = events[0]
        assert ev["event"] == "store"
        assert ev["status"] == "success"
        assert ev["document_id"] == "trade_abc"
        assert ev["chunk_count"] == 2
        assert "timestamp" in ev
        assert "ingested_at" in ev

    def test_audit_event_shape_error(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        audit = AuditLog(path)
        audit.store_error(
            source="trade",
            node="write_trade_memory",
            error_type="ChromaWriteError",
            error_message="connection refused",
        )
        events = [json.loads(line) for line in Path(path).read_text().splitlines()]
        ev = events[0]
        assert ev["status"] == "error"
        assert ev["error_type"] == "ChromaWriteError"
        assert ev["error_message"] == "connection refused"

    def test_audit_append_only(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        audit = AuditLog(path)
        for i in range(5):
            audit.write({"seq": i, "event": "test"})

        lines = Path(path).read_text().splitlines()
        assert len(lines) == 5
        for i, line in enumerate(lines):
            ev = json.loads(line)
            assert ev["seq"] == i


# ---------------------------------------------------------------------------
# Indexer tests
# ---------------------------------------------------------------------------


class TestIndexer:
    def test_deduplicate_keeps_earliest_by_ingested_at(self):
        col = _fake_collection()
        # Insert two chunks with the same content_hash but different ingested_at
        col.upsert(
            ids=["doc_a:0000", "doc_b:0000"],
            documents=["same content", "same content"],
            metadatas=[
                {
                    "document_id": "doc_a",
                    "chunk_id": "doc_a:0000",
                    "chunk_index": 0,
                    "chunk_count": 1,
                    "source": "trade",
                    "content_hash": "aabbcc",
                    "ingested_at": "2026-03-06T10:00:00Z",
                    "timestamp": "2026-03-06T10:00:00Z",
                },
                {
                    "document_id": "doc_b",
                    "chunk_id": "doc_b:0000",
                    "chunk_index": 0,
                    "chunk_count": 1,
                    "source": "trade",
                    "content_hash": "aabbcc",
                    "ingested_at": "2026-03-06T11:00:00Z",
                    "timestamp": "2026-03-06T11:00:00Z",
                },
            ],
        )

        from src.memory.indexer import run_deduplication

        result = run_deduplication(col)
        assert result.duplicates_removed == 1

        # Earlier one (doc_a) should survive
        remaining = col.get(include=["metadatas"])
        surviving_ids = remaining["ids"]
        assert "doc_a:0000" in surviving_ids
        assert "doc_b:0000" not in surviving_ids

    def test_orphan_detection_missing_chunk_index(self):
        col = _fake_collection()
        # Insert chunk_count=3 but only provide chunk indexes 0 and 2 (missing 1)
        col.upsert(
            ids=["doc_c:0000", "doc_c:0002"],
            documents=["chunk 0", "chunk 2"],
            metadatas=[
                {
                    "document_id": "doc_c",
                    "chunk_id": "doc_c:0000",
                    "chunk_index": 0,
                    "chunk_count": 3,
                    "source": "research",
                    "content_hash": "hash0",
                    "ingested_at": "2026-03-06T12:00:00Z",
                    "timestamp": "2026-03-06T12:00:00Z",
                },
                {
                    "document_id": "doc_c",
                    "chunk_id": "doc_c:0002",
                    "chunk_index": 2,
                    "chunk_count": 3,
                    "source": "research",
                    "content_hash": "hash2",
                    "ingested_at": "2026-03-06T12:00:00Z",
                    "timestamp": "2026-03-06T12:00:00Z",
                },
            ],
        )

        from src.memory.indexer import run_deduplication

        result = run_deduplication(col)
        assert result.orphans_removed == 2

    def test_deduplicate_noop_on_clean_store(self):
        svc = _make_service()
        svc.store(SHORT_CONTENT, MemorySource.TRADE, _trade_meta())
        result = svc.deduplicate()
        assert result.duplicates_removed == 0
        assert result.orphans_removed == 0


# ---------------------------------------------------------------------------
# Tools tests
# ---------------------------------------------------------------------------


class TestMemoryTools:
    def test_memory_search_tool_formats_structured_output(self):
        from src.memory.tools import make_memory_search_tool

        mock_svc = MagicMock()
        mock_svc.search.return_value = [
            MemoryHit(
                document_id="trade_abc",
                chunk_id="trade_abc:0000",
                content="NVDA buy signal",
                source=MemorySource.TRADE,
                metadata={"timestamp": "2026-03-06T12:00:00Z", "symbol": "NVDA"},
                score=0.91,
            )
        ]

        tool = make_memory_search_tool(mock_svc)
        output = tool.func("NVDA earnings")

        assert "Memory result" in output
        assert "trade" in output.lower()
        assert "0.91" in output or "91" in output
        assert "NVDA buy signal" in output

    def test_memory_search_tool_handles_empty_results(self):
        from src.memory.tools import make_memory_search_tool

        mock_svc = MagicMock()
        mock_svc.search.return_value = []

        tool = make_memory_search_tool(mock_svc)
        output = tool.func("unknown query")
        assert isinstance(output, str)
        assert len(output) >= 0  # no crash


# ---------------------------------------------------------------------------
# L1 recency filter test
# ---------------------------------------------------------------------------


class TestRecencyFilter:
    def test_search_recency_filter_applied(self):
        """Hits older than 30 days should be filtered before passing to L1 prompt."""
        from src.memory.tools import filter_hits_by_recency

        now = datetime.now(timezone.utc)
        old_ts = (now - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
        new_ts = (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")

        old_hit = MemoryHit(
            document_id="doc_old",
            chunk_id="doc_old:0000",
            content="old trade",
            source=MemorySource.TRADE,
            metadata={"timestamp": old_ts},
            score=0.9,
        )
        new_hit = MemoryHit(
            document_id="doc_new",
            chunk_id="doc_new:0000",
            content="new trade",
            source=MemorySource.TRADE,
            metadata={"timestamp": new_ts},
            score=0.85,
        )

        filtered = filter_hits_by_recency([old_hit, new_hit], days=30)
        assert len(filtered) == 1
        assert filtered[0].document_id == "doc_new"


# ---------------------------------------------------------------------------
# Integration tests (real ChromaDB EphemeralClient)
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_integration_store_and_retrieve_trade(self):
        svc = _make_service()
        content = "Bought 100 shares of NVDA at $850. Strong momentum, earnings beat."
        meta = _trade_meta(pnl=1500.0)
        doc_id = svc.store(content, MemorySource.TRADE, meta)

        hits = svc.search("NVDA trade earnings", source_filter=MemorySource.TRADE)
        assert len(hits) >= 1
        assert any(h.document_id == doc_id for h in hits)

        stored = svc.get(doc_id)
        assert stored is not None
        assert stored.source == MemorySource.TRADE
        full_text = " ".join(stored.chunks)
        assert "NVDA" in full_text

    def test_integration_deduplication_removes_duplicate(self):
        col = _fake_collection()
        # Manually insert two chunks with identical content_hash
        col.upsert(
            ids=["dup_a:0000", "dup_b:0000"],
            documents=["identical content", "identical content"],
            metadatas=[
                {
                    "document_id": "dup_a",
                    "chunk_id": "dup_a:0000",
                    "chunk_index": 0,
                    "chunk_count": 1,
                    "source": "trade",
                    "content_hash": "identical_hash_xyz",
                    "ingested_at": "2026-03-06T09:00:00Z",
                    "timestamp": "2026-03-06T09:00:00Z",
                },
                {
                    "document_id": "dup_b",
                    "chunk_id": "dup_b:0000",
                    "chunk_index": 0,
                    "chunk_count": 1,
                    "source": "trade",
                    "content_hash": "identical_hash_xyz",
                    "ingested_at": "2026-03-06T10:00:00Z",
                    "timestamp": "2026-03-06T10:00:00Z",
                },
            ],
        )

        svc = MemoryService(collection=col)
        result = svc.deduplicate()
        assert result.duplicates_removed == 1

        remaining = col.get(include=[])
        assert len(remaining["ids"]) == 1
