---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Reliable Infrastructure
status: Green
stopped_at: Phase 28 context gathered
last_updated: "2026-03-09T17:32:30.883Z"
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 2
  completed_plans: 2
  percent: 20
---

# Project State

> Machine-readable state lives in YAML frontmatter above.
> This markdown body is auto-generated -- do not edit manually.

## Milestone

**v1.5 Reliable Infrastructure** -- ACTIVE

Previous: v1.4 Beta: Observable Swarm -- SHIPPED 2026-03-09 (4 phases, 10 plans)

## Current Phase

Phase 27 of 31 (Environment Stabilization) -- COMPLETE (2 of 2 plans done)

Progress: [==........] 20%

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-09)

**Core value:** Institutional-quality trade signal generation through adversarial AI debate, with self-improving memory rules validated by backtesting, hard compliance guardrails, and immutable per-trade audit trails
**Current focus:** Phase 27 complete -- env deps fixed; ready for Phase 28

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

Status: Green
- Phase 27 complete: 680 passed, 4 skipped, 0 failures
- Environment issues resolved (ccxt lazy init, asyncio_mode=auto, PG skipif)
- KAMI Accuracy frozen at 0.5 (30% of merit inert) -- P0 for Phase 30

## Session Continuity

Last session: 2026-03-09T17:32:30.882Z
Stopped at: Phase 28 context gathered
Resume file: .planning/phases/28-gemini-api-circuit-breaker/28-CONTEXT.md
