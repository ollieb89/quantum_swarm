# Architecture Patterns: Multi-Agent Financial Swarms

**Domain:** Quantitative Finance / Multi-Agent Systems
**Researched:** 2026-03-05
**Project:** Quantum Swarm

## Recommended Architecture

The Quantum Swarm follows a **Hierarchical Orchestration** pattern (L1/L2/L3) implemented using an asynchronous directed acyclic graph (DAG) via **LangGraph**. This structure ensures clear separation between high-level strategy, domain-specific analysis, and stateless execution.

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **L1: Strategic Orchestrator** | Intent classification, task routing, final consensus synthesis. | User (via OpenClaw), L2 Domain Managers. |
| **L2: Domain Managers** | Specialized analysis (Macro, Quant). Translates strategy into tactical hypotheses. | L1 Orchestrator, L2 Researchers. |
| **L2: Adversarial Layer** | Parallel "Bullish" vs "Bearish" research to prevent confirmation bias. | L2 Domain Managers, Debate Synthesizer. |
| **L2: Risk Manager** | Final veto power. Validates proposals against hard constraints and provenance. | Debate Synthesizer, L3 Executors. |
| **L3: Stateless Executors** | Data fetching, backtesting, and order routing (Nautilus Trader). | L2/L1 (via tools/nodes), Market APIs. |

### Data Flow

1.  **Trigger:** User input or market event enters the **L1 Intent Classifier**.
2.  **Delegation:** L1 routes the task to appropriate **L2 Analysts** (Macro or Quant).
3.  **Adversarial Expansion:** Analyst output fans out to **Bullish** and **Bearish Researchers** in parallel.
4.  **Synthesis:** **Debate Synthesizer** aggregates parallel research into a `weighted_consensus_score`.
5.  **Gating:** **Risk Manager** intercepts if the score > 0.6; otherwise, the process holds.
6.  **Execution Chain:** If approved, a sequential chain of L3 nodes runs: **Data Fetcher** → **Backtester** → **Order Router** → **Trade Logger**.
7.  **Closing:** **L1 Synthesizer** produces the final response/alert.

## Patterns to Follow

### Pattern 1: Adversarial Debate
**What:** Running specialized agents with opposing goals (Bullish vs. Bearish) to stress-test a hypothesis.
**When:** Any trade proposal or high-stakes market analysis.
**Example:**
```python
# Fan-out to researchers
workflow.add_edge("quant_modeler", "bullish_researcher")
workflow.add_edge("quant_modeler", "bearish_researcher")
# Fan-in to synthesizer
workflow.add_edge(["bullish_researcher", "bearish_researcher"], "debate_synthesizer")
```

### Pattern 2: Filesystem-as-Context (Blackboard)
**What:** Using the filesystem (`MEMORY.md`, `data/inbox/`, etc.) as a persistent shared state.
**When:** To maintain long-term memory across sessions or provide large context windows without overwhelming LLM context.
**Instead of:** Relying purely on ephemeral in-memory state.

### Pattern 3: Stateless L3 Workers
**What:** Keeping execution tools (Data Fetchers, Order Routers) as stateless functions.
**When:** Interaction with external APIs or heavy compute (Backtesting).
**Why:** Improves reliability, testability, and allows for easy swapping of providers (e.g., yfinance to Bloomberg).

## Anti-Patterns to Avoid

### Anti-Pattern 1: Flattened Hierarchy
**What:** Letting the top-level orchestrator call L3 tools directly.
**Why bad:** Creates a "God Agent" with too much context, leading to "context rot" and poor reasoning.
**Instead:** Always route through L2 domain managers to filter and prioritize information.

### Anti-Pattern 2: Missing Provenance
**What:** Executing a trade without a recorded debate history or risk log.
**Why bad:** Impossible to audit or improve the system after a failure.
**Instead:** The **Risk Manager** should veto any proposal that lacks `debate_history`.

## Suggested Build Order

Based on component dependencies, the following build order is recommended:

1.  **Phase 1: Graph Skeleton (L1):** Establish the LangGraph framework, state schema (`SwarmState`), and intent classification.
2.  **Phase 2: Core Analysis (L2):** Implement the Macro and Quant analysts.
3.  **Phase 3: Adversarial Layer (L2):** Add parallel researchers and the debate synthesis logic (Crucial for reliability).
4.  **Phase 4: Functional Tools (L3):** Build the Data Fetcher and Order Router (Paper Trading).
5.  **Phase 5: Execution Engine (L3):** Integrate Nautilus Trader for backtesting and live order routing.
6.  **Phase 6: Observability:** Build the dashboard and monitoring for the L1/L2/L3 flow.

## Sources

- `src/graph/orchestrator.py`: Implementation of the LangGraph DAG.
- `src/orchestrator/strategic_l1.py`: Original L1 logic and patterns.
- `src/agents/l3_executor.py`: L3 worker definitions.
- `ROADMAP.md`: Project progression and phase structure.
