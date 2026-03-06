---
phase:
  current: not_started
  name: ""
  status: pending
  started: ""
  completed: ""
  blockers: []
milestone:
  current: v1.1
  name: Self-Improvement Loop
  status: active
  started: 2026-03-06
  previous: v1.0
  previous_name: MVP
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

## Milestone

**v1.1 Self-Improvement Loop** — ACTIVE (started 2026-03-06)

Previous: v1.0 MVP — SHIPPED 2026-03-06 (155 tests, 4 phases, ~14,600 LOC)

## Current Phase

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-06 — Milestone v1.1 started

## Health

Status: Green
- v1.0 shipped: 155 tests passing, all 4 phases complete
- PostgreSQL infrastructure operational (Port 5433)
- Architecture stable: LangGraph + Gemini + psycopg3

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-06 — Milestone v1.1 started)

**Core value:** Institutional-quality trade signal generation through adversarial AI debate, with immutable audit trails and hard compliance guardrails
**Current focus:** v1.1 — Self-improvement loop, stop-loss enforcement, quant alpha skill

## Architecture

- Runtime: Python 3.12 (uv managed)
- Pattern: LangGraph Orchestration (L1 -> L2 Fan-out/Fan-in -> L3 Chain)
- Communication: LangGraph `SwarmState` + Filesystem Blackboard
- Persistence: PostgreSQL (AsyncPostgresSaver) for state + Trade Warehouse
- LLM: Google Gemini (gemini-2.0-flash)

## Key Paths

| Component | Path |
|-----------|------|
| Main | `main.py` |
| Config | `config/` |
| Graph | `src/graph/` |
| Agents | `src/graph/agents/` |
| Planning | `.planning/` |
| Data | `data/` |

## Accumulated Context (from v1.0)

- Lazy LLM init pattern required for all module-level LLM instances (GOOGLE_API_KEY not available at import)
- pytest binary missing from venv — use `.venv/bin/python3.12 -m pytest`
- Python 3.12: use `asyncio.run()` not `asyncio.get_event_loop().run_until_complete()`
- ccxt package broken in env; chromadb and pytest-asyncio missing — known env issues, not regressions
- psycopg3 async throughout (not psycopg2)
