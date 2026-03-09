---
phase: 27-environment-stabilization
plan: 01
subsystem: infra
tags: [ccxt, chromadb, pytest-asyncio, pydantic, lazy-init, dependency-pinning]

requires:
  - phase: none
    provides: n/a
provides:
  - Exact version pins for ccxt, chromadb, pytest-asyncio
  - Lazy init pattern for ccxt in ccxt_client.py and order_router_ccxt.py
  - Pydantic V2 compliant AuditLogEntry model
affects: [27-02, 28-test-suite-repair, environment-stabilization]

tech-stack:
  added: []
  patterns: [lazy-init-ccxt, exact-version-pinning]

key-files:
  created: []
  modified:
    - pyproject.toml
    - uv.lock
    - src/models/audit.py
    - src/tools/data_sources/ccxt_client.py
    - src/agents/order_router_ccxt.py

key-decisions:
  - "Removed class Config from AuditLogEntry rather than migrating to model_config -- Pydantic V2 handles datetime ISO serialization by default"
  - "Used _get_ccxt_async() lazy import pattern matching existing codebase convention from soul_loader.py"

patterns-established:
  - "Lazy ccxt import: _get_ccxt_async() for async, _get_exchange() for sync -- prevents import-time side effects"
  - "Exact version pinning: all volatile deps use == not >= to ensure reproducible builds"

requirements-completed: [ENV-01, ENV-02, ENV-03]

duration: 4min
completed: 2026-03-09
---

# Phase 27 Plan 01: Dependency Pins & Lazy Init Summary

**Pinned ccxt/chromadb/pytest-asyncio to exact versions, replaced MagicMock hack with lazy ccxt imports, and fixed Pydantic V2 deprecation warning**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-09T15:43:41Z
- **Completed:** 2026-03-09T15:47:48Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Pinned ccxt==4.5.42, chromadb==1.5.2, pytest-asyncio==1.3.0 for reproducible builds
- Replaced module-level MagicMock in ccxt_client.py with _get_ccxt_async() lazy import
- Converted order_router_ccxt.py from import-time exchange init to _get_exchange() lazy pattern
- Removed deprecated Pydantic class Config from AuditLogEntry

## Task Commits

Each task was committed atomically:

1. **Task 1: Pin exact dependency versions and fix Pydantic ConfigDict** - `dfaf3c1` (chore)
2. **Task 2: Restore ccxt lazy init in ccxt_client.py and order_router_ccxt.py** - `a918282` (fix)

## Files Created/Modified
- `pyproject.toml` - Exact version pins for 3 volatile dependencies
- `uv.lock` - Regenerated lockfile
- `src/models/audit.py` - Removed deprecated class Config block
- `src/tools/data_sources/ccxt_client.py` - Lazy ccxt.async_support import via _get_ccxt_async()
- `src/agents/order_router_ccxt.py` - Lazy exchange init via _get_exchange()

## Decisions Made
- Removed class Config entirely from AuditLogEntry rather than migrating to model_config = ConfigDict(...), since Pydantic V2 serializes datetime as ISO by default
- Matched existing lazy init pattern from soul_loader.py for consistency

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Clean ccxt imports enable test suite repair in Plan 02
- All 5 data fetcher tests pass with new lazy init pattern
- Pydantic deprecation warning eliminated

---
*Phase: 27-environment-stabilization*
*Completed: 2026-03-09*
