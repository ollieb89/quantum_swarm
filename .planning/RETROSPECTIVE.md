# Retrospective: Quantum Swarm

## Milestone: v1.0 MVP

**Shipped:** 2026-03-06
**Phases:** 4 | **Plans:** 13 | **Tests:** 155

### What Was Built

- L1 LangGraph orchestrator with ClawGuard security and YAML skill registry
- L2 adversarial debate (MacroAnalyst + QuantModeler + Bull/Bear researchers) with weighted consensus gate
- L3 executor chain: real market data, NautilusTrader backtesting, multi-venue order routing
- PostgreSQL persistence layer: LangGraph checkpoints, hash-chained audit trail, trade warehouse
- Institutional compliance guardrails (leverage limits, restricted assets)

### What Worked

- **LangGraph migration**: Moving from custom orchestrator to LangGraph StateGraph was the right call — fan-out/fan-in and conditional routing worked cleanly out of the box
- **Adversarial debate pattern**: Bull vs Bear forced stress-testing of every thesis; the weighted consensus score is a clean, tunable risk gate
- **Lazy LLM initialization**: The `_get_llm()` getter pattern was essential for making the test suite work without an API key
- **TRUNCATE CASCADE for test isolation**: Critical pattern for any test that touches shared DB state across test runs
- **`try/except` around DB persistence in nodes**: Allowed nodes to degrade gracefully in test environments without a running PostgreSQL

### What Was Inefficient

- REQUIREMENTS.md was never updated during development — all requirements show "Pending" at close
- Phase 4 implemented outside GSD workflow (no PLAN.md files), requiring retroactive summary creation
- Phase 1 plan 03 summary was also missing at close — created retroactively
- hash-chained audit test failures (stale DB data) took debugging time to diagnose

### Patterns Established

- **Lazy init for module-level LLMs**: `_llm = None; def _get_llm(): global _llm; if _llm is None: _llm = ChatGoogleGenerativeAI(...)` — required for all agents
- **Mocking async nodes in tests**: Set `mod._private_llm = MagicMock()`, patch `bind_tools` + `invoke`, return `AIMessage(content=..., tool_calls=[])` to terminate ReAct loop
- **Test DB isolation**: `TRUNCATE table RESTART IDENTITY CASCADE` in async fixture setup
- **Async node upgrade pattern**: When adding DB persistence to a sync node, add `@pytest.mark.asyncio` + `await` to all tests calling it

### Key Lessons

- Keep REQUIREMENTS.md updated during development — retroactive traceability is painful
- GSD workflow (PLAN.md → SUMMARY.md) should be enforced even for "single session" phases; Phase 4 without PLAN files created archival friction
- `asyncio.run()` pattern applies only outside pytest-asyncio; inside use `@pytest.mark.asyncio`

### Cost Observations

- Model: claude-sonnet-4-6 throughout
- Sessions: ~4-5 main sessions across 2 days
- 67 commits for full 4-phase build from scratch

## Milestone: v1.1 — Self-Improvement

**Shipped:** 2026-03-08
**Phases:** 4 (5, 6, 7, 12) | **Plans:** 7 | **Tests:** 246

### What Was Built

- `quant-alpha-intelligence` skill: centralized RSI, MACD, Bollinger Bands, ATR with `{name}_{period}` result keying
- ATR-based stop-loss hard gate — OrderRouter rejects missing stop-loss; stop_loss_level/entry_price/position_size in PostgreSQL audit record
- PerformanceReviewAgent + RuleGenerator self-improvement pipeline with `--review` CLI and dual-source memory injection
- MEM-03 gap closed (Phase 12): rules promoted to `active`, institutional memory forwarded into analyst sub-graph invocations

### What Worked

