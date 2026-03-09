---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: "Reliable Infrastructure"
status: active
stopped_at: Defining requirements
last_updated: "2026-03-09"
last_activity: 2026-03-09 — Milestone v1.5 started
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

> Machine-readable state lives in YAML frontmatter above.
> This markdown body is auto-generated — do not edit manually.

## Milestone

**v1.5 Reliable Infrastructure** — ACTIVE

Previous: v1.4 Beta: Observable Swarm — SHIPPED 2026-03-09 (4 phases, 10 plans)

## Current Phase

Not started (defining requirements)

Progress: [░░░░░░░░░░] 0%

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-09)

**Core value:** Institutional-quality trade signal generation through adversarial AI debate, with self-improving memory rules validated by backtesting, hard compliance guardrails, and immutable per-trade audit trails
**Current focus:** Stabilize foundation — fix deps, rebalance KAMI, add PersonaScore 5D, token cost tracking, Gemini circuit breakers

## Architecture

- Runtime: Python 3.12 (uv managed)
- Pattern: LangGraph Orchestration (L1 -> L2 Fan-out/Fan-in -> L3 Chain)
- Communication: LangGraph `SwarmState` + Filesystem Blackboard
- Persistence: PostgreSQL (AsyncPostgresSaver) for state + Trade Warehouse + cycle_snapshots
- LLM: Google Gemini (gemini-2.5-flash)

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
| Cycles | `data/cycles/` |

## Health

Status: Yellow
- v1.4 shipped: 300+ tests passing, 0 failures (excluding pre-existing env issues)
- 13 tests broken due to env issues (ccxt, chromadb, pytest-asyncio) — P0 for v1.5
- KAMI Accuracy frozen at 0.5 (30% of merit inert) — P0 for v1.5

## Session Continuity

Last session: 2026-03-09
Stopped at: Defining requirements for v1.5
Resume file: None
