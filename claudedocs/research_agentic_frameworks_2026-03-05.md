# Agentic Framework Analysis for Quantum Swarm
**Date:** 2026-03-05
**Objective:** Evaluate frameworks for implementing the Multi-Agent Financial Analysis Swarm

---

## Executive Summary

After analyzing 11 repositories and cross-referencing with current ecosystem data, **LangGraph** emerges as the strongest candidate for Quantum Swarm's core orchestration layer. This choice is strongly validated by **TradingAgents** (31.3k stars), a production LangGraph-based financial multi-agent system with nearly identical architecture to ours.

**Key finding:** The optimal Quantum Swarm is a **4-layer hybrid architecture:**
- **OpenClaw** (agent runtime + message routing + skills)
- **LangGraph** (workflow orchestration + state management + hierarchical coordination)
- **TradingAgents patterns** (adversarial debate, analyst fan-out, risk veto -- adapted, not forked)
- **NautilusTrader** (L3 execution infrastructure -- production-grade order management + nanosecond backtesting)

**Confidence level:** Very High (9/10) -- based on 11 repo analyses, ecosystem surveys, architectural alignment scoring, and discovery of a validated production reference (TradingAgents) using our exact stack.

---

## Framework Comparison Matrix

| Framework | Language | Hierarchy Support | Python | LLM Flexibility | Financial Features | Routing/Conflict | Maturity | **Score** |
|-----------|----------|-------------------|--------|-----------------|-------------------|------------------|----------|-----------|
| **Microsoft Agent Framework** | Python + C# | Graph-based (flexible) | Yes (first-class) | Yes (multi-provider) | None built-in | Conditional edges | RC2/RC3 (early) | **7.5/10** |
| **Ruflo (Claude Flow v3.5)** | TypeScript + Rust WASM | Hierarchical-mesh, Queen model | No (TS only) | Claude-centric | None | Q-Learning Router, CRDTs | Niche, small community | **5/10** |
| **DeerFlow (ByteDance)** | Python (LangGraph) | Hub-spoke (Lead Agent) | Yes | Yes (multi-provider) | None built-in | 11-step middleware pipeline | Active, MIT | **6.5/10** |
| **AWS Agentic Samples** | Python | Mixed (sample collection) | Yes | Yes (Bedrock focus) | Trading example (A2A) | Per-sample | Samples only, not a framework | **4/10** |
| **MS Agent Framework Samples** | Python + .NET | Graph-based (Pregel) | Yes | Yes | None | A2A + MCP + conditional edges | Companion to MS AF | **6/10** |
| **TEN Framework** | C++ core, polyglot | Graph + subgraphs | Yes (extensions) | Via extensions | None | Ownership-based message passing | Large (real-time focus) | **5/10** |
| **AI Agents Survey** | N/A (survey) | N/A | N/A | N/A | N/A | N/A | Survey of 10 frameworks | **Reference** |

### Frameworks from Ecosystem Research (not in original list but highly relevant)

| Framework | Language | Hierarchy Support | Python | LLM Flexibility | Financial Features | Routing/Conflict | Maturity | **Score** |
|-----------|----------|-------------------|--------|-----------------|-------------------|------------------|----------|-----------|
| **LangGraph** | Python | Supervisor, hierarchical, custom graphs | Yes (native) | Yes (all providers) | No (but ecosystem) | Conditional routing, checkpoints | Production (LangChain) | **8.5/10** |
| **CrewAI** | Python | Sequential, hierarchical crews | Yes (native) | Yes (100+ LLMs) | Community examples | Manager delegation | Production, large community | **7/10** |
| **Google ADK** | Python | Hierarchical compositions | Yes (native) | Gemini-first, others via adapters | None | Agent nesting | New (April 2025) | **6/10** |
| **Agno** | Python | Team-based multi-agent | Yes (native) | Yes (multi-provider) | YFinance tools built-in | Team coordination | Growing (fast) | **6.5/10** |

### Financial Domain & Specialized Frameworks

