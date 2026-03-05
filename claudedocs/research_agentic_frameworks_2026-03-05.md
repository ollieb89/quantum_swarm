# Agentic Framework Analysis for Quantum Swarm
**Date:** 2026-03-05
**Objective:** Evaluate frameworks for implementing the Multi-Agent Financial Analysis Swarm

---

## Executive Summary

After analyzing 7 repositories and cross-referencing with current ecosystem data, **LangGraph** emerges as the strongest candidate for Quantum Swarm's core orchestration layer, with **Microsoft Agent Framework** as a strong alternative. The existing OpenClaw integration should be preserved as the agent runtime/routing layer, with the chosen framework handling workflow orchestration and state management.

**Key finding:** No single framework perfectly matches the full Quantum Swarm design. The optimal approach is a **hybrid architecture** combining OpenClaw (agent runtime + message routing + skills) with LangGraph or Microsoft Agent Framework (workflow orchestration + state management + hierarchical coordination).

**Confidence level:** High (8/10) -- based on 7 repo analyses, ecosystem surveys, and architectural alignment scoring.

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

1. Microsoft Agent Framework -- github.com/microsoft/agent-framework (RC2/RC3, Python+C#)
2. Ruflo (Claude Flow) -- github.com/ruvnet/ruflo (TypeScript, hierarchical-mesh)
3. DeerFlow -- github.com/bytedance/deer-flow (Python/LangGraph, hub-spoke)
4. AWS Agentic Samples -- github.com/aws-samples/sample-agentic-frameworks-on-aws (multi-framework samples)
5. MS Agent Framework Samples -- github.com/microsoft/Agent-Framework-Samples (Python+.NET samples)
6. TEN Framework -- github.com/TEN-framework/ten-framework (C++ core, real-time media)
7. AI Agents Survey -- github.com/martimfasantos/ai-agents-frameworks (10-framework comparison)
8. DataCamp 2026 AI Agents Survey -- datacamp.com/blog/best-ai-agents
9. AgentOrchestra (arXiv) -- arxiv.org/html/2506.12508v4
10. Digital Applied AI Orchestration Comparison -- digitalapplied.com/blog/ai-workflow-orchestration-platforms-comparison
11. Agno vs LangGraph -- zenml.io/blog/agno-vs-langgraph
