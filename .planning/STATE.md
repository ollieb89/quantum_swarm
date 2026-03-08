---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: MBS Persona System
status: active
last_updated: "2026-03-08"
last_activity: 2026-03-08 — Roadmap created; 5 phases defined (15-19), 18 requirements mapped
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

> Machine-readable state lives in YAML frontmatter above.
> This markdown body is auto-generated — do not edit manually.

## Milestone

**v1.3 MBS Persona System** — ACTIVE (started 2026-03-08)

Previous: v1.2 Risk Governance — SHIPPED 2026-03-08 (260+ tests, 6 phases)

## Current Phase

Phase: 15 of 19 (Soul Foundation — ready to plan)
Plan: —
Status: Ready to plan
Last activity: 2026-03-08 — Roadmap created; Phase 15 is next

## Progress

```
v1.3: [__________] 0/5 phases complete
```

## Health

Status: Green
- v1.2 shipped clean: 260+ tests passing, 0 failures (excluding 2 known-broken env files)
- InstitutionalGuard wired and verified; MEM-06 gate order fixed (Phase 14 complete)
- Architecture stable: LangGraph + Gemini + psycopg3

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-08 after v1.3 milestone start)

**Core value:** Institutional-quality trade signal generation through adversarial AI debate, with self-improving memory rules validated by backtesting, hard compliance guardrails, and immutable per-trade audit trails
**Current focus:** v1.3 Phase 15 — Soul Foundation

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

## Accumulated Context (v1.3 critical patterns)

- `system_prompt` and `active_persona` must NEVER enter `state["messages"]` — `operator.add` reducer causes unbounded accumulation and corrupts MiFID II audit trail
- `AUDIT_EXCLUDED_FIELDS = {"system_prompt", "active_persona", "soul_sync_context"}` must be set in `AuditLogger` before `macro_analyst_node` is wired into the graph
- `autouse` fixture calling `load_soul.cache_clear()` before/after every test is mandatory — add to `tests/core/conftest.py` in Phase 15 Plan 01 before writing any soul tests
- Skeleton agents with empty `IDENTITY.md` receive `weight_multiplier=0.0` in DebateSynthesizer — prevents cold-start EMA 0.5 from diluting established agent scores
- Agent Church must be a standalone script (`python -m src.core.agent_church`), not a LangGraph node — blocking node causes deadlock and L1 self-approval conflict-of-interest
- ARS suspension gates MEMORY.md evolution writes only — no code path to `order_router_node` or `route_after_institutional_guard` (pitfall 7 from research)
- All soul file I/O uses synchronous `Path.read_text()` — `asyncio.run()` inside node functions is a known project-breaking pattern (MEM-06 defect)
- `lru_cache` + `dataclasses.dataclass(frozen=True)` for SoulLoader — frozen required for hashability and concurrent fan-out read safety
- No new dependencies required — all features achievable with existing `pyproject.toml` (numpy, psycopg, functools, difflib, re, pathlib, collections)

## v1.3 Phase Dependency Chain

Phase 15 (Soul Foundation) → Phase 16 (KAMI Merit Index) → Phase 17 (MEMORY.md Evolution + Agent Church) → Phase 18 (Theory of Mind Soul-Sync) → Phase 19 (ARS Drift Auditor)

Phase 18 depends on Phase 17: Soul-Sync reads MEMORY.md context; merit scores in peer summaries only meaningful after KAMI is live.
Phase 19 depends on Phase 17: ARS reads `[KAMI_DELTA:]` markers from MEMORY.md structured logs written by EVOL-01.
