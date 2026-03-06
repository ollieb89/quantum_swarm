---
phase:
  current: 4
  name: Memory & Institutional Compliance
  status: not_started
  started: null
  completed: null
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
- Status: Not Started
- Previous: Phase 3 (Market Execution & Data) — Completed 2026-03-06

## Health

Status: Green
- Full suite: 106 tests passing (2026-03-06).
- Phase 3 smoke run verified with live GOOGLE_API_KEY.
- Token tracking wired across all L2 agent nodes (analysts + researchers).
- Blackboard TOCTOU fixed; test regressions from partial() injection resolved.

## Architecture

- Runtime: Python 3.12 (uv managed)
- Pattern: LangGraph Orchestration (L1 -> L2 Fan-out/Fan-in -> L3 Chain)
- Communication: LangGraph `SwarmState` with supplementary Filesystem Blackboard for persistent risk logs.
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
