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

## Cross-Milestone Trends

| Milestone | Phases | Tests | Days | LOC |
|-----------|--------|-------|------|-----|
| v1.0 MVP  | 4      | 155   | 2    | ~14,600 |
| v1.1 Self-Improvement | 4 | 246 | 3 | ~22,500 |
