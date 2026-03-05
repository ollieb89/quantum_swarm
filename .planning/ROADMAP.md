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
  status: in_progress
  started: '2026-03-05'
  completed: null
  plan_file: PHASES/phase-2.md
  plans_completed:
  - 02-01: L2 Analyst Agents (MacroAnalyst + QuantModeler ReAct nodes, analyst_tools)
  - 02-02: Adversarial Researcher Nodes (BullishResearcher + BearishResearcher with BudgetedTool and ToolCache)
  - 02-03: Debate Synthesis (DebateSynthesizer node, fan-out/fan-in wiring, weighted_consensus_score)
  - 02-04: Risk Gating (RiskManager node, conditional edge with >0.6 threshold, route_after_debate)
  deliverables:
  - Migrate MacroAnalyst, QuantModeler, RiskManager to LangGraph subgraphs
  - Implement adversarial debate (bullish/bearish thesis resolution)
  - Wire consensus scoring into graph state
- number: 3
  name: L3 Executors & NautilusTrader Integration
  status: not_started
  started: null
  completed: null
  plan_file: null
  deliverables:
  - Migrate DataFetcher, Backtester, OrderRouter
  - Integrate NautilusTrader for live execution
  - Implement trade logging and self-improvement loop
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

## Phase 2 — L2 Domain Managers & Adversarial Debate Layer [IN PROGRESS]
- Started: 2026-03-05
- Plan: [[planning/PHASES/phase-2]]
- Plans completed: 02-01 (L2 Analyst Agents), 02-02 (Adversarial Researcher Nodes), 02-03 (Debate Synthesis), 02-04 (Risk Gating)
- Deliverables:
  - Migrate MacroAnalyst, QuantModeler, RiskManager to LangGraph subgraphs
  - Implement adversarial debate (bullish/bearish thesis resolution)
  - Wire consensus scoring into graph state

## Phase 3 — L3 Executors & NautilusTrader Integration [NOT STARTED]
- Deliverables:
  - Migrate DataFetcher, Backtester, OrderRouter
  - Integrate NautilusTrader for live execution
  - Implement trade logging and self-improvement loop

## Phase 4 — Dashboard & Observability [NOT STARTED]
- Deliverables:
  - Real-time graph execution visualization
  - LangSmith integration for tracing
  - Alert system for risk threshold breaches
