# Agentic Framework Implementation Plan: LangGraph Migration

**Status:** Draft
**Date:** 2026-03-05
**Scope:** Migrate Quantum Swarm from custom OpenClaw orchestration to LangGraph-based workflow engine

---

## Overview

This document describes the phased migration of the Quantum Swarm multi-agent financial analysis system from its current custom orchestration layer to LangGraph. The goal is to gain structured workflow management, checkpoint-based state persistence, and native support for parallel agent execution — while preserving the existing skills, configuration schema, and OpenClaw external integrations.

### Reference Architectures

This plan is informed by analysis of 11 repositories (see `claudedocs/research_agentic_frameworks_2026-03-05.md`). Key influences:

| Source | What We Adopt | Why |
|--------|--------------|-----|
| **TradingAgents** (31.3k stars, LangGraph) | Adversarial bullish/bearish researcher debate pattern, 4-analyst fan-out, risk veto authority | Proven at scale, nearly identical L1->L2->L3 architecture, same tech stack |
| **NautilusTrader** (20.9k stars, Rust+Python) | L3 execution backend: order management, nanosecond backtesting, multi-venue routing | Production-grade, replaces custom OrderRouter/Backtester, designed for AI agent training |
| **quant-trading** (9.3k stars) | Strategy implementations as LangChain tools (MACD, RSI, Bollinger, pair trading, Monte Carlo) | Clean Python, well-tested, wrappable without major refactoring |
| **multi-agent-framework** (ICRA 2024) | HMAS-2 topology validation, full dialogue history retention | Academic proof that 2-level hierarchy outperforms flat/distributed coordination |

---

## Phase 0: Assessment & Setup

- [x] Audit existing codebase: Identify what works (skills, config, `agents.json` schema, file protocol) vs. what needs replacement (orchestration logic, agent communication)
- [x] Study TradingAgents repo architecture: Extract the adversarial debate pattern, agent sub-graph structure, and LangGraph wiring patterns
- [x] Install dependencies: `pip install langgraph langchain-anthropic langchain-community nautilus_trader`
- [x] Set up LangSmith for observability (optional but recommended)
- [x] Create a proof-of-concept: Single L1->L2 delegation using LangGraph supervisor pattern
- [x] Create a NautilusTrader proof-of-concept: Verify backtest execution and data feed integration with existing config

---

## Phase 1: Core Orchestration Migration (L1 Orchestrator)

**Goal:** Replace `StrategicOrchestrator` (`src/orchestrator/strategic_l1.py`) with a LangGraph-based orchestrator.

- [x] Define the swarm state schema (`TypedDict` with all shared state fields)
- [x] Implement L1 Orchestrator as a LangGraph supervisor node
- [x] Implement intent classification as a conditional edge router
- [x] Wire up the existing `swarm_config.yaml` routing rules as LangGraph edges
- [x] Implement the "Blackboard" as LangGraph shared state with checkpoint persistence
- [x] Preserve existing OpenClaw gateway integration (`src/core/cli_wrapper.py` stays as-is)

### State Schema

```python
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent

class SwarmState(TypedDict):
    task_id: str
    intent: str
    messages: list  # Full dialogue history (HMAS-2 validated: don't prune)
    macro_report: Optional[dict]
    quant_proposal: Optional[dict]
    # Adversarial debate (adapted from TradingAgents)
    bullish_thesis: Optional[dict]   # Arguments for the trade
    bearish_thesis: Optional[dict]   # Arguments against the trade
    debate_resolution: Optional[dict] # Synthesized position after debate
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
# Adversarial debate layer (adapted from TradingAgents pattern)
orchestrator.add_node("bullish_researcher", bullish_agent)
orchestrator.add_node("bearish_researcher", bearish_agent)
orchestrator.add_node("debate_synthesizer", resolve_debate)
orchestrator.add_node("risk_manager", risk_agent)
orchestrator.add_node("synthesize", synthesize_consensus)
orchestrator.add_node("execute", execute_trade)

# Intent routing
orchestrator.add_conditional_edges("classify_intent", route_by_intent, {
    "trade": ["quant_modeler", "macro_analyst"],
    "macro": ["macro_analyst"],
    "analysis": ["macro_analyst", "quant_modeler"],
})

# Analyst outputs feed into adversarial debate
orchestrator.add_edge("macro_analyst", "bullish_researcher")
orchestrator.add_edge("macro_analyst", "bearish_researcher")
orchestrator.add_edge("quant_modeler", "bullish_researcher")
orchestrator.add_edge("quant_modeler", "bearish_researcher")

# Debate resolution -> Risk gating
orchestrator.add_edge("bullish_researcher", "debate_synthesizer")
orchestrator.add_edge("bearish_researcher", "debate_synthesizer")
orchestrator.add_edge("debate_synthesizer", "risk_manager")
orchestrator.add_edge("risk_manager", "synthesize")

# Consensus gating
orchestrator.add_conditional_edges("synthesize", check_consensus, {
    "approved": "execute",
    "rejected": END,
    "indeterminate": END,
})
```

