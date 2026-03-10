# Phase 27: Environment Stabilization - Research

**Researched:** 2026-03-09
**Domain:** Python dependency management, test infrastructure
**Confidence:** HIGH

## Summary

Phase 27 fixes broken dependencies and restores code quality around ccxt, chromadb, and pytest-asyncio. Live investigation of the current codebase reveals that the "13 broken tests" is largely a historical designation -- the environment has been partially patched through workarounds (module-level mocks in ccxt_client.py, chromadb already installed). The current test suite shows **681 passed, 2 failed, 2 errors** -- all 4 failures are PostgreSQL-related (need running PG instance), not environment dependency issues.

The real work in this phase is **code quality restoration**: replacing the module-level ccxt mock with a proper lazy import, converting order_router_ccxt.py to lazy init, stripping redundant `@pytest.mark.asyncio` decorators (since `asyncio_mode = "auto"` is already configured), pinning exact versions for reproducibility, and fixing the trivial Pydantic ConfigDict deprecation.

**Primary recommendation:** Pin exact versions of ccxt==4.5.42, chromadb==1.5.2, pytest-asyncio==1.3.0 in pyproject.toml. Restore real ccxt import in ccxt_client.py with lazy init pattern. Convert order_router_ccxt.py to lazy init. Strip `@pytest.mark.asyncio` decorators. Fix Pydantic ConfigDict warning. Verify full suite green.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Fix real deps: pin/upgrade to working versions so tests exercise real code paths
- Mocking only where dep is genuinely optional at test time (e.g., no API key available)
- Guard with `skipIf` only for tests needing external services (live API keys, running servers); unit tests using in-process fakes (EphemeralClient, mocked exchange) run unconditionally
- When a dep is fundamentally broken, pin to last working version (not replace or drop)
- Fix Pydantic deprecation warnings if the fix is trivial (one-line ConfigDict migration); otherwise leave
- Keep ccxt as a real dependency, pin to a working version that resolves the lighter_client packaging bug
- Restore real import in `ccxt_client.py`: replace the module-level mock with lazy init pattern (getter function, no side effects at import)
- Tests mock ccxt at test level, not module level
- `order_router_ccxt.py`: convert to lazy init pattern (getter function for exchange instance, no import-time side effects)
- Pin chromadb to a working version for Python 3.12
- chromadb is a real dependency -- no skipIf guards on tests
- EphemeralClient tests should run unconditionally
- Keep chromadb as the vector store
- Set mode to `auto` in pyproject.toml -- all async test functions auto-detected
- Pin pytest-asyncio to exact version for reproducibility
- Strip redundant `@pytest.mark.asyncio` decorators from all test files (auto mode makes them unnecessary)

### Claude's Discretion
- Exact pinned versions for ccxt and chromadb (whatever installs and passes tests)
- Pydantic ConfigDict migration approach (if trivial)
- Whether any additional test infrastructure changes are needed to make the 13 tests green

### Deferred Ideas (OUT OF SCOPE)
- Consider alternative vector stores (lancedb, sqlite-vec) if chromadb keeps causing install issues -- future phase
- Pydantic V2 full migration (beyond trivial ConfigDict fixes) -- not in scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ENV-01 | All ccxt-dependent tests pass after dependency fix | ccxt 4.5.42 works. Restore real import in ccxt_client.py (remove module-level mock, use lazy init). Convert order_router_ccxt.py to lazy init. Pin ccxt==4.5.42. |
| ENV-02 | All chromadb-dependent tests pass after dependency fix | chromadb 1.5.2 already installed and working. 47 memory/KB tests pass. Pin chromadb==1.5.2 for reproducibility. |
| ENV-03 | All pytest-asyncio-dependent tests pass after dependency fix | pytest-asyncio 1.3.0 installed, asyncio_mode="auto" already configured. Pin pytest-asyncio==1.3.0. Strip 19 redundant @pytest.mark.asyncio decorators. |
| ENV-04 | CI test suite reports 0 env-related failures | Current state: 681 pass, 4 PostgreSQL failures (not env-related). After ccxt lazy init + version pinning, all env-related issues resolved. |
</phase_requirements>

## Current State Analysis

### Actual Test Results (2026-03-09)

| Metric | Value |
|--------|-------|
| Total collected | 684 |
| Passed | 681 |
| Failed | 2 (PostgreSQL -- not env deps) |
| Errors | 2 (PostgreSQL -- not env deps) |
| Run time | ~329s |

