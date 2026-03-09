# Phase 28: Gemini API Circuit Breaker - Research

**Researched:** 2026-03-09
**Domain:** Resilience / Circuit Breaker Pattern for LLM API calls
**Confidence:** HIGH

## Summary

Phase 28 implements a 3-state circuit breaker (CLOSED/OPEN/HALF-OPEN) for Gemini API calls, integrated through the existing `with_audit_logging` wrapper. The implementation is pure stdlib (no pybreaker/aiobreaker), following the project's convention of minimal external dependencies.

The key integration point is `with_audit_logging` in `src/graph/orchestrator.py` (line 176), which already wraps all 17 graph nodes and handles both sync and async dispatch. The circuit breaker will be a module-level singleton in `src/core/circuit_breaker.py`, checked before node execution for LLM nodes and updated after success/failure. Exception detection requires handling two distinct paths: `ChatGoogleGenerativeAIError` (wraps 429 ClientError) and `google.genai.errors.ServerError` (503, not caught by LangChain), plus `httpx.TimeoutException` for timeouts.

**Primary recommendation:** Implement a standalone `CircuitBreaker` class with `threading.Lock` for thread safety (matching BudgetManager pattern), integrate it into `with_audit_logging` with an explicit `LLM_NODES` set, and add a `degraded` field to `CycleSnapshot` for downstream visibility.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- 3 consecutive failures trigger OPEN state; counter resets to 0 on any successful call (no sliding window)
- 30-second cooldown before half-open probe
- Only 429, 503, and timeout errors count as circuit-breaker failures (not 400/401/403)
- One global circuit breaker shared by all LLM nodes
- LLM nodes only -- non-LLM nodes pass through untouched
- LLM nodes identified by explicit set of node IDs
- When circuit is OPEN, LLM nodes return empty dict -- downstream nodes continue with degraded data
- Graph run completes normally with partial/no signal; no short-circuit
- CycleSnapshot gets `degraded: true` field + list of soft-failed nodes
- Debate synthesizer detects all-empty inputs and returns hold with confidence 0
- KAMI merit update is skipped for soft-failed agents
- Standalone `CircuitBreaker` class in `src/core/circuit_breaker.py`
- Default constants: `DEFAULT_THRESHOLD=3`, `DEFAULT_COOLDOWN_S=30`
- `with_audit_logging` instantiates/calls the circuit breaker
- No external config file -- Python constants, version-controlled
- Kill switch via env var: `CIRCUIT_BREAKER_ENABLED=false`
- State observable via `CircuitBreaker.state` property; transitions logged via structlog
- No pybreaker/aiobreaker dependency

### Claude's Discretion
- Exact exception types to catch for timeout detection
- Thread-safety approach for the global circuit breaker instance
- How `with_audit_logging` detects and classifies Gemini API errors from LangChain's exception wrapping
- Test fixture design for circuit breaker unit tests

### Deferred Ideas (OUT OF SCOPE)
- Circuit breakers for yfinance and PostgreSQL (SEC-08, deferred to v2)
- Automatic cycle retry with exponential backoff after recovery (SEC-09, deferred to v2)
- Circuit breaker state visible in replay CLI (nice-to-have, not required for Phase 28)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SEC-03 | Gemini API circuit breaker detects transient failures (429, 503, timeout) and transitions through CLOSED -> OPEN -> HALF-OPEN states | Exception hierarchy documented: `ChatGoogleGenerativeAIError` wraps 429 `ClientError`, `google.genai.errors.ServerError` propagates 503 directly, `httpx.TimeoutException` for timeouts. Status code extraction patterns identified. |
| SEC-04 | Circuit breaker in OPEN state returns soft-fail response (empty dict) instead of crashing | `with_audit_logging` integration point confirmed at orchestrator.py:176. Empty dict return is compatible with all downstream nodes (debate synthesizer already handles missing inputs). |
| SEC-05 | Circuit breaker integrates into existing `with_audit_logging` wrapper as single integration point | Wrapper confirmed: handles sync/async dispatch, catches exceptions at line 205. Circuit breaker check goes before node execution, failure recording in except block. |
| SEC-06 | Circuit breaker state transitions are logged via structlog for debugging | structlog already configured via `src/core/logging_config.py`. Standard `logger.info()` pattern used throughout codebase. |
| SEC-07 | Circuit breaker recovery_timeout allows automatic probe after configurable cooldown period | Half-open state allows exactly one probe call; success closes circuit, failure reopens. `time.monotonic()` for timing (not wall clock). |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (threading, time, enum) | 3.12 | Circuit breaker implementation | Project philosophy: no external deps for simple patterns |
| structlog (via logging) | existing | State transition logging | Already configured in project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| google.genai.errors | installed | Exception type detection | Catch `ServerError` (503) and `ClientError` (429 via LangChain wrapper) |
| httpx | 0.28.1 | Timeout exception detection | Catch `httpx.TimeoutException` for network timeouts |
| langchain_google_genai | installed | Wrapped exception detection | Catch `ChatGoogleGenerativeAIError` which wraps `ClientError` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib implementation | pybreaker | External dep, overkill for single-breaker use case; OUT OF SCOPE per REQUIREMENTS.md |
| threading.Lock | asyncio.Lock | asyncio.Lock requires await; threading.Lock matches BudgetManager pattern and works in both sync/async contexts |