- **TDD RED→GREEN discipline**: Consistently writing failing tests first (RuleValidator, institutional guard, MEM-06 gate) gave confidence at each stage
- **Gap closure phase pattern**: Inserting decimal/numbered gap-closure phases (Phase 12 for MC-01/MC-02) after milestone audit kept scope clean without polluting the core milestone plan
- **`route_after_institutional_guard` with `is False` check**: Distinguishing explicit rejection from unevaluated (`None`) prevented false routing on not-yet-run nodes
- **Lazy property pattern for LLMs**: `_llm` field + `@property` getter + `@llm.setter` for injection — cleaner than module-level `_get_llm()` singleton, applied to PerformanceReviewAgent and RuleGenerator
- **LangGraph edge inspection via `workflow.branches` + `workflow.edges`**: Catching both conditional and direct edges in tests — catching edge-inspection gaps (Phase 13)

### What Was Inefficient

- Phase 12 VERIFICATION.md became stale immediately when Phase 14 superseded its direct-promotion behavior — VERIFICATION files should note "may be superseded by gap-closure phases"
- MC-03 advisory (ATR typed extraction) discovered at audit time rather than design time — typed result extraction should be part of skill contract review
- `datetime.utcnow()` deprecation left in l3_executor.py despite being flagged — quick fixes shouldn't need a separate phase

### Patterns Established

- **`os.replace()` atomic save pattern**: `tmp → final` POSIX rename for any file that multiple processes might read during write
- **RuleValidator 2-of-3 majority vote**: Sharpe + max drawdown + win rate; drawdown improvement direction is `treatment > baseline` (less negative is better)
- **Registry stale-read prevention**: `self.registry.schema = self.registry._load()` at entry of `validate_proposed_rules()` before any in-flight rule check
- **`asyncio.run(asyncio.to_thread(...))` for sync RuleValidator**: Avoids nested event loop issues from a synchronous call site running async backtest
- **Phase gap-closure pattern**: After milestone audit reveals integration gaps, insert numbered phase (e.g., Phase 12) to close gap and re-audit — cleaner than retroactively modifying existing phase plans

### Key Lessons

- Run milestone audit (`/gsd:audit-milestone`) immediately when a phase completes claiming to close a requirement — gap closures discovered late (MC-01/MC-02 at v1.1 audit) added extra phases
- `workflow.branches` is where LangGraph stores conditional edges; `workflow.edges` for direct — both must be checked in graph wiring tests
- Rejected trades should always route to a synthesis/explanation node rather than END — explainability preserved at no cost

### Cost Observations

- Model: claude-sonnet-4-6 throughout
- Sessions: ~6-8 sessions across 3 days
- ~90 commits covering 4 primary phases + 2 gap-closure phases (12, 14 opened by audit)

## Milestone: v1.2 — Risk Governance and Rule Validation

**Shipped:** 2026-03-08
**Phases:** 6 (8, 9, 10, 11, 13, 14) | **Plans:** 14 | **Tests:** 260+

### What Was Built

- `InstitutionalGuard` portfolio risk gate: drawdown circuit breaker (>5% daily loss), exposure/concentration limits, wired as mandatory `claw_guard → institutional_guard` graph node
- `MemoryRegistry` structured JSON registry: Pydantic-validated rules, one-way lifecycle transitions (proposed → active → archived), atomic `os.replace()` save
- `RuleValidator` 2-of-3 backtest harness: NautilusTrader baseline + treatment backtests per proposed rule; Sharpe/drawdown/win-rate majority vote; MiFID II audit events to `data/audit.jsonl`
- `DecisionCard` immutable audit trail: SHA-256 hash-chained JSON for every trade, portfolio risk score, applied rule IDs — appended to `audit.jsonl` by `decision_card_writer_node`
- Gap closures: RISK-07 (institutional_guard wired, Phase 13), RISK-08 (trade_risk_score/portfolio_heat propagation, Phase 13), MEM-06 async fix (ThreadPoolExecutor replaces asyncio.run, post-close fix)

### What Worked

- **Audit-driven gap closure**: Running `/gsd:audit-milestone` after Phase 14 revealed MEM-06 was still unsatisfied at runtime — linear unit tests missed the async context failure. The audit correctly blocked milestone completion until resolved.
- **ThreadPoolExecutor fix specificity**: The MEM-06 async defect had a clearly documented root cause in the audit report (exact line numbers, failure mode, fix options). Applied in one small diff with 14 tests confirming the fix.
- **InstitutionalGuard as graph node (not inline check)**: Wiring as a mandatory graph node gives clean routing with `route_after_institutional_guard()` — rejected trades get an explanation via synthesize rather than silently dying at END.
- **DecisionCard SHA-256 hash chain**: Simple pattern — each card includes `prev_hash` of prior card in `audit.jsonl` — gives tamper-evidence without a blockchain.

