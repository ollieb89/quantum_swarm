"""
Tests for src.cli.prune — prune subcommand: archive rendering, rule-aware
filtering, archive+delete orchestration, and MemoryService.list_documents().
"""

from __future__ import annotations

import os
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.memory.service import MemoryService, MemorySource, StoredDocument


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_collection(entries: list[dict]) -> MagicMock:
    """Build a mock ChromaDB collection from a list of chunk dicts.

    Each entry: {id, document, metadata}
    """
    col = MagicMock()
    col.count.return_value = len(entries)

    def _get_side_effect(**kwargs):
        include = kwargs.get("include", [])
        where = kwargs.get("where")
        ids_filter = kwargs.get("ids")

        filtered = entries
        if where:
            filtered = [
                e for e in filtered
                if all(e["metadata"].get(k) == v for k, v in where.items())
            ]
        if ids_filter:
            id_set = set(ids_filter)
            filtered = [e for e in filtered if e["id"] in id_set]

        result = {"ids": [e["id"] for e in filtered]}
        if "documents" in include:
            result["documents"] = [e["document"] for e in filtered]
        if "metadatas" in include:
            result["metadatas"] = [e["metadata"] for e in filtered]
        return result

    col.get.side_effect = _get_side_effect

    deleted_ids: list[str] = []

    def _delete_side_effect(ids):
        deleted_ids.extend(ids)
        # Remove entries from the mock so subsequent calls reflect deletion
        nonlocal entries
        id_set = set(ids)
        entries = [e for e in entries if e["id"] not in id_set]

    col.delete.side_effect = _delete_side_effect
    col._deleted_ids = deleted_ids
    return col


def _chunk_entry(doc_id: str, chunk_index: int, text: str, source: str,
                 timestamp: str, **extra_meta) -> dict:
    chunk_count = extra_meta.pop("chunk_count", 1)
    meta = {
        "document_id": doc_id,
        "source": source,
        "timestamp": timestamp,
        "ingested_at": timestamp,
        "content_hash": "abc123",
        "chunk_id": f"{doc_id}:{chunk_index:04d}",
        "chunk_index": chunk_index,
        "chunk_count": chunk_count,
        **extra_meta,
    }
    return {"id": f"{doc_id}:{chunk_index:04d}", "document": text, "metadata": meta}


# ---------------------------------------------------------------------------
# MemoryService.list_documents() tests
# ---------------------------------------------------------------------------


class TestListDocuments:
    def test_empty_collection_returns_empty(self):
        col = _make_collection([])
        svc = MemoryService(collection=col)
        assert svc.list_documents() == []

    def test_groups_chunks_by_document_id(self):
        entries = [
            _chunk_entry("doc1", 0, "chunk0", "trade", "2026-01-01T00:00:00Z", chunk_count=2),
            _chunk_entry("doc1", 1, "chunk1", "trade", "2026-01-01T00:00:00Z", chunk_count=2),
            _chunk_entry("doc2", 0, "only chunk", "research", "2026-01-02T00:00:00Z"),
        ]
        col = _make_collection(entries)
        svc = MemoryService(collection=col)
        docs = svc.list_documents()

        assert len(docs) == 2
        doc_ids = {d.document_id for d in docs}
        assert doc_ids == {"doc1", "doc2"}

    def test_sorts_chunks_by_index(self):
        entries = [
            _chunk_entry("doc1", 2, "third", "trade", "2026-01-01T00:00:00Z", chunk_count=3),
            _chunk_entry("doc1", 0, "first", "trade", "2026-01-01T00:00:00Z", chunk_count=3),
            _chunk_entry("doc1", 1, "second", "trade", "2026-01-01T00:00:00Z", chunk_count=3),
        ]
        col = _make_collection(entries)
        svc = MemoryService(collection=col)
        docs = svc.list_documents()

        assert len(docs) == 1
        assert docs[0].chunks == ["first", "second", "third"]


# ---------------------------------------------------------------------------
# _render_archive_markdown tests
# ---------------------------------------------------------------------------


