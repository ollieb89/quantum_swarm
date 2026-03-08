---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: MBS Persona System
status: completed
last_updated: "2026-03-08T15:00:46.527Z"
last_activity: "2026-03-08 — 18-02 complete: soul_sync_handshake_node (sync barrier, zero LLM calls) + orchestrator rewire (researchers→handshake→debate_synthesizer) + USER.md empathetic refutation few-shots for MOMENTUM and CASSANDRA; 16/16 test_soul_sync tests GREEN; Phase 18 TOM-01 + TOM-02 satisfied; next: Phase 19 (ARS Drift Auditor)"
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 11
  completed_plans: 11
---

# Project State

> Machine-readable state lives in YAML frontmatter above.
> This markdown body is auto-generated — do not edit manually.

## Milestone

**v1.3 MBS Persona System** — ACTIVE (started 2026-03-08)

Previous: v1.2 Risk Governance — SHIPPED 2026-03-08 (260+ tests, 6 phases)

## Current Phase

Phase: 18 of 19 (Theory of Mind Soul-Sync — COMPLETE)
Plan: 02/02 complete
Status: Phase 18 complete — soul_sync_handshake_node wired as barrier between researchers and debate_synthesizer; USER.md empathetic refutation authored for MOMENTUM and CASSANDRA; 16/16 tests GREEN; TOM-01 + TOM-02 satisfied; next: Phase 19 (ARS Drift Auditor)
Last activity: 2026-03-08 — 18-02 complete: soul_sync_handshake_node (sync barrier, zero LLM calls) + orchestrator rewire + USER.md few-shots; 16/16 soul_sync tests GREEN; Phase 18 TOM-01 + TOM-02 fully satisfied

## Decisions

- **[15-01]** Added `AUDIT_EXCLUDED_FIELDS` frozenset to `AuditLogger` in Plan 01 (not Plan 03) — ensures no soul data enters the hash chain even during incremental development between plans
- **[15-01]** Added `system_prompt` and `active_persona` Optional[str] fields to `SwarmState` in Plan 01 — required for `TestSwarmStateFields` to pass in this plan's verify step; backward-compatible (None default)
- [Phase 15-02]: MacroAnalyst wired to call load_soul('macro_analyst') and return system_prompt + active_persona in state — SOUL-05 injection at node level
- [Phase 15-02]: Soul files use free-flowing prose with no YAML frontmatter; H1 for persona name, H2 for canonical sections — locked pattern for Phase 17 Agent Church diff targeting
- [Phase 15]: _strip_excluded() added as module-level function in audit_logger — _calculate_hash and verify_chain strip soul fields consistently before SHA-256 computation
- [Phase 15]: soul_system_message added as Optional param to _run_researcher_agent — soul prepended locally to messages list, never written to state['messages']
- [Phase 16-kami-merit-index]: round(raw, 10) before clamp in compute_merit eliminates IEEE 754 jitter (0.30+0.35+0.25+0.10 != exactly 1.0 in Python float arithmetic)
- [Phase 16-kami-merit-index]: merit_scores is plain Optional[Dict] in SwarmState with no Annotated reducer — merit_loader overwrites per cycle, not accumulates
- [Phase 16-kami-merit-index]: evolution_suspended column pre-declared in agent_merit_scores DDL to avoid ALTER TABLE migration in Phase 19 ARS-02
- [Phase 16-02]: merit_updater returns {} on DB failure — DB and SwarmState merit_scores kept strictly in sync
- [Phase 16-02]: Accuracy dimension is never updated in-cycle — deferred to post-trade resolution in a later phase
- [Phase 16-02]: merit_loader is new graph entry point replacing classify_intent — merit scores loaded before any analysis
- [Phase 16-kami-merit-index]: Character-length proxy (len(text)) fully removed from DebateSynthesizer — merit composite is the only strength signal
- [Phase 16-03]: Accuracy dimension deferred — thesis_records/ stub established for future reconciliation process (Phase 17+)
- [Phase 17-01]: MEMORY.md prev_score default is 0.5 (cold-start) matching KAMI DEFAULT_MERIT — first entry computes delta against neutral rather than 0.0
- [Phase 17-01]: _get_souls_dir() extracted as monkeypatchable function — test isolation for MEMORY.md I/O without touching real souls/ directories
- [Phase 17-01]: memory_writer_node uses synchronous file I/O only (Path.read_text/write_text) — asyncio.run() inside node functions is project-breaking pattern (MEM-06 defect)
- [Phase 17]: PROPOSALS_DIR is a module-level Path constant — created lazily on first write_proposal_atomic call, not at import time
- [Phase 17]: agent_id in SoulProposal set to soul HANDLE (not agent directory name) — consistent with Agent Church SOUL.md lookup
- [Phase 17]: proposed_content in trigger-generated proposals is a sentinel string — memory_writer does not draft soul content; Agent Church generates replacement text in Plan 03
- [Phase 17-03]: Agent Church is a standalone __main__ script — not a LangGraph node — to avoid deadlock and L1 self-approval conflict-of-interest
- [Phase 17-03]: RequiresHumanApproval propagates from review_proposals() to caller — not caught internally
- [Phase 17-03]: HANDLE_TO_AGENT_ID copied into agent_church.py (not imported from src.graph.nodes) to maintain Import Layer Law
- [Phase 17-03]: memory_writer_node wired between merit_updater and trade_logger in orchestrator — Phase 17 EVOL-01/02/03 complete end-to-end
- [Phase 18-01]: users field placed as LAST field in AgentSoul frozen dataclass — Python dataclass requires fields with defaults to follow fields without defaults
- [Phase 18-01]: soul_sync_context uses plain Optional[Dict[str, str]] with no Annotated reducer — written once by handshake node, same pattern as merit_scores
- [Phase 18-01]: public_soul_summary() uses re.split on H2 boundaries with _PEER_VISIBLE_SECTIONS frozenset filter; falls back to raw soul[:300] if no matching sections found
- [Phase 18]: soul_sync_handshake_node implemented as synchronous (not async) — all reads are lru_cache hits via warmup_soul_cache(), no I/O needed; with_audit_logging handles sync nodes via asyncio.to_thread
- [Phase 18]: TestNoLLMCalls patch fixed with create=True — module correctly never imports ChatGoogleGenerativeAI; patch target needs create=True when testing absence of an import

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
**Current focus:** v1.3 Phase 18 — Theory of Mind Soul-Sync (Phase 17 MEMORY.md Evolution + Agent Church complete 2026-03-08)

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