**Why the debate layer?** TradingAgents (31.3k stars) demonstrates that adversarial reasoning between bullish and bearish researchers reduces confirmation bias and catches risks that consensus-only approaches miss. The bullish researcher argues for the trade based on analyst outputs; the bearish researcher argues against it. The debate synthesizer resolves the conflict into a net position with weighted confidence, which then flows to the Risk Manager for final gating.

---

## Phase 2: L2 Domain Managers & Adversarial Debate Layer

**Goal:** Each L2 agent becomes a LangGraph sub-graph with its own tool set. Add adversarial debate layer (adapted from TradingAgents) between analyst output and risk gating.

**Model:** `claude-haiku-4-5-20251001` for all L2 agents (superior tool-use over Haiku 3.x).

### L2 Analyst Agents
- [ ] Migrate `MacroAnalyst` to a LangGraph ReAct agent with market analysis tools
- [ ] Migrate `QuantModeler` to a LangGraph ReAct agent with technical analysis tools
- [ ] Each L2 agent delegates to L3 executors via tool calls (preserving stateless executor pattern)
- [ ] Implement confidence scoring as structured output from each L2 agent

### Adversarial Debate Layer (New — from TradingAgents)
- [ ] Implement `BullishResearcher` agent: receives analyst outputs, argues FOR the proposed action
- [ ] Implement `BearishResearcher` agent: receives analyst outputs, argues AGAINST the proposed action
- [ ] Implement `DebateSynthesizer` node: resolves debate into net position with weighted confidence
- [ ] Debate agents use `claude-haiku-4-5-20251001` (reasoning-focused, no tools needed)

### Risk Gating
- [ ] Migrate `RiskManager` to a LangGraph agent with hard-coded compliance rules + LLM reasoning
- [ ] Risk Manager receives debate-resolved position (not raw analyst outputs)
- [ ] Wire conflict resolution: Risk Manager output gates all trade execution paths

### Agent-Tool Mapping

| L2 Agent | L3 Tools | Skills | Model |
|----------|----------|--------|-------|
| Macro Analyst | `data_fetcher` | `market-environment-analysis`, `economic-indicators` | Haiku 4.5 |
| Quant Modeler | `nautilus_backtest`, `data_fetcher` | `day-trading-skill`, `technical-analysis` | Haiku 4.5 |
| Bullish Researcher | None (reasoning only) | N/A | Haiku 4.5 |
| Bearish Researcher | None (reasoning only) | N/A | Haiku 4.5 |
| Risk Manager | `nautilus_order_router` (gated) | `risk-management`, `position-sizing` | Haiku 4.5 |

---

## Phase 3: L3 Executors — NautilusTrader Integration

**Goal:** L3 executors become deterministic LangChain tools backed by NautilusTrader (Rust+Python, 20.9k stars) for production-grade execution and backtesting. Zero token cost for all L3 operations.

### 3a: NautilusTrader Core Setup
- [ ] Install and configure NautilusTrader: `pip install nautilus_trader`
- [ ] Configure venue adapters for supported exchanges (Binance, Kraken — matching `swarm_config.yaml:integrations`)
- [ ] Set up data catalog for historical data ingestion (replaces yfinance for backtesting)
- [ ] Configure risk engine with limits from `swarm_config.yaml:risk_limits`

### 3b: Backtester Migration
- [ ] Replace custom `Backtester` (`src/agents/l3_executor.py`) with NautilusTrader backtest engine
- [ ] Wrap as LangChain tool with nanosecond-resolution simulation
- [ ] Integrate strategy implementations from quant-trading repo (MACD, RSI, Bollinger, pair trading)
- [ ] Add realistic transaction costs, slippage modeling, and partial fill simulation (currently assumed frictionless)

### 3c: Order Router Migration
- [ ] Replace custom `OrderRouter` (`src/agents/l3_executor.py`) with NautilusTrader execution engine
- [ ] Gain advanced order types (IOC, FOK, GTC), contingency orders (OCO, OUO, OTO), and iceberg execution
- [ ] Wire multi-venue routing: execute across Binance + Kraken simultaneously
- [ ] Integrate NautilusTrader's built-in position tracking and risk engine

### 3d: Data Fetcher
- [ ] Convert `DataFetcher` to LangChain tool wrapping NautilusTrader data adapters + yfinance fallback
- [ ] Use NautilusTrader's data catalog for tick-level and OHLCV data

### 3e: Strategy Tools (from quant-trading)
- [ ] Wrap quant-trading strategy implementations as LangChain tools:
  - `technical_analysis`: MACD, RSI, Bollinger Bands, Parabolic SAR, Heikin-Ashi
  - `statistical_arbitrage`: Pair trading (cointegration-based)
  - `risk_simulation`: Monte Carlo simulation, VIX calculator
- [ ] Preserve existing `src/skills/` directory — register as LangChain tools alongside new tools

### Example Tool Registration