## Architecture Patterns

### Recommended Project Structure
```
src/core/
    circuit_breaker.py    # NEW: CircuitBreaker class + module-level singleton
src/graph/
    orchestrator.py       # MODIFIED: with_audit_logging enhanced with circuit breaker
src/core/
    cycle_snapshot.py     # MODIFIED: add degraded field
```

### Pattern 1: Exception Classification for Gemini API Errors

**What:** LangChain wraps Google API errors inconsistently. The circuit breaker must detect transient failures from multiple exception types.

**When to use:** Inside `with_audit_logging` exception handler.

**Exception flow (verified from source code):**

```
Gemini API returns 429 (rate limit):
  -> google.genai.errors.ClientError(code=429)
  -> LangChain catches ClientError
  -> raises ChatGoogleGenerativeAIError("Error calling model '...' (RESOURCE_EXHAUSTED): ...")
  -> Circuit breaker catches ChatGoogleGenerativeAIError, checks __cause__ for ClientError

Gemini API returns 503 (service unavailable):
  -> google.genai.errors.ServerError(code=503)
  -> LangChain does NOT catch ServerError
  -> ServerError propagates directly to with_audit_logging
  -> Circuit breaker catches ServerError directly

Network timeout:
  -> httpx.TimeoutException (ConnectTimeout, ReadTimeout, WriteTimeout, PoolTimeout)
  -> May be caught by google SDK or propagate directly
  -> Circuit breaker catches httpx.TimeoutException
```

**Classification function:**
```python
from google.genai.errors import ClientError, ServerError
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError
import httpx

# HTTP status codes that indicate transient API outage
_TRANSIENT_CODES = {429, 503}

def _is_transient_llm_error(exc: Exception) -> bool:
    """Return True if exc represents a transient Gemini API failure."""
    # Direct ServerError from google SDK (503, 500, etc.)
    if isinstance(exc, ServerError) and getattr(exc, 'code', 0) in _TRANSIENT_CODES:
        return True

    # LangChain-wrapped ClientError (429 rate limit)
    if isinstance(exc, ChatGoogleGenerativeAIError):
        cause = exc.__cause__
        if isinstance(cause, ClientError) and getattr(cause, 'code', 0) in _TRANSIENT_CODES:
            return True

    # Network-level timeout
    if isinstance(exc, httpx.TimeoutException):
        return True

    return False
```

**Confidence:** HIGH -- verified from installed source code at `.venv/lib/python3.12/site-packages/langchain_google_genai/chat_models.py` lines 133-145, 3046-3051. `ClientError` is caught and re-raised as `ChatGoogleGenerativeAIError` with `__cause__` set. `ServerError` is NOT caught.

### Pattern 2: Thread-Safe Circuit Breaker Singleton

**What:** Module-level singleton with `threading.Lock`, matching `BudgetManager` pattern.

