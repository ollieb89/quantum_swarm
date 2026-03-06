# Agent Ecosystem Guide

This guide details the specialized agents within the **Quantum Swarm** and their roles in the LangGraph orchestration.

## L1: Strategic Orchestration
*   **Path**: `src/graph/orchestrator.py`
*   **Role**: Entry point for all user tasks. Responsible for intent classification and routing.
*   **Capabilities**: Uses a deterministic skill registry to bypass the graph for common commands or routes to the analysis layers based on intent (trade, macro, analysis).

## L2: Cognitive Analysis Layer
The L2 layer performs adversarial analysis to reach a high-confidence consensus.

### Analysts (ReAct Agents)
*   **MacroAnalyst** (`src/graph/agents/analysts.py`): Performs broad market analysis using economic data and sentiment.
*   **QuantModeler** (`src/graph/agents/analysts.py`): Executes quantitative analysis on specific symbols to generate trade proposals (signal, confidence, stop-loss).

### Researchers (Adversarial Nodes)
*   **BullishResearcher** (`src/graph/agents/researchers.py`): Gathers supporting evidence for the analyst's proposal.
*   **BearishResearcher** (`src/graph/agents/researchers.py`): Attempts to refute the proposal using macro headwinds and contrary data.
*   **Verification**: Both researchers use the `BudgetedTool` wrapper to enforce call limits and ensure data deduplication.

### Debate Synthesizer
*   **Path**: `src/graph/debate.py`
*   **Role**: Aggregates researcher outputs and computes a **Weighted Consensus Score**.
*   **Threshold**: Only scores > 0.6 proceed to execution (L3).

## L3: Execution Engine
*   **Risk Manager**: Validates position sizing, leverage, and daily loss limits.
*   **ClawGuard**: Hard-coded safety node that blocks execution if risk approval is missing or if PII/credentials are detected in the state messages.
*   **Executors**:
    *   `data_fetcher`: Real-time market data retrieval.
    *   `backtester`: Historical strategy verification.
    *   `order_router`: Direct integration with OpenClaw/CCXT.
    *   `trade_logger`: Persistence of trade outcomes for self-learning.

## Testing & Quality Gates
*   **Unit Tests**: Located in `tests/test_*.py`.
*   **Reproduction**: Use `uv run python -m pytest` for all verification.
*   **Mocking**: LLM nodes must be mocked using the `unittest.mock` pattern to ensure tests run without API keys.

---

## Coding Standards for Agents
1.  **Lazy Initialization**: Initialize LLM singletons inside getter functions to prevent API key validation errors at import time.
2.  **State Immutability**: Always return a partial state update dictionary from graph nodes.
3.  **Traceability**: Ensure all AIMessages are tagged with a unique `name` (e.g., `bullish_research`) for consensus aggregation.