```python
from langchain_core.tools import tool
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.model.identifiers import InstrumentId, Venue

@tool
def fetch_market_data(symbol: str, timeframe: str = "1H", lookback_days: int = 30) -> dict:
    """Fetch OHLCV market data for a symbol. Returns dict with prices, volume, and timestamps."""
    # NautilusTrader data adapter with yfinance fallback
    adapter = get_data_adapter(symbol)
    return adapter.fetch(symbol, timeframe, lookback_days)

@tool
def run_backtest(strategy: dict, symbol: str, start_date: str, end_date: str) -> dict:
    """Execute a historical backtest with NautilusTrader engine.
    Returns PnL distribution, drawdown metrics, Sharpe ratio, with realistic fills and slippage."""
    engine = BacktestEngine()
    # Configure with transaction costs, slippage, and position limits
    configure_engine(engine, strategy, symbol, start_date, end_date)
    engine.run()
    return extract_results(engine)

@tool
def submit_order(symbol: str, direction: str, size: float, order_type: str = "MARKET",
                 stop_loss: float = None, take_profit: float = None) -> dict:
    """Submit order via NautilusTrader execution engine.
    Supports advanced order types (IOC, FOK, GTC) and contingency orders (OCO)."""
    # Routes to appropriate venue based on symbol
    exec_client = get_execution_client(symbol)
    return exec_client.submit(direction, size, order_type, stop_loss, take_profit)

@tool
def run_monte_carlo(symbol: str, num_simulations: int = 10000, horizon_days: int = 30) -> dict:
    """Run Monte Carlo price simulation. Returns probability distributions and VaR estimates."""
    # Adapted from quant-trading repo
    return monte_carlo_simulate(symbol, num_simulations, horizon_days)
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
| `src/agents/l3_executor.py:Backtester` | NautilusTrader backtest engine (`src/tools/nautilus_backtest.py`) |
| `src/agents/l3_executor.py:OrderRouter` | NautilusTrader execution engine (`src/tools/nautilus_execution.py`) |
| `src/agents/l3_executor.py:DataFetcher` | NautilusTrader data adapters + yfinance fallback (`src/tools/data_fetcher.py`) |
| `main.py` `QuantumSwarm` class | LangGraph application with compiled graph |

### Add New

| Path | Purpose |
|------|---------|
| `src/graph/` | LangGraph workflow definitions |
| `src/graph/state.py` | Shared state schema (`SwarmState` with debate fields) |
| `src/graph/orchestrator.py` | L1 graph definition (including debate layer) |
| `src/graph/agents/` | L2 sub-graphs (macro, quant, bullish/bearish researchers, risk) |
| `src/graph/debate.py` | Adversarial debate logic (bullish/bearish/synthesizer) |
| `src/graph/safety.py` | Circuit breakers, budget tracking |
| `src/tools/` | LangChain tool wrappers for all L3 executors |
| `src/tools/nautilus_backtest.py` | NautilusTrader backtest engine wrapper |
| `src/tools/nautilus_execution.py` | NautilusTrader order management wrapper |
| `src/tools/data_fetcher.py` | Market data tool (NautilusTrader + yfinance) |
| `src/tools/strategies/` | Strategy tools adapted from quant-trading repo |
| `src/tools/strategies/technical.py` | MACD, RSI, Bollinger, Parabolic SAR, Heikin-Ashi |
| `src/tools/strategies/statistical.py` | Pair trading, Monte Carlo, VIX calculator |

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

## Dependencies

```
# Core orchestration
langgraph>=0.2.0
langchain-anthropic>=0.3.0
langchain-community>=0.3.0
langsmith>=0.2.0           # optional, for observability

# L3 execution infrastructure
nautilus_trader>=1.210.0    # Rust+Python trading platform (backtest + live execution)

# Data & analysis (existing + new)
yfinance>=0.2.0            # Market data fallback
ccxt>=4.0.0                # Crypto exchange connectivity
numpy>=1.26.0
pandas>=2.2.0

# Strategy tools (from quant-trading patterns)
scipy>=1.12.0              # Statistical tests for pair trading
statsmodels>=0.14.0        # Cointegration, time-series analysis
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LangGraph API changes | Low | Medium | Pin version, abstract behind interfaces |
| OpenClaw + LangGraph integration friction | Medium | Medium | Clean separation: OpenClaw handles external I/O, LangGraph handles internal orchestration |
| Token cost increase from debate layer (2 extra LLM calls) | Medium | Low | Haiku 4.5 for researchers (~$0.001/call); debate only triggers on trade intents, not analysis-only |
| NautilusTrader learning curve (Rust internals) | Medium | Medium | Use Python-only interface; treat as black-box execution engine behind LangChain tool wrappers |
| NautilusTrader breaking changes | Low | Medium | Pin version; abstract behind tool interface so engine can be swapped |
| Migration disrupts working features | Low | High | Phased approach; each phase independently testable |
| LangSmith vendor lock-in | Low | Low | LangSmith is optional; standard Python logging as fallback |
