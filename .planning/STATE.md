---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Self-Improvement
status: completed
last_updated: "2026-03-08T02:01:55.574Z"
last_activity: 2026-03-08 — Phase 11-02 completed; decision_card_writer_node wired into LangGraph; conditional edge order_router->decision_card_writer->trade_logger; 21/21 decision card tests passing; 225-test suite clean.
progress:
  total_phases: 7
  completed_phases: 6
  total_plans: 13
  completed_plans: 15
---

# Project State

> Machine-readable state lives in YAML frontmatter above.
> This markdown body is auto-generated — do not edit manually.

## Milestone

**v1.2 Risk Governance and Rule Validation** — ACTIVE (started 2026-03-06)

Previous: v1.1 Self-Improvement Loop — SHIPPED 2026-03-06 (169 tests, 3 phases)

## Current Phase

Phase: 11 — Explainability & Decision Cards
Plan: 02 (complete)
Status: Complete (2/2 plans done)
Last activity: 2026-03-08 — Phase 11-02 completed; decision_card_writer_node wired into LangGraph; conditional edge order_router->decision_card_writer->trade_logger; 21/21 decision card tests passing; 225-test suite clean.

## Progress

```
v1.2: [==========] 4/4 phases complete
Phase 8: Portfolio Risk Governance     — Complete (2026-03-06)
Phase 9: Structured Memory Registry    — Complete (2026-03-06)
Phase 10: Rule Validation Harness      — Complete (2026-03-08)
Phase 11: Explainability & Decision Cards — Complete (2026-03-08)
```

## Health

Status: Green
- Phase 9 complete (09-01 + 09-02): MemoryRegistry models + lifecycle controls + integration tests; MEM-04 + MEM-05 fully verified; 14/14 structured memory tests.
- Phase 8 complete (08-01 + 08-02): TDD stubs written then turned GREEN; RISK-07 + RISK-08 fully satisfied.
- Phase 7 complete (07-01 + 07-02): self-improvement loop end-to-end + MEM-02/MEM-03 gap closure.
- 225 tests passing (225 excluding 2 known-broken test files: test_order_router + test_persistence); 21/21 decision card tests passing.
- InstitutionalGuard enforces: restricted assets, max concurrent trades, max notional exposure, asset concentration, daily drawdown.
- Architecture stable: LangGraph + Gemini + psycopg3.

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-08 — Phase 5 complete)

**Core value:** Institutional-quality trade signal generation through adversarial AI debate, with immutable audit trails and hard compliance guardrails
**Current focus:** v1.2 — Milestone complete (Phase 11 done); v1.1 bookkeeping gap resolved (Phase 5 ANALY-03 now closed)

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
- LangGraphOrchestrator.__new__() pattern avoids __init__ side effects (YAML load, MemoryService, LangGraph compilation) for testing internal methods (09-02)
- Orchestrator _load_institutional_memory() tested by patching src.graph.orchestrator.MemoryRegistry + Path — no live registry or file system required (09-02)
- RuleGenerator test isolation: redirect .registry and .memory_md_path instance attributes to temp paths — no mock needed (09-02)
- RuleValidator test isolation: redirect .registry and .audit_path instance attributes to temp paths — same pattern as RuleGenerator (10-01)
- get_proposed_rules() mirrors get_active_rules() one-liner filter: status == "proposed"; no other changes to MemoryRegistry (10-01)
- Wave 0 TDD RED scaffold: tests/test_rule_validator.py imports fail with ModuleNotFoundError until Plan 02 creates src/agents/rule_validator.py (10-01)
- config/swarm_config.yaml self_improvement: validation_lookback_days: 90, validation_min_trades: 10 — read by RuleValidator.__init__ (10-01)
- RuleValidator.validate_proposed_rules() is synchronous; uses asyncio.run(asyncio.to_thread(_run_nautilus_backtest, ...)) twice per rule — avoids nested event loop issues from synchronous call site (10-02)
- drawdown improvement direction: treatment_drawdown > baseline_drawdown = improvement (less negative is better); 2-of-3 majority vote: Sharpe, drawdown, win_rate (10-02)
- Evidence dict populated on live registry object after update_status(), then registry.save() — six keys: baseline_sharpe, treatment_sharpe, baseline_drawdown, treatment_drawdown, baseline_win_rate, treatment_win_rate (10-02)
- Backtest exceptions caught silently in RuleValidator — rule stays proposed; no re-raise to prevent batch abort (10-02)
- Registry stale-read prevention: self.registry.schema = self.registry._load() at entry of validate_proposed_rules() (10-02)
- Audit events written to data/audit.jsonl with fields: timestamp, event, rule_id, before_status, after_status, six metric values, three deltas (10-02)
- persist_rules() auto-calls RuleValidator.validate_proposed_rules() after every registry write; validator.registry = self.registry shares instance to see in-flight rules without disk round-trip (10-03)
- Integration tests for RuleValidator drive chain through rg.persist_rules([rule]) not validate_proposed_rules() directly — verifies auto-wiring is real; audit_path redirected via patched __init__ wrapper (10-03)
- DecisionCard content_hash excluded from its own SHA-256 payload; model_dump(mode="json") used before hashing so datetimes are ISO strings; verify_decision_card() is a pure function — never mutates card_dict (11-01)
- portfolio_risk_score in DecisionCard sourced via state.get("metadata", {}).get("trade_risk_score") — not a top-level SwarmState field (11-01)
- decision_card_writer_node wired via conditional edge after order_router; success==True -> decision_card_writer -> trade_logger; failure -> trade_logger directly (11-02)
- Test isolation for audit.jsonl writes: patch builtins.open on mode=='a' with mock_open(); avoid Path monkeypatching which causes recursive calls (11-02)
- get_pool() DB failure in decision_card_writer is non-fatal: caught, prev_audit_hash=None, card still written (11-02)
- SwarmState Phase 11 fields: decision_card_status (Literal pending/written/failed), decision_card_error (str), decision_card_audit_ref (str card_id) — all Optional, initialized to None (11-02)

## v1.1 Phase Dependency Chain

Phase 5 (ANALY-03) -> Phase 6 (RISK-03, RISK-05, RISK-06) -> Phase 7 (MEM-02, MEM-03)

Phase 6 depends on Phase 5: ATR is a technical indicator; the quant-alpha-intelligence skill provides the
calculation infrastructure that Phase 6's stop-loss logic calls into.

Phase 7 depends on Phase 6: meaningful weekly review requires real execution records that include
stop-loss data written to the trade warehouse by Phase 6.