**The "13 broken tests" is a historical designation.** The environment has been partially stabilized through prior work. The ccxt_client.py module-level mock masked ccxt failures, chromadb was installed, and pytest-asyncio works.

### Dependency Versions (currently installed, working)

| Package | Installed | pyproject.toml spec | Action |
|---------|-----------|-------------------|--------|
| ccxt | 4.5.42 | `>=4.5.42` | Pin to `==4.5.42` |
| chromadb | 1.5.2 | `>=1.5.2` | Pin to `==1.5.2` |
| pytest-asyncio | 1.3.0 | `>=0.24.0` | Pin to `==1.3.0` |
| pydantic | 2.12.5 | (transitive) | Fix ConfigDict warning |

### Files Requiring Changes

| File | Issue | Fix |
|------|-------|-----|
| `pyproject.toml` | Minimum version specs instead of pinned | Pin exact versions |
| `src/tools/data_sources/ccxt_client.py` | Module-level MagicMock replaces real ccxt import | Remove mock, use lazy init for `ccxt.async_support` |
| `src/agents/order_router_ccxt.py` | Import-time `import ccxt` + exchange init at module level | Convert to lazy init pattern |
| `src/models/audit.py` | Pydantic V1-style `class Config` with `json_encoders` | Migrate to `model_config = ConfigDict(...)` |
| 7 test files | Redundant `@pytest.mark.asyncio` decorators | Strip all 19 occurrences |

## Standard Stack

### Core (already in use, pin exact versions)
| Library | Version | Purpose | Why Pin |
|---------|---------|---------|---------|
| ccxt | 4.5.42 | Crypto exchange data | lighter_client packaging bug in other versions |
| chromadb | 1.5.2 | Vector store for memory | API stability across 0.x/1.x breaking changes |
| pytest-asyncio | 1.3.0 | Async test support | Mode configuration compatibility |
| pydantic | 2.12.5 | Data validation (transitive) | ConfigDict deprecation fix |

### No New Dependencies
This phase adds zero new dependencies. All work is pinning, fixing imports, and cleaning decorators.

## Architecture Patterns

### Pattern 1: Lazy Init for ccxt (apply to ccxt_client.py)
**What:** Replace module-level MagicMock with lazy import of real ccxt
**When to use:** Any module that imports a dependency that may fail at import time or needs deferred initialization

```python
# Source: Established project pattern (soul_loader.py, LLM instances)
# In ccxt_client.py:
_ccxt_async = None

def _get_ccxt_async():
    global _ccxt_async
    if _ccxt_async is None:
        import ccxt.async_support as _mod
        _ccxt_async = _mod
    return _ccxt_async

# Usage in fetch_crypto_ohlcv:
async def fetch_crypto_ohlcv(symbol, exchange_id="binance", ...):
    ccxt = _get_ccxt_async()
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({"enableRateLimit": True})
    # ... rest unchanged
```

### Pattern 2: Lazy Init for order_router_ccxt.py
**What:** Convert module-level `import ccxt` + exchange initialization to getter function
**When to use:** The exchange object requires API keys and network -- must not init at import time

```python
# In order_router_ccxt.py:
import os

_exchange = None

def _get_exchange():
    global _exchange
    if _exchange is None:
        import ccxt
        exchange_id = os.getenv("EXCHANGE_ID", "binance")
        api_key = os.getenv("API_KEY")
        api_secret = os.getenv("API_SECRET")
        exchange_class = getattr(ccxt, exchange_id)
        _exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
    return _exchange

def route_order(pipeline_payload: dict, agent_action: dict):
    exchange = _get_exchange()
    # ... rest unchanged, replace bare `exchange` references
```

### Pattern 3: Pydantic ConfigDict Migration
**What:** Replace `class Config` with `model_config = ConfigDict(...)`

```python
# Before (src/models/audit.py):
class AuditLogEntry(BaseModel):
    # ... fields ...
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

# After:
from pydantic import ConfigDict

class AuditLogEntry(BaseModel):
    model_config = ConfigDict(
        json_serialization_schema=None,  # See note below
    )
    # ... fields ...
```

**Note on json_encoders:** In Pydantic V2, `json_encoders` is replaced by custom serializers. The simplest fix is to remove `json_encoders` entirely since `datetime.isoformat()` is Pydantic V2's default serialization for datetime fields. The `class Config` with `json_encoders` is a no-op warning -- Pydantic V2 already serializes datetimes as ISO format by default.

