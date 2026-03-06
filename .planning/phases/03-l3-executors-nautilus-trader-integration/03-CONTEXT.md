# Phase 3: L3 Executors & NautilusTrader Integration - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the stub L3 executor classes (DataFetcher, Backtester, OrderRouter) into real LangGraph nodes with live data, integrate NautilusTrader for paper and live execution, implement trade logging, and build a self-improvement feedback loop from trade outcomes back to the L2 debate layer. Dexter fundamentals delegation and MCP server wrapping are adjacent concerns addressed here at the CLI subprocess level only.

</domain>

<decisions>
## Implementation Decisions

### Self-improvement loop
- Triggered by: trade outcome settled — when P&L is known after a trade closes
- Feeds back to: L2 Debate layer (BullishResearcher and BearishResearcher receive outcome signal)
- Mechanism: `trade_history` list added to SwarmState — L2 agents read it as context on next invocation
- History retention: sliding window of last N trades (10-20), oldest dropped when limit hit

### DataFetcher data sources
- Implement all four sources for real: yfinance (equities), ccxt (crypto), news sentiment, economic calendar
- Separation of concerns: DataFetcher handles market data (prices, ccxt, news, economic); Dexter handles deep fundamental research (SEC filings, DCF, analyst estimates, insider trades)
- Dexter invocation: CLI subprocess — Python calls `bun run src/index.tsx --query "[QUERY]"` from the `src/agents/dexter/` directory, captures Markdown STDOUT
- Return format: Typed Pydantic models — `MarketData`, `FundamentalsData`, `SentimentData` dataclasses (type-safe, fits LangGraph state)
- Caching: in-memory cache per swarm run (same ticker queried twice in one session = one API call)

### NautilusTrader execution scope
- Execution mode: paper + live switchable via `config/swarm_config.yaml` flag (paper by default)
- Market venues: equities (US stocks), crypto (spot), and futures/derivatives
- Broker for live equities: Alpaca — free paper + live API, NautilusTrader has a built-in Alpaca adapter
- Backtester: migrate to NautilusTrader's event-driven backtest engine (replace the stub Backtester entirely)

### Claude's Discretion
- Exact N value for trade history window (within 10-20 range)
- Specific Pydantic model schema details
- NautilusTrader crypto and futures adapter selection (Binance, Bybit, etc.)
- How trade_history is formatted/summarized before being injected into L2 agent context

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/agents/l3_executor.py`: BaseExecutor, DataFetcher, Backtester, OrderRouter, ExecutorFactory, MarketData dataclass — all stub implementations, ~363 lines. Migrate and extend rather than replace.
- `src/graph/state.py`: SwarmState TypedDict — add `trade_history: list` field here
- `src/agents/dexter/`: Full TypeScript/Bun Dexter agent. Entry: `src/index.tsx`. Run via `bun run src/index.tsx --query "..."`. Requires `FINANCIAL_DATASETS_API_KEY`, `EXASEARCH_API_KEY`, `ANTHROPIC_API_KEY` in dexter's `.env`

### Established Patterns
- L2 agents are LangGraph ReAct nodes with BudgetedTool and ToolCache wrappers (see Phase 2 plans)
- Fan-out/fan-in wiring used in debate layer — L3 nodes should follow the same pattern
- Weighted consensus scoring in SwarmState — trade_history field should mirror this pattern (append, not replace)
- Config-driven behavior via `config/swarm_config.yaml` — execution mode flag belongs here

### Integration Points
- `src/graph/orchestrator.py`: Add L3 nodes and wire them after the debate/risk gating step
- `src/graph/state.py`: Add `trade_history`, `execution_mode`, and typed executor result fields to SwarmState
- `config/swarm_config.yaml`: Add `execution_mode: paper | live` toggle and Alpaca credentials section
- Dexter invocation: Python `subprocess.run` or `asyncio.create_subprocess_exec` with 90s timeout cap

</code_context>

<specifics>
## Specific Ideas

- The `docs/deep_research_dexter_integration.md` (Gemini CLI report) lays out the exact CLI invocation pattern and env vars needed. Use it as the spec for the DataFetcher -> Dexter bridge.
- NautilusTrader should start with paper mode ON by default — no live execution without explicit config change
- Alpaca adapter is the priority; crypto/futures adapters can be implemented as secondary within Phase 3

</specifics>

<deferred>
## Deferred Ideas

- MCP server wrapping Dexter tools — proposed in deep_research doc as "Phase 2 (scalable)" path. Defer to a future phase.
- LangSmith trace injection for self-improvement (proposed in Phase 4 Dashboard) — self-improvement via SwarmState covers Phase 3 needs without it
- Full L1 routing weight updates from trade outcomes — only L2 debate layer in Phase 3

</deferred>

---

*Phase: 03-l3-executors-nautilus-trader-integration*
*Context gathered: 2026-03-06*