### What Was Inefficient

- **MEM-06 async failure was invisible to Phase 14 tests**: Tests called `persist_rules()` from synchronous context, so `asyncio.run()` succeeded. The runtime failure only emerged when called through `run_review_async()`. A test that calls `validate_proposed_rules()` from within an `asyncio.run()` wrapper would have caught this.
- **All 8 production rules stayed `proposed` through entire v1.2 development** — the core loop (generate → validate → promote) was never observable end-to-end until the async fix. Integration testing in async context should be explicit acceptance criteria for MEM-06.
- **Nyquist VALIDATION.md files skipped for all v1.2 phases** — momentum from phase-to-phase execution caused this gap. Nyquist coverage should be a checklist item in each phase plan.
- **`risk_approved` omission on approval path** — InstitutionalGuard writes `compliance_flags` and `metadata` but not `risk_approved: True` on the approval path. Audit trail is incomplete. Small oversight caught only at audit time.

### Patterns Established

- **Async context test coverage**: For any component that runs inside an async coroutine, add a test that invokes it through `asyncio.run()` (simulating the production context) — not just direct synchronous calls.
- **ThreadPoolExecutor for sync→async bridge**: `concurrent.futures.ThreadPoolExecutor` + `.submit().result()` is the correct pattern for calling synchronous blocking code (backtest runner) from within async coroutines — no event loop nesting.
- **`route_after_institutional_guard()` with `is False` explicit check**: Distinguish rejection (explicit False) from unevaluated state (None) to prevent false routing before the guard runs.
- **Graph node vs. inline enforcement**: For constraints that must be audited and routed, use a dedicated graph node (InstitutionalGuard) rather than inline checks in other nodes — routing branches stay testable.

### Key Lessons

- **Unit tests in sync context can hide async failures**: MEM-06 passed 14 unit tests but failed at runtime. When a sync method is called from async production code, add an async integration test that wraps the call in `asyncio.run()`.
- **Audit `status: gaps_found` is a hard gate, not a soft warning**: The workflow correctly blocked milestone completion on `gaps_found` status. Following that gate led directly to finding and fixing the real production failure.
- **Production rule lifecycle needs an observable end-to-end test**: 8 rules in `memory_registry.json` stayed `proposed` throughout v1.2. An integration test that seeds a rule and runs the full pipeline would have caught MEM-06 immediately.

### Cost Observations

- Model: claude-sonnet-4-6 throughout
- Sessions: ~6 sessions across 2 days
- ~25 commits covering 6 phases + MEM-06 async post-close fix

## Milestone: v1.3 — MBS Persona System

**Shipped:** 2026-03-08
**Phases:** 8 (15-22) | **Plans:** 18 | **Tests:** 300+

### What Was Built

- SoulLoader with frozen AgentSoul dataclass, lru_cache, path-traversal guard; AXIOM fully populated + 4 skeleton personas
- KAMI Merit Index: multi-dimensional formula (Accuracy+Recovery+Consensus+Fidelity) with EMA decay, PostgreSQL persistence, replaces character-length proxy in DebateSynthesizer
- Per-agent MEMORY.md forensic logs (50-entry cap, KAMI deltas), SoulProposal triggers, standalone Agent Church approval gate
- Theory of Mind soul-sync handshake: peer soul summaries exchanged before debate, Empathetic Refutation few-shots
- ARS Drift Auditor: 5 stdlib-only drift metrics, 30-cycle warm-up, flag-then-suspend escalation, daily systemd timer
- Pipeline closure: drift flags from SOUL.md rules, soul-sync context in debate, failure paths through KAMI+memory

### What Worked

