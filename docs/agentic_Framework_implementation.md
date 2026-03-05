# Agentic Framework Implementation Plan: LangGraph Migration

**Status:** Draft
**Date:** 2026-03-05
**Scope:** Migrate Quantum Swarm from custom OpenClaw orchestration to LangGraph-based workflow engine

---

## Overview

This document describes the phased migration of the Quantum Swarm multi-agent financial analysis system from its current custom orchestration layer to LangGraph. The goal is to gain structured workflow management, checkpoint-based state persistence, and native support for parallel agent execution — while preserving the existing skills, configuration schema, and OpenClaw external integrations.

---

## Phase 0: Assessment & Setup

- [ ] Audit existing codebase: Identify what works (skills, config, `agents.json` schema, file protocol) vs. what needs replacement (orchestration logic, agent communication)
- [ ] Install LangGraph: `pip install langgraph langchain-anthropic langchain-community`
- [ ] Set up LangSmith for observability (optional but recommended)
- [ ] Create a proof-of-concept: Single L1->L2 delegation using LangGraph supervisor pattern

---

## Phase 1: Core Orchestration Migration (L1 Orchestrator)

**Goal:** Replace `StrategicOrchestrator` (`src/orchestrator/strategic_l1.py`) with a LangGraph-based orchestrator.

- [ ] Define the swarm state schema (`TypedDict` with all shared state fields)
- [ ] Implement L1 Orchestrator as a LangGraph supervisor node
- [ ] Implement intent classification as a conditional edge router
- [ ] Wire up the existing `swarm_config.yaml` routing rules as LangGraph edges
- [ ] Implement the "Blackboard" as LangGraph shared state with checkpoint persistence
- [ ] Preserve existing OpenClaw gateway integration (`src/core/cli_wrapper.py` stays as-is)

### State Schema

```python
from typing import TypedDict, Optional
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
```

### Graph Topology

```python
# L1 Orchestrator graph
orchestrator = StateGraph(SwarmState)
orchestrator.add_node("classify_intent", classify_intent)
orchestrator.add_node("macro_analyst", macro_agent)
orchestrator.add_node("quant_modeler", quant_agent)
orchestrator.add_node("risk_manager", risk_agent)
orchestrator.add_node("synthesize", synthesize_consensus)
orchestrator.add_node("execute", execute_trade)

# Intent routing
orchestrator.add_conditional_edges("classify_intent", route_by_intent, {
    "trade": ["quant_modeler", "macro_analyst"],
    "macro": ["macro_analyst"],
    "analysis": ["macro_analyst", "quant_modeler"],
})

# Bottom-up aggregation
orchestrator.add_edge("macro_analyst", "risk_manager")
orchestrator.add_edge("quant_modeler", "risk_manager")
orchestrator.add_edge("risk_manager", "synthesize")

# Consensus gating
orchestrator.add_conditional_edges("synthesize", check_consensus, {
    "approved": "execute",
    "rejected": END,
    "indeterminate": END,
})
```

---

## Phase 2: L2 Domain Managers as Sub-Graphs

**Goal:** Each L2 agent becomes a LangGraph sub-graph with its own tool set.

**Model:** `claude-haiku-4-5-20251001` for all L2 agents (superior tool-use over Haiku 3.x).

- [ ] Migrate `MacroAnalyst` to a LangGraph ReAct agent with market analysis tools
- [ ] Migrate `QuantModeler` to a LangGraph ReAct agent with technical analysis tools
- [ ] Migrate `RiskManager` to a LangGraph agent with hard-coded compliance rules + LLM reasoning
- [ ] Each L2 agent delegates to L3 executors via tool calls (preserving stateless executor pattern)
- [ ] Implement confidence scoring as structured output from each L2 agent
- [ ] Wire conflict resolution: Risk Manager output gates all trade execution paths

### Agent-Tool Mapping

