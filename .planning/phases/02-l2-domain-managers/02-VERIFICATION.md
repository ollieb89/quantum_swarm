---
phase: 02-l2-domain-managers
verified: 2026-03-05T23:00:00Z
status: passed
score: 14/14 must-haves verified
re_verification: false
human_verification:
  - test: "Run the full debate pipeline end-to-end with a real ANTHROPIC_API_KEY"
    expected: "MacroAnalyst and QuantModeler call the Anthropic API, researchers run their ReAct loops, DebateSynthesizer returns a weighted_consensus_score, and RiskManager approves or rejects accordingly"
    why_human: "All automated tests use mocked LLMs; real API behavior (token limits, tool-call formatting, network errors) cannot be verified programmatically without a live key"
---

# Phase 2: L2 Domain Managers & Adversarial Debate Layer — Verification Report

**Phase Goal:** Migrate MacroAnalyst, QuantModeler, RiskManager to LangGraph subgraphs; implement adversarial debate (bullish/bearish thesis resolution); wire consensus scoring into graph state.
**Verified:** 2026-03-05
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | MacroAnalyst and QuantModeler are wrapped as LangGraph ReAct agents | VERIFIED | `src/graph/agents/analysts.py` — `create_react_agent` singletons compiled at module load; `MacroAnalyst(state)` and `QuantModeler(state)` return `{"messages": [AIMessage(...)]}` |
| 2 | L3 tools are registered and @tool-decorated | VERIFIED | `src/tools/analyst_tools.py` — `fetch_market_data`, `run_backtest`, `fetch_economic_data` all decorated with `@tool` from `langchain_core.tools`; delegate to `DataFetcher` / `Backtester` singletons |
| 3 | Agents use claude-haiku-4-5-20251001 | VERIFIED | `_MODEL_ID = "claude-haiku-4-5-20251001"` set in both `analysts.py` (line 36) and `researchers.py` (line 43) |
| 4 | BullishResearcher and BearishResearcher nodes exist and are importable | VERIFIED | `src/graph/agents/researchers.py` — both node functions confirmed importable; `python -c "from src.graph.agents.researchers import BullishResearcher, BearishResearcher"` exits 0 |
| 5 | Tool budget wrapper limits researchers to max 5 calls | VERIFIED | `BudgetedTool.__call__` raises `ToolBudgetExceeded` when `_call_count >= max_calls`; `test_budget_enforcement` passes |
| 6 | Every researcher tool call requires a hypothesis parameter | VERIFIED | `BudgetedTool.__call__` pops `hypothesis` kwarg and raises `ValueError` if absent or empty; `test_hypothesis_required` passes |
| 7 | Tool-level deduplication reuses cached data | VERIFIED | Module-level `ToolCache` dict; `test_cache_hit` verifies underlying tool called only once for identical args |
| 8 | Neither researcher references execution or order-routing tools | VERIFIED | `researchers.py` imports only `fetch_market_data`, `fetch_economic_data`, `run_backtest`; no `fetch_execute` or `OrderRouter` present |
| 9 | DebateSynthesizer computes weighted_consensus_score and writes to SwarmState | VERIFIED | `src/graph/debate.py` — pure aggregation, no LLM call; returns `{"weighted_consensus_score": float, "debate_history": list}` |
| 10 | Orchestrator wires fan-out/fan-in debate subgraph | VERIFIED | `orchestrator.py` lines 218-224: 4 fan-out edges (both analysts → both researchers), fan-in edge `["bullish_researcher", "bearish_researcher"] → "debate_synthesizer"` |
| 11 | weighted_consensus_score and debate_history fields in SwarmState | VERIFIED | `src/graph/state.py` — both fields present; `python -c "... print('weighted_consensus_score' in s, 'debate_history' in s)"` outputs `True True` |
| 12 | RiskManager node with conditional edge enforcing >0.6 threshold | VERIFIED | `orchestrator.py` `route_after_debate()` at line 150; `add_conditional_edges("debate_synthesizer", route_after_debate, {...})` at line 228-235; strict `score > 0.6` |
| 13 | risk_approved and risk_notes fields in SwarmState | VERIFIED | `src/graph/state.py` — both fields present; `python -c "... 'risk_approved' in s, 'risk_notes' in s"` outputs `True True` |
| 14 | Integration tests pass: overfitting, budget, provenance | VERIFIED | `pytest tests/ -v` — 11/11 tests passed; 3 adversarial debate scenarios, 3 risk gating tests, 3 verification wrapper tests, 2 pre-existing CLI tests |

