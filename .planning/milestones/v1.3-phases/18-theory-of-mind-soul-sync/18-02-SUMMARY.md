---
phase: 18-theory-of-mind-soul-sync
plan: "02"
subsystem: graph-nodes
tags: [soul-sync, theory-of-mind, barrier-node, orchestrator, user-md]
dependency_graph:
  requires:
    - "18-01"  # AgentSoul.users field, public_soul_summary(), soul_sync_context in SwarmState
  provides:
    - "soul_sync_handshake_node registered in graph"
    - "barrier edge: researchers → soul_sync_handshake_node → debate_synthesizer"
    - "USER.md empathetic refutation content for MOMENTUM and CASSANDRA"
    - "soul_sync_context: None in initial_state"
  affects:
    - "src/graph/orchestrator.py"
    - "tests/core/test_soul_sync.py"
tech_stack:
  added: []
  patterns:
    - "Synchronous barrier node reading lru_cache (no async required for pure cache reads)"
    - "patch(..., create=True) for testing absent module attributes"
key_files:
  created:
    - "src/graph/nodes/soul_sync_handshake.py"
    - "src/core/souls/bullish_researcher/USER.md"
    - "src/core/souls/bearish_researcher/USER.md"
  modified:
    - "src/graph/orchestrator.py"
    - "tests/core/test_soul_sync.py"
decisions:
  - "soul_sync_handshake_node implemented as synchronous (not async) — all reads are lru_cache hits, no I/O or coroutine needed; LangGraph's with_audit_logging wrapper handles sync nodes via asyncio.to_thread"
  - "TestNoLLMCalls patch fixed with create=True — module correctly never imports ChatGoogleGenerativeAI; patch target must use create=True when testing absence of an import"
metrics:
  duration: "3 minutes"
  completed_date: "2026-03-08"
  tasks_completed: 2
  files_changed: 5
---

# Phase 18 Plan 02: Soul-Sync Handshake Node and USER.md Content Summary

Barrier node implementation with zero LLM calls, fan-in edge rewire, and empathetic refutation few-shots authored for both adversarial researcher archetypes.

## What Was Built

**soul_sync_handshake_node** — A synchronous LangGraph node that fires after both BullishResearcher and BearishResearcher complete. It reads each researcher's peer-visible soul summary from `lru_cache` (populated at graph creation by `warmup_soul_cache()`) and writes them into `SwarmState["soul_sync_context"]`. Zero LLM calls. Zero filesystem I/O at runtime.

**Graph rewiring** — The existing single fan-in edge `[bullish_researcher, bearish_researcher] → debate_synthesizer` was replaced with a two-edge barrier: `[bullish_researcher, bearish_researcher] → soul_sync_handshake_node → debate_synthesizer`. Parallel researcher fan-out topology is fully preserved.

**USER.md content** — Empathetic refutation few-shots authored for both researchers:
- MOMENTUM (bullish_researcher): 3 examples covering strong CASSANDRA argument, weak CASSANDRA argument, and neutral/conflicted regime
- CASSANDRA (bearish_researcher): 3 examples covering strong MOMENTUM argument, weak MOMENTUM argument, and neutral/conflicted regime

## Test Results

- Phase 18 test suite: **16/16 PASSED** (plan said 14; actual count is 16 after TestUserMdContent 2 tests counted)
- Full core suite: **90/90 PASSED**
- Import boundary law: **14/14 PASSED**
- Graph topology smoke test: PASSED (`compiled ok`)
- Audit exclusion check: PASSED (`excluded ok`)
- USER.md loaded into AgentSoul.users: PASSED (`users loaded: True`)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Made soul_sync_handshake_node synchronous (not async)**
- **Found during:** Task 1 verification
- **Issue:** Test `TestSoulSyncHandshakeNode::test_node_returns_dict` called node without `await`, expecting a dict. An async node returns a coroutine, failing `isinstance(result, dict)` check.
- **Fix:** Changed node function from `async def` to `def`. Pure cache reads require no async I/O; `with_audit_logging` handles sync nodes via `asyncio.to_thread`.
- **Files modified:** `src/graph/nodes/soul_sync_handshake.py`
- **Commit:** 348af04

**2. [Rule 1 - Bug] Fixed TestNoLLMCalls patch target with create=True**
- **Found during:** Task 2 verification
- **Issue:** `patch("src.graph.nodes.soul_sync_handshake.ChatGoogleGenerativeAI")` raised `AttributeError` because the module correctly never imports `ChatGoogleGenerativeAI`. The `patch` default `create=False` fails when the attribute is absent.
- **Fix:** Added `create=True` to the `patch()` call. The test now correctly: (a) creates a mock in the module namespace, (b) runs the node, (c) asserts mock was never called — verifying no LLM invocation.
- **Files modified:** `tests/core/test_soul_sync.py`
- **Commit:** 854a2ce

## Phase 18 Complete

Both TOM-01 and TOM-02 are fully satisfied:
- **TOM-01:** Barrier node exists, graph topology preserved, zero LLM calls, lru_cache reads only
- **TOM-02:** USER.md files present for both researchers, loaded into AgentSoul.users, soul_sync_context: None in initial_state

## Self-Check: PASSED

All created files verified present. Both task commits (348af04, 854a2ce) confirmed in git log.
