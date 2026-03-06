# Architecture

**Analysis Date:** 2025-03-05

## Pattern Overview

**Overall:** 3-Level Hierarchical Swarm with Adversarial Debate

**Key Characteristics:**
- **Hierarchical Orchestration:** Level 1 (Strategic) → Level 2 (Domain Managers) → Level 3 (Specialized Workers).
- **Adversarial Debate:** L3 Researchers (Bullish vs. Bearish) perform adversarial analysis to mitigate hallucination and bias.
- **Asynchronous LangGraph Flow:** Uses LangGraph to manage complex, stateful agent interactions and parallel execution.
- **Hybrid Technology Stack:** Python-based swarm orchestration with a TypeScript/Bun bridge to the Dexter fundamental analysis agent.

## Layers

**Level 1: Strategic Orchestrator:**
- Purpose: Entry point for user requests; handles intent classification and task decomposition.
- Location: `src/orchestrator/strategic_l1.py` and `src/graph/orchestrator.py`
- Contains: Intent classification logic, task routing, and final consensus synthesis.
- Depends on: Level 2 Agents, LangGraph State.
- Used by: End users via CLI or Dashboard.

**Level 2: Domain Managers (Analysts):**
- Purpose: Specialized reasoning for specific financial domains (Macro, Quant).
- Location: `src/graph/agents/analysts.py`
- Contains: `MacroAnalyst` and `QuantModeler` ReAct agents.
- Depends on: Level 3 Workers for data and research.
- Used by: Level 1 Orchestrator.

**Level 3: Specialized Workers (Executors/Researchers):**
- Purpose: Stateless workers for technical tasks like data fetching, backtesting, and deep research.
- Location: `src/graph/agents/researchers.py`, `src/graph/agents/l3/data_fetcher.py`, and `src/agents/l3_executor.py`
- Contains: `BullishResearcher`, `BearishResearcher`, `DataFetcher`, `OrderRouter`.
- Depends on: External APIs (YFinance, CCXT, News, Dexter).
- Used by: Level 1 or Level 2 agents.

## Data Flow

**Standard Trading Intent Flow:**

1. **Intent Classification:** L1 (`src/graph/orchestrator.py:classify_intent`) identifies "trade" or "analysis" intent.
2. **Domain Analysis:** L2 Agents (`MacroAnalyst`, `QuantModeler`) generate initial domain-specific reports.
3. **Adversarial Research (Fan-out):** `BullishResearcher` and `BearishResearcher` execute in parallel to find evidence for and against the proposed trade.
4. **Data Enrichment:** `DataFetcher` (`src/graph/agents/l3/data_fetcher.py`) retrieves live market, sentiment, and fundamental data (via Dexter).
5. **Debate Synthesis (Fan-in):** `DebateSynthesizer` (`src/graph/debate.py`) weighs all research and calculates a consensus score.
6. **Risk Gating:** `RiskManager` (`src/graph/orchestrator.py:risk_manager_node`) performs final validation against risk limits.
7. **Decision Execution:** Final node synthesizes the result; future phases will integrate `OrderRouter` for execution.

**State Management:**
- **SwarmState:** Centralized state managed by LangGraph (`src/graph/state.py`).
- **Persistence:** Checkpointing via `MemorySaver` in LangGraph.

## Key Abstractions

**Dexter Bridge:**
- Purpose: Async wrapper to invoke the TypeScript Dexter agent for deep fundamental research.
- Examples: `src/tools/dexter_bridge.py`
- Pattern: Asynchronous subprocess execution using `bun run`.

**L3 Executor Interface:**
- Purpose: Standard interface for stateless workers.
- Examples: `src/agents/l3_executor.py`
- Pattern: Factory pattern for creating specialized executors.

## Entry Points

**CLI Wrapper:**
- Location: `src/core/cli_wrapper.py`
- Triggers: User commands.
- Responsibilities: Standardizing agent communication and file-based protocol.

**LangGraph Orchestrator:**
- Location: `src/graph/orchestrator.py`
- Triggers: Called by `main.py` or `LangGraphOrchestrator` wrapper.
- Responsibilities: Compiling and executing the SwarmState graph.

## Error Handling

**Strategy:** Graceful degradation with fallback mechanisms.

**Patterns:**
- **Dexter Safe Wrapper:** `invoke_dexter_safe` in `src/tools/dexter_bridge.py` catches all process errors and returns a failure reason instead of crashing.
- **Risk Veto:** `RiskManager` can veto any decision if consensus is low or risk parameters are breached.

## Cross-Cutting Concerns

**Logging:** Centralized logging to `data/logs/` and STDOUT using standard Python `logging`.
**Validation:** Pydantic models in `src/models/data_models.py` for structured data validation.
**Memory:** Long-term patterns stored in `data/MEMORY.md` for RAG-like context retrieval.

---

*Architecture analysis: 2025-03-05*