| L2 Agent | L3 Tools | Skills |
|----------|----------|--------|
| Macro Analyst | `data_fetcher` | `market-environment-analysis`, `economic-indicators` |
| Quant Modeler | `backtester`, `data_fetcher` | `day-trading-skill`, `technical-analysis` |
| Risk Manager | `order_router` (gated) | `risk-management`, `position-sizing` |

---

## Phase 3: L3 Executors as Tools

**Goal:** L3 executors become deterministic LangChain tools (not LLM agents). Zero token cost for procedural tasks.

- [ ] Convert `DataFetcher` (`src/agents/l3_executor.py`) to a LangChain tool wrapping yfinance/ccxt APIs
- [ ] Convert `Backtester` to a LangChain tool wrapping the existing backtest scripts
- [ ] Convert `OrderRouter` to a LangChain tool wrapping the exchange API
- [ ] Use `command-dispatch` pattern: Skip LLM for purely procedural L3 tasks
- [ ] Preserve the existing `src/skills/` directory — register as LangChain tools

### Example Tool Registration

```python
from langchain_core.tools import tool

@tool
def fetch_market_data(symbol: str, timeframe: str = "1H", lookback_days: int = 30) -> dict:
    """Fetch OHLCV market data for a symbol. Returns dict with prices, volume, and timestamps."""
    # Wraps existing DataFetcher logic — no LLM invocation
    fetcher = DataFetcher(config)
    return fetcher.fetch(symbol, timeframe, lookback_days)

@tool
def run_backtest(strategy: dict, symbol: str, start_date: str, end_date: str) -> dict:
    """Execute a historical backtest. Returns PnL distribution, drawdown metrics, Sharpe ratio."""
    backtester = Backtester(config)
    return backtester.run(strategy, symbol, start_date, end_date)
```

---

## Phase 4: Self-Improvement Integration

**Goal:** Connect the existing self-learning pipeline (`src/skills/crypto_learning.py`) to the new orchestration.

- [ ] Wire `SelfLearningPipeline` into LangGraph's checkpointing (trades auto-logged with full state)
- [ ] Use LangGraph's state persistence for richer trade context capture
- [ ] Implement `MEMORY.md` updates as a scheduled LangGraph workflow
- [ ] Connect weekly review as a LangGraph workflow triggered by cron

### State Persistence Advantage

LangGraph checkpointing captures the full `SwarmState` at every node transition. This means the self-learning pipeline gets access to:
- The exact macro report that informed the trade
- The quant proposal with all indicator values
- The risk manager's reasoning and approval/rejection rationale
- The consensus score at decision time

This is significantly richer than the current file-based logging approach.

---

## Phase 5: Safety & Monitoring

**Goal:** Implement safety guardrails from the design doc as first-class graph constructs.

- [ ] Implement circuit breakers as LangGraph conditional edges (API degradation -> halt)
- [ ] Implement budget ceilings via LangChain callback handlers (token tracking)
- [ ] Implement P&L anomaly detection as a monitoring node in the graph
- [ ] Wire Risk Manager as a mandatory gate (no trade bypasses risk validation)
- [ ] Add human-in-the-loop approval for live trades (LangGraph interrupt mechanism)

### Circuit Breaker Pattern

```python
def check_system_health(state: SwarmState) -> str:
    """Conditional edge: halt execution if safety thresholds breached."""
    if api_degradation_detected():
        return "halt"
    if daily_loss_exceeded(state, threshold=0.05):
        return "halt"
    if token_budget_exceeded():
        return "halt"
    return "continue"

orchestrator.add_conditional_edges("risk_manager", check_system_health, {
    "continue": "synthesize",
    "halt": END,
})
```

### Risk Limits (from `swarm_config.yaml`)

These existing limits are enforced at the graph level:
- Max position size: 10% of portfolio
- Max leverage: 10x
- Max daily loss: 5% of portfolio
- Max drawdown: 15% of portfolio
- Stop-loss required on every trade
- Min risk/reward ratio: 1.5

---

## Phase 6: Dashboard & External Integrations

**Goal:** Connect the web dashboard and notification channels.

