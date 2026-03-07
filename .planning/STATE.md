---
phase:
  current: 10
  name: Rule Validation Harness
  status: not_started
  started: ''
  completed: ''
  blockers: []
milestone:
  current: v1.2
  name: Risk Governance and Rule Validation
  status: active
  started: 2026-03-06
  previous: v1.1
  previous_name: Self-Improvement Loop
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
updated: '2026-03-07'
---

# Project State

> Machine-readable state lives in YAML frontmatter above.
> This markdown body is auto-generated — do not edit manually.

## Milestone

**v1.2 Risk Governance and Rule Validation** — ACTIVE (started 2026-03-06)

Previous: v1.1 Self-Improvement Loop — SHIPPED 2026-03-06 (169 tests, 3 phases)

## Current Phase

Phase: 10 — Rule Validation Harness
Plan: TBD
Status: Not started
Last activity: 2026-03-07 — Phase 04-02 completed; KnowledgeBase lazy init refactor (get_kb() getter, no module-level singleton).

## Progress

```
v1.2: [=====     ] 2/4 phases complete
Phase 8: Portfolio Risk Governance     — Complete (2026-03-06)
Phase 9: Structured Memory Registry    — Complete (2026-03-06)
Phase 10: Rule Validation Harness      — Not started
Phase 11: Explainability & Decision Cards — Not started
```

## Health

Status: Green
- v1.2 Phase 9 complete: Freeform memory replaced by governed JSON registry.
- 176 tests passing (including 4 new phase 9 tests).
- RuleGenerator now produces structured, validated rules with lifecycle states.
- Architecture stable: LangGraph + Gemini + psycopg3.

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-06 — Milestone v1.1 started)

**Core value:** Institutional-quality trade signal generation through adversarial AI debate, with immutable audit trails and hard compliance guardrails
**Current focus:** v1.1 — Phase 5: Quant Alpha Intelligence (ANALY-03)

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
- KnowledgeBase lazy init: chromadb/duckdb imported inside __init__; get_kb() getter replaces module-level singleton (2026-03-07)
- psycopg3 async throughout (not psycopg2)

## v1.1 Phase Dependency Chain

Phase 5 (ANALY-03) -> Phase 6 (RISK-03, RISK-05, RISK-06) -> Phase 7 (MEM-02, MEM-03)

Phase 6 depends on Phase 5: ATR is a technical indicator; the quant-alpha-intelligence skill provides the
calculation infrastructure that Phase 6's stop-loss logic calls into.

Phase 7 depends on Phase 6: meaningful weekly review requires real execution records that include
stop-loss data written to the trade warehouse by Phase 6.
