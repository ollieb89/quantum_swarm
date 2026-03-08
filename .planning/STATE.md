---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: "Beta: Observable Swarm"
status: active
last_updated: "2026-03-08T23:00:00.000Z"
last_activity: "2026-03-08 — Milestone v1.4 started"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

> Machine-readable state lives in YAML frontmatter above.
> This markdown body is auto-generated — do not edit manually.

## Milestone

**v1.4 Beta: Observable Swarm** — ACTIVE

Previous: v1.3 MBS Persona System — SHIPPED 2026-03-08 (300+ tests, 8 phases)

## Current Phase

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-08 — Milestone v1.4 started

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-08)

**Core value:** Institutional-quality trade signal generation through adversarial AI debate, with self-improving memory rules validated by backtesting, hard compliance guardrails, and immutable per-trade audit trails
**Current focus:** Making the institution observable — fully populated personas, end-to-end pipeline, cycle replay

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
| Soul files | `src/core/souls/` |
| Planning | `.planning/` |
| Data | `data/` |

## Health

Status: Green
- v1.3 shipped: 300+ tests passing, 0 failures (excluding pre-existing env files)
- Full MBS persona system live: SoulLoader, KAMI, Agent Church, Soul-Sync, ARS
- Architecture stable: LangGraph + Gemini + psycopg3

## Accumulated Context

- Known env issues: broken `ccxt`, missing `chromadb` and `pytest-asyncio` (~13 tests affected, not regressions)
- Tech debt from v1.3: skeleton agents have no YAML drift_guard block, Nyquist VALIDATION.md partial/missing for phases 15-22, thesis_records/ stub for deferred Accuracy dimension
- 4 of 5 agent personas are skeletons (only AXIOM fully populated)
