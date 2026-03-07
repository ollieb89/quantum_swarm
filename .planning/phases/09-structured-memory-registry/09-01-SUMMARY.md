---
phase: 09-structured-memory-registry
plan: "01"
subsystem: memory
tags: [memory-registry, lifecycle, tdd, atomic-write, MEM-05]
dependency_graph:
  requires: []
  provides: [update_status, atomic-save, lifecycle-transitions]
  affects: [src/core/memory_registry.py, tests/test_structured_memory.py]
tech_stack:
  added: []
  patterns: [atomic-write-os-replace, VALID_TRANSITIONS-dict, assertLogs-for-logging-tests]
key_files:
  created: []
  modified:
    - src/core/memory_registry.py
    - tests/test_structured_memory.py
decisions:
  - "VALID_TRANSITIONS defined as module-level constant for clarity and testability"
  - "update_status() calls self.save() internally — callers don't need to save manually"
  - "save() uses file_path.with_suffix('.tmp') then os.replace() for POSIX atomic rename"
  - "Pydantic status field uses Literal type — update_status() assigns with type: ignore comment"
metrics:
  duration_seconds: 72
  tasks_completed: 2
  files_modified: 2
  completed_date: "2026-03-07"
requirements:
  - MEM-05
---

# Phase 09 Plan 01: Structured Memory Registry — Lifecycle Controls Summary

**One-liner:** MemoryRegistry gains `update_status()` with governed one-way transitions and atomic `save()` via `os.replace()`, fully verified by 10 TDD tests including `assertLogs`.

## What Was Built

`src/core/memory_registry.py` extended with two features:

1. **`update_status(rule_id, new_status)`** — enforces the MEM-05 lifecycle state machine:
   - `proposed` -> `active` | `rejected`
   - `active` -> `deprecated` | `rejected`
   - `deprecated` (terminal), `rejected` (terminal)
   - Raises `ValueError` for missing rule ID or invalid transition
   - Increments `rule.version`, refreshes `rule.updated_at`
   - Logs transition at INFO level: `Rule {id} transitioned {old} -> {new} (v{n})`

2. **Hardened `save()`** — atomic write via POSIX rename:
   - Writes JSON to `{file_path}.tmp`
   - Calls `os.replace(tmp_path, file_path)` — atomic on Linux (rename syscall)
   - No partial-write corruption possible

`tests/test_structured_memory.py` expanded from 4 to 10 tests:
- `test_update_status_valid`: proposed -> active, version == 2
- `test_update_status_terminal`: active -> deprecated succeeds; deprecated -> active raises ValueError
- `test_update_status_not_found`: nonexistent ID raises ValueError
- `test_update_status_invalid_reverse`: proposed -> proposed raises ValueError
- `test_atomic_save`: no `.tmp` file persists after save()
- `test_transition_logged`: `assertLogs` confirms INFO record contains rule ID

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add lifecycle transition tests | b982356 | tests/test_structured_memory.py |
| 1 (GREEN) | Implement update_status() and atomic save() | 47a9d90 | src/core/memory_registry.py |

## Verification

```
.venv/bin/python3.12 -m pytest tests/test_structured_memory.py -v
10 passed in 0.01s
```

```
grep -n "update_status|os.replace" src/core/memory_registry.py
54:            os.replace(tmp_path, self.file_path)
75:    def update_status(self, rule_id: str, new_status: str) -> MemoryRule:
```

## Deviations from Plan

None — plan executed exactly as written. The two plan tasks (Task 1 + Task 2) were combined into a single TDD cycle since writing tests before the implementation is the correct RED->GREEN order.

## Decisions Made

- `VALID_TRANSITIONS` as module-level constant keeps the transition table readable and independently testable
- `update_status()` always calls `self.save()` — no two-step API burden on callers
- `os.replace()` chosen over `shutil.move()` because it is guaranteed atomic on POSIX and available in stdlib without extra imports beyond `os`

## Self-Check: PASSED

- [x] src/core/memory_registry.py exists and contains `update_status` and `os.replace`
- [x] tests/test_structured_memory.py has 10 tests
- [x] Commits b982356 and 47a9d90 exist