class TestRenderArchiveMarkdown:
    def test_produces_yaml_frontmatter(self):
        from src.cli.prune import _render_archive_markdown

        doc = StoredDocument(
            document_id="trade_abc123",
            chunks=["Hello world"],
            source=MemorySource.TRADE,
            metadata={
                "document_id": "trade_abc123",
                "source": "trade",
                "timestamp": "2026-01-01T00:00:00Z",
                "ingested_at": "2026-01-01T00:00:00Z",
                "content_hash": "deadbeef",
                "chunk_id": "trade_abc123:0000",
                "chunk_index": 0,
                "chunk_count": 1,
                "symbol": "BTCUSD",
            },
        )
        md = _render_archive_markdown(doc)

        # Valid frontmatter delimiters
        assert md.startswith("---\n")
        parts = md.split("---\n")
        assert len(parts) >= 3  # before ---, frontmatter, after ---

        # Required fields in frontmatter
        assert "document_id: trade_abc123" in md
        assert "source: trade" in md
        assert "timestamp:" in md
        assert "content_hash:" in md

        # Excluded chunk metadata
        assert "chunk_id:" not in md
        assert "chunk_index:" not in md
        assert "chunk_count:" not in md

        # Extra metadata preserved
        assert "symbol: BTCUSD" in md

        # Body content
        assert "Hello world" in md

    def test_reassembles_chunks(self):
        from src.cli.prune import _render_archive_markdown

        doc = StoredDocument(
            document_id="doc1",
            chunks=["Part one", "Part two", "Part three"],
            source=MemorySource.RESEARCH,
            metadata={
                "document_id": "doc1",
                "source": "research",
                "timestamp": "2026-01-01T00:00:00Z",
                "ingested_at": "2026-01-01T00:00:00Z",
                "content_hash": "abc",
                "chunk_id": "doc1:0000",
                "chunk_index": 0,
                "chunk_count": 3,
            },
        )
        md = _render_archive_markdown(doc)
        assert "Part one\n\nPart two\n\nPart three" in md


# ---------------------------------------------------------------------------
# _compute_protection_cutoff tests
# ---------------------------------------------------------------------------


class TestComputeProtectionCutoff:
    def test_no_active_rules_returns_none(self):
        from src.cli.prune import _compute_protection_cutoff

        registry = MagicMock()
        registry.get_active_rules.return_value = []
        assert _compute_protection_cutoff(registry) is None

    def test_returns_oldest_rule_created_at(self):
        from src.cli.prune import _compute_protection_cutoff
        from src.models.memory import MemoryRule

        old_dt = datetime(2025, 6, 1, tzinfo=timezone.utc)
        new_dt = datetime(2026, 1, 1, tzinfo=timezone.utc)

        r1 = MagicMock(spec=MemoryRule)
        r1.created_at = old_dt
        r2 = MagicMock(spec=MemoryRule)
        r2.created_at = new_dt

        registry = MagicMock()
        registry.get_active_rules.return_value = [r2, r1]

        cutoff = _compute_protection_cutoff(registry)
        assert cutoff == old_dt


# ---------------------------------------------------------------------------
# _classify_documents tests
# ---------------------------------------------------------------------------


class TestClassifyDocuments:
    def _make_doc(self, doc_id: str, timestamp_str: str, source: str = "trade") -> StoredDocument:
        return StoredDocument(
            document_id=doc_id,
            chunks=["content"],
            source=MemorySource(source),
            metadata={"timestamp": timestamp_str, "document_id": doc_id, "source": source},
        )

    def test_old_doc_no_rules_marked_archive(self):
        from src.cli.prune import _classify_documents

        now = datetime.now(timezone.utc)
        old_ts = _utc_iso(now - timedelta(days=120))
        doc = self._make_doc("old_doc", old_ts)

        threshold = now - timedelta(days=90)
        result = _classify_documents([doc], threshold, None)
        assert len(result) == 1
        assert result[0][1] == "archive"

    def test_recent_doc_marked_skip(self):
        from src.cli.prune import _classify_documents

        now = datetime.now(timezone.utc)
        recent_ts = _utc_iso(now - timedelta(days=10))
        doc = self._make_doc("new_doc", recent_ts)

        threshold = now - timedelta(days=90)
        result = _classify_documents([doc], threshold, None)
        assert result[0][1] == "skip"

    def test_old_doc_within_rule_window_marked_protected(self):
        from src.cli.prune import _classify_documents

        now = datetime.now(timezone.utc)
        # Doc is old enough to prune (120 days) but within rule window
        old_ts = _utc_iso(now - timedelta(days=120))
        doc = self._make_doc("protected_doc", old_ts)

        threshold = now - timedelta(days=90)
        # Protection cutoff is 200 days ago -- doc is newer than cutoff
        cutoff = now - timedelta(days=200)
        result = _classify_documents([doc], threshold, cutoff)
        assert result[0][1] == "protected"

    def test_very_old_doc_beyond_rule_window_marked_archive(self):
        from src.cli.prune import _classify_documents

        now = datetime.now(timezone.utc)
        very_old_ts = _utc_iso(now - timedelta(days=300))
        doc = self._make_doc("ancient_doc", very_old_ts)

        threshold = now - timedelta(days=90)
        cutoff = now - timedelta(days=200)
        result = _classify_documents([doc], threshold, cutoff)
        assert result[0][1] == "archive"