### Anti-Patterns to Avoid
- **Module-level mocks in production code:** Never use `MagicMock()` at module level in `src/` files. Mocks belong in test files only.
- **Import-time side effects:** Never initialize exchange connections, API clients, or database pools at import time. Use lazy init.
- **Mixing `>=` and `==` pins for critical deps:** Pin exact versions for deps with known packaging bugs (ccxt) or breaking API changes (chromadb).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async test detection | Custom async test runners | pytest-asyncio `asyncio_mode = "auto"` | Already configured in pyproject.toml; auto-detects `async def test_*` |
| ccxt exchange mocking | Module-level MagicMock in production | `unittest.mock.patch` in test files | Tests should mock at test level, not pollute production code |
| Version locking | requirements.txt alongside pyproject.toml | `uv.lock` (already exists) + exact pins in pyproject.toml | uv.lock is the authoritative lockfile; exact pins prevent drift |

## Common Pitfalls

### Pitfall 1: ccxt_client.py Tests Depend on Module-Level Mock
**What goes wrong:** When you remove the MagicMock from ccxt_client.py, tests that import ccxt_client will now trigger a real `import ccxt.async_support`. If any test calls `fetch_crypto_ohlcv` without patching the exchange, it will attempt real network calls.
**Why it happens:** The current test_data_fetcher.py patches `ccxt.async_support.binance` -- this patch target is correct for the lazy init pattern but was originally designed for the mocked module.
**How to avoid:** After converting to lazy init, verify that `test_data_fetcher_ccxt` patches `ccxt.async_support.binance` (not `src.tools.data_sources.ccxt_client.ccxt.binance`). The patch target may need adjustment.
**Warning signs:** `test_data_fetcher_ccxt` fails with network timeout or exchange API errors.

