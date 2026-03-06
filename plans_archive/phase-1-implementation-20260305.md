# Implementation Plan: Phase 1 - Core Orchestration Migration (L1 Orchestrator)

**Project:** Quantum Swarm LangGraph Migration
**Phase:** 1 (L1 Orchestrator Migration)
**Date:** 2026-03-05
**Status:** Completed

---

## ## Approach
- **Why this solution:** Replacing the custom `StrategicOrchestrator` with a LangGraph `StateGraph` enables built-in state management, checkpoint persistence, and the structured "adversarial debate" pattern from the TradingAgents architecture. This approach ensures the orchestrator is no longer just a script but a robust, stateful engine.
- **Alternatives considered:**
  - *Directly porting current Python methods:* Rejected. LangGraph nodes and conditional edges provide better decoupling and error recovery.
  - *Stateless Orchestration:* Rejected. Long-running financial analysis requires persistence (checkpoints) to recover from API failures.

---

## ## Steps

### 1. Define Swarm State & Initial Structure (30 min)
- [x] **Files to create:** `src/graph/state.py`, `src/graph/__init__.py`
- [x] **Core Implementation:**
  ```python
  import operator
  from typing import Annotated, List, TypedDict, Optional

  class SwarmState(TypedDict):
      task_id: str
      intent: str
      messages: Annotated[List[dict], operator.add]
      macro_report: Optional[dict]
      quant_proposal: Optional[dict]
      bullish_thesis: Optional[dict]
      bearish_thesis: Optional[dict]
      debate_resolution: Optional[dict]
      risk_approval: Optional[dict]
      consensus_score: float
      compliance_flags: List[str]
      final_decision: Optional[dict]
  ```

### 2. Implement L1 Nodes & Routing Logic (90 min)
- [x] **Files to create:** `src/graph/orchestrator.py`
- [x] **Nodes to implement:**
  - [x] `classify_intent`: Uses `claude-sonnet-4-20250514` (mocked with pattern matching for PoC) to determine if input is `trade`, `macro`, `analysis`, or `risk`.
  - [x] `route_by_intent`: Conditional edge logic that directs the graph based on the intent field in state.
  - [x] `synthesize_consensus`: Aggregates analyst reports and debate resolutions into a final decision.
  - [x] `execute_trade`: Node that interacts with `src/agents/l3_executor.py:OrderRouter`.

### 3. Build the Orchestrator Graph (90 min)
- [x] **Implementation:** Wire the nodes together using the `StateGraph` and `conditional_edges` as designed in the `docs/agentic_Framework_implementation.md`.
- [x] **Checkpointing:** Integrate `langgraph.checkpoint.memory.MemorySaver` for in-memory persistence (to be replaced with Postgres/Redis in Phase 5).

### 4. Integration with OpenClaw & Main (60 min)
- [x] **Files to modify:** `main.py`
- [x] **Implementation:** 
  - [x] Update the `QuantumSwarm` class to initialize the compiled LangGraph app.
  - [x] Bridge `OpenClawCLI` into the graph context as a configuration parameter.
  - [x] Ensure the `main.py` entry point correctly invokes the graph.

### 5. Testing & Validation (90 min)
- [x] **Test files to create:** `tests/test_graph_orchestrator.py` (PoC script used)
- [x] **Requirements:** 
  - [x] Validate intent routing (e.g., "Buy BTC" -> `trade` route).
  - [x] Validate consensus gating (e.g., low consensus score -> `REJECT`).
  - [x] Verify that `messages` history is correctly accumulated across nodes.

---

## ## Timeline
| Phase | Duration |
|-------|----------|
| 1. State Definition | 30 min |
| 2. Node Implementation | 90 min |
| 3. Graph Wiring | 90 min |
| 4. Main Integration | 60 min |
| 5. Testing | 90 min |
| **Total** | **6 hours** |

---

## ## Rollback Plan
1. **Fallback Strategy:** Keep `src/orchestrator/strategic_l1.py` as `strategic_l1_legacy.py`.
2. **Revert:** In `main.py`, switch the orchestrator initialization back to the legacy class if the graph fails to compile or route correctly.
3. **Rollback Step:** Delete `src/graph/` and revert `main.py` changes.

---

## ## Security Checklist
- [x] **Credential Protection:** Ensure `messages` history in `SwarmState` does not store API tokens or plain-text credentials.
- [x] **Risk Gating:** Verify that the `execute_trade` node is unreachable if `risk_approval` is False.
- [x] **Input Validation:** Sanitize user input before it enters the `classify_intent` node.

---

## NEXT STEPS
```bash
# Phase 1 Complete. Proceed to Phase 2: L2 Domain Managers & Adversarial Debate Layer.
/cook @plans/phase-2-implementation-YYYYMMDD.md
```
