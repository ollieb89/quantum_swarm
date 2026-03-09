# Phase 31: ChromaDB Prune-to-Obsidian - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Archive old ChromaDB vectors to searchable Obsidian-compatible Markdown files with YAML frontmatter, then prune them from the database. Exposed as a `prune` CLI subcommand with `--dry-run` support. Rule-aware safety ensures active MemoryRegistry rules are never orphaned.

</domain>

<decisions>
## Implementation Decisions

### Archive file structure
- One Markdown file per logical document (grouped by document_id, not per-chunk)
- Chunks reassembled into full document content in the Markdown body
- Output directory: `quantum-swarm/Archives/memory/` (inside Obsidian vault)
- Subdirectories by source type: `trade/`, `research/`, `external_data/`
- Filename: `{document_id}.md` (already prefixed with source type, e.g. `trade_abc123.md`)
- YAML frontmatter includes: document_id, source, timestamp, ingested_at, content_hash, all original metadata fields

### Age threshold & rule-aware cutoff
- Default age threshold: 90 days (configurable via `--days N` flag)
- Threshold measured against the `timestamp` metadata field (not `ingested_at`)
- Rule-aware safety: before pruning, load MemoryRegistry active rules and cross-reference by timestamp overlap — any document whose timestamp falls within the window of an active rule's evidence period is protected
- Since MemoryRule has no direct ChromaDB document_id link, protection is conservative: if a document's timestamp is newer than the oldest active rule's `created_at`, it is protected
- Protected documents are listed in dry-run output as "skipped (active rule protection)"

### CLI design
- New subcommand: `python -m src.main prune`
- Flags: `--dry-run` (show what would happen, no modifications), `--days N` (age threshold, default 90), `--no-archive` (delete without archiving — requires explicit opt-in)
- Default behavior (no flags): archive + delete
- Output: structlog events for each archived/deleted document, summary counts at end
- Exit code: 0 on success, 1 on error

### Dry-run output
- Table showing: document_id, source, timestamp, chunk_count, action (archive/skip/protected)
- Summary line: "Would archive N documents (M chunks), skip P (rule-protected)"
- Uses rich console for table formatting (consistent with replay CLI pattern)

### Prune operation flow
1. Query all ChromaDB documents via MemoryService
2. Filter by age threshold
3. Cross-reference with MemoryRegistry active rules for protection
4. If not `--dry-run`: write Markdown files, then delete from ChromaDB
5. Archive-then-delete ordering ensures no data loss on crash (worst case: duplicates on re-run, handled by idempotent filenames)

### Claude's Discretion
- Exact YAML frontmatter field ordering
- Rich table styling details
- Whether to batch ChromaDB deletes or delete one-by-one
- Internal helper function decomposition

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MemoryService` (`src/memory/service.py`): Sole ChromaDB interface with `get()`, `delete()`, `search()`, `health_check()` — prune should use this, not raw ChromaDB
- `MemoryService._collection.get(include=["metadatas"])`: Pattern from `indexer.py` for bulk metadata fetch
- `MemoryRegistry` (`src/core/memory_registry.py`): `get_active_rules()` not yet present but `schema.rules` with status filtering is trivial
- `MemorySource` enum: TRADE, RESEARCH, EXTERNAL_DATA — maps directly to archive subdirectories
- `StoredDocument` dataclass: Already reassembles chunks into logical documents
- `register_replay_parser` pattern in `main.py`: Template for adding `prune` subcommand
- Rich console pattern from replay CLI (`src/cli/replay.py`): Reuse for dry-run table output

### Established Patterns
- structlog for all operational logging (Phase 25/28)
- CLI subcommand registration via argparse subparsers
- Lazy ChromaDB import (no key needed at module load)
- Atomic file operations (os.replace pattern from MemoryRegistry)

### Integration Points
- `src/main.py`: Add `register_prune_parser(sub)` + `handle_prune(args)` dispatch
- `src/memory/service.py`: May need a `list_all()` or `get_all_metadata()` method for bulk enumeration
- `src/core/memory_registry.py`: Need to read active rules for protection check
- `quantum-swarm/Archives/memory/`: New Obsidian vault directory for archived documents

</code_context>

<specifics>
## Specific Ideas

- Archive files should be valid Obsidian notes — YAML frontmatter, clean Markdown body, no HTML
- The `prune` command follows the same graceful-degradation pattern as `analyze`: if ChromaDB is unreachable, log warning and exit cleanly
- Idempotent: re-running prune on already-archived documents should skip them (check if .md file exists before archiving)

</specifics>

<deferred>
## Deferred Ideas

- Scheduled automatic pruning via systemd timer — future phase
- Obsidian search index / tag generation for archived memories — future phase
- Reverse operation (re-import from Obsidian to ChromaDB) — future phase

</deferred>

---

*Phase: 31-chromadb-prune-to-obsidian*
*Context gathered: 2026-03-10*