- [ ] Wire LangGraph event streaming to Flask-SocketIO dashboard
- [ ] Connect Telegram/Discord notifications via LangGraph event handlers
- [ ] Implement the file-based protocol as a LangGraph persistence layer (backward compatible)

---

## What Stays vs. What Changes

### Keep (Already Working)

| Component | Path | Notes |
|-----------|------|-------|
| Swarm config | `config/swarm_config.yaml` | Extend, don't replace |
| Agent definitions | `config/agents.json` | Extend with LangGraph node configs |
| Skills modules | `src/skills/` | Register as LangChain tools |
| CLI wrapper | `src/core/cli_wrapper.py` | OpenClaw CLI integration |
| Self-learning | `src/skills/crypto_learning.py` | Wire into checkpointing |
| File protocol dirs | `data/inbox`, `data/outbox`, etc. | Backward compat |
| Dashboard | `dashboard/` | Wire to event stream |
| Risk limits config | `swarm_config.yaml:risk_limits` | Enforce at graph level |
| Cron definitions | `swarm_config.yaml:scheduled_tasks` | Trigger LangGraph workflows |

### Replace / Migrate

| Current | Replacement |
|---------|-------------|
| `src/orchestrator/strategic_l1.py` | LangGraph supervisor workflow (`src/graph/orchestrator.py`) |
| `src/agents/__init__.py` (L2 classes) | LangGraph sub-graph agents (`src/graph/agents/`) |
| `src/agents/l3_executor.py` | LangChain tools — deterministic, no LLM (`src/tools/`) |
| `main.py` `QuantumSwarm` class | LangGraph application with compiled graph |

### Add New

| Path | Purpose |
|------|---------|
| `src/graph/` | LangGraph workflow definitions |
| `src/graph/state.py` | Shared state schema (`SwarmState`) |
| `src/graph/orchestrator.py` | L1 graph definition |
| `src/graph/agents/` | L2 sub-graphs (macro, quant, risk) |
| `src/tools/` | LangChain tool wrappers for L3 executors |
| `src/graph/safety.py` | Circuit breakers, budget tracking |

---

## OpenClaw's Role in the New Architecture

OpenClaw remains critical but shifts responsibility:

| Layer | Before | After |
|-------|--------|-------|
| Agent Runtime | OpenClaw manages agent lifecycle | LangGraph manages workflow; OpenClaw manages agent deployment/hosting |
| Message Routing | OpenClaw gateway routes all messages | LangGraph edges route within workflow; OpenClaw routes external messages (Telegram, Discord, cron triggers) |
| Skills | OpenClaw skills registry | Skills registered as both OpenClaw skills AND LangChain tools |
| State | File-based (`MEMORY.md`, inbox/outbox) | LangGraph checkpointer (primary) + file-based (backward compat) |
| Monitoring | OpenClaw daemon | LangSmith (workflow tracing) + OpenClaw daemon (infrastructure) |

---

## Model Configuration

| Layer | Model | Purpose | Token Cost |
|-------|-------|---------|------------|
| L1 Orchestrator | `claude-sonnet-4-20250514` | Strategic reasoning, consensus synthesis | Medium |
| L2 Domain Managers | `claude-haiku-4-5-20251001` | Domain-specific analysis with tool use | Low |
| L3 Executors | None (deterministic tools) | API calls, backtests, order execution | Zero |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LangGraph API changes | Low | Medium | Pin version, abstract behind interfaces |
| OpenClaw + LangGraph integration friction | Medium | Medium | Clean separation: OpenClaw handles external I/O, LangGraph handles internal orchestration |
| Token cost increase from richer agent interactions | Medium | Medium | Deterministic tools for L3 (zero tokens); Haiku 4.5 for L2 reasoning |
| Migration disrupts working features | Low | High | Phased approach; each phase independently testable |
| LangSmith vendor lock-in | Low | Low | LangSmith is optional; standard Python logging as fallback |

---

## Dependencies

```
langgraph>=0.2.0
langchain-anthropic>=0.3.0
langchain-community>=0.3.0
langsmith>=0.2.0  # optional, for observability
```
