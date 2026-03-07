---
phase: 04-memory-compliance
plan: "02"
subsystem: database
tags: [chromadb, duckdb, lazy-init, singleton, knowledge-base]

requires:
  - phase: 04-01
    provides: Retroactive phase plans for memory-compliance

provides:
  - Lazy-initialised KnowledgeBase via get_kb() — no module-level singleton
  - Safe import of src.tools.knowledge_base in environments without chromadb

affects:
  - src/graph/nodes/knowledge_base.py
  - tests/test_knowledge_base.py
  - Any future phase importing from src.tools.knowledge_base

tech-stack:
  added: []
  patterns:
    - "Lazy init singleton: _kb private cache with get_kb() public getter (mirrors src/memory/service.py pattern)"
    - "Heavy optional dependencies (chromadb, duckdb) imported inside __init__ not at module scope"

key-files:
  created: []
  modified:
    - src/tools/knowledge_base.py
    - src/graph/nodes/knowledge_base.py
    - tests/test_knowledge_base.py

key-decisions:
  - "Move chromadb and duckdb imports inside KnowledgeBase.__init__ to make module import side-effect-free"
  - "Replace module-level kb = KnowledgeBase() singleton with _kb private cache and get_kb() public getter"
  - "Update test_knowledge_base.py as part of Task 2 — it was a direct kb caller, not pre-existing unrelated code"

patterns-established:
  - "Lazy init pattern: _obj = None / def get_obj(): global _obj; if _obj is None: _obj = Cls(); return _obj"

requirements-completed: [MEM-01]

duration: 8min
completed: 2026-03-07
---

# Phase 04 Plan 02: KnowledgeBase Lazy Init Summary

**ChromaDB singleton replaced with lazy get_kb() getter, moving heavy imports inside __init__ so the module is safely importable without chromadb installed**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-07T00:00:00Z
- **Completed:** 2026-03-07T00:08:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Removed module-level `import chromadb`, `from chromadb.utils import embedding_functions`, and `import duckdb` — moved inside `__init__`
- Replaced `kb = KnowledgeBase()` singleton with `_kb` private cache and `get_kb()` lazy getter
- Updated `src/graph/nodes/knowledge_base.py` to import and call `get_kb()` instead of `kb`
- Fixed `tests/test_knowledge_base.py` which also imported the old singleton — all 3 tests now pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Convert KnowledgeBase to lazy init with get_kb() getter** - `345c776` (refactor)
2. **Task 2: Update knowledge_base_node callers and verify test suite** - `df0b710` (feat)

## Files Created/Modified

- `src/tools/knowledge_base.py` - Heavy imports moved inside `__init__`; `kb = KnowledgeBase()` replaced with `_kb` + `get_kb()`
- `src/graph/nodes/knowledge_base.py` - Updated import to `get_kb`; all `kb.method()` calls replaced with `get_kb().method()`
- `tests/test_knowledge_base.py` - Updated import and usage from `kb` to `get_kb()`; all 3 tests pass

## Decisions Made

- Moved chromadb/duckdb imports inside `__init__` rather than using try/except at module level — cleaner, matches the stated target pattern from the plan
- Updated `tests/test_knowledge_base.py` as part of Task 2 (it was a direct caller of the `kb` singleton; not updating it would have caused `ImportError` at collection time)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_knowledge_base.py importing old kb singleton**
- **Found during:** Task 2 (Update knowledge_base_node callers and verify test suite)
- **Issue:** `tests/test_knowledge_base.py` imported `from src.tools.knowledge_base import kb`, which no longer exists after Task 1's refactor. Test collection failed with `ImportError`.
- **Fix:** Updated import to `get_kb` and replaced all `kb.method()` calls with `get_kb().method()`
- **Files modified:** `tests/test_knowledge_base.py`
- **Verification:** All 3 tests pass (`3 passed in 6.14s`)
- **Committed in:** `df0b710` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Necessary to keep test collection from failing. No scope creep — the test file was a direct caller of the singleton being removed.

## Issues Encountered

- `tests/test_institutional_guard.py` fails with `TypeError: 'coroutine' object is not subscriptable` — pre-existing async test issue unrelated to this plan's changes. Confirmed by isolating: the failure is not caused by any file modified here.

## Next Phase Readiness

- `src/tools/knowledge_base.py` is now safe to import in any test environment, even without chromadb installed
- The lazy init pattern is consistent with `src/memory/service.py` (established project pattern)
- MEM-01 requirement satisfied: module-level singleton eliminated

---
*Phase: 04-memory-compliance*
*Completed: 2026-03-07*
