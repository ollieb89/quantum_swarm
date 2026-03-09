---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: Reliable Infrastructure
status: Green
stopped_at: Completed 30-02-PLAN.md
last_updated: "2026-03-09T23:48:15.199Z"
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 8
  completed_plans: 8
  percent: 98
---

# Project State

> Machine-readable state lives in YAML frontmatter above.
> This markdown body is auto-generated -- do not edit manually.

## Milestone

**v1.5 Reliable Infrastructure** -- ACTIVE

Previous: v1.4 Beta: Observable Swarm -- SHIPPED 2026-03-09 (4 phases, 10 plans)

## Current Phase

Phase 30 of 31 (KAMI Weight Rebalance + Token Tracking) -- Ready to plan

Progress: [████████████████████] 43/44 plans (98%)

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-10)

**Core value:** Institutional-quality trade signal generation through adversarial AI debate, with self-improving memory rules validated by backtesting, hard compliance guardrails, and immutable per-trade audit trails
**Current focus:** Phase 30 -- KAMI Weight Rebalance + Token Tracking

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
- Phase 29 complete: PersonaScore 5D + KAMI fidelity wiring verified
- All 12 merit_updater tests passing (including 4 fixed pre-existing mocks)
- KAMI Accuracy frozen at 0.5 (30% of merit inert) -- P0 for Phase 30

## Decisions

- Separate CircuitBreaker instance for judge calls (threshold=3, cooldown=30s) isolates from graph breaker
- persona_scores excluded from audit hash chain (infrastructure metadata, not MiFID II trade data)
- Fallback on evaluation failure: spread previous composite across all 5 dims, or 0.5 if no history
- KAMI fidelity reads continuous PersonaScore composite; falls back to binary soul check when None
- [Phase 30]: Shift 22% weight from Accuracy to Fidelity to eliminate inert composite contribution
- [Phase 30]: agent_id Optional[str]=None for backward compat; token_usage excluded from audit hash; BudgetManager single authoritative source

## Session Continuity

Last session: 2026-03-09T23:48:15.198Z
Stopped at: Completed 30-02-PLAN.md
Resume file: None
