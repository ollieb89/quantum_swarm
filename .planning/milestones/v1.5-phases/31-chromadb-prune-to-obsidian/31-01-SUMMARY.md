---
phase: 31-chromadb-prune-to-obsidian
plan: 01
subsystem: cli
tags: [chromadb, obsidian, yaml, rich, archival, prune]

requires:
  - phase: 04-memory-service
    provides: "MemoryService with get/delete/store/health_check"
  - phase: 07-memory-registry
    provides: "MemoryRegistry with get_active_rules()"
  - phase: 26-replay-cli
    provides: "CLI subcommand registration pattern with Rich tables"
provides:
  - "MemoryService.list_documents() for bulk document enumeration"
  - "Prune core module with archive rendering, rule-aware filtering, archive+delete orchestration"
  - "register_prune_parser / handle_prune CLI entry points"
affects: [31-02-cli-wiring, obsidian-vault, memory-maintenance]

tech-stack:
  added: [pyyaml]
  patterns: [archive-then-delete, conservative-rule-protection, idempotent-archival]

key-files:
  created:
    - src/cli/prune.py
    - tests/cli/test_prune.py
  modified:
    - src/memory/service.py

key-decisions:
  - "stdlib logging with extra dict instead of structlog kwargs -- project uses logging.getLogger not structlog.get_logger"
  - "Conservative rule protection: documents newer than oldest active rule created_at are always protected"
  - "Atomic file writes via tempfile + os.replace for crash safety"

patterns-established:
  - "list_documents() pattern: collection.get() -> group by document_id -> sort by chunk_index -> StoredDocument list"
  - "Archive-then-delete ordering with idempotent filename check"

requirements-completed: [OBS-03, OBS-06, OBS-07]

duration: 12min
completed: 2026-03-10
---

# Phase 31 Plan 01: ChromaDB Prune Core Summary

**Prune core module with list_documents bulk enumeration, YAML-frontmatter Obsidian archival, and rule-aware protection cutoff**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-10T01:19:51Z
- **Completed:** 2026-03-10T01:32:18Z
- **Tasks:** 1 (TDD: RED-GREEN)
- **Files modified:** 3

## Accomplishments
- Added list_documents() to MemoryService for bulk document enumeration with chunk reassembly
- Created src/cli/prune.py with full prune logic: archive rendering, classification, orchestration
- 18 unit tests covering archive format, rule-aware protection, dry-run, idempotency, graceful degradation

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `a7f2d12` (test)
2. **Task 1 GREEN: Implementation** - `2f54b48` (feat)

## Files Created/Modified
- `src/cli/prune.py` - Prune core module: register_prune_parser, handle_prune, _render_archive_markdown, _classify_documents, _compute_protection_cutoff
- `src/memory/service.py` - Added list_documents() method and defaultdict import
- `tests/cli/test_prune.py` - 18 unit tests covering OBS-03, OBS-06, OBS-07

## Decisions Made
- Used stdlib logging with `extra={}` dict for structured fields since the project uses `logging.getLogger(__name__)` not structlog's native logger
- Conservative rule protection: any document with timestamp newer than oldest active rule's `created_at` is protected from deletion
- Atomic file writes via `tempfile.mkstemp` + `os.replace` pattern (consistent with MemoryRegistry)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed logging kwargs incompatibility with stdlib logger**
- **Found during:** Task 1 GREEN (implementation)
- **Issue:** Plan suggested `logger.info("event", key=value)` structlog-style kwargs, but project uses stdlib logging.getLogger which rejects arbitrary kwargs
- **Fix:** Changed to `logger.info("event", extra={"key": value})` for structured fields and `logger.warning("event: %s", value)` for simple messages
- **Files modified:** src/cli/prune.py, tests/cli/test_prune.py
- **Verification:** All 18 tests pass
- **Committed in:** 2f54b48

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for correctness. No scope creep.

## Issues Encountered
- Pre-existing test failures in test_cycle_runner.py and test_cycle_runner_persona.py (unrelated to this plan, coroutine serialization issues)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Prune core logic complete, ready for Plan 02 CLI wiring into main.py
- register_prune_parser and handle_prune exported and tested
- ARCHIVE_BASE constant available for override in tests

---
*Phase: 31-chromadb-prune-to-obsidian*
*Completed: 2026-03-10*
