---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: MBS Persona System
status: active
last_updated: "2026-03-08"
last_activity: 2026-03-08 — Milestone v1.3 started; defining requirements
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

**v1.3 MBS Persona System** — ACTIVE (started 2026-03-08)

Previous: v1.2 Risk Governance — SHIPPED 2026-03-08 (260+ tests, 6 phases)

## Current Phase

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-08 — Milestone v1.3 started

## Progress

```
v1.3: [__________] 0/TBD phases complete (roadmap pending)
```

## Health

Status: Green
- Phase 9 complete (09-01 + 09-02): MemoryRegistry models + lifecycle controls + integration tests; MEM-04 + MEM-05 fully verified; 14/14 structured memory tests.
- Phase 8 complete (08-01 + 08-02): TDD stubs written then turned GREEN; RISK-07 + RISK-08 fully satisfied.
- Phase 7 complete (07-01 + 07-02): self-improvement loop end-to-end + MEM-02/MEM-03 gap closure.
- 244 tests passing (excluding 2 known-broken test files: test_order_router + test_persistence); 21/21 decision card tests passing; 2 graph wiring tests GREEN.
- InstitutionalGuard enforces: restricted assets, max concurrent trades, max notional exposure, asset concentration, daily drawdown.
- Phase 13 complete: institutional_guard_node wired into live execution graph; RISK-07 + RISK-08 closed.
- Architecture stable: LangGraph + Gemini + psycopg3.

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-08 after v1.2 milestone)

**Core value:** Institutional-quality trade signal generation through adversarial AI debate, with self-improving memory rules validated by backtesting, hard compliance guardrails, and immutable per-trade audit trails
**Current focus:** v1.3 MBS Persona System — defining requirements

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
- Phase 12 TDD RED pattern: patch.object(RuleValidator, "validate_proposed_rules", return_value=0) to isolate MC-01 gap in persist_rules() without triggering live backtests (12-01)
- Memory forwarding test: capture mock_agent.invoke.call_args[0][0]["messages"] to assert memory dict prepended; check content generically via hasattr(.content) or dict.get("content") so test survives Plan 02 type conversion (12-01)
- MC-01 gap: persist_rules() calls registry.add_rule(rule) which saves as "proposed"; no code ever calls update_status(rule.id, "active"); get_active_rules() always returns [] (12-01)
- MC-02 gap: MacroAnalyst line 133 and QuantModeler line 191 invoke with [HumanMessage(query)] only — state["messages"] memory message is never prepended (12-01)
- MC-01 fix: persist_rules() calls update_status(rule.id, "active") after add_rule() — rules immediately available via get_active_rules() without waiting for validator (12-02)
- MC-02 fix: MacroAnalyst() and QuantModeler() extract state["messages"][0] dict, convert to HumanMessage, prepend to invoke() call — LLM receives institutional memory before query (12-02)
- Stale test pattern: tests asserting old broken behavior (status=="proposed" after persist_rules) must be updated when production behavior changes; use patch.object(RuleValidator, "validate_proposed_rules", return_value=0) for isolation (12-02)
- RuleValidator audit trail test isolation: use RuleValidator.__new__() + direct attribute injection to bypass __init__; call validate_proposed_rules() on registry with hand-crafted proposed rule (12-02)
- route_after_institutional_guard uses 'is False' identity check (not falsy) to distinguish explicit rejection from not-yet-evaluated (None) (13-02)
- LangGraph conditional edges stored in workflow.branches not workflow.edges — edge inspection tests must check both (13-02)
- Rejected trades route to 'synthesize' for explanatory summary rather than silently ending at END (13-02)
- test_l3_chain_order stale assertion pattern: when a direct edge is replaced by a guarded chain, any test asserting the old edge must be updated (13-02)
- MEM-06 gate order tests use recording side_effect to observe registry state during validator backtest calls — captures intermediate proposed status before validator decides (14-01)
- git stash round-trip technique: stash working-tree fix, run tests to confirm RED, pop stash, confirm GREEN — validates TDD test quality without needing a separate branch (14-01)
- persist_rules() working-tree fix already applied before Plan 01 ran: update_status("active") removed from rule_generator.py in working tree; Plan 02 commits this fix (14-01)
- _patch_validator_audit() helper pattern: wraps RuleValidator.__init__ via patch.object to redirect audit_path to tmp_path without changing production interface (14-01)
- MEM-06 gate order enforced: persist_rules() for loop calls only add_rule(); validator.validate_proposed_rules() is sole promoter via 2-of-3 backtest harness; update_status("active") removed from loop (14-02)
- Stale direct-promotion test pattern: Phase 12 tests asserting immediate active promotion after persist_rules() must be updated with backtest mocks when production behavior changes to validator-mediated promotion (14-02)
- Phase 14 COMPLETE: 246 tests passing (excluding test_order_router + test_persistence known-broken files); MEM-06 closed (14-02)

## v1.1 Phase Dependency Chain

Phase 5 (ANALY-03) -> Phase 6 (RISK-03, RISK-05, RISK-06) -> Phase 7 (MEM-02, MEM-03)

Phase 6 depends on Phase 5: ATR is a technical indicator; the quant-alpha-intelligence skill provides the
calculation infrastructure that Phase 6's stop-loss logic calls into.

Phase 7 depends on Phase 6: meaningful weekly review requires real execution records that include
stop-loss data written to the trade warehouse by Phase 6.
