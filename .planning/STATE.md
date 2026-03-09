---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Reliable Infrastructure
status: Yellow
stopped_at: Phase 27 context gathered
last_updated: "2026-03-09T15:07:49.237Z"
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

> Machine-readable state lives in YAML frontmatter above.
> This markdown body is auto-generated -- do not edit manually.

## Milestone

**v1.5 Reliable Infrastructure** -- ACTIVE

Previous: v1.4 Beta: Observable Swarm -- SHIPPED 2026-03-09 (4 phases, 10 plans)

## Current Phase

Phase 27 of 31 (Environment Stabilization) -- ready to plan

Progress: [..........] 0%

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-09)

**Core value:** Institutional-quality trade signal generation through adversarial AI debate, with self-improving memory rules validated by backtesting, hard compliance guardrails, and immutable per-trade audit trails
**Current focus:** Phase 27 -- fix broken ccxt/chromadb/pytest-asyncio deps to unblock all subsequent phases

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
- 13 tests broken due to env issues (ccxt, chromadb, pytest-asyncio) -- P0 for Phase 27
- KAMI Accuracy frozen at 0.5 (30% of merit inert) -- P0 for Phase 30

## Session Continuity

Last session: 2026-03-09T15:07:49.236Z
Stopped at: Phase 27 context gathered
Resume file: .planning/phases/27-environment-stabilization/27-CONTEXT.md