**Why threading.Lock not asyncio.Lock:** The `with_audit_logging` wrapper uses `asyncio.to_thread()` for sync nodes (orchestrator.py:204). This means circuit breaker state may be accessed from both the main async event loop thread AND thread pool worker threads. `threading.Lock` is safe in both contexts. `asyncio.Lock` would not be (it's async-only). This matches `BudgetManager` which also uses `threading.Lock` (budget_manager.py:85).

```python
import threading
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, threshold: int = DEFAULT_THRESHOLD, cooldown_s: float = DEFAULT_COOLDOWN_S):
        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._threshold = threshold
        self._cooldown_s = cooldown_s
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state

    def check(self) -> bool:
        """Return True if call should proceed, False if circuit is open."""
        ...

    def record_success(self) -> None:
        """Record a successful call. Resets failure counter, closes circuit from half-open."""
        ...

    def record_failure(self) -> None:
        """Record a failed call. Increments counter, may open circuit."""
        ...
```

### Pattern 3: with_audit_logging Integration

**What:** The wrapper checks circuit breaker state before executing LLM nodes and records outcomes after.

**Critical constraint:** The audit hash chain must NOT be corrupted. When circuit is open and node is soft-failed, the audit logger should still record the transition (with output = `{}`) so the hash chain remains consistent.

```python
# In orchestrator.py -- enhanced with_audit_logging

LLM_NODES: frozenset[str] = frozenset({
    'macro_analyst', 'quant_modeler',
    'bullish_researcher', 'bearish_researcher',
    'debate_synthesizer',  # Note: debate_synthesizer is pure aggregation, NOT an LLM caller
})
# Actually only: macro_analyst, quant_modeler, bullish_researcher, bearish_researcher
# debate_synthesizer does NO LLM calls -- exclude from LLM_NODES

_circuit_breaker: CircuitBreaker | None = None

def _get_circuit_breaker() -> CircuitBreaker:
    """Lazy singleton, matching _get_llm() pattern."""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()
    return _circuit_breaker
```

### Pattern 4: Soft-fail Propagation Through Graph

**What:** When circuit is OPEN, LLM nodes return `{}` (empty dict). This propagates naturally through the graph.

**Verified downstream behavior:**
- `DebateSynthesizer`: Already handles missing messages (debate.py:157) -- returns neutral placeholder with `strength: 0.0`
- Consensus score: Defaults to 0.5 (neutral) when no merit data -- combined with empty debate, score <= 0.6 triggers `route_after_debate` -> `hold` (END)
- `merit_updater_node`: Already skips update when `execution_result` is None (merit_updater.py:81)
- The graph naturally short-circuits to END via the hold path without executing downstream L3 nodes

**Additional behavior needed per CONTEXT.md:** DebateSynthesizer should detect ALL inputs are empty (circuit breaker active) and return `{signal: 'hold', confidence: 0, reason: 'circuit_breaker_active'}`. This requires checking if both bullish and bearish texts are empty AND the circuit breaker is open.

### Anti-Patterns to Avoid
- **Per-node circuit breaker wiring:** WRONG -- single integration point in `with_audit_logging`
- **asyncio.Lock for thread safety:** WRONG -- `asyncio.to_thread()` means mixed thread access
- **Counting 400/401/403 as transient:** WRONG -- those are bugs, not outages (per user decision)
- **Wall clock for cooldown timing:** WRONG -- use `time.monotonic()` (immune to clock adjustments)
- **Suppressing audit logging on soft-fail:** WRONG -- hash chain must remain continuous

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Exception type detection | String parsing of error messages | `isinstance()` checks on `__cause__` chain | Fragile string matching breaks on message changes |
| Thread-safe singleton | Double-checked locking | Simple lazy init with `threading.Lock` (matching BudgetManager) | Python GIL makes simple approach sufficient |

## Common Pitfalls

### Pitfall 1: LangChain Exception Wrapping Hides Status Codes
**What goes wrong:** `ChatGoogleGenerativeAIError` is a plain Exception subclass with the status code embedded in the message string, not as a structured attribute.
**Why it happens:** LangChain's `_handle_client_error` (chat_models.py:133) creates a new exception with `f"Error calling model '{model_name}' ({e.status}): {e}"` and chains the original via `from e`.
**How to avoid:** Always check `exc.__cause__` for the original `ClientError` which has `.code` (int) and `.status` (str) attributes. Never parse the error message string.
**Warning signs:** Tests passing with mocked string messages but failing with real API errors.

### Pitfall 2: ServerError Not Caught by LangChain
**What goes wrong:** 503 errors from Gemini raise `google.genai.errors.ServerError` which LangChain does NOT catch (only `ClientError` is caught at chat_models.py:3050).
**Why it happens:** LangChain only handles `ClientError` in its try/except blocks.
**How to avoid:** Circuit breaker must catch BOTH `ChatGoogleGenerativeAIError` (for wrapped 429) AND `ServerError` (for unwrapped 503).
**Warning signs:** Circuit breaker works for 429 but crashes on 503.

### Pitfall 3: Audit Hash Chain Corruption
**What goes wrong:** If soft-failed nodes skip audit logging, the hash chain has gaps that break `verify_chain()`.
**Why it happens:** Temptation to skip audit for "non-events."
**How to avoid:** Always log the transition even for soft-fails. Output is `{}` which is valid. The audit logger already handles empty dicts.
**Warning signs:** `audit_logger.verify_chain()` returns False after a circuit-open cycle.

### Pitfall 4: CycleSnapshot.validate_completed() Fails on Degraded Cycles
**What goes wrong:** If the circuit breaker causes a degraded run that still "completes," `validate_completed()` raises ValueError because required fields are None.
**Why it happens:** `_COMPLETED_REQUIRED_FIELDS` includes `macro_report`, `execution_result`, etc.
**How to avoid:** Degraded cycles should have status `"completed"` with a `degraded=True` flag, OR use a new status. The simplest approach: when circuit is open, the graph routes to `hold` (END) naturally, so `run_cycle` sees no `risk_approved` and no `execution_result` -- it will set status based on existing logic. Need to verify CycleRunner status determination handles this correctly.
**Warning signs:** ValueError on `validate_completed()` for degraded runs.

### Pitfall 5: Kill Switch Checked at Wrong Time
**What goes wrong:** If `CIRCUIT_BREAKER_ENABLED=false` is read at import time, changing it requires restart.
**Why it happens:** Caching env var in module constant.
**How to avoid:** Read `os.environ.get("CIRCUIT_BREAKER_ENABLED", "true")` inside `check()` or at singleton creation. Since the singleton is lazily created, reading at creation time is acceptable -- the kill switch is for local dev, not runtime toggling.

## Code Examples

### CircuitBreaker Class (Complete Implementation Pattern)

```python
# src/core/circuit_breaker.py
import logging
import os
import threading
import time
from enum import Enum

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 3
DEFAULT_COOLDOWN_S = 30


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """3-state circuit breaker for Gemini API resilience.

    Thread-safe via threading.Lock (matches BudgetManager pattern).
    Uses time.monotonic() for cooldown timing.
    """

    def __init__(
        self,
        threshold: int = DEFAULT_THRESHOLD,
        cooldown_s: float = DEFAULT_COOLDOWN_S,
    ) -> None:
        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._threshold = threshold
        self._cooldown_s = cooldown_s
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state

    def check(self) -> bool:
        """Return True if call should proceed, False if circuit is open.

        In HALF_OPEN, allows exactly one probe call.
        """
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.OPEN:
                elapsed = time.monotonic() - (self._opened_at or 0)
                if elapsed >= self._cooldown_s:
                    self._state = CircuitState.HALF_OPEN
                    logger.info(
                        "circuit_breaker_transition",
                        extra={"from": "open", "to": "half_open", "elapsed_s": round(elapsed, 1)},
                    )
                    return True  # Allow one probe
                return False
            # HALF_OPEN: allow the probe call
            return True

    def record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info(
                    "circuit_breaker_transition",
                    extra={"from": "half_open", "to": "closed"},
                )
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            if self._state == CircuitState.HALF_OPEN:
                # Probe failed -- reopen
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                logger.info(
                    "circuit_breaker_transition",
                    extra={"from": "half_open", "to": "open", "failures": self._failure_count},
                )
            elif self._failure_count >= self._threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                logger.info(
                    "circuit_breaker_transition",
                    extra={"from": "closed", "to": "open", "failures": self._failure_count},
                )
```

### Exception Classification (Verified from installed packages)

```python
# In src/core/circuit_breaker.py or src/graph/orchestrator.py

from google.genai.errors import ClientError, ServerError
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError
import httpx

_TRANSIENT_CODES: frozenset[int] = frozenset({429, 503})

def is_transient_llm_error(exc: Exception) -> bool:
    """Classify whether an exception represents a transient Gemini API failure.

    Returns True for:
    - 429 (rate limit) wrapped as ChatGoogleGenerativeAIError with ClientError cause
    - 503 (service unavailable) as direct ServerError
    - httpx.TimeoutException (connect, read, write, pool timeouts)

    Returns False for 400/401/403 (bugs, not outages).
    """
    if isinstance(exc, ServerError):
        return getattr(exc, 'code', 0) in _TRANSIENT_CODES

    if isinstance(exc, ChatGoogleGenerativeAIError):
        cause = exc.__cause__
        if isinstance(cause, ClientError):
            return getattr(cause, 'code', 0) in _TRANSIENT_CODES

    if isinstance(exc, httpx.TimeoutException):
        return True

    return False
```

### Enhanced with_audit_logging Integration

```python
# Key changes to with_audit_logging in orchestrator.py

LLM_NODES: frozenset[str] = frozenset({
    'macro_analyst', 'quant_modeler',
    'bullish_researcher', 'bearish_researcher',
})

def with_audit_logging(node_fn, node_id: str):
    async def wrapped_node(state: SwarmState, **kwargs):
        import time as _time

        # Circuit breaker gate (LLM nodes only)
        if node_id in LLM_NODES and _is_circuit_breaker_enabled():
            cb = _get_circuit_breaker()
            if not cb.check():
                logger.info("node_circuit_break", extra={"node": node_id, "state": cb.state.value})
                # Still log audit transition for hash chain continuity
                # ... audit_logger.log_transition with output={}
                return {}

        task_id = state.get("task_id", "unknown")
        # ... existing input_snapshot and node_enter logic ...

        try:
            if asyncio.iscoroutinefunction(node_fn):
                result = await node_fn(state, **kwargs)
            else:
                result = await asyncio.to_thread(node_fn, state, **kwargs)
        except Exception as exc:
            # Circuit breaker failure recording (LLM nodes only)
            if node_id in LLM_NODES and _is_circuit_breaker_enabled():
                if is_transient_llm_error(exc):
                    _get_circuit_breaker().record_failure()
                    logger.info("node_soft_fail", extra={"node": node_id, "error": str(exc)[:200]})
                    # Soft-fail: return empty dict instead of crashing
                    return {}
            # Non-transient or non-LLM: re-raise as before
            raise

        # Record success for LLM nodes
        if node_id in LLM_NODES and _is_circuit_breaker_enabled():
            _get_circuit_breaker().record_success()

        # ... existing audit logging and return ...
        return result

    return wrapped_node
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No resilience | Crash on API error | Current | Graph run fails completely on 429/503/timeout |
| No budget protection | Full budget burn on repeated failures | Current | 3+ failed API calls before crash consumes budget |

**After Phase 28:**
- 429/503/timeout: circuit opens after 3 failures, subsequent calls return empty dict immediately
- Budget protected: no API calls while circuit is open
- Graph completes with degraded signal (hold, no trade)

## Open Questions

1. **DebateSynthesizer circuit-aware behavior**
   - What we know: CONTEXT.md says it should return `{signal: 'hold', confidence: 0, reason: 'circuit_breaker_active'}` when all inputs are empty
   - What's unclear: DebateSynthesizer currently has no access to circuit breaker state. It can detect empty inputs but can't distinguish "circuit open" from "researchers produced no output for other reasons"
   - Recommendation: Add a `soft_failed_nodes: list[str]` field to SwarmState (set by `with_audit_logging` on soft-fail). DebateSynthesizer checks this list. This is cleaner than importing circuit breaker state into the debate module.

2. **CycleSnapshot `degraded` field propagation**
   - What we know: CONTEXT.md says CycleSnapshot gets `degraded: true` + list of soft-failed nodes
   - What's unclear: CycleRunner extracts snapshot from final_state -- how does it know which nodes were soft-failed?
   - Recommendation: Store soft-failed node list in SwarmState. CycleRunner reads it during `_extract_snapshot`. Add `degraded: bool = False` and `soft_failed_nodes: list[str] = []` to CycleSnapshot model.

3. **Exactly which nodes are LLM nodes?**
   - What we know: `macro_analyst`, `quant_modeler`, `bullish_researcher`, `bearish_researcher` all call `ChatGoogleGenerativeAI.invoke()`
   - Verified: `debate_synthesizer` does NOT make LLM calls (pure aggregation)
   - Verified: `classify_intent` does NOT use LLM (regex/pattern matching)
   - Verified: `risk_manager` is rules-only (no LLM)
   - Verified: No other nodes in `src/graph/nodes/` use LLM
   - Recommendation: `LLM_NODES = {'macro_analyst', 'quant_modeler', 'bullish_researcher', 'bearish_researcher'}`

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via `.venv/bin/python3.12 -m pytest`) |
| Config file | `pytest.ini` or `pyproject.toml` |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/core/test_circuit_breaker.py -x` |
| Full suite command | `.venv/bin/python3.12 -m pytest -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEC-03 | State transitions CLOSED->OPEN->HALF-OPEN on 3 consecutive failures + cooldown | unit | `.venv/bin/python3.12 -m pytest tests/core/test_circuit_breaker.py::test_state_transitions -x` | -- Wave 0 |
| SEC-03 | Exception classification: 429 wrapped, 503 direct, timeout | unit | `.venv/bin/python3.12 -m pytest tests/core/test_circuit_breaker.py::test_is_transient_llm_error -x` | -- Wave 0 |
| SEC-04 | OPEN state returns empty dict, no crash | unit | `.venv/bin/python3.12 -m pytest tests/core/test_circuit_breaker.py::test_open_returns_empty -x` | -- Wave 0 |
| SEC-05 | Integration through with_audit_logging | unit | `.venv/bin/python3.12 -m pytest tests/test_circuit_breaker_integration.py -x` | -- Wave 0 |
| SEC-06 | structlog output on state transitions | unit | `.venv/bin/python3.12 -m pytest tests/core/test_circuit_breaker.py::test_transition_logging -x` | -- Wave 0 |
| SEC-07 | Half-open probe after cooldown, recovery on success | unit | `.venv/bin/python3.12 -m pytest tests/core/test_circuit_breaker.py::test_half_open_recovery -x` | -- Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python3.12 -m pytest tests/core/test_circuit_breaker.py -x`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/core/test_circuit_breaker.py` -- covers SEC-03, SEC-04, SEC-06, SEC-07
- [ ] `tests/test_circuit_breaker_integration.py` -- covers SEC-05 (with_audit_logging integration)
- [ ] No framework gaps -- pytest already configured and working (680 tests pass)

## Sources

### Primary (HIGH confidence)
- Installed source: `.venv/lib/python3.12/site-packages/langchain_google_genai/chat_models.py` -- exception wrapping at lines 133-145, ClientError catch at 3050-3051, ServerError NOT caught
- Installed source: `.venv/lib/python3.12/site-packages/google/genai/errors.py` -- `APIError` base with `.code` (int) and `.status` (str), `ClientError` (4xx), `ServerError` (5xx)
- Project source: `src/graph/orchestrator.py` -- `with_audit_logging` wrapper at line 176
- Project source: `src/core/budget_manager.py` -- `threading.Lock` pattern at line 85
- Project source: `src/graph/debate.py` -- DebateSynthesizer pure aggregation (no LLM calls)
- Project source: `src/core/cycle_snapshot.py` -- CycleSnapshot model, `_COMPLETED_REQUIRED_FIELDS`
- httpx 0.28.1 -- `TimeoutException` hierarchy verified

### Secondary (MEDIUM confidence)
- None needed -- all findings verified from installed source code

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- stdlib only, no new dependencies, all exception types verified from installed packages
- Architecture: HIGH -- single integration point (`with_audit_logging`) confirmed, thread safety pattern established by BudgetManager
- Pitfalls: HIGH -- exception wrapping behavior verified directly from LangChain source code, ServerError non-catch confirmed

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable -- stdlib patterns, installed package versions unlikely to change mid-milestone)