- **Audit-driven gap closure (again)**: Running `/gsd:audit-milestone` after Phase 19 revealed 3 integration gaps (hardcoded DRIFT_FLAGS, orphaned soul_sync_context, failure path bypass). Phases 20-22 closed these cleanly without disrupting the core phase chain.
- **Frozen dataclass + lru_cache pattern for AgentSoul**: Hashability required for caching, immutability prevents concurrent fan-out mutation. The pattern held cleanly across 8 phases of extensions (drift_rules, users field).
- **Synchronous node functions everywhere**: After MEM-06's asyncio.run() defect, enforcing synchronous I/O in all node functions prevented an entire class of bugs.
- **Import Layer Law enforcement**: `test_import_boundaries.py` caught potential upward imports from core → agents/orchestrator early, preventing soul system from leaking graph-layer concerns.
- **Standalone Agent Church pattern**: Keeping soul mutation out-of-band (not a LangGraph node) avoided deadlock, L1 self-approval conflicts, and mid-graph cache invalidation.
- **Counter cosine for ARS sentiment**: stdlib-only approach (no numpy/sentence-transformers) kept the background auditor lightweight and dependency-free.

### What Was Inefficient

- **8 phases in 1 day**: Velocity was high but Nyquist VALIDATION.md files were skipped for most phases (partial for 15-18, missing for 19-22). Speed vs. validation documentation tradeoff.
- **SUMMARY frontmatter gaps**: Several phases had requirements-completed fields missing or listed in wrong phase SUMMARY files. Frontmatter validation should be automated.
- **Skeleton agents remain unpopulated**: MOMENTUM, CASSANDRA, SIGMA, GUARDIAN still have minimal prose content. Drift evaluation returns 'none' for them by design, but full persona diversity deferred.
- **Accuracy dimension deferred**: KAMI Accuracy is never updated in-cycle — thesis_records/ stub exists but no reconciliation process. Recovery and Consensus carry all the weight.

### Patterns Established

- **Frozen dataclass field ordering**: Fields with defaults must come after fields without defaults — `users` and `drift_rules` placed last in AgentSoul to satisfy Python dataclass constraint
- **Module-level monkeypatch for tests**: `monkeypatch.setattr(module, 'function_name', mock)` instead of string path patches — avoids AttributeError when modules aren't loaded as submodule attributes
- **Fail-soft on malformed config**: `drift_rules=()` on YAML parse failure, `_check_evolution_suspended` returns False on DB error — agents function without optional features rather than crashing
- **_EXTERNAL_CAUSES duplication across layers**: Duplicating constants between graph/core layers (not importing) preserves Import Layer Law
- **Direct edge for unconditional routing**: When routing becomes unconditional (failure path always flows through KAMI+memory), delete the conditional router entirely and use a direct graph edge

### Key Lessons

- **Audit → gap phases → re-audit is the reliable pattern**: v1.3 audit revealed INT-01/INT-02/INT-03 gaps, Phases 20-22 closed them, and re-audit confirmed 18/18 requirements. This pattern has worked across v1.1, v1.2, and v1.3.
- **Soul file content is a product decision, not an engineering task**: The 4 skeleton personas need creative writing (HEXACO-6 profiles, diverse cognitive styles). Engineering can scaffold the format but can't generate authentic personality content.
- **Background auditors must never gate revenue paths**: ARS suspension gates evolution only (not trades). This strict scope boundary is the key architectural constraint — any leak would make safety and revenue goals adversarial.

### Cost Observations

- Model: claude-sonnet-4-6 (balanced profile)
- Sessions: ~3-4 sessions in 1 day
- 90 commits covering 8 phases (5 core + 3 gap closure)

## Cross-Milestone Trends

| Milestone | Phases | Tests | Days | LOC |
|-----------|--------|-------|------|-----|
| v1.0 MVP  | 4      | 155   | 2    | ~14,600 |
| v1.1 Self-Improvement | 4 | 246 | 3 | ~22,500 |
| v1.2 Risk Governance  | 6 | 260+ | 2 | ~23,500 |
| v1.3 MBS Persona System | 8 | 300+ | 1 | ~30,600 |