| Framework | Language | Hierarchy Support | Python | LLM Flexibility | Financial Features | Routing/Conflict | Maturity | **Score** |
|-----------|----------|-------------------|--------|-----------------|-------------------|------------------|----------|-----------|
| **TradingAgents** | Python (LangGraph) | Analyst->Researcher->Trader->Risk pipeline | Yes (native) | Yes (OpenAI, Claude, Gemini, Grok, Ollama) | Full: technical, fundamental, sentiment, risk mgmt | Bullish/bearish debate + risk veto | Production (31.3k stars, v0.2.0) | **9/10** |
| **NautilusTrader** | Rust + Python (Cython/PyO3) | Not multi-agent (event-driven platform) | Yes (bindings) | N/A (not LLM-based) | Full: multi-asset, multi-venue, order management | Event bus + message passing | Production (20.9k stars) | **7/10** (as L3 infra) |
| **quant-trading** | Python | Not multi-agent (strategy library) | Yes (native) | N/A (not LLM-based) | Strategies: MACD, RSI, Bollinger, pairs, Monte Carlo | N/A | Mature (9.3k stars, 859 commits) | **5/10** (as reference) |
| **multi-agent-framework** | Python | HMAS/DMAS/CMAS comparative | Yes (native) | OpenAI only | None (robotics domain) | Dialogue-based coordination | Academic (41 stars, ICRA 2024) | **4/10** (arch patterns) |

---

## Detailed Framework Analyses

### 1. Microsoft Agent Framework
**Repo:** github.com/microsoft/agent-framework

- **Architecture:** Graph-based Pregel-style workflow engine. Executors (nodes) connected by Edges with conditional routing. Supports linear chains, fan-out/fan-in, cycles.
- **Strengths:** First-class Python support, A2A protocol for cross-framework interop, MCP integration, agent-as-tool composition, streaming, human-in-the-loop, checkpointing.
- **Weaknesses:** Still at RC2/RC3 stage (not production-stable). No financial domain features. Microsoft ecosystem gravity.
- **Fit for Quantum Swarm:** The graph-based model maps well to L1->L2->L3 hierarchy. A2A protocol could enable OpenClaw agents to communicate with external agent systems. The agent-as-tool pattern mirrors how L2 managers delegate to L3 executors.

### 2. Ruflo (Claude Flow v3.5)
**Repo:** github.com/ruvnet/ruflo

- **Architecture:** Layered with selectable topologies (hierarchical, mesh, hybrid). Queen-led hierarchy with worker agents. Q-Learning router, 60+ agents, RuVector intelligence layer.
- **Strengths:** Sophisticated multi-topology support, CRDT-based conflict resolution, gossip protocol, self-optimization. Very ambitious design.
- **Weaknesses:** **TypeScript/Node.js only -- no Python support.** Claude-centric (not LLM-agnostic). Niche community. Complex architecture may be over-engineered for the use case.
- **Fit for Quantum Swarm:** Poor. The TS-only requirement conflicts with the existing Python codebase. Interesting architectural concepts (Queen hierarchy, adaptive topology) but would require a full rewrite.

### 3. DeerFlow (ByteDance)
**Repo:** github.com/bytedance/deer-flow

- **Architecture:** Hub-spoke with a Lead Agent orchestrator. Built on LangGraph. 11-step deterministic middleware pipeline. Sandbox execution.
- **Strengths:** Well-structured middleware pipeline (prevents race conditions by design), MCP tool integration, SSE streaming, sandbox execution for code. Active development from ByteDance.
- **Weaknesses:** Single Lead Agent model -- not designed for true hierarchical multi-agent (L1/L2/L3). More of a "super agent" harness than a swarm framework. Tool-call delegation only.
- **Fit for Quantum Swarm:** Moderate. The middleware pipeline concept is excellent for the Orchestrator layer. However, it lacks native support for multi-level agent hierarchies. Would need significant extension.

### 4. AWS Agentic Samples
**Repo:** github.com/aws-samples/sample-agentic-frameworks-on-aws

