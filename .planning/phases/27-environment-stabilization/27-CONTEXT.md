# Phase 27: Environment Stabilization - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix broken dependencies (ccxt, chromadb, pytest-asyncio) to restore all 13 failing tests to green. No new features, no architecture changes — purely dependency resolution and test configuration.

</domain>

<decisions>
## Implementation Decisions

### Test Philosophy
- Fix real deps: pin/upgrade to working versions so tests exercise real code paths
- Mocking only where dep is genuinely optional at test time (e.g., no API key available)
- Guard with `skipIf` only for tests needing external services (live API keys, running servers); unit tests using in-process fakes (EphemeralClient, mocked exchange) run unconditionally
- When a dep is fundamentally broken, pin to last working version (not replace or drop)
- Fix Pydantic deprecation warnings if the fix is trivial (one-line ConfigDict migration); otherwise leave

### ccxt Disposition
- Keep ccxt as a real dependency, pin to a working version that resolves the lighter_client packaging bug
- Restore real import in `ccxt_client.py`: replace the module-level mock with lazy init pattern (getter function, no side effects at import)
- Tests mock ccxt at test level, not module level
- `order_router_ccxt.py`: convert to lazy init pattern (getter function for exchange instance, no import-time side effects)

### chromadb Fix Strategy
- Pin chromadb to a working version for Python 3.12
- chromadb is a real dependency — no skipIf guards on tests
- EphemeralClient tests should run unconditionally
- Keep chromadb as the vector store; note "consider alternatives" as a future discussion point if install issues recur

### pytest-asyncio Configuration
- Set mode to `auto` in pyproject.toml — all async test functions auto-detected
- Pin pytest-asyncio to exact version (e.g., `==0.24.0`) for reproducibility
- Strip redundant `@pytest.mark.asyncio` decorators from all test files (auto mode makes them unnecessary)

### Claude's Discretion
- Exact pinned versions for ccxt and chromadb (whatever installs and passes tests)
- Pydantic ConfigDict migration approach (if trivial)
- Whether any additional test infrastructure changes are needed to make the 13 tests green

</decisions>

<specifics>
## Specific Ideas

- ccxt_client.py lazy import should match the established project pattern: `_client = None; def _get_client(): global _client; if _client is None: _client = ...; return _client`
- order_router_ccxt.py same lazy init pattern — no exchange initialization at import time
- pytest-asyncio pinned exact, not minimum version, for reproducibility

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- Lazy init pattern established across codebase (ChatGoogleGenerativeAI, LLM instances) — apply same to ccxt and exchange init
- `conftest.py` fixtures in `tests/core/` — may need similar fixture setup for ccxt/chromadb test cleanup

### Established Patterns
- Lazy init for API-dependent modules: `_llm = None; def _get_llm()` pattern
- Synchronous file I/O in node functions (no asyncio.run() inside nodes)
- structlog for all logging

### Integration Points
- `pyproject.toml` — dependency version pins
- `src/tools/data_sources/ccxt_client.py` — ccxt lazy import restoration
- `src/agents/order_router_ccxt.py` — lazy init conversion
- `src/memory/service.py` — chromadb already lazy, just needs working version
- `src/tools/knowledge_base.py` — chromadb already lazy, just needs working version
- All `tests/test_*.py` files with `@pytest.mark.asyncio` — strip decorators

</code_context>

<deferred>
## Deferred Ideas

- Consider alternative vector stores (lancedb, sqlite-vec) if chromadb keeps causing install issues — future phase
- Pydantic V2 full migration (beyond trivial ConfigDict fixes) — not in scope

</deferred>

---

*Phase: 27-environment-stabilization*
*Context gathered: 2026-03-09*