# ---------------------------------------------------------------------------
# handle_prune integration tests
# ---------------------------------------------------------------------------


class TestHandlePrune:
    def _setup(self, tmp_path: Path, entries: list[dict], active_rules=None):
        col = _make_collection(entries)
        svc = MagicMock(spec=MemoryService)
        svc.health_check.return_value = True

        # Build StoredDocument list from entries
        from collections import defaultdict
        groups: dict[str, list] = defaultdict(list)
        for e in entries:
            m = e["metadata"]
            groups[m["document_id"]].append((m.get("chunk_index", 0), e["document"], m))

        docs = []
        for doc_id, chunks in groups.items():
            chunks.sort(key=lambda t: t[0])
            first_meta = chunks[0][2]
            try:
                source = MemorySource(first_meta.get("source", ""))
            except ValueError:
                source = MemorySource.EXTERNAL_DATA
            docs.append(StoredDocument(
                document_id=doc_id,
                chunks=[t for _, t, _ in chunks],
                source=source,
                metadata=first_meta,
            ))

        svc.list_documents.return_value = docs

        registry = MagicMock()
        registry.get_active_rules.return_value = active_rules or []

        return svc, registry

    def test_dry_run_no_side_effects(self, tmp_path):
        from src.cli.prune import handle_prune

        now = datetime.now(timezone.utc)
        old_ts = _utc_iso(now - timedelta(days=120))
        entries = [_chunk_entry("doc1", 0, "content", "trade", old_ts)]
        svc, registry = self._setup(tmp_path, entries)

        args = Namespace(dry_run=True, days=90, no_archive=False)
        archive_dir = tmp_path / "archives"

        with patch("src.cli.prune.MemoryService", return_value=svc), \
             patch("src.cli.prune.MemoryRegistry", return_value=registry), \
             patch("src.cli.prune.ARCHIVE_BASE", archive_dir):
            code = handle_prune(args)

        assert code == 0
        svc.delete.assert_not_called()
        assert not any(archive_dir.rglob("*.md"))

    def test_archive_writes_file_and_deletes(self, tmp_path):
        from src.cli.prune import handle_prune

        now = datetime.now(timezone.utc)
        old_ts = _utc_iso(now - timedelta(days=120))
        entries = [_chunk_entry("doc1", 0, "archived content", "trade", old_ts)]
        svc, registry = self._setup(tmp_path, entries)

        args = Namespace(dry_run=False, days=90, no_archive=False)
        archive_dir = tmp_path / "archives"

        with patch("src.cli.prune.MemoryService", return_value=svc), \
             patch("src.cli.prune.MemoryRegistry", return_value=registry), \
             patch("src.cli.prune.ARCHIVE_BASE", archive_dir):
            code = handle_prune(args)

        assert code == 0
        # Archive file created
        md_files = list(archive_dir.rglob("*.md"))
        assert len(md_files) == 1
        assert "doc1.md" in md_files[0].name
        content = md_files[0].read_text()
        assert "archived content" in content
        assert content.startswith("---\n")

        # ChromaDB delete called
        svc.delete.assert_called_once_with("doc1", node="prune")

    def test_idempotent_skip_existing_archive(self, tmp_path):
        from src.cli.prune import handle_prune

        now = datetime.now(timezone.utc)
        old_ts = _utc_iso(now - timedelta(days=120))
        entries = [_chunk_entry("doc1", 0, "content", "trade", old_ts)]
        svc, registry = self._setup(tmp_path, entries)

        archive_dir = tmp_path / "archives"
        # Pre-create the archive file
        trade_dir = archive_dir / "trade"
        trade_dir.mkdir(parents=True)
        (trade_dir / "doc1.md").write_text("already archived")

        args = Namespace(dry_run=False, days=90, no_archive=False)

        with patch("src.cli.prune.MemoryService", return_value=svc), \
             patch("src.cli.prune.MemoryRegistry", return_value=registry), \
             patch("src.cli.prune.ARCHIVE_BASE", archive_dir):
            code = handle_prune(args)

        assert code == 0
        # File not overwritten
        assert (trade_dir / "doc1.md").read_text() == "already archived"
        # But still deleted from ChromaDB
        svc.delete.assert_called_once_with("doc1", node="prune")

    def test_no_archive_flag_deletes_without_writing(self, tmp_path):
        from src.cli.prune import handle_prune

        now = datetime.now(timezone.utc)
        old_ts = _utc_iso(now - timedelta(days=120))
        entries = [_chunk_entry("doc1", 0, "content", "trade", old_ts)]
        svc, registry = self._setup(tmp_path, entries)

        args = Namespace(dry_run=False, days=90, no_archive=True)
        archive_dir = tmp_path / "archives"

        with patch("src.cli.prune.MemoryService", return_value=svc), \
             patch("src.cli.prune.MemoryRegistry", return_value=registry), \
             patch("src.cli.prune.ARCHIVE_BASE", archive_dir):
            code = handle_prune(args)

        assert code == 0
        assert not any(archive_dir.rglob("*.md"))
        svc.delete.assert_called_once()

    def test_chromadb_unreachable_returns_1(self, tmp_path):
        from src.cli.prune import handle_prune

        svc = MagicMock(spec=MemoryService)
        svc.health_check.return_value = False

        registry = MagicMock()
        args = Namespace(dry_run=False, days=90, no_archive=False)

        with patch("src.cli.prune.MemoryService", return_value=svc), \
             patch("src.cli.prune.MemoryRegistry", return_value=registry):
            code = handle_prune(args)

        assert code == 1

    def test_protected_documents_not_deleted(self, tmp_path):
        from src.cli.prune import handle_prune
        from src.models.memory import MemoryRule

        now = datetime.now(timezone.utc)
        # Doc is 120 days old -- old enough to prune
        old_ts = _utc_iso(now - timedelta(days=120))
        entries = [_chunk_entry("doc1", 0, "content", "trade", old_ts)]

        # Active rule created 200 days ago -- doc is newer, so protected
        rule = MagicMock(spec=MemoryRule)
        rule.created_at = now - timedelta(days=200)

        svc, registry = self._setup(tmp_path, entries, active_rules=[rule])

        args = Namespace(dry_run=False, days=90, no_archive=False)
        archive_dir = tmp_path / "archives"

        with patch("src.cli.prune.MemoryService", return_value=svc), \
             patch("src.cli.prune.MemoryRegistry", return_value=registry), \
             patch("src.cli.prune.ARCHIVE_BASE", archive_dir):
            code = handle_prune(args)

        assert code == 0
        svc.delete.assert_not_called()
        assert not any(archive_dir.rglob("*.md"))

    def test_structlog_events(self, tmp_path):
        from src.cli.prune import handle_prune

        now = datetime.now(timezone.utc)
        old_ts = _utc_iso(now - timedelta(days=120))
        entries = [_chunk_entry("doc1", 0, "content", "trade", old_ts)]
        svc, registry = self._setup(tmp_path, entries)

        args = Namespace(dry_run=False, days=90, no_archive=False)
        archive_dir = tmp_path / "archives"

        with patch("src.cli.prune.MemoryService", return_value=svc), \
             patch("src.cli.prune.MemoryRegistry", return_value=registry), \
             patch("src.cli.prune.ARCHIVE_BASE", archive_dir), \
             patch("src.cli.prune.logger") as mock_logger:
            code = handle_prune(args)

        assert code == 0
        # Check document_archived event
        archive_calls = [c for c in mock_logger.info.call_args_list
                         if c[0][0] == "document_archived"]
        assert len(archive_calls) == 1

        # Check prune_complete summary
        complete_calls = [c for c in mock_logger.info.call_args_list
                          if c[0][0] == "prune_complete"]
        assert len(complete_calls) == 1
