---
project: quantum-swarm
updated: '2026-03-05'
phases:
- number: 0
  name: LangGraph Migration Assessment & Setup
  status: completed
  started: '2026-03-05'
  completed: '2026-03-05'
  plan_file: PHASES/phase-0.md
  deliverables:
  - langgraph, langchain-anthropic, nautilus_trader dependencies
  - Codebase audit and migration mapping
  - Adversarial debate layer design
  - LangGraph PoC (src/poc/langgraph_orchestrator_poc.py)
  - NautilusTrader PoC (src/poc/nautilus_integration_poc.py)
- number: 1
  name: Core Orchestration Migration (L1 Orchestrator)
  status: completed
  started: '2026-03-05'
  completed: '2026-03-05'
  plan_file: PHASES/phase-1.md
  deliverables:
  - SwarmState definition (src/graph/state.py)
  - L1 nodes & routing logic
  - LangGraph StateGraph orchestrator (src/graph/orchestrator.py)
  - Integration with OpenClaw & main.py
  - Testing & validation
- number: 2
  name: L2 Domain Managers & Adversarial Debate Layer
  status: completed
  started: '2026-03-05'
  completed: '2026-03-05'
  plan_file: PHASES/phase-2.md
  plans_completed:
  - 02-01: L2 Analyst Agents (MacroAnalyst + QuantModeler ReAct nodes, analyst_tools)
  - 02-02: Adversarial Researcher Nodes (BullishResearcher + BearishResearcher with BudgetedTool and ToolCache)
  - 02-03: Debate Synthesis (DebateSynthesizer node, fan-out/fan-in wiring, weighted_consensus_score)
  - 02-04: Risk Gating (RiskManager node, conditional edge with >0.6 threshold, route_after_debate)
  - 02-05: Integration Tests (3-scenario adversarial debate test suite, 11/11 tests passing)
  deliverables:
  - Migrate MacroAnalyst, QuantModeler, RiskManager to LangGraph subgraphs
  - Implement adversarial debate (bullish/bearish thesis resolution)
  - Wire consensus scoring into graph state
  - Full integration test suite for debate pipeline (tests/test_adversarial_debate.py)
- number: 3
  name: L3 Executors & NautilusTrader Integration
  status: completed
  started: '2026-03-06'
  completed: '2026-03-06'
  plan_file: PHASES/03-l3-executors-nautilus-trader-integration
  plans_count: 5
  plans_completed:
  - 03-00: Environment setup — NautilusTrader install, Pydantic data models, test stubs
  - 03-01: DataFetcher node — yfinance, ccxt, news sentiment, economic calendar, Dexter bridge
  - 03-02: Backtester node — NautilusTrader BacktestEngine wrapped in asyncio.to_thread
  - 03-03: OrderRouter node — paper simulation + IB live equities + Binance live crypto
  - 03-04: TradeLogger + self-improvement loop + orchestrator wiring (human checkpoint approved)
  deliverables:
  - Migrate DataFetcher, Backtester, OrderRouter to real LangGraph async nodes
  - Integrate NautilusTrader BacktestEngine (paper + live execution)
  - IB adapter for live equities, Binance adapter for live crypto
  - Dexter fundamentals bridge (async subprocess)
  - Implement trade logging and self-improvement loop via trade_history in SwarmState
- number: 4
  name: Dashboard & Observability
  status: not_started
  started: null
  completed: null
  plan_file: null
  deliverables:
  - Real-time graph execution visualization
  - LangSmith integration for tracing
  - Alert system for risk threshold breaches
---

# Roadmap

> Machine-readable phase data lives in YAML frontmatter above.
> This markdown body is auto-generated — do not edit manually.

## Phase 0 — LangGraph Migration Assessment & Setup [COMPLETED]
- Completed: 2026-03-05
- Plan: [[planning/PHASES/phase-0]]

## Phase 1 — Core Orchestration Migration (L1 Orchestrator) [COMPLETED]
- Completed: 2026-03-05
- Plan: [[planning/PHASES/phase-1]]

## Phase 2 — L2 Domain Managers & Adversarial Debate Layer [COMPLETED]
- Started: 2026-03-05
- Completed: 2026-03-05
- Plan: [[planning/PHASES/phase-2]]
- Plans completed: 02-01 (L2 Analyst Agents), 02-02 (Adversarial Researcher Nodes), 02-03 (Debate Synthesis), 02-04 (Risk Gating), 02-05 (Integration Tests)
- Deliverables:
  - Migrate MacroAnalyst, QuantModeler, RiskManager to LangGraph subgraphs
  - Implement adversarial debate (bullish/bearish thesis resolution)
  - Wire consensus scoring into graph state
  - Full integration test suite for debate pipeline (tests/test_adversarial_debate.py)

## Phase 3 — L3 Executors & NautilusTrader Integration [COMPLETED]
- Started: 2026-03-06
- Completed: 2026-03-06
- Plans: 5/5 complete
- Plans:
  - [x] 03-00-PLAN.md — Environment setup: NautilusTrader install, Pydantic data models, test stubs
  - [x] 03-01-PLAN.md — DataFetcher node: yfinance, ccxt, news sentiment, economic calendar, Dexter bridge
  - [x] 03-02-PLAN.md — Backtester node: NautilusTrader BacktestEngine wrapped in asyncio.to_thread
  - [x] 03-03-PLAN.md — OrderRouter node: paper simulation + IB live equities + Binance live crypto
  - [x] 03-04-PLAN.md — TradeLogger + self-improvement loop + orchestrator wiring (human checkpoint approved)
- Deliverables:
  - Migrate DataFetcher, Backtester, OrderRouter to real LangGraph async nodes
  - Integrate NautilusTrader BacktestEngine (paper + live execution)
  - IB adapter for live equities, Binance for crypto (Alpaca has no NT adapter)
  - Dexter fundamentals bridge (async subprocess, 90s timeout)
  - Implement trade logging and self-improvement loop via trade_history in SwarmState

## Phase 4 — Dashboard & Observability [NOT STARTED]
- Deliverables:
  - Real-time graph execution visualization
  - LangSmith integration for tracing
  - Alert system for risk threshold breaches
