# Implementation Plan: Phase 2 - L2 Domain Managers & Adversarial Debate Layer

**Project:** Quantum Swarm LangGraph Migration
**Phase:** 2 (L2 Domain Managers & Adversarial Debate)
**Date:** 2026-03-05
**Status:** Ready for Execution

---

## ## Approach
- **Why this solution:** Migrating L2 Domain Managers to LangGraph ReAct agents using `claude-haiku-4-5-20251001` provides structured tool use and autonomous reasoning at a low cost. The addition of the **Adversarial Debate Layer** (Bullish/Bearish Researchers) using **Approach 2 (Independent Verification Toolset)** ensures robust validation. By allowing researchers to pull their own primary data (with budgets and hypothesis-driven logging), we catch "blind spots" and confirmation bias that a consensus-only model would miss.
- **Alternatives considered:**
    - *Reasoning-only researchers (Option A):* Rejected. Limits the ability to catch data-driven errors or analyst cherry-picking.
    - *Shared Blackboard (Approach 1):* Kept as a baseline caching/evidence log, but upgraded with independent fetch rights to ensure true adversarial pressure.

---

## ## Steps

### 1. Implement L2 Analyst Agents (120 min)
- [ ] **Files to create:** `src/graph/agents/analysts.py`, `src/tools/analyst_tools.py`
- [ ] **Core Implementation:**
    - [ ] Wrap `MacroAnalyst` and `QuantModeler` as LangGraph ReAct agents.
    - [ ] Register L3 tools: `fetch_market_data`, `run_backtest`, `fetch_economic_data`.
    - [ ] Use `claude-haiku-4-5-20251001` for superior tool-calling performance.

### 2. Adversarial Researcher Nodes & Permission Schema (180 min)
- [ ] **Files to create:** `src/graph/agents/researchers.py`, `src/tools/verification_wrapper.py`
- [ ] **Implementation:**
    - [ ] Create `BullishResearcher` and `BearishResearcher` nodes.
    - [ ] **Tool Budgeting:** Implement a wrapper that restricts researchers to 3–5 primary fetches each.
    - [ ] **Hypothesis Gating:** Enforce a `hypothesis` parameter for all researcher tool calls (logged to `SwarmState`).
    - [ ] **Caching Layer:** Implement tool-level deduplication to reuse analyst-fetched data when identical.

### 3. Debate Synthesis & Conflict Resolution (90 min)
- [ ] **Files to modify:** `src/graph/orchestrator.py`, `src/graph/debate.py`
- [ ] **Implementation:**
    - [ ] Update graph to route analyst outputs to both researchers in parallel (`fan-out`).
    - [ ] Implement `DebateSynthesizer` node to resolve conflicting theses into a net position.
    - [ ] Calculate `weighted_consensus_score` (Strength of Analyst Signal - Strength of Researcher Counter-arguments).

### 4. Risk Gating & Execution Wiring (60 min)
- [ ] **Files to modify:** `src/graph/orchestrator.py`
- [ ] **Implementation:**
    - [ ] Migrate `RiskManager` to a LangGraph node.
    - [ ] Implement a conditional edge: `debate_synthesizer` -> `risk_manager` (if consensus > 0.6) -> `execute`.
    - [ ] Ensure Risk Manager receives the full debate history (provenance) for final validation.

### 5. Testing & Validation (120 min)
- [ ] **Test files to create:** `tests/test_adversarial_debate.py`
- [ ] **Validation Scenarios:**
    - [ ] **Scenario A (Overfitting):** Provide a Quant proposal with high confidence but poor macro data. Verify `BearishResearcher` fetches macro data and lowers consensus.
    - [ ] **Scenario B (Budget):** Verify the system halts researcher fetches after the 5th call.
    - [ ] **Scenario C (Provenance):** Ensure `SwarmState` contains the hypothesis for every researcher fetch.

---

## ## Timeline
| Phase | Duration |
| :--- | :--- |
| 1. L2 Analysts | 120 min |
| 2. Adversarial Layer | 180 min |
| 3. Debate Synthesis | 90 min |
| 4. Risk Gating | 60 min |
| 5. Testing | 120 min |
| **Total** | **9.5 hours** |

---

## ## Rollback Plan
1. **Fallback:** Disable the `Bullish/BearishResearcher` nodes in `orchestrator.py` and route analysts directly to `synthesize`.
2. **Revert:** Revert `SwarmState` to remove thesis fields and restore the sequential PoC graph.

---

## ## Security Checklist
- [ ] [**Budgeting**] Tool budget prevents recursive loop / API cost spikes.
- [ ] [**Gating**] Researchers are strictly prohibited from accessing `OrderRouter` (execute) tools.
- [ ] [**Logging**] All hypothesis-driven fetches are stored in the state history for post-mortem analysis.

## NEXT STEPS
```bash
# Phase 2 Plan Ready. Proceed to Implementation?
/cook @plans/phase-2-implementation-20260305.md
```
