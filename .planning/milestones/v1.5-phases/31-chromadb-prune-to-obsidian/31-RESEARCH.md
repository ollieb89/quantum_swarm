# Phase 31: ChromaDB Prune-to-Obsidian - Research

**Researched:** 2026-03-10
**Domain:** ChromaDB bulk operations, Obsidian Markdown archival, CLI subcommand design
**Confidence:** HIGH

## Summary

This phase adds a `prune` CLI subcommand that archives old ChromaDB vectors to Obsidian-compatible Markdown files and then deletes them from the database. The technical domain is well-understood: all building blocks already exist in the codebase. The `MemoryService` provides the sole ChromaDB interface (bulk `.get()` with metadata, per-document `.delete()`), `MemoryRegistry` provides `get_active_rules()` for rule-aware protection, and the replay CLI establishes the exact pattern for argparse subcommand registration with Rich table output.

The primary complexity is the archive-then-delete ordering (crash safety via idempotent filenames) and the conservative rule-aware cutoff logic. ChromaDB's `collection.get()` without filters returns all entries -- this is the established pattern in `indexer.py` for bulk enumeration. No new dependencies are required.

**Primary recommendation:** Build a `src/cli/prune.py` module following the exact `src/cli/replay.py` pattern. Add a `list_documents()` method to `MemoryService` that groups chunks into logical documents with metadata. Use `MemoryRegistry.get_active_rules()` for the protection check with the conservative timestamp-based cutoff described in CONTEXT.md.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Archive file structure: one Markdown file per logical document (grouped by document_id), chunks reassembled into full document content in Markdown body
- Output directory: `quantum-swarm/Archives/memory/` with subdirectories by source type: `trade/`, `research/`, `external_data/`
- Filename: `{document_id}.md`
- YAML frontmatter includes: document_id, source, timestamp, ingested_at, content_hash, all original metadata fields
- Default age threshold: 90 days configurable via `--days N`, measured against `timestamp` metadata field
- Rule-aware safety: conservative protection -- if document timestamp newer than oldest active rule's `created_at`, it is protected
- CLI: `python -m src.main prune` with `--dry-run`, `--days N`, `--no-archive` flags
- Dry-run output: Rich table with document_id, source, timestamp, chunk_count, action columns; summary line
- Prune flow: query all -> filter by age -> cross-reference rules -> if not dry-run: write Markdown then delete from ChromaDB
- Archive-then-delete ordering for crash safety (idempotent filenames handle duplicates on re-run)
- Idempotent: skip archiving if .md file already exists
- Graceful degradation: if ChromaDB unreachable, log warning and exit cleanly

### Claude's Discretion
- Exact YAML frontmatter field ordering
- Rich table styling details
- Whether to batch ChromaDB deletes or delete one-by-one
- Internal helper function decomposition

### Deferred Ideas (OUT OF SCOPE)
- Scheduled automatic pruning via systemd timer
- Obsidian search index / tag generation for archived memories
- Reverse operation (re-import from Obsidian to ChromaDB)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OBS-03 | CLI `prune` command archives ChromaDB entries older than configurable threshold to Obsidian-compatible Markdown files | `register_replay_parser` pattern for CLI; `MemoryService.get()` + `collection.get(include=["metadatas", "documents"])` for bulk fetch; YAML frontmatter + Markdown body generation |
| OBS-06 | Prune operation respects active MemoryRegistry rules -- never deletes vectors backing active rules | `MemoryRegistry.get_active_rules()` exists and returns `List[MemoryRule]` with `created_at` field for conservative cutoff |
| OBS-07 | Prune operation logs archived/deleted counts via structlog | `structlog` via `logging.getLogger(__name__)` + ProcessorFormatter pattern from `logging_config.py` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| chromadb | (installed) | Vector store being pruned | Already sole persistence backend via MemoryService |
| rich | (installed) | Terminal table output for dry-run | Already used in replay CLI |
| structlog | (installed) | Structured logging for prune events | Project-wide logging standard since Phase 25 |
| pyyaml | (installed) | YAML frontmatter generation | Standard for Obsidian-compatible frontmatter |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | stdlib | File path operations for archive directory | Creating archive dirs, checking file existence |
| datetime | stdlib | Timestamp parsing and age threshold calculation | Filtering documents by age |

