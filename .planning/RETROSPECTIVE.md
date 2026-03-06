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

## Cross-Milestone Trends

| Milestone | Phases | Tests | Days | LOC |
|-----------|--------|-------|------|-----|
| v1.0 MVP  | 4      | 155   | 2    | ~14,600 |