- **Architecture:** Collection of independent examples, not a unified framework. Demonstrates LangGraph, CrewAI, Strands Agents, LlamaIndex patterns.
- **Strengths:** Includes an A2A advisory trading system with Portfolio Manager -> 3 specialists (closest to Quantum Swarm's design). Shows real financial agent patterns. Multi-framework comparison.
- **Weaknesses:** Not a framework -- just samples. AWS/Bedrock ecosystem lock-in. No reusable orchestration layer.
- **Fit for Quantum Swarm:** **Valuable as a reference architecture**, especially the A2A trading system pattern. Not suitable as the framework itself, but the patterns should inform the implementation.

### 5. TEN Framework
**Repo:** github.com/TEN-framework/ten-framework

- **Architecture:** Graph-based with subgraph composition. C++ core with polyglot extensions. Ownership-based message passing (prevents data races).
- **Strengths:** High-performance runtime, real-time streaming (audio/video), composable subgraphs, cross-graph communication.
- **Weaknesses:** Designed primarily for **real-time media/conversational AI**, not financial analysis. The streaming focus is irrelevant. C++ core adds complexity. Community is real-time AI focused.
- **Fit for Quantum Swarm:** Poor. Architectural concepts (subgraphs, ownership semantics) are interesting but the framework's focus on real-time media processing makes it a poor fit for financial analysis workflows.

### 6. AI Agents Frameworks Survey
**Repo:** github.com/martimfasantos/ai-agents-frameworks

- **Key Finding:** All 10 surveyed frameworks are Python-native. The top frameworks for multi-agent orchestration are: **CrewAI** (most multi-agent-focused), **LangGraph** (most flexible graph-based), **Google ADK** (hierarchical compositions), **AutoGen/AG2** (multi-agent conversations).
- **For financial use:** No framework has built-in financial features. Agno has YFinance tools. LangGraph and CrewAI have the largest ecosystems for building custom financial tools.

### 7. TradingAgents (Tauric Research)
**Repo:** github.com/TauricResearch/TradingAgents

- **Architecture:** Multi-agent LLM framework built on **LangGraph** that simulates institutional trading firms. Hierarchical pipeline: Analyst Team (4 specialists) -> Researcher Team (bullish/bearish debate) -> Trader Agent -> Risk Manager + Portfolio Manager.
- **Agent Roles:**
  - *Fundamentals Analyst:* Company financials, earnings, valuation metrics
  - *Sentiment Analyst:* Social media sentiment scoring
  - *News Analyst:* News event impact assessment
  - *Technical Analyst:* MACD, RSI, pattern recognition
  - *Bullish Researcher:* Argues for opportunity from analyst inputs
  - *Bearish Researcher:* Argues for risk/caution from analyst inputs
  - *Trader Agent:* Synthesizes debate into trade timing and sizing
  - *Risk Manager / Portfolio Manager:* Veto authority, portfolio-level risk assessment
- **Strengths:** Purpose-built for financial markets. The bullish/bearish debate mechanism is unique -- it forces adversarial reasoning before trade decisions, reducing confirmation bias. Multi-provider LLM support (OpenAI, Claude, Gemini, Grok, Ollama). 31.3k stars, very active community. Built on LangGraph, so compatible with our chosen orchestration layer.
- **Weaknesses:** Focused on equity analysis (not crypto-native). No built-in self-improvement/learning loop. The debate mechanism adds latency (2 extra LLM calls per decision). No integrated execution layer (simulated exchange only).
- **Fit for Quantum Swarm:** **Extremely high.** The architecture is nearly identical to our L1->L2->L3 design. Key patterns to adopt:
  1. The adversarial researcher debate pattern (bullish vs bearish) could replace simple consensus scoring with richer conflict resolution
  2. The 4-analyst fan-out pattern maps directly to our L2 domain managers
  3. Risk Manager veto authority matches our priority-based preemption model
  4. Since it's LangGraph-native, we can potentially reuse or adapt their agent sub-graphs directly

### 8. Multi-Agent Framework (Yongchao et al.)
**Repo:** github.com/yongchao98/multi-agent-framework

- **Architecture:** Academic implementation comparing 4 multi-agent coordination architectures: **HMAS-2** (hierarchical, 2-level), **HMAS-1** (hierarchical, 1-level), **DMAS** (distributed/peer-to-peer), **CMAS** (centralized). Agents coordinate through dialogue history with configurable retention. Supports ICRA 2024 paper.
- **Strengths:** Rigorous comparative analysis of coordination topologies. Provides empirical data on when hierarchical outperforms distributed and vice versa. Clean experimental design with 4 testable environments (BoxNet1, BoxNet2, BoxLift, Warehouse).
- **Weaknesses:** Robotics domain (not financial). OpenAI-only. 41 stars, academic code quality. Not a reusable framework -- it's a research artifact.
- **Fit for Quantum Swarm:** **Low for direct use, high for architectural insight.** Key learnings:
  1. *HMAS-2 (2-level hierarchy) consistently outperforms flat/distributed for complex coordination* -- validates our L1->L2->L3 design choice
  2. *Dialogue history retention matters* -- agents that retain full conversation context coordinate better than those with sliding windows. Implications for our LangGraph state management (keep full message history in checkpoints, don't prune aggressively)
  3. *Centralized (CMAS) fails at scale* -- confirms that a single orchestrator bottleneck is dangerous. Our design correctly uses the L1 as a router, not a processor

### 9. quant-trading (je-suis-tm)
**Repo:** github.com/je-suis-tm/quant-trading

- **Architecture:** Collection of independent Python trading strategy implementations with backtesting. NOT a multi-agent system. Each strategy is a standalone script with its own analysis pipeline.
- **Strategies Implemented:**
  - *Technical:* MACD, Awesome Oscillator, Bollinger Bands, RSI, Parabolic SAR, Heikin-Ashi
  - *Pattern:* Shooting Star, London Breakout, Dual Thrust
  - *Statistical:* Pair Trading (cointegration-based)
  - *Options:* Straddle strategy
  - *Quantitative:* Monte Carlo simulation, VIX calculator
  - *Alternative Data:* Oil Money (petrocurrency analysis), Smart Farmers (agricultural commodities)
- **Strengths:** 9.3k stars, 859 commits, well-documented. Clean Python implementations of proven strategies. "Quantamental" approach combining technical + fundamental analysis. Educational with strong documentation.
- **Weaknesses:** No agent architecture. No real-time execution. No risk management framework. Assumes frictionless trading (no transaction costs). Individual scripts, not an integrated system.
- **Fit for Quantum Swarm:** **Moderate -- as a strategy library for L3 tools.** Key value:
  1. The strategy implementations (MACD, RSI, Bollinger, pair trading) can be wrapped as LangChain tools for the Quant Modeler's L3 Backtester
  2. The Monte Carlo simulation and VIX calculator are directly useful for the Risk Manager's portfolio analysis
  3. The pair trading implementation provides a template for statistical arbitrage strategies
  4. Code is clean enough to extract and adapt without major refactoring

### 10. NautilusTrader (Nautech Systems)
**Repo:** github.com/nautechsystems/nautilus_trader

- **Architecture:** High-performance, event-driven algorithmic trading platform. Rust core with Python bindings (Cython + PyO3). Modular design: message bus -> cache -> adapters -> execution engine. Multi-venue, multi-asset support.
- **Key Capabilities:**
  - *Order Management:* Advanced order types (IOC, FOK, GTC, GTD, DAY), contingency orders (OCO, OUO, OTO), execution instructions (post-only, reduce-only, icebergs)
  - *Backtesting:* Nanosecond-resolution historical simulation, fast enough to train AI agents via RL
  - *Live Trading:* Identical code for backtest and production (zero parity gap)
  - *Venues:* 15+ integrated (Binance, Kraken, Interactive Brokers, Betfair, Bybit, dYdX)
  - *Assets:* FX, equities, futures, options, crypto, DeFi
  - *Precision:* Standard (64-bit) and high-precision (128-bit) calculation modes
- **Strengths:** 20.9k stars, bi-weekly releases, production-grade. Rust core provides memory safety + performance without GC overhead. The backtest engine is explicitly designed to "train AI trading agents." Multi-venue support means we can execute across exchanges simultaneously.
- **Weaknesses:** Not a multi-agent framework. Steep learning curve (Rust + Cython internals). Breaking changes still possible. No LLM integration (purely algorithmic).
- **Fit for Quantum Swarm:** **Very high -- as the L3 execution infrastructure.** This is the strongest candidate to replace our custom `OrderRouter` and `Backtester`:
  1. Replace `l3_executor.py:OrderRouter` with NautilusTrader's execution engine -- gain institutional-grade order management, multi-venue routing, and nanosecond execution
  2. Replace `l3_executor.py:Backtester` with NautilusTrader's backtest engine -- gain nanosecond-resolution simulation with realistic fills, slippage modeling, and transaction costs
  3. The event-driven message bus complements LangGraph's state management (LangGraph handles agent orchestration, NautilusTrader handles market events)
  4. The "AI agent training" design goal means our LangGraph agents can use NautilusTrader as a reinforcement learning environment for strategy optimization
  5. Multi-venue support enables the Risk Manager to monitor positions across all exchanges simultaneously

---

## Recommendation: Hybrid Architecture

### Primary Recommendation: OpenClaw + LangGraph

**Why LangGraph wins for Quantum Swarm:**

1. **Hierarchical orchestration is native.** LangGraph supports supervisor-worker patterns with configurable depth -- mapping directly to L1 (supervisor) -> L2 (sub-supervisors) -> L3 (worker agents).

2. **State management.** LangGraph's shared state graph with checkpointing maps perfectly to the "Blackboard" pattern in the design doc. State persists across agent invocations and can be rolled back.

3. **Conditional routing.** Edges can route based on runtime conditions -- ideal for intent classification (trade/macro/analysis routing) and conflict resolution (Risk Manager priority preemption).

4. **Python-native.** Your entire codebase is Python. LangGraph is Python-first with no foreign runtime dependencies.

5. **LLM provider flexibility.** Via LangChain, it supports Claude, GPT, Gemini, local models, and any OpenAI-compatible API.

6. **Production maturity.** Backed by LangChain with LangSmith for observability. Large community, active development, production deployments.

7. **Ecosystem.** LangChain's tool ecosystem provides pre-built integrations for financial data sources (yfinance, Alpha Vantage, etc.), which complement your existing skills.

8. **Complementary to OpenClaw.** LangGraph handles workflow orchestration; OpenClaw handles agent runtime, message routing, skills, and the gateway server. They serve different layers.

9. **Validated by TradingAgents.** The TradingAgents project (31.3k stars) proves LangGraph works at scale for financial multi-agent systems with a nearly identical architecture to ours. This de-risks the framework choice significantly.

### Recommended Component Stack

Based on the expanded research, the optimal Quantum Swarm architecture combines 4 layers:

| Layer | Component | Role |
|-------|-----------|------|
| **L0: Runtime** | OpenClaw | Agent deployment, external message routing (Telegram, Discord, cron), skills registry, gateway server |
| **L1-L2: Orchestration** | LangGraph | Workflow graphs, state management, conditional routing, checkpointing, human-in-the-loop |
| **L2: Agent Patterns** | TradingAgents (reference) | Adopt adversarial debate pattern (bullish/bearish researchers), 4-analyst fan-out, risk veto authority |
| **L3: Execution** | NautilusTrader | Production-grade order management, multi-venue execution, nanosecond backtesting, RL training environment |
| **L3: Strategies** | quant-trading (reference) | Strategy implementations (MACD, RSI, Bollinger, pair trading, Monte Carlo) wrapped as LangChain tools |
| **Architecture** | HMAS-2 pattern (validated by multi-agent-framework) | 2-level hierarchy with full dialogue history retention |

### Alternative: OpenClaw + Microsoft Agent Framework

**If you want bleeding-edge interop features:**
- A2A protocol for cross-framework agent communication
- MCP integration (already in your design via OpenClaw)
- Pregel-style supersteps for deterministic execution ordering
- **Risk:** Still RC2/RC3, API may change. Less community than LangGraph.

### Not Recommended
- **Ruflo:** TypeScript-only, would require full rewrite
- **TEN Framework:** Real-time media focus, wrong domain
- **AWS Samples:** Reference only, not a framework
- **DeerFlow:** Single lead-agent model, insufficient for L1/L2/L3

---

## Implementation Plan

### Phase 0: Assessment & Setup (1 phase)
- [ ] Audit existing codebase: Identify what works (skills, config, agents.json schema, file protocol) vs. what needs replacement (orchestration logic, agent communication)
- [ ] Install LangGraph: `pip install langgraph langchain-anthropic langchain-community`
- [ ] Set up LangSmith for observability (optional but recommended)
- [ ] Create a proof-of-concept: Single L1->L2 delegation using LangGraph supervisor pattern

### Phase 1: Core Orchestration Migration (L1 Orchestrator)
**Goal:** Replace `StrategicOrchestrator` with a LangGraph-based orchestrator

- [ ] Define the swarm state schema (TypedDict with all shared state fields)
- [ ] Implement L1 Orchestrator as a LangGraph supervisor node
- [ ] Implement intent classification as a conditional edge router
- [ ] Wire up the existing `swarm_config.yaml` routing rules as LangGraph edges
- [ ] Implement the "Blackboard" as LangGraph shared state with checkpoint persistence
- [ ] Preserve existing OpenClaw gateway integration (CLI wrapper stays as-is)

**Key design:**
```python
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent

class SwarmState(TypedDict):
    task_id: str
    intent: str
    messages: list
    macro_report: Optional[dict]
    quant_proposal: Optional[dict]
    risk_approval: Optional[dict]
    consensus_score: float
    compliance_flags: list
    final_decision: Optional[dict]

# L1 Orchestrator graph
orchestrator = StateGraph(SwarmState)
orchestrator.add_node("classify_intent", classify_intent)
orchestrator.add_node("macro_analyst", macro_agent)
orchestrator.add_node("quant_modeler", quant_agent)
orchestrator.add_node("risk_manager", risk_agent)
orchestrator.add_node("synthesize", synthesize_consensus)
orchestrator.add_node("execute", execute_trade)

# Routing
orchestrator.add_conditional_edges("classify_intent", route_by_intent, {
    "trade": ["quant_modeler", "macro_analyst"],
    "macro": ["macro_analyst"],
    "analysis": ["macro_analyst", "quant_modeler"],
})
orchestrator.add_edge("macro_analyst", "risk_manager")
orchestrator.add_edge("quant_modeler", "risk_manager")
orchestrator.add_edge("risk_manager", "synthesize")
orchestrator.add_conditional_edges("synthesize", check_consensus, {
    "approved": "execute",
    "rejected": END,
    "indeterminate": END,
})
```

### Phase 2: L2 Domain Managers as Sub-Graphs
**Goal:** Each L2 agent becomes a LangGraph sub-graph with its own tool set

- [ ] Migrate `MacroAnalyst` to a LangGraph ReAct agent with market analysis tools
- [ ] Migrate `QuantModeler` to a LangGraph ReAct agent with technical analysis tools
- [ ] Migrate `RiskManager` to a LangGraph agent with hard-coded compliance rules + LLM reasoning
- [ ] Each L2 agent delegates to L3 executors via tool calls (preserving stateless executor pattern)
- [ ] Implement confidence scoring as structured output from each L2 agent
- [ ] Wire conflict resolution: Risk Manager output gates all trade execution paths

### Phase 3: L3 Executors as Tools
**Goal:** L3 executors become deterministic tools (not LLM agents)

- [ ] Convert `DataFetcher` to a LangChain tool wrapping yfinance/ccxt APIs
- [ ] Convert `Backtester` to a LangChain tool wrapping the existing backtest scripts
- [ ] Convert `OrderRouter` to a LangChain tool wrapping the exchange API
- [ ] Use `command-dispatch` pattern: Skip LLM for purely procedural L3 tasks (zero token cost)
- [ ] Preserve the existing `skills/` directory -- register as LangChain tools

### Phase 4: Self-Improvement Integration
**Goal:** Connect the existing self-learning pipeline to the new orchestration

- [ ] Wire `SelfLearningPipeline` into LangGraph's checkpointing (trades auto-logged with full state)
- [ ] Use LangGraph's state persistence for richer trade context capture
- [ ] Implement `MEMORY.md` updates as a scheduled LangGraph workflow
- [ ] Connect weekly review as a LangGraph workflow triggered by cron

### Phase 5: Safety & Monitoring
**Goal:** Implement the safety guardrails from the design doc

- [ ] Implement circuit breakers as LangGraph conditional edges (API degradation -> halt)
- [ ] Implement budget ceilings via LangChain callback handlers (token tracking)
- [ ] Implement P&L anomaly detection as a monitoring node in the graph
- [ ] Wire Risk Manager as a mandatory gate (no trade bypasses risk validation)
- [ ] Add human-in-the-loop approval for live trades (LangGraph interrupt mechanism)

### Phase 6: Dashboard & External Integrations
**Goal:** Connect the web dashboard and notification channels

- [ ] Wire LangGraph event streaming to Flask-SocketIO dashboard
- [ ] Connect Telegram/Discord notifications via LangGraph event handlers
- [ ] Implement the file-based protocol as a LangGraph persistence layer (backward compatible)

---

## What Stays vs. What Changes

### Keep (Already Working Well)
- `config/swarm_config.yaml` -- Configuration schema (extend, don't replace)
- `config/agents.json` -- Agent definitions (extend with LangGraph node configs)
- `src/skills/` -- All skill modules (register as LangChain tools)
- `src/core/cli_wrapper.py` -- OpenClaw CLI integration
- `src/skills/crypto_learning.py` -- Self-learning pipeline
- File-based protocol directories (`data/inbox`, `data/outbox`, etc.)
- Dashboard (`dashboard/`)
- Risk limits configuration
- Cron job definitions

### Replace/Migrate
- `src/orchestrator/strategic_l1.py` -> LangGraph supervisor workflow
- `src/agents/__init__.py` (L2 agent classes) -> LangGraph sub-graph agents
- `src/agents/l3_executor.py` -> LangChain tools (deterministic, no LLM)
- `main.py` QuantumSwarm class -> LangGraph application with compiled graph

### Add New
- `src/graph/` -- LangGraph workflow definitions
- `src/graph/state.py` -- Shared state schema
- `src/graph/orchestrator.py` -- L1 graph
- `src/graph/agents/` -- L2 sub-graphs
- `src/tools/` -- LangChain tool wrappers for L3 executors
- `src/graph/safety.py` -- Circuit breakers, budget tracking
- LangSmith configuration for observability

---

## OpenClaw's Role in the New Architecture

OpenClaw remains critical but shifts responsibility:

| Layer | Before | After |
|-------|--------|-------|
| Agent Runtime | OpenClaw manages agent lifecycle | LangGraph manages workflow; OpenClaw manages agent deployment/hosting |
| Message Routing | OpenClaw gateway routes all messages | LangGraph edges route within workflow; OpenClaw routes external messages (Telegram, Discord, cron triggers) |
| Skills | OpenClaw skills registry | Skills registered as both OpenClaw skills AND LangChain tools |
| State | File-based (MEMORY.md, inbox/outbox) | LangGraph checkpointer (primary) + file-based (backward compat) |
| Monitoring | OpenClaw daemon | LangSmith (workflow tracing) + OpenClaw daemon (infrastructure) |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LangGraph API changes | Low | Medium | Pin version, abstract behind interfaces |
| OpenClaw + LangGraph integration friction | Medium | Medium | Keep clean separation of concerns; OpenClaw handles external I/O, LangGraph handles internal orchestration |
| Token cost increase from richer agent interactions | Medium | Medium | Use deterministic tools for L3 (zero tokens); use Haiku for L2 reasoning |
| Migration disrupts working features | Low | High | Phased approach; each phase is independently testable |
| LangSmith vendor lock-in | Low | Low | LangSmith is optional; standard Python logging as fallback |

---

## Sources

### Agentic Frameworks (General)
1. Microsoft Agent Framework -- github.com/microsoft/agent-framework (RC2/RC3, Python+C#)
2. Ruflo (Claude Flow) -- github.com/ruvnet/ruflo (TypeScript, hierarchical-mesh)
3. DeerFlow -- github.com/bytedance/deer-flow (Python/LangGraph, hub-spoke)
4. AWS Agentic Samples -- github.com/aws-samples/sample-agentic-frameworks-on-aws (multi-framework samples)
5. MS Agent Framework Samples -- github.com/microsoft/Agent-Framework-Samples (Python+.NET samples)
6. TEN Framework -- github.com/TEN-framework/ten-framework (C++ core, real-time media)
7. AI Agents Survey -- github.com/martimfasantos/ai-agents-frameworks (10-framework comparison)

### Financial Domain & Specialized
8. TradingAgents -- github.com/TauricResearch/TradingAgents (Python/LangGraph, 31.3k stars, multi-agent trading)
9. NautilusTrader -- github.com/nautechsystems/nautilus_trader (Rust+Python, 20.9k stars, production trading platform)
10. quant-trading -- github.com/je-suis-tm/quant-trading (Python, 9.3k stars, strategy implementations)
11. Multi-Agent Framework -- github.com/yongchao98/multi-agent-framework (Python, ICRA 2024, coordination topology comparison)

### Ecosystem Research
12. DataCamp 2026 AI Agents Survey -- datacamp.com/blog/best-ai-agents
13. AgentOrchestra (arXiv) -- arxiv.org/html/2506.12508v4
14. Digital Applied AI Orchestration Comparison -- digitalapplied.com/blog/ai-workflow-orchestration-platforms-comparison
15. Agno vs LangGraph -- zenml.io/blog/agno-vs-langgraph