### Alternatives Considered
None -- all decisions locked, no new dependencies needed.

**Installation:**
No new packages required. All dependencies already installed.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── cli/
│   ├── replay.py          # Existing -- template for prune.py
│   └── prune.py           # NEW -- prune subcommand handlers
├── memory/
│   └── service.py         # MODIFY -- add list_documents() method
├── core/
│   └── memory_registry.py # EXISTING -- get_active_rules() already present
└── main.py                # MODIFY -- register prune parser + dispatch
```

### Pattern 1: CLI Subcommand Registration
**What:** Follow the exact `register_replay_parser` / `handle_replay` pattern from `src/cli/replay.py`
**When to use:** Always -- this is the established CLI pattern
**Example:**
```python
# src/cli/prune.py
from argparse import Namespace, _SubParsersAction

def register_prune_parser(sub: _SubParsersAction) -> None:
    prune_parser = sub.add_parser("prune", help="Archive and prune old ChromaDB vectors")
    prune_parser.add_argument("--dry-run", action="store_true", help="Show plan without modifying data")
    prune_parser.add_argument("--days", type=int, default=90, help="Age threshold in days (default: 90)")
    prune_parser.add_argument("--no-archive", action="store_true", help="Delete without archiving")

def handle_prune(args: Namespace) -> int:
    """Top-level prune dispatch. Returns exit code."""
    ...
```

### Pattern 2: Bulk Document Enumeration via MemoryService
**What:** Add a `list_documents()` method to MemoryService that returns all logical documents with metadata, following the existing `indexer.py` bulk-fetch pattern
**When to use:** For the prune command's initial scan of all documents
**Example:**
```python
# New method on MemoryService
def list_documents(self) -> list[StoredDocument]:
    """Return all logical documents with chunks reassembled."""
    result = self._collection.get(include=["documents", "metadatas"])
    ids = result.get("ids") or []
    docs = result.get("documents") or []
    metas = result.get("metadatas") or []

    # Group by document_id, sort chunks by chunk_index
    doc_groups: dict[str, list[tuple]] = defaultdict(list)
    for chunk_id, doc_text, meta in zip(ids, docs, metas):
        if meta is None:
            continue
        doc_id = meta.get("document_id", chunk_id)
        doc_groups[doc_id].append((meta.get("chunk_index", 0), doc_text, meta))

    documents = []
    for doc_id, entries in doc_groups.items():
        entries.sort(key=lambda t: t[0])
        chunks = [text for _, text, _ in entries]
        first_meta = entries[0][2]
        source_val = first_meta.get("source", "")
        try:
            source_enum = MemorySource(source_val)
        except ValueError:
            source_enum = MemorySource.EXTERNAL_DATA
        documents.append(StoredDocument(
            document_id=doc_id, chunks=chunks,
            source=source_enum, metadata=first_meta,
        ))
    return documents
```

### Pattern 3: Obsidian-Compatible Markdown with YAML Frontmatter
**What:** Write archive files as valid Obsidian notes with `---` delimited YAML frontmatter
**When to use:** For each archived document
**Example:**
```python
import yaml

def _render_archive_markdown(doc: StoredDocument) -> str:
    meta = dict(doc.metadata)
    frontmatter = {
        "document_id": doc.document_id,
        "source": doc.source.value,
        "timestamp": meta.get("timestamp", ""),
        "ingested_at": meta.get("ingested_at", ""),
        "content_hash": meta.get("content_hash", ""),
    }
    # Add all remaining original metadata
    for k, v in meta.items():
        if k not in frontmatter and k not in ("chunk_id", "chunk_index", "chunk_count"):
            frontmatter[k] = v

    body = "\n\n".join(doc.chunks)
    return f"---\n{yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)}---\n\n{body}\n"
```

### Pattern 4: Conservative Rule-Aware Cutoff
**What:** Load active rules, find oldest `created_at`, protect any document with timestamp newer than that
**When to use:** Always before pruning -- the safety check
**Example:**
```python
from src.core.memory_registry import MemoryRegistry

def _compute_protection_cutoff(registry: MemoryRegistry) -> datetime | None:
    active_rules = registry.get_active_rules()
    if not active_rules:
        return None  # No protection needed
    oldest = min(r.created_at for r in active_rules)
    return oldest