### Pitfall 2: order_router_ccxt.py Module-Level Side Effects
**What goes wrong:** `order_router_ccxt.py` currently does `import ccxt` AND `exchange = exchange_class({...})` at module level. This means importing the module creates a live exchange connection attempt.
**Why it happens:** The file was written as a standalone script (`if __name__ == "__main__"`) and wasn't designed for import-time safety.
**How to avoid:** The lazy init conversion must move ALL of lines 7-24 into the getter function. The `ccxt.InsufficientFunds` exception reference at line 125 needs `import ccxt` available -- either lazy import or keep ccxt as a type-only import.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'InsufficientFunds'` in exception handlers.

### Pitfall 3: Stripping @pytest.mark.asyncio Breaks Tests
**What goes wrong:** If `asyncio_mode = "auto"` is not properly configured, stripping decorators will cause async tests to silently not run or fail with "coroutine never awaited".
**Why it happens:** The `asyncio_mode = "auto"` setting in pyproject.toml must be under `[tool.pytest.ini_options]` (which it already is).
**How to avoid:** Verify `asyncio_mode = "auto"` is present before stripping decorators. Run tests after stripping to confirm async tests still execute.
**Warning signs:** Test count drops after stripping decorators.

### Pitfall 4: PostgreSQL Tests Are Not Environment Issues
**What goes wrong:** The 4 PostgreSQL failures (test_persistence.py, test_audit_chain.py) require a running PostgreSQL instance. These are NOT env-dependency issues -- they are infrastructure tests.
**Why it happens:** These tests connect to a real database via `DB_URL` and will fail without a running PG server.
**How to avoid:** Do NOT count these as part of ENV-04. They are pre-existing integration tests that require infrastructure, not dependency fixes. Consider adding `@pytest.mark.skipif` or `pytest.mark.integration` to isolate them (Claude's discretion area).
**Warning signs:** Claiming "13 tests fixed" when the PG tests are still failing.

## Code Examples

### ccxt_client.py Full Rewrite Pattern
```python
# Source: Current codebase pattern (lazy init)
"""
src.tools.data_sources.ccxt_client -- Crypto market data via ccxt.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from src.models.data_models import MarketData

logger = logging.getLogger(__name__)

_data_cache: Dict[Tuple[str, str, str], MarketData] = {}
_ccxt_async = None


def _get_ccxt_async():
    """Lazy import of ccxt.async_support -- no side effects at module load."""
    global _ccxt_async
    if _ccxt_async is None:
        import ccxt.async_support as _mod
        _ccxt_async = _mod
    return _ccxt_async


def clear_cache():
    _data_cache.clear()


async def fetch_crypto_ohlcv(
    symbol: str, exchange_id: str = "binance", timeframe: str = "1h", limit: int = 100
) -> MarketData:
    cache_key = (symbol, exchange_id, timeframe)
    if cache_key in _data_cache:
        return _data_cache[cache_key]

    ccxt = _get_ccxt_async()
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({"enableRateLimit": True})
    # ... rest identical to current implementation
```

### Pydantic ConfigDict Fix (src/models/audit.py)
```python
# Before:
class AuditLogEntry(BaseModel):
    # ... fields ...
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

# After (remove Config entirely -- Pydantic V2 serializes datetime as ISO by default):
class AuditLogEntry(BaseModel):
    # ... fields ...
    # No class Config needed -- Pydantic V2 handles datetime serialization natively
```

### Test Files: Strip @pytest.mark.asyncio
Files containing redundant decorators (19 total across 7 files):
- `tests/test_data_fetcher.py` (5 decorators)
- `tests/test_calibration.py` (4 decorators)
- `tests/test_dexter_bridge.py` (3 decorators)
- `tests/test_audit_chain.py` (2 decorators)
- `tests/test_persistence.py` (2 decorators)
- `tests/test_trade_logger.py` (2 decorators)
- `tests/test_knowledge_base.py` (1 decorator)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/ -x -q` |
| Full suite command | `.venv/bin/python3.12 -m pytest --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENV-01 | ccxt import works, fetch_crypto_ohlcv callable | unit | `.venv/bin/python3.12 -m pytest tests/test_data_fetcher.py::test_data_fetcher_ccxt -x` | Yes |
| ENV-02 | chromadb EphemeralClient tests pass | unit | `.venv/bin/python3.12 -m pytest tests/test_memory.py -x -q` | Yes |
| ENV-03 | async tests run without @pytest.mark.asyncio | unit | `.venv/bin/python3.12 -m pytest tests/test_calibration.py tests/test_dexter_bridge.py -x -q` | Yes |
| ENV-04 | Full suite green (minus PG infra tests) | integration | `.venv/bin/python3.12 -m pytest --ignore=tests/test_persistence.py --ignore=tests/test_audit_chain.py -q` | Yes |

### Sampling Rate
- **Per task commit:** `.venv/bin/python3.12 -m pytest -x -q --tb=short`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
None -- existing test infrastructure covers all phase requirements. No new test files needed. The work is fixing production code and cleaning test decorators.

## Open Questions

1. **PostgreSQL test disposition**
   - What we know: 4 tests (test_persistence.py, test_audit_chain.py) fail without a running PostgreSQL instance. They are NOT env-dependency issues.
   - What's unclear: Should these be marked with `@pytest.mark.skipif` for CI environments without PG, or left as-is?
   - Recommendation: Mark with `pytest.mark.integration` or `skipIf(not PG_AVAILABLE)` so the full suite can pass in all environments. This is within "Claude's Discretion" per CONTEXT.md.

2. **test_data_fetcher_ccxt patch target after lazy init**
   - What we know: The test patches `ccxt.async_support.binance`. After removing the module-level mock and using lazy init, this patch target should still work because `_get_ccxt_async()` returns the real `ccxt.async_support` module.
   - What's unclear: Whether the test's `with patch("ccxt.async_support.binance", ...)` will correctly intercept when accessed via the lazy getter.
   - Recommendation: Test immediately after conversion. If patch doesn't work, switch to `with patch("src.tools.data_sources.ccxt_client._get_ccxt_async")` returning a mock module.

## Sources

### Primary (HIGH confidence)
- Live codebase inspection: `pyproject.toml`, `src/tools/data_sources/ccxt_client.py`, `src/agents/order_router_ccxt.py`, `src/memory/service.py`, `src/models/audit.py`
- Live test execution: `.venv/bin/python3.12 -m pytest --tb=no -q` -- 681 pass, 2 fail, 2 error
- Live dependency check: `ccxt==4.5.42`, `chromadb==1.5.2`, `pytest-asyncio==1.3.0`, `pydantic==2.12.5`
- Import verification: `import ccxt.async_support` succeeds, `import ccxt` succeeds, `import chromadb` succeeds

### Secondary (MEDIUM confidence)
- `.planning/research/PITFALLS.md` -- pitfall #11 (ChromaDB version mismatch)
- `.planning/research/STACK.md` -- ccxt lighter_client bug history

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - versions verified by live import, tests pass
- Architecture: HIGH - lazy init pattern well-established in codebase (6+ examples)
- Pitfalls: HIGH - verified by running tests and inspecting code directly

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable domain, dependency versions pinned)
