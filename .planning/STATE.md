---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Self-Improvement
status: completed
last_updated: "2026-03-07T22:12:00.000Z"
last_activity: 2026-03-07 — Phase 09-01 completed; update_status() lifecycle controls + atomic save() added to MemoryRegistry. MEM-05 satisfied. 10/10 structured memory tests passing.
progress:
  total_phases: 7
  completed_phases: 3
  total_plans: 7
  completed_plans: 9
---

# Project State

> Machine-readable state lives in YAML frontmatter above.
> This markdown body is auto-generated — do not edit manually.

## Milestone

**v1.2 Risk Governance and Rule Validation** — ACTIVE (started 2026-03-06)

Previous: v1.1 Self-Improvement Loop — SHIPPED 2026-03-06 (169 tests, 3 phases)

## Current Phase

Phase: 09 — Structured Memory Registry
Plan: 01 (complete)
Status: In progress (1/1 plans done)
Last activity: 2026-03-07 — Phase 09-01 completed; update_status() lifecycle controls + atomic save() added to MemoryRegistry. MEM-05 satisfied. 10/10 structured memory tests passing.

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
- Phase 9 plan 01 complete (09-01): update_status() + atomic save(); MEM-05 lifecycle controls verified; 10/10 tests.
- Phase 8 complete (08-01 + 08-02): TDD stubs written then turned GREEN; RISK-07 + RISK-08 fully satisfied.
- Phase 7 complete (07-01 + 07-02): self-improvement loop end-to-end + MEM-02/MEM-03 gap closure.
- 201 tests passing (196 passing + 5 known pre-existing failures in test_order_router + test_persistence).
- InstitutionalGuard enforces: restricted assets, max concurrent trades, max notional exposure, asset concentration, daily drawdown.
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
- AsyncMock pattern for DB tests: patch.object(Class, '_async_method', new_callable=AsyncMock, return_value=[...]) avoids live PostgreSQL (2026-03-07)
- trades DDL extended in Phase 6: atr_at_entry, stop_loss_multiplier, stop_loss_method, trade_risk_score, portfolio_heat columns added; existing DBs need ALTER TABLE ... ADD COLUMN IF NOT EXISTS for each (2026-03-07)
- OrderRouter compliance gate raises ValueError("Compliance Error: ...") for missing or directionally invalid stop_loss — LONG stop must be below entry, SHORT stop must be above entry (2026-03-07)
- quant_alpha_intelligence handle() result keys are {name}_{period} (e.g. rsi_14, atr_14, bb_20) — Phase 6 order_router must use keyed form when reading indicator results (2026-03-07)
- RSI handle() result is {"value": float, "state": "overbought"|"oversold"|"neutral"} — not plain float (2026-03-07)
- Error codes: INSUFFICIENT_DATA (series too short), INVALID_INPUT (bad params/schema) — INVALID_PARAMETER retired (2026-03-07)
- Lazy LLM property pattern: _llm field + @property getter calling _get_llm() singleton + @llm.setter for test injection — applied to PerformanceReviewAgent and RuleGenerator (2026-03-07)
- _load_institutional_memory() reads both MemoryRegistry JSON (governed rules) and data/MEMORY.md (pipeline-written rules) — dual-source injection into agent prompts (2026-03-07)
- test_rule_generator_logic: generate_rules() returns List[MemoryRule] not List[str]; mock must return valid JSON list matching MemoryRule schema (2026-03-07)
- review_agent.py SQL uses t.position_size and t.entry_price — NOT t.quantity / t.execution_price (Phase 06 schema rename 2026-03-07)
- RuleGenerator.memory_md_path instance attribute redirectable in tests; persist_rules() appends "- PREFER:/AVOID:/CAUTION: {title}" lines with ISO timestamp comment to data/MEMORY.md (2026-03-07)
- Phase 8 TDD RED pattern: inspect.getsource() validates SQL column names without live DB; assert counterfactual (expected result post-implementation) on existing method to get clean AssertionError (2026-03-07)
- institutional_guard.py _get_open_positions() SQL fixed: uses position_size/entry_price (Phase 6 schema rename — fixed in 08-02)
- setup_persistence() has idx_trades_exit_time index on trades.exit_time (added in 08-02)
- check_compliance() drawdown circuit breaker implemented: rejects trades when daily loss > max_daily_loss (5%) of starting_capital (08-02)
- _get_daily_pnl() async helper: COALESCE SUM(pnl) for last 24h, safe-fail 0.0 on DB error (08-02)
- Drawdown test stubs updated to use AsyncMock(_get_daily_pnl, -60000.0) — no live DB required (08-02)
- MemoryRegistry.update_status() enforces VALID_TRANSITIONS dict; terminal states (deprecated, rejected) have empty allowed lists (09-01)
- MemoryRegistry.save() uses os.replace(tmp, final) for atomic POSIX rename — no partial-write corruption (09-01)
- test_transition_logged uses self.assertLogs('src.core.memory_registry', level='INFO') to verify logger.info() is called with rule_id (09-01)

## v1.1 Phase Dependency Chain

Phase 5 (ANALY-03) -> Phase 6 (RISK-03, RISK-05, RISK-06) -> Phase 7 (MEM-02, MEM-03)

Phase 6 depends on Phase 5: ATR is a technical indicator; the quant-alpha-intelligence skill provides the
calculation infrastructure that Phase 6's stop-loss logic calls into.

Phase 7 depends on Phase 6: meaningful weekly review requires real execution records that include
stop-loss data written to the trade warehouse by Phase 6.
