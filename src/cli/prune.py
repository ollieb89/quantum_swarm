"""
src.cli.prune -- Prune subcommand: archive old ChromaDB vectors to
Obsidian-compatible Markdown files, then delete from the database.

Exported functions:
    register_prune_parser -- Wire prune subcommand into argparse
    handle_prune          -- Top-level prune dispatch
"""

from __future__ import annotations

import logging
import os
import tempfile
from argparse import Namespace, _SubParsersAction
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import yaml
from rich.console import Console
from rich.table import Table

from src.core.memory_registry import MemoryRegistry
from src.memory.service import MemoryService, MemorySource, StoredDocument

logger = logging.getLogger(__name__)

# Default archive output directory (inside Obsidian vault)
ARCHIVE_BASE = Path("quantum-swarm/Archives/memory")

# Chunk metadata keys excluded from YAML frontmatter
_EXCLUDED_META = frozenset({"chunk_id", "chunk_index", "chunk_count"})


# ---------------------------------------------------------------------------
# Parser registration
# ---------------------------------------------------------------------------


def register_prune_parser(sub: _SubParsersAction) -> None:
    """Add the 'prune' subcommand to *sub*."""
    prune_parser = sub.add_parser(
        "prune", help="Archive and prune old ChromaDB vectors"
    )
    prune_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show plan without modifying data",
    )
    prune_parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Age threshold in days (default: 90)",
    )
    prune_parser.add_argument(
        "--no-archive",
        action="store_true",
        default=False,
        help="Delete without archiving (requires explicit opt-in)",
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_timestamp(ts: str) -> datetime:
    """Parse an ISO 8601 timestamp string to a timezone-aware datetime."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _render_archive_markdown(doc: StoredDocument) -> str:
    """Render a StoredDocument as Obsidian-compatible Markdown with YAML frontmatter."""
    meta = dict(doc.metadata)

    # Build frontmatter with required fields first, then extras
    frontmatter: dict = {
        "document_id": doc.document_id,
        "source": doc.source.value,
        "timestamp": meta.get("timestamp", ""),
        "ingested_at": meta.get("ingested_at", ""),
        "content_hash": meta.get("content_hash", ""),
    }

    # Add all remaining original metadata (excluding chunk-level keys and
    # keys already in frontmatter)
    for k, v in meta.items():
        if k not in frontmatter and k not in _EXCLUDED_META:
            frontmatter[k] = v

    body = "\n\n".join(doc.chunks)
    fm_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    return f"---\n{fm_str}---\n\n{body}\n"


def _compute_protection_cutoff(registry: MemoryRegistry) -> Optional[datetime]:
    """Return the oldest active rule's created_at, or None if no active rules."""
    active_rules = registry.get_active_rules()
    if not active_rules:
        return None
    return min(r.created_at for r in active_rules)


def _classify_documents(
    docs: list[StoredDocument],
    threshold_dt: datetime,
    cutoff_dt: Optional[datetime],
) -> list[tuple[StoredDocument, str]]:
    """Classify each document as 'archive', 'protected', or 'skip'.

    - Documents newer than threshold_dt -> 'skip' (too recent)
    - Documents older than threshold but newer than cutoff_dt -> 'protected'
    - Documents older than threshold and older than cutoff_dt (or no cutoff) -> 'archive'
    """
    result: list[tuple[StoredDocument, str]] = []
    for doc in docs:
        ts_str = doc.metadata.get("timestamp", "")
        try:
            doc_ts = _parse_timestamp(ts_str)
        except (ValueError, TypeError):
            # Unparseable timestamp -- skip to be safe
            result.append((doc, "skip"))
            continue

        if doc_ts >= threshold_dt:
            result.append((doc, "skip"))
        elif cutoff_dt is not None and doc_ts >= cutoff_dt:
            result.append((doc, "protected"))
        else:
            result.append((doc, "archive"))

    return result


# ---------------------------------------------------------------------------
# Top-level dispatch
# ---------------------------------------------------------------------------


def handle_prune(args: Namespace) -> int:
    """Execute the prune operation. Returns exit code."""
    try:
        svc = MemoryService()
        if not svc.health_check():
            logger.warning("chromadb_unavailable: ChromaDB unreachable, cannot prune")
            return 1
    except Exception as exc:
        logger.warning("chromadb_init_failed: %s", exc)
        return 1

    registry = MemoryRegistry()

    now = datetime.now(timezone.utc)
    threshold_dt = now - timedelta(days=args.days)
    cutoff_dt = _compute_protection_cutoff(registry)

    all_docs = svc.list_documents()
    classified = _classify_documents(all_docs, threshold_dt, cutoff_dt)

    # Counters
    archived = 0
    deleted = 0
    protected = 0
    skipped = 0

    if args.dry_run:
        con = Console()
        table = Table(title="Prune Plan (dry run)")
        table.add_column("Document ID", style="cyan")
        table.add_column("Source", style="bold")
        table.add_column("Timestamp")
        table.add_column("Chunks", justify="right")
        table.add_column("Action")

        for doc, action in classified:
            table.add_row(
                doc.document_id,
                doc.source.value,
                doc.metadata.get("timestamp", ""),
                str(len(doc.chunks)),
                action,
            )
            if action == "archive":
                archived += 1
            elif action == "protected":
                protected += 1
            else:
                skipped += 1

        con.print(table)
        con.print(
            f"\nWould archive {archived} documents, "
            f"skip {skipped} (too recent), "
            f"{protected} (rule-protected)"
        )
        return 0

    # Real prune
    for doc, action in classified:
        if action == "skip":
            skipped += 1
            continue
        if action == "protected":
            protected += 1
            continue

        # action == "archive"
        if not args.no_archive:
            archive_path = ARCHIVE_BASE / doc.source.value / f"{doc.document_id}.md"
            if archive_path.exists():
                logger.info(
                    "document_already_archived: %s at %s",
                    doc.document_id,
                    archive_path,
                )
            else:
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                content = _render_archive_markdown(doc)
                # Atomic write: tmp + os.replace
                fd, tmp_path = tempfile.mkstemp(
                    dir=str(archive_path.parent), suffix=".tmp"
                )
                try:
                    with os.fdopen(fd, "w") as f:
                        f.write(content)
                    os.replace(tmp_path, archive_path)
                except Exception:
                    # Clean up tmp on failure
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass
                    raise

            archived += 1

        svc.delete(doc.document_id, node="prune")
        deleted += 1

        logger.info(
            "document_archived",
            extra={
                "document_id": doc.document_id,
                "source": doc.source.value,
                "chunk_count": len(doc.chunks),
            },
        )

    logger.info(
        "prune_complete",
        extra={
            "archived": archived,
            "deleted": deleted,
            "protected": protected,
            "skipped": skipped,
        },
    )

    return 0
