---
phase: 02-l2-domain-managers
plan: "02-02"
subsystem: agents
tags: [langgraph, langchain, react-agent, anthropic, claude-haiku, tool-budgeting, adversarial-debate, caching]

# Dependency graph
requires:
  - phase: 02-l2-domain-managers
    plan: "02-01"
    provides: analyst_tools.py @tool functions (fetch_market_data, run_backtest, fetch_economic_data), MacroAnalyst and QuantModeler node functions
provides:
  - src/tools/verification_wrapper.py with BudgetedTool, ToolCache, budgeted() factory
  - src/graph/agents/researchers.py with BullishResearcher and BearishResearcher LangGraph node functions
  - tests/test_verification_wrapper.py with 3 passing pytest unit tests
affects:
  - 02-03-orchestrator-integration
  - debate-synthesizer

# Tech tracking
tech-stack:
  added:
    - BudgetedTool (custom class wrapping @tool callables with call budget enforcement)
    - ToolCache (module-level frozenset-keyed deduplication cache)
    - langchain_core.messages.ToolMessage (used in ReAct tool dispatch loop)
  patterns:
    - Adversarial researcher pattern: two independent agents verify conclusions from opposite hypotheses
    - Manual ReAct loop pattern: bind_tools() for schema, BudgetedTool dispatch for execution
    - Per-invocation budget reset: create fresh BudgetedTool instances inside node function to reset call counters
    - Tool deduplication: module-level ToolCache reuses analyst-fetched data for identical researcher calls

key-files:
  created:
    - src/tools/verification_wrapper.py
    - src/graph/agents/researchers.py
    - tests/test_verification_wrapper.py
  modified: []

key-decisions:
  - "Manual ReAct loop chosen over create_react_agent so BudgetedTool instances (with per-invocation counters) are dispatched directly"
  - "BudgetedTool instances created fresh inside node functions to guarantee counter resets per graph invocation"
  - "ToolCache keyed by (tool_name, frozenset(args)) enabling cross-agent deduplication within same Python process"
  - "hypothesis kwarg popped before forwarding to underlying tool — analyst tools do not accept it"

patterns-established:
  - "Budget wrapper pattern: BudgetedTool wraps any callable, enforces N-call budget, requires hypothesis kwarg"
  - "Adversarial node pattern: extract prior analyst context from state messages, run manual ReAct, tag AIMessage with role name"

requirements-completed:
  - REQ-02-02

# Metrics
duration: 3min
completed: 2026-03-05
---

# Phase 02 Plan 02: Adversarial Researcher Nodes Summary

**BullishResearcher and BearishResearcher ReAct nodes with per-invocation tool budget (max 5 calls), mandatory hypothesis logging, and module-level deduplication cache reusing analyst-fetched data**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-05T22:18:42Z
- **Completed:** 2026-03-05T22:21:20Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Created `src/tools/verification_wrapper.py` with `BudgetedTool` (enforces N-call limit, requires hypothesis kwarg), `ToolCache` (frozenset-keyed deduplication dict), and `budgeted()` factory
- Created `src/graph/agents/researchers.py` with `BullishResearcher` (finds supporting evidence) and `BearishResearcher` (finds refuting evidence) as LangGraph node functions using claude-haiku-4-5-20251001; neither agent references execution or order-routing tools
- Created `tests/test_verification_wrapper.py` with 3 pytest tests; all pass: budget enforcement, hypothesis requirement, and cache deduplication

## Task Commits

Each task was committed atomically:

1. **Task 1: Create verification_wrapper.py with BudgetedTool and cache layer** - `1b324f7` (feat)
2. **Task 2: Create researchers.py with BullishResearcher and BearishResearcher nodes** - `38e9be4` (feat)
3. **Task 3: Verify budget enforcement with a unit test** - `be45b47` (test)

## Files Created/Modified

- `src/tools/verification_wrapper.py` - BudgetedTool class, ToolCache dict, and budgeted() factory for wrapping analyst tools with call budget enforcement and hypothesis gating
- `src/graph/agents/researchers.py` - BullishResearcher and BearishResearcher LangGraph node functions with manual ReAct loop, budgeted tool dispatch, and tagged AIMessage output
- `tests/test_verification_wrapper.py` - Pytest unit tests covering budget enforcement, hypothesis requirement, and cache deduplication

## Decisions Made

- Used a manual ReAct loop inside `_run_researcher_agent()` rather than `create_react_agent` so that `BudgetedTool` instances (with per-invocation call counters) can be dispatched directly without being re-wrapped by LangGraph internals
- Fresh `BudgetedTool` instances created inside each node function call to guarantee the call counter resets per graph invocation; stale counters would silently block valid calls
- `hypothesis` kwarg is popped from kwargs before forwarding to the underlying tool — analyst tools (`fetch_market_data`, etc.) do not accept this parameter
- `ToolCache` keyed by `(tool_name, frozenset(args))` enables deduplication across both researchers within the same Python process; cache is intentionally module-level and persists across invocations

## Deviations from Plan

None — plan executed exactly as written.

Minor note: `pytest` was not installed in the project's `.venv`; installed it (Rule 3 auto-fix) to run the verification command. The venv Python must be used for all verifications (`python` system binary does not have project dependencies).

## Issues Encountered

- System Python (`/usr/bin/python`) lacks project dependencies; all import verifications and pytest runs require `.venv/bin/python`. This was resolved per-command — no files modified.

## User Setup Required

None — no external service configuration required for this plan.
An `ANTHROPIC_API_KEY` environment variable is needed when running researcher agents against the live API (future integration test phase), but is not needed for import verification or unit tests.

## Next Phase Readiness

- `BullishResearcher` and `BearishResearcher` are importable and return tagged AIMessage findings ready for a `DebateSynthesizer` node to consume
- `BudgetedTool` and `ToolCache` are general utilities usable by any future researcher-type agent
- No blockers for 02-03 (Orchestrator Integration — wiring all agents into the StateGraph)

---
*Phase: 02-l2-domain-managers*
*Completed: 2026-03-05*

## Self-Check: PASSED

| Item | Status |
|------|--------|
| src/tools/verification_wrapper.py | FOUND |
| src/graph/agents/researchers.py | FOUND |
| tests/test_verification_wrapper.py | FOUND |
| .planning/phases/02-l2-domain-managers/02-02-SUMMARY.md | FOUND |
| commit 1b324f7 (Task 1) | FOUND |
| commit 38e9be4 (Task 2) | FOUND |
| commit be45b47 (Task 3) | FOUND |
