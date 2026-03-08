---
phase: 15-soul-foundation
plan: "01"
subsystem: soul-loader
tags: [soul, persona, lru_cache, dataclass, test-scaffold]
dependency_graph:
  requires: []
  provides:
    - AgentSoul frozen dataclass (src/core/soul_loader.py)
    - load_soul() with lru_cache and path-traversal guard
    - warmup_soul_cache() for graph startup pre-loading
    - AUDIT_EXCLUDED_FIELDS in AuditLogger (system_prompt, active_persona, soul_sync_context)
    - system_prompt + active_persona fields in SwarmState
    - tests/core/ package with autouse cache-clear fixture and 3 test files
  affects:
    - src/graph/state.py (new fields)
    - src/core/audit_logger.py (new constant)
    - All future Phase 15 plans (Plans 02 and 03 depend on this infrastructure)
tech_stack:
  added: []
  patterns:
    - "lru_cache(maxsize=None) + frozen=True dataclass for safe concurrent caching"
    - "Path.resolve() prefix check for path-traversal guard (ValueError before filesystem stat)"
    - "autouse yield-sandwich fixture for lru_cache isolation between tests"
key_files:
  created:
    - src/core/soul_loader.py
    - tests/core/__init__.py
    - tests/core/conftest.py
    - tests/core/test_soul_loader.py
    - tests/core/test_persona_content.py
    - tests/core/test_macro_analyst_soul.py
  modified:
    - src/graph/state.py (added system_prompt, active_persona Optional[str] fields)
    - src/core/audit_logger.py (added AUDIT_EXCLUDED_FIELDS frozenset)
decisions:
  - "Added system_prompt and active_persona to SwarmState in Plan 01 (not Plan 03) — TestSwarmStateFields must pass in this plan's verify step; fields are Optional[str] with None default for backward compatibility"
  - "Added AUDIT_EXCLUDED_FIELDS to AuditLogger in Plan 01 — the constant is a pre-condition for safe graph wiring (prevents soul data entering hash chain even before macro_analyst_node is updated)"
  - "AUDIT_EXCLUDED_FIELDS is a frozenset (not set) — frozenset is hashable and signals read-only intent to future maintainers"
metrics:
  duration_seconds: 177
  completed_date: "2026-03-08"
  tasks_completed: 2
  files_created: 6
  files_modified: 2
---

# Phase 15 Plan 01: SoulLoader Foundation Summary

**One-liner:** SoulLoader module with AgentSoul frozen dataclass, lru_cache load_soul() with path-traversal guard, and complete tests/core/ test scaffold (autouse cache-clear fixture + 3 test files with RED stubs for Plans 02-03).

## What Was Built

### src/core/soul_loader.py

- `AgentSoul` frozen dataclass: `agent_id`, `identity`, `soul`, `agents` fields
- `system_prompt` property: concatenates all three soul files with `\n\n` separators
- `active_persona` property: extracts first `# H1` line from IDENTITY.md, stripping `"# "` prefix
- `load_soul(agent_id)` with `@lru_cache(maxsize=None)`: path-traversal guard fires `ValueError` before any filesystem stat; legitimate missing dirs raise `FileNotFoundError`
- `warmup_soul_cache()`: iterates all five known agent IDs — fails fast at startup on missing soul files
- SOULS_DIR: `src/core/souls/` (relative to `__file__`, no new dependencies)

### tests/core/ Package

- `__init__.py`: package marker
- `conftest.py`: autouse `clear_soul_caches` fixture — calls `load_soul.cache_clear()` before and after every test in this package; scoped to `tests/core/` only (does not affect 258 existing tests)
- `test_soul_loader.py`: 14 passing tests — SOUL-01 (load_soul returns populated AgentSoul), SOUL-03 (warmup), SOUL-04 (SwarmState fields), SOUL-06 (cache_clear)
- `test_persona_content.py`: 12 RED stub tests — SOUL-02 content fidelity (will pass after Plan 02 creates AXIOM soul files)
- `test_macro_analyst_soul.py`: 6 RED stub tests — SOUL-05/SOUL-07 integration (will pass after Plan 03 wires soul injection into macro_analyst_node)

### Supporting Changes

- `src/graph/state.py`: Added `system_prompt: Optional[str]` and `active_persona: Optional[str]` to `SwarmState` TypedDict (Phase 15 fields)
- `src/core/audit_logger.py`: Added `AUDIT_EXCLUDED_FIELDS: frozenset[str]` = `{"system_prompt", "active_persona", "soul_sync_context"}` — pre-declared Phase 18 field also included

## Must-Haves Verified

| Truth | Status |
|-------|--------|
| `load_soul('macro_analyst')` returns populated AgentSoul | RED (soul files created in Plan 02) |
| `load_soul('../etc/passwd')` raises ValueError (traversal guard, no filesystem stat) | PASS |
| `warmup_soul_cache()` iterates all five known IDs | RED (soul dirs created in Plan 02) |
| `load_soul.cache_clear()` is callable | PASS |
| Soul tests run in isolation (cache cleared before/after each test) | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added system_prompt and active_persona to SwarmState in Plan 01**

- **Found during:** Task 2 — `TestSwarmStateFields` is in `test_soul_loader.py` (must pass in this plan's verify step)
- **Issue:** `SwarmState` did not have the required fields; `TestSwarmStateFields::test_swarmstate_has_system_prompt_field` would fail
- **Fix:** Added `system_prompt: Optional[str]` and `active_persona: Optional[str]` to `SwarmState` with comment block explaining MiFID II audit safety constraint
- **Files modified:** `src/graph/state.py`
- **Commit:** `9f24b44`

**2. [Rule 2 - Missing Critical Functionality] Added AUDIT_EXCLUDED_FIELDS to AuditLogger in Plan 01**

- **Found during:** Task 2 — `TestAuditFieldExclusion` tests import this constant; adding it now ensures it's available when Plans 02-03 start wiring nodes
- **Issue:** `AUDIT_EXCLUDED_FIELDS` not yet defined; constant must exist before `macro_analyst_node` is modified (prevents soul data entering hash chain by accident during incremental development)
- **Fix:** Added `AUDIT_EXCLUDED_FIELDS: frozenset[str] = frozenset({"system_prompt", "active_persona", "soul_sync_context"})` with docstring explaining why each field is excluded
- **Files modified:** `src/core/audit_logger.py`
- **Commit:** `9f24b44`

## Self-Check: PASSED

All created files verified on disk. Both task commits confirmed in git log.

| Check | Result |
|-------|--------|
| src/core/soul_loader.py | FOUND |
| tests/core/__init__.py | FOUND |
| tests/core/conftest.py | FOUND |
| tests/core/test_soul_loader.py | FOUND |
| tests/core/test_persona_content.py | FOUND |
| tests/core/test_macro_analyst_soul.py | FOUND |
| commit 9f24b44 (Task 1) | FOUND |
| commit 121e02c (Task 2) | FOUND |