```

### Anti-Patterns to Avoid
- **Direct chromadb import in prune.py:** Always go through MemoryService -- it is the sole ChromaDB interface per project convention
- **Deleting before archiving:** Archive-then-delete ordering is mandatory for crash safety
- **Non-idempotent filenames:** Using timestamps or UUIDs in filenames would create duplicates on re-run; use `{document_id}.md` which is deterministic

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML serialization | String concatenation for frontmatter | `yaml.dump()` with `default_flow_style=False` | Handles escaping, multi-line strings, special characters |
| Rich table output | Manual string formatting | `rich.table.Table` + `rich.console.Console` | Consistent with replay CLI, handles terminal width |
| Atomic file writes | Direct `open().write()` | Write to tmp + `os.replace()` pattern | Already used in MemoryRegistry; prevents partial writes on crash |
| Document grouping | Custom iteration logic | Extend MemoryService with `list_documents()` | Centralizes chunk-to-document reassembly logic |

**Key insight:** The codebase already has every building block. The prune module is primarily orchestration of existing capabilities.

## Common Pitfalls

### Pitfall 1: ChromaDB `.get()` Returns All Chunks, Not Documents
**What goes wrong:** ChromaDB stores chunks, not logical documents. A naive `.get()` returns individual chunks that must be grouped by `document_id`.
**Why it happens:** ChromaDB has no concept of "logical document" -- all entries are flat vectors with metadata.
**How to avoid:** Group by `document_id` metadata field before processing. The `indexer.py` already demonstrates this pattern.
**Warning signs:** Archive files containing single chunks instead of reassembled documents.

### Pitfall 2: Timestamp Parsing Inconsistency
**What goes wrong:** The `timestamp` metadata field may be in different ISO 8601 formats (with/without Z suffix, with/without timezone).
**Why it happens:** Different data sources may store timestamps differently; `_now_utc()` uses `%Y-%m-%dT%H:%M:%SZ` format.
**How to avoid:** Use `datetime.fromisoformat(ts.replace("Z", "+00:00"))` -- this is the existing pattern in `src/memory/tools.py` line 106.
**Warning signs:** `ValueError` on timestamp parsing, documents not being pruned when they should be.

### Pitfall 3: MemoryRule `created_at` is a datetime object, not a string
**What goes wrong:** Comparing `created_at` (datetime) with parsed timestamp string requires type-aware comparison.
**Why it happens:** `MemoryRule` uses Pydantic `datetime` field with `default_factory=lambda: datetime.now(timezone.utc)`.
**How to avoid:** Parse document timestamps to timezone-aware datetime before comparison. Ensure both sides are UTC.
**Warning signs:** TypeError on comparison, or all documents being protected/unprotected.

### Pitfall 4: Empty ChromaDB Collection
**What goes wrong:** `collection.get()` on empty collection returns empty lists, not None.
**Why it happens:** ChromaDB returns `{"ids": [], "documents": [], "metadatas": []}` for empty collections.
**How to avoid:** Check `if not ids` early and return empty results gracefully. Already handled in indexer.py.
**Warning signs:** IndexError or empty iteration with no output.

### Pitfall 5: Archive Directory Not Created
**What goes wrong:** Writing to `quantum-swarm/Archives/memory/trade/` fails because directory tree doesn't exist.
**Why it happens:** The `Archives/` directory and subdirectories are new.
**How to avoid:** Use `Path.mkdir(parents=True, exist_ok=True)` before writing files.
**Warning signs:** FileNotFoundError on first prune run.

## Code Examples

### CLI Registration in main.py
```python
# In main.py imports (after configure_logging):
from src.cli.prune import handle_prune, register_prune_parser  # noqa: E402

# In main() function, after register_replay_parser(sub):
register_prune_parser(sub)

# In dispatch section:
if args.command == "prune":
    sys.exit(handle_prune(args))
```

### Structlog Event Logging
```python
# Following project convention: stdlib logger + structlog ProcessorFormatter
import logging
logger = logging.getLogger(__name__)

# Log individual archive events with structured context
logger.info("document_archived", document_id=doc.document_id, source=doc.source.value,
            chunk_count=len(doc.chunks), archive_path=str(archive_path))

