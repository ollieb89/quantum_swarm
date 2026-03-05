---
project: quantum-swarm
updated: '2026-03-05'
phase:
  current: 2
  name: L2 Domain Managers & Adversarial Debate Layer
  status: in_progress
  started: '2026-03-05'
  completed: null
  current_plan: 02-02
  plans_completed:
    - "02-01: L2 Analyst Agents (MacroAnalyst + QuantModeler ReAct nodes)"
    - "02-02: Adversarial Researcher Nodes (BullishResearcher + BearishResearcher with BudgetedTool)"
  blockers: []
previous_phase:
  number: 1
  name: Core Orchestration Migration (L1 Orchestrator)
  status: completed
  completed: '2026-03-05'
architecture:
  runtime: langgraph
  pattern: hierarchical_swarm
  layers:
    l1: strategic_orchestrator
    l2: domain_managers
    l3: stateless_executors
  communication: file_protocol
  dashboard: flask_socketio
paths:
  entry: main.py
  graph_state: src/graph/state.py
  orchestrator: src/graph/orchestrator.py
  l2_agents: src/agents/__init__.py
  l3_executors: src/agents/l3_executor.py
  config: config/swarm_config.yaml
  planning: .planning/
  vault: quantum-swarm/
health:
  status: yellow
  risks:
  - Schema drift if payload format changes without script updates
  blockers: []
active_decisions:
- LangGraph over custom orchestration
- JSON-driven Obsidian tracking updates
- Conventional commits for automated documentation
- Single state layer with transclusion projections
- claude-haiku-4-5-20251001 for L2 analyst agents (fast, cost-efficient)
- ReAct agents compiled as module-level singletons to avoid per-invocation overhead
- L3 executor capabilities wrapped as @tool functions for ReAct agent tool discovery
- Manual ReAct loop for researchers so BudgetedTool instances are dispatched directly
- BudgetedTool instances created fresh inside node functions to reset call counters per invocation
- ToolCache keyed by (tool_name, frozenset(args)) for cross-agent deduplication within process
---

# Project State

> Machine-readable state lives in YAML frontmatter above.
> This markdown body is auto-generated — do not edit manually.

## Current Phase

**Phase 2** — L2 Domain Managers & Adversarial Debate Layer
- Status: In Progress
- Started: 2026-03-05
- Current Plan: 02-02 (completed 2026-03-05)
- Next Plan: 02-03
- Previous: Phase 1 (Core Orchestration Migration (L1 Orchestrator)) — Completed 2026-03-05

## Health

Status: Yellow

### Risks
- [0] Schema drift if payload format changes without script updates

## Architecture

- Runtime: Langgraph
- Pattern: Hierarchical Swarm (Strategic Orchestrator > Domain Managers > Stateless Executors)
- Communication: File Protocol
- Dashboard: Flask Socketio

## Key Paths

| Component | Path |
|-----------|------|
| Entry | `main.py` |
| Graph State | `src/graph/state.py` |
| Orchestrator | `src/graph/orchestrator.py` |
| L2 Agents | `src/agents/__init__.py` |
| L3 Executors | `src/agents/l3_executor.py` |
| Config | `config/swarm_config.yaml` |
| Planning | `.planning/` |
| Vault | `quantum-swarm/` |
