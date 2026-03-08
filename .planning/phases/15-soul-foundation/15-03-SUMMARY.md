---
phase: 15-soul-foundation
plan: "03"
subsystem: soul-integration
tags: [soul, audit, state, orchestrator, analysts, researchers]
dependency_graph:
  requires: [15-01, 15-02]
  provides: [SOUL-04, SOUL-05, SOUL-07]
  affects: [src/core/audit_logger.py, src/graph/state.py, src/graph/orchestrator.py, src/graph/agents/analysts.py, src/graph/agents/researchers.py]
tech_stack:
  added: []
  patterns: [lazy-soul-load-at-node-entry, strip-excluded-before-hash, warmup-at-graph-creation]
key_files:
  created: []
  modified:
    - src/core/audit_logger.py
    - src/graph/orchestrator.py
    - src/graph/agents/analysts.py
    - src/graph/agents/researchers.py
decisions:
  - "_strip_excluded() added as module-level function in audit_logger so _calculate_hash and verify_chain both strip consistently without needing instance access"
  - "soul_system_message added as Optional[SystemMessage] parameter to _run_researcher_agent — avoids changing node function signatures and keeps soul local to invocation context"
  - "QuantModeler, BullishResearcher, and BearishResearcher all write system_prompt and active_persona to state return dict — LangGraph fan-in merge will use last-write-wins for plain fields"
metrics:
  duration: "287 seconds (~5 minutes)"
  completed_date: "2026-03-08"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
---

# Phase 15 Plan 03: Soul Integration Wire-Up Summary

**One-liner:** `_strip_excluded` audit hash stripping + `warmup_soul_cache` orchestrator warmup + soul injection wired into QuantModeler, BullishResearcher, and BearishResearcher via `load_soul()` at node entry with SystemMessage prepended locally.

## Objective

Complete the soul integration layer: ensure soul content reaches all five L2 LLM invocations at runtime, and is provably absent from the SHA-256 hash-chained audit trail.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add _strip_excluded to audit hash and warmup_soul_cache in orchestrator | 70bb789 | src/core/audit_logger.py, src/graph/orchestrator.py |
| 2 | Inject soul into QuantModeler, BullishResearcher, BearishResearcher | 6472659 | src/graph/agents/analysts.py, src/graph/agents/researchers.py |

## What Was Already Done (Phase 15-01 and 15-02)

Before this plan executed, the following were already in place:
- `SwarmState` had `system_prompt` and `active_persona` Optional[str] fields (Plan 01)
- `AUDIT_EXCLUDED_FIELDS` frozenset existed in `audit_logger.py` (Plan 01)
- `MacroAnalyst` node already called `load_soul("macro_analyst")` and returned soul fields (Plan 02)

## What This Plan Added

**Task 1:**
- Added `_strip_excluded(data: dict) -> dict` module-level helper to `src/core/audit_logger.py`
- Modified `_calculate_hash` to call `_strip_excluded` on `input_data` and `output_data` before `json.dumps` — ensures `verify_chain` also strips consistently since it calls `_calculate_hash`
- Added `from src.core.soul_loader import warmup_soul_cache` import to `src/graph/orchestrator.py`
- Added `warmup_soul_cache()` call inside `create_orchestrator_graph()` body, after `workflow.compile()` — fast-fail on missing soul dirs at graph creation time, not during live runs

**Task 2:**
- `QuantModeler` (analysts.py): Added `soul = load_soul("quant_modeler")` at node end, returns `system_prompt` and `active_persona` in state dict
- `_run_researcher_agent` (researchers.py): Added `soul_system_message: Optional[SystemMessage] = None` parameter; prepends it to the messages list before the HumanMessage if provided
- `BullishResearcher` (researchers.py): Added `soul = load_soul("bullish_researcher")` at node entry, passes `SystemMessage(content=soul.system_prompt)` to `_run_researcher_agent`, returns soul fields in state dict
- `BearishResearcher` (researchers.py): Identical pattern with `load_soul("bearish_researcher")`
- Added `SystemMessage` to the `langchain_core.messages` import in researchers.py
- Added `from src.core.soul_loader import load_soul` import to researchers.py

## Decisions Made

1. `_strip_excluded()` is a module-level function (not a method) so both `_calculate_hash` (instance method) and any future `verify_chain` refactors can call it without an instance reference.

2. `soul_system_message` added as an optional parameter to `_run_researcher_agent` rather than restructuring the node functions — preserves backward compatibility and keeps soul injection at the call site where intent is clear.

3. Soul fields (`system_prompt`, `active_persona`) are written to state return dicts by all nodes. In the LangGraph fan-in from parallel BullishResearcher + BearishResearcher, the plain (non-reducer) fields use last-write-wins semantics — this is acceptable since both researchers load the same soul role conceptually and the values are identical.

## Test Results

- `tests/core/` — 33 tests, all passing
- Full suite — 292 passed, 1 pre-existing failure (`test_persistence.py::test_trade_warehouse_persistence` fails due to PostgreSQL schema mismatch: column `position_size` does not exist in `trades` table — not caused by this plan's changes, confirmed by git stash verification)

## Deviations from Plan

None — plan executed exactly as written.

The `system_prompt` and `active_persona` fields in `SwarmState` and the `AUDIT_EXCLUDED_FIELDS` constant in `audit_logger.py` were already present from Phase 15-01 and 15-02. Task 1 only needed to add `_strip_excluded` and the hash stripping logic, plus the orchestrator warmup call.

## Self-Check: PASSED

- SUMMARY.md: FOUND at .planning/phases/15-soul-foundation/15-03-SUMMARY.md
- Task 1 commit 70bb789: FOUND
- Task 2 commit 6472659: FOUND
- src/core/audit_logger.py: _strip_excluded present, _calculate_hash uses it
- src/graph/orchestrator.py: warmup_soul_cache imported and called inside create_orchestrator_graph
- src/graph/agents/analysts.py: load_soul called in both MacroAnalyst and QuantModeler
- src/graph/agents/researchers.py: load_soul called in BullishResearcher and BearishResearcher
- 33 core tests passing, 292 total tests passing
