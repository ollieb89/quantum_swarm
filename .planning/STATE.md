---
phase:
  current: 4
  name: Memory & Institutional Compliance
  status: complete
  started: 2026-03-06
  completed: 2026-03-06
  blockers: []
previous_phase:
  number: 3
  name: Market Execution & Data (L3)
  status: completed
  completed: 2026-03-06
health:
  status: green
  risks: []
  blockers: []
architecture:
  runtime: python
  pattern: langgraph_orchestration
  layers:
    l1: strategic_intent_classifier
    l2: adversarial_debate_analysis
    l3: risk_gated_execution
  communication: langgraph_state_plus_blackboard
  persistence: postgresql
  dashboard: html
paths:
  main: main.py
  config: config/
  agents: src/graph/agents/
  orchestrator: src/graph/orchestrator.py
  planning: .planning/
  data: data/
updated: '2026-03-06'
---

# Project State

> Machine-readable state lives in YAML frontmatter above.
> This markdown body is auto-generated — do not edit manually.

## Current Phase

**Phase 4** — Memory & Institutional Compliance
- Status: Complete
- Completed: 2026-03-06

## Health

Status: Green
- Phase 4 successfully verified: persistence, audit logs, and guardrails passing.
- Total test suite: 113 tests passing.
- PostgreSQL infrastructure operational (Port 5433).

## Architecture

- Runtime: Python 3.12 (uv managed)
- Pattern: LangGraph Orchestration (L1 -> L2 Fan-out/Fan-in -> L3 Chain)
- Communication: LangGraph `SwarmState` + Filesystem Blackboard.
- Persistence: PostgreSQL (AsyncPostgresSaver) for state + Trade Warehouse.
- Dashboard: Html/Flask

## Key Paths

| Component | Path |
|-----------|------|
| Main | `main.py` |
| Config | `config/` |
| Graph | `src/graph/` |
| Agents | `src/graph/agents/` |
| Planning | `.planning/` |
| Data | `data/` |
