---
phase: 02-l2-domain-managers
plan: "02-03"
subsystem: agents
tags: [langgraph, debate, consensus, fan-out, fan-in, aggregation, orchestrator]

# Dependency graph
requires:
  - phase: 02-l2-domain-managers
    plan: "02-01"
    provides: MacroAnalyst and QuantModeler node functions
  - phase: 02-l2-domain-managers
    plan: "02-02"
    provides: BullishResearcher and BearishResearcher node functions
provides:
  - src/graph/debate.py with DebateSynthesizer pure-aggregation node
  - Wired fan-out/fan-in debate subgraph in orchestrator.py
  - weighted_consensus_score and debate_history fields in SwarmState
  - build_graph() convenience function in orchestrator.py
affects:
  - 02-04-risk-gating (reads weighted_consensus_score to decide execution)
  - downstream risk manager and synthesize nodes

# Tech tracking
tech-stack:
  added:
    - DebateSynthesizer (pure-aggregation node, no LLM calls)
    - LangGraph fan-out pattern: add_edge(analyst, researcher) x4 (parallel execution)
    - LangGraph fan-in pattern: add_edge([bullish_researcher, bearish_researcher], debate_synthesizer)
  patterns:
    - Pure aggregation node pattern: deterministic, no LLM, reads tagged AIMessages from state
    - Strength proxy scoring: character length as heuristic for evidence density (replaceable)
    - Fan-out: multiple edges from one node to N parallel nodes
    - Fan-in: add_edge(list_of_nodes, single_node) waits for ALL sources before proceeding

key-files:
  created:
    - src/graph/debate.py
  modified:
    - src/graph/state.py
    - src/graph/orchestrator.py

key-decisions:
  - "DebateSynthesizer uses character length as strength proxy — deterministic, no LLM call, replaceable heuristic"
  - "Fan-out implemented via 4 edges (both analysts to both researchers) — LangGraph executes parallel branches natively"
  - "Fan-in implemented via add_edge(['bullish_researcher', 'bearish_researcher'], 'debate_synthesizer') — waits for both"
  - "build_graph() added as no-config alias to create_orchestrator_graph({}) for easy graph verification"
  - "UserWarning on config typing in existing placeholder nodes is pre-existing and cosmetic — not touched (out of scope)"

patterns-established:
  - "Aggregation node pattern: read tagged AIMessages by name attribute, compute score, return state update dict"
  - "Debate history provenance: each entry carries source, hypothesis, evidence text, and computed strength"

requirements-completed:
  - REQ-02-03

# Metrics
duration: 2min
completed: 2026-03-05
---

# Phase 02 Plan 03: Debate Synthesis Summary

**DebateSynthesizer aggregation node wired into orchestrator with LangGraph fan-out/fan-in, computing weighted_consensus_score from bullish/bearish researcher text strength**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-05T22:23:38Z
- **Completed:** 2026-03-05T22:25:43Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Added `weighted_consensus_score: Optional[float]` and `debate_history: Annotated[List[dict], operator.add]` to `SwarmState`
- Created `src/graph/debate.py` with `DebateSynthesizer` — a pure aggregation node (no LLM calls) that extracts tagged researcher messages, computes a strength-weighted consensus score, and builds a provenance-rich debate history
- Wired the full fan-out/fan-in debate subgraph in `orchestrator.py`: both analysts fan out to both researchers in parallel; fan-in waits for both researchers to complete before passing to `DebateSynthesizer`; added `build_graph()` convenience function

## Task Commits

Each task was committed atomically:

1. **Task 1: Add weighted_consensus_score and debate_history to SwarmState** - `459900e` (feat)
2. **Task 2: Create debate.py with DebateSynthesizer node** - `f8175e1` (feat)
3. **Task 3: Wire fan-out and fan-in into orchestrator.py** - `34cf6af` (feat)

## Files Created/Modified

- `src/graph/state.py` - Added `weighted_consensus_score: Optional[float]` and `debate_history: Annotated[List[dict], operator.add]` fields
- `src/graph/debate.py` - `DebateSynthesizer` node: extracts `bullish_research`/`bearish_research` AIMessages, computes consensus score via character-length strength proxy, returns `weighted_consensus_score` and `debate_history`
- `src/graph/orchestrator.py` - Imports all 5 real agent node functions; wires fan-out (analysts → researchers) and fan-in (researchers → synthesizer); adds `build_graph()` alias; updates initial state dict with new fields

## Decisions Made

- Used character length as the bullish/bearish strength proxy — completely deterministic, no LLM needed in the synthesizer, and easy to swap for a more sophisticated signal (e.g., evidence count parsing) in a future plan without changing the interface
- Fan-out wired with 4 individual edges (macro_analyst → bullish, macro_analyst → bearish, quant_modeler → bullish, quant_modeler → bearish) to handle both intent routing paths (analysis routes to quant_modeler, macro routes to macro_analyst)
- Fan-in uses `add_edge(["bullish_researcher", "bearish_researcher"], "debate_synthesizer")` — LangGraph waits for ALL listed sources before executing the target node
- `build_graph()` added as a zero-config entry point matching the plan's verification command signature

## Deviations from Plan

None — plan executed exactly as written.

Note: LangGraph emits `UserWarning` about `config` parameter typing on the existing placeholder nodes (`classify_intent`, `risk_manager`, `synthesize`). This is a pre-existing cosmetic warning from Phase 1 — not introduced by this plan, not touched (out of scope per deviation rules).

## Issues Encountered

None — all three tasks completed cleanly.

## User Setup Required

None — no external service configuration required for this plan. The synthesizer node itself makes no API calls. An `ANTHROPIC_API_KEY` is required when running the full debate loop end-to-end (analyst and researcher nodes do call the Anthropic API), but not for import verification or graph compilation.

## Next Phase Readiness

- `DebateSynthesizer` writes `weighted_consensus_score` to `SwarmState` — ready to be consumed by the Risk Manager gating node in plan 02-04
- `debate_history` provides full provenance for audit and compliance use cases
- Graph compiles cleanly with all Phase 2 nodes wired; plan 02-04 can add risk gating edges after `debate_synthesizer` without restructuring anything
- No blockers for 02-04 (Risk Gating — reads `weighted_consensus_score` to approve/reject execution)

---
*Phase: 02-l2-domain-managers*
*Completed: 2026-03-05*

## Self-Check: PASSED

| Item | Status |
|------|--------|
| src/graph/state.py | FOUND |
| src/graph/debate.py | FOUND |
| src/graph/orchestrator.py | FOUND |
| .planning/phases/02-l2-domain-managers/02-03-SUMMARY.md | FOUND |
| commit 459900e (Task 1) | FOUND |
| commit f8175e1 (Task 2) | FOUND |
| commit 34cf6af (Task 3) | FOUND |