# Log summary at end
logger.info("prune_complete", archived=archived_count, deleted=deleted_count,
            protected=protected_count, skipped=skipped_count)
```

### Idempotent Archive Check
```python
archive_path = archive_dir / f"{doc.document_id}.md"
if archive_path.exists():
    logger.info("document_already_archived", document_id=doc.document_id,
                path=str(archive_path))
    # Still delete from ChromaDB since archive exists
    continue_to_delete = True
```

### Graceful ChromaDB Failure
```python
# Following the analyze command pattern
try:
    svc = MemoryService()
    if not svc.health_check():
        logger.warning("chromadb_unavailable", message="ChromaDB unreachable, cannot prune")
        return 1
except Exception as exc:
    logger.warning("chromadb_init_failed", error=str(exc))
    return 1
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual ChromaDB cleanup | No cleanup mechanism exists | Phase 31 | First formal prune capability |
| Direct collection access | MemoryService as sole interface | Phase 4 (v1.0) | All ChromaDB ops through service layer |

**Deprecated/outdated:**
- None relevant -- this is greenfield functionality using established patterns.

## Open Questions

1. **ChromaDB `get()` performance on large collections**
   - What we know: `collection.get(include=["documents", "metadatas"])` fetches everything into memory. The indexer already does this for deduplication.
   - What's unclear: At what collection size this becomes problematic (memory/time).
   - Recommendation: Accept the same approach as indexer.py for now. If collections grow very large, pagination can be added later (ChromaDB supports `limit`/`offset` on `.get()`).

2. **PyYAML vs manual frontmatter**
   - What we know: PyYAML is likely already installed (transitive dependency). Manual string formatting risks escaping bugs.
   - What's unclear: Whether PyYAML is an explicit project dependency.
   - Recommendation: Use `yaml.dump()` -- if not installed, `yaml.safe_dump()` from PyYAML is a trivial addition. Verify at implementation time with `import yaml`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via `.venv/bin/python3.12 -m pytest`) |
| Config file | pyproject.toml or pytest.ini (project standard) |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/cli/test_prune.py -x` |
| Full suite command | `.venv/bin/python3.12 -m pytest -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OBS-03 | `prune --dry-run` shows archive plan; `prune` writes Markdown files with YAML frontmatter and deletes from ChromaDB | unit + integration | `.venv/bin/python3.12 -m pytest tests/cli/test_prune.py -x` | Wave 0 |
| OBS-06 | Documents within active rule protection window are skipped | unit | `.venv/bin/python3.12 -m pytest tests/cli/test_prune.py::test_rule_protected_documents_skipped -x` | Wave 0 |
| OBS-07 | Archived/deleted counts logged via structlog | unit | `.venv/bin/python3.12 -m pytest tests/cli/test_prune.py::test_prune_logs_counts -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python3.12 -m pytest tests/cli/test_prune.py -x`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/cli/test_prune.py` -- covers OBS-03, OBS-06, OBS-07
- [ ] `tests/cli/__init__.py` -- package init (check if exists)
- [ ] Verify `pyyaml` importable: `python -c "import yaml"`

## Sources

### Primary (HIGH confidence)
- `src/memory/service.py` -- MemoryService API, StoredDocument dataclass, MemorySource enum, delete() method
- `src/memory/indexer.py` -- Bulk `collection.get(include=["metadatas"])` pattern for full-collection scan
- `src/core/memory_registry.py` -- `get_active_rules()` returning `List[MemoryRule]` with `created_at` datetime field
- `src/models/memory.py` -- MemoryRule Pydantic model with `created_at`, `status` fields
- `src/cli/replay.py` -- `register_replay_parser()` / `handle_replay()` pattern, Rich table usage
- `src/main.py` -- CLI dispatch pattern, subparser registration, structlog initialization
- `src/core/logging_config.py` -- structlog ProcessorFormatter configuration

### Secondary (MEDIUM confidence)
- ChromaDB `.get()` API supports `limit`/`offset` parameters for pagination (from training data, consistent with observed usage in codebase)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use, no new dependencies
- Architecture: HIGH -- all patterns copied from existing codebase (replay CLI, indexer bulk fetch)
- Pitfalls: HIGH -- identified from direct code reading of timestamp formats, ChromaDB return shapes, and MemoryRule types

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable domain, no external API changes expected)