**Score:** 14/14 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/tools/analyst_tools.py` | Three `@tool`-decorated L3 wrapper functions | VERIFIED | 138 lines; all 3 tools substantive with real delegation to `DataFetcher`/`Backtester`; imported by `analysts.py` and `researchers.py` |
| `src/graph/agents/analysts.py` | MacroAnalyst and QuantModeler ReAct node functions | VERIFIED | 245 lines; both nodes compile sub-graphs at module level, invoke per state, return `{"messages": [AIMessage(...)]}` with correct `name` tag |
| `src/tools/verification_wrapper.py` | BudgetedTool, ToolCache, budgeted() | VERIFIED | 179 lines; `BudgetedTool` enforces budget + hypothesis; `ToolCache` deduplicates; `budgeted()` factory present |
| `src/graph/agents/researchers.py` | BullishResearcher and BearishResearcher node functions | VERIFIED | 392 lines; manual ReAct loop with `BudgetedTool` dispatch; tagged `AIMessage` output (`bullish_research` / `bearish_research`) |
| `src/graph/debate.py` | DebateSynthesizer pure-aggregation node | VERIFIED | 146 lines; extracts researcher messages by name tag, computes character-length strength ratio, returns `weighted_consensus_score` and `debate_history` |
| `src/graph/state.py` | SwarmState with Phase 2 fields | VERIFIED | Contains `weighted_consensus_score: Optional[float]`, `debate_history: Annotated[List[dict], operator.add]`, `risk_approved: Optional[bool]`, `risk_notes: Optional[str]` |
| `src/graph/orchestrator.py` | Full fan-out/fan-in graph, RiskManager, conditional edge | VERIFIED | Imports all 5 real agent nodes; fan-out (4 edges), fan-in (list edge), `add_conditional_edges` on `debate_synthesizer`; `build_graph()` compiles without error |
| `tests/test_verification_wrapper.py` | 3 unit tests | VERIFIED | 3/3 pass: budget enforcement, hypothesis required, cache deduplication |
| `tests/test_risk_gating.py` | 3 routing tests | VERIFIED | 3/3 pass: score=0.8 → risk_manager, score=0.4 → hold, score=0.6 → hold (boundary excluded) |
| `tests/test_adversarial_debate.py` | 3 integration scenario tests | VERIFIED | 3/3 pass: Scenario A (overfitting), Scenario B (budget), Scenario C (provenance) |
| `conftest.py` | sys.path fix for pytest | VERIFIED | Present at repo root; enables `src.*` imports in all test files |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `analysts.py` | `analyst_tools.py` | `from src.tools.analyst_tools import fetch_market_data, fetch_economic_data, run_backtest` | WIRED | Lines 24-28; tools passed directly to `create_react_agent` |
| `researchers.py` | `verification_wrapper.py` | `from src.tools.verification_wrapper import BudgetedTool, budgeted` | WIRED | Line 35; `budgeted()` called inside `_make_budgeted_tools()` |
| `researchers.py` | `analyst_tools.py` | `from src.tools.analyst_tools import ...` | WIRED | Lines 30-34; 3 tools wrapped with `budgeted()` and dispatched in ReAct loop |
| `orchestrator.py` | `analysts.py` | `from .agents.analysts import MacroAnalyst, QuantModeler` | WIRED | Line 12; both registered as graph nodes at lines 185-186 |
| `orchestrator.py` | `researchers.py` | `from .agents.researchers import BullishResearcher, BearishResearcher` | WIRED | Line 13; both registered as graph nodes at lines 190-191 |
| `orchestrator.py` | `debate.py` | `from .debate import DebateSynthesizer` | WIRED | Line 14; registered as graph node at line 195 |
| `debate_synthesizer` → `risk_manager` | Conditional edge | `route_after_debate(state["weighted_consensus_score"] > 0.6)` | WIRED | `add_conditional_edges` at line 228; routing function at line 150 |
| `DebateSynthesizer` | `SwarmState["weighted_consensus_score"]` | `return {"weighted_consensus_score": score, "debate_history": ...}` | WIRED | `debate.py` line 142; field present in `SwarmState` with `Optional[float]` type |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REQ-02-01 | 02-01 | MacroAnalyst and QuantModeler as LangGraph ReAct agents with L3 tools | SATISFIED | `analysts.py` + `analyst_tools.py`; `create_react_agent` with correct tool sets; model `claude-haiku-4-5-20251001` |
| REQ-02-02 | 02-02 | Adversarial researcher nodes with tool budgeting, hypothesis gating, deduplication | SATISFIED | `researchers.py` + `verification_wrapper.py`; `BudgetedTool` enforces all three constraints; 3 unit tests pass |
| REQ-02-03 | 02-03 | DebateSynthesizer node, fan-out/fan-in wiring, weighted_consensus_score in SwarmState | SATISFIED | `debate.py` + `orchestrator.py`; fan-out (4 edges), fan-in (list edge), score written to state |
| REQ-02-04 | 02-04 | RiskManager as LangGraph node with conditional edge at >0.6 threshold | SATISFIED | `risk_manager_node` in `orchestrator.py`; `route_after_debate` with strict `> 0.6`; 3 routing tests pass |
| REQ-02-05 | 02-05 | Integration test suite: overfitting, budget, provenance scenarios | SATISFIED | `tests/test_adversarial_debate.py`; 3/3 scenarios pass; 11/11 total tests pass with no regressions |

---

## Anti-Patterns Found

| File | Lines | Pattern | Severity | Impact |
|------|-------|---------|----------|--------|
| `src/graph/orchestrator.py` | 43-65 | Three stale placeholder functions (`macro_analyst_node`, `quant_modeler_node`, `debate_synthesizer_node`) with `{"status": "pending_implementation"}` returns exist as dead code | Warning | Not registered in the graph; real implementations used instead. No runtime impact, but naming could cause future confusion. |
| `src/graph/agents/analysts.py` | 45, 60 | `create_react_agent` imported from `langgraph.prebuilt` — deprecated since LangGraph V1.0; correct import is `from langchain.agents import create_react_agent` | Warning | Emits `LangGraphDeprecatedSinceV10` warning in test output; will break in LangGraph V2.0 |

No blocker anti-patterns found. Both items are cosmetic warnings.

---

## Human Verification Required

### 1. Live API End-to-End Run

**Test:** With `ANTHROPIC_API_KEY` set, invoke `LangGraphOrchestrator.run_task("Should I buy BTC today?")` with intent `"analysis"` routed to `quant_modeler`.
**Expected:** QuantModeler calls the Anthropic API, BullishResearcher and BearishResearcher complete their ReAct loops (respecting the 5-call budget), DebateSynthesizer computes a non-zero `weighted_consensus_score`, and RiskManager produces a `risk_approved` decision. No uncaught exceptions.
**Why human:** All automated tests mock the LLM. Real tool-call formatting, token limits, and API errors are outside the scope of the existing test suite.

---

## Summary

All 14 must-haves from the five plan `must_haves` blocks are verified. The phase goal is fully achieved:

- **MacroAnalyst and QuantModeler** are substantive LangGraph ReAct agents wired into the graph (not placeholders). REQ-02-01 satisfied.
- **Adversarial researchers** (BullishResearcher, BearishResearcher) implement genuine directional pressure with enforced tool budgets, mandatory hypothesis logging, and deduplication caching. REQ-02-02 satisfied.
- **DebateSynthesizer** is a pure aggregation node that computes `weighted_consensus_score` from researcher output strength; fan-out/fan-in correctly wired in the orchestrator. REQ-02-03 satisfied.
- **RiskManager** validates debate provenance and gates execution via a strict `> 0.6` conditional edge. REQ-02-04 satisfied.
- **Integration test suite** (11/11 passing) covers all three validation scenarios with zero regressions. REQ-02-05 satisfied.

Two warning-level anti-patterns exist: stale placeholder functions in `orchestrator.py` (dead code, not wired) and a deprecated `create_react_agent` import path. Neither blocks goal achievement.

---

_Verified: 2026-03-05_
_Verifier: Claude (gsd-verifier)_
