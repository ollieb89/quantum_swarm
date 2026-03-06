# Implementation Plan: Phase 0 - LangGraph Migration Assessment & Setup

**Project:** Quantum Swarm LangGraph Migration
**Phase:** 0 (Assessment & Setup)
**Date:** 2026-03-05
**Status:** Completed

---

## ## Approach
- **Phase 0 Strategy:** This is a "Research and Foundation" phase. The goal is to move from custom orchestration (`strategic_l1.py`) to a structured, stateful LangGraph workflow.
- **Why this solution:** LangGraph provides the necessary primitives for adversarial debate (bullish vs. bearish), checkpoint-based persistence (vital for long-running financial analysis), and clear agent-to-tool delegation. NautilusTrader provides a robust, production-grade backtesting and execution engine that replaces custom, less-tested logic.
- **Alternatives considered:**
  - *Direct Migration (Phase 1 first):* Rejected. High risk of breaking the existing system without first verifying the LangGraph + NautilusTrader integration.
  - *AutoGPT/CrewAI:** Rejected. LangGraph's control flow and state management are more suitable for the rigorous, multi-level hierarchy of the Quantum Swarm (HMAS-2).

---

## ## Steps

### 1. Dependency Installation & Environment Prep (15 min)
- [x] **Install packages:**
  ```bash
  pip install langgraph langchain-anthropic langchain-community nautilus_trader
  ```
- [x] **Configure LangSmith (Optional but Recommended):**
  - Create a `.env` file (if not exists) with:
    - `LANGCHAIN_TRACING_V2=true`
    - `LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"`
    - `LANGCHAIN_API_KEY="your_api_key"`
- [x] **Verify existing compatibility:** Run a smoke test to ensure `yfinance` and `ccxt` still function alongside the new libraries.

### 2. Codebase Audit & Migration Mapping (45 min)
- [x] **Map Orchestrator:** Document how the rules in `src/orchestrator/strategic_l1.py` will translate to LangGraph conditional edges.
- [x] **Audit Skills:** List all skills in `src/skills/` and identify which ones can be directly wrapped as LangChain `@tool`s.
- [x] **Analyze State:** Define the `SwarmState` TypedDict to include all necessary fields for the adversarial debate layer (bullish_thesis, bearish_thesis, debate_resolution, risk_approval).

### 3. Adversarial Debate Layer Design (30 min)
- [x] **Structure:**
  - `L1 Supervisor`: Classifies intent and routes to Analysts.
  - `L2 Analysts (Macro/Quant)`: Perform analysis and output data.
  - `Adversarial Layer (Bullish/Bearish Researchers)`: These agents will consume Analyst outputs and debate the trade's validity.
  - `Debate Synthesizer`: Resolves conflict into a net position with weighted confidence.
  - `Risk Manager`: Final gating.
- [x] **Model Selection:** Confirm `claude-haiku-4-5-20251001` for L2 and Debate agents.

### 4. PoC: LangGraph L1 -> L2 Delegation (60 min)
- [x] **File:** `src/poc/langgraph_orchestrator_poc.py`
- [x] **Goal:** Demonstrate the supervisor pattern delegating to two mock analyst nodes.
- [x] **Key Success Metric:** Messages correctly flow from L1 to L2 and return to L1 for final synthesis.

### 5. PoC: NautilusTrader Integration (60 min)
- [x] **File:** `src/poc/nautilus_integration_poc.py`
- [x] **Goal:** Initialize the `BacktestEngine`, load a minimal data set, and execute a trivial trade.
- [x] **Check:** Ensure the NautilusTrader output (PnL, Drawdown) can be parsed back into the `SwarmState`.

### 6. Phase 0 Wrap-up & Reporting (30 min)
- [x] **Deliverable:** Update `docs/agentic_Framework_implementation.md` with status updates and findings.
- [x] **Action:** Refine Phase 1 tasks in the master implementation plan based on PoC outcomes.

---

## ## Timeline
| Phase | Duration |
|-------|----------|
| 1. Dependency Setup | 15 min |
| 2. Audit & Mapping | 45 min |
| 3. Pattern Research | 30 min |
| 4. LangGraph PoC | 60 min |
| 5. NautilusTrader PoC | 60 min |
| 6. Reporting | 30 min |
| **Total** | **4 hours** |

---

## ## Rollback Plan
1. **Dependency Revert:** `pip uninstall langgraph nautilus_trader` and restore original `requirements.txt`.
2. **File Cleanup:** Remove all files in `src/poc/`.
3. **Configuration:** Revert `.env` changes related to LangChain.

---

## ## Security Checklist
- [x] **Credential Safety:** Do not commit `.env` or any hardcoded API keys.
- [x] **Risk Gating:** Ensure NautilusTrader's internal risk engine is configured with conservative limits in PoC.
- [x] **Monitoring:** Verify LangSmith tracing does not leak sensitive trade data.

---

## NEXT STEPS
```bash
# Ready for Phase 1?
/cook @plans/phase-1-implementation-YYYYMMDD.md
```
