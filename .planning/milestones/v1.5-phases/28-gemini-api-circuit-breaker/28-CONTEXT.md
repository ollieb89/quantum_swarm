# Phase 28: Gemini API Circuit Breaker - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

LLM call failures degrade gracefully instead of crashing graph runs. Implement a 3-state circuit breaker (CLOSED/OPEN/HALF-OPEN) that integrates through the existing `with_audit_logging` wrapper. Non-LLM service breakers (yfinance, PostgreSQL) are deferred to v2 (SEC-08).

</domain>

<decisions>
## Implementation Decisions

### Failure Thresholds
- 3 consecutive failures trigger OPEN state
- Counter resets to 0 on any successful call (no sliding window)
- 30-second cooldown before half-open probe
- Only 429, 503, and timeout errors count as circuit-breaker failures (not 400/401/403 — those are bugs, not outages)

### Circuit Scope
- One global circuit breaker shared by all LLM nodes (if Gemini is down, it's down for everyone)
- LLM nodes only — non-LLM nodes (data_fetcher, order_router, etc.) pass through untouched
- LLM nodes identified by explicit set of node IDs (e.g., `LLM_NODES = {'macro_analyst', 'quant_modeler', 'bullish_researcher', ...}`)
- Circuit breaker state persists across graph runs/cycles (avoids burning 3 calls to rediscover a known outage)

### Soft-fail Propagation
- When circuit is OPEN, LLM nodes return empty dict — downstream nodes continue with degraded data
- Graph run completes normally with partial/no signal; no short-circuit of remaining nodes
- CycleSnapshot gets a `degraded: true` field + list of soft-failed nodes (replay CLI can surface this)
- Debate synthesizer detects all-empty inputs and returns `{signal: 'hold', confidence: 0, reason: 'circuit_breaker_active'}` — no trade executed
- KAMI merit update is skipped for soft-failed agents (don't penalize for API outages)

### Configuration & Structure
- Standalone `CircuitBreaker` class in `src/core/circuit_breaker.py` with `check()`/`record_success()`/`record_failure()` methods
- Default constants in the module: `DEFAULT_THRESHOLD=3`, `DEFAULT_COOLDOWN_S=30`
- `with_audit_logging` instantiates/calls the circuit breaker
- No external config file — Python constants, version-controlled
- Kill switch via env var: `CIRCUIT_BREAKER_ENABLED=false` disables entirely (useful for local dev/debugging)
- State observable via `CircuitBreaker.state` property; transitions logged via structlog (meets SEC-06)

### Claude's Discretion
- Exact exception types to catch for timeout detection (httpx.TimeoutException, google.api_core.exceptions, etc.)
- Thread-safety approach for the global circuit breaker instance
- How `with_audit_logging` detects and classifies Gemini API errors from LangChain's exception wrapping
- Test fixture design for circuit breaker unit tests

</decisions>

<specifics>
## Specific Ideas

- No pybreaker/aiobreaker dependency — stdlib implementation preferred (per project philosophy, REQUIREMENTS.md Out of Scope)
- The `with_audit_logging` wrapper already handles sync/async dispatch and wraps all 17 graph nodes — minimal wiring needed
- Circuit breaker is the same pattern as the lazy-init LLM instances: a module-level singleton accessed by the wrapper

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `with_audit_logging` (src/graph/orchestrator.py:176): async wrapper around all 17 graph nodes, already catches exceptions and logs node_enter/node_exit events — natural integration point
- structlog logging already configured (src/core/logging_config.py, src/main.py)
- Lazy init pattern established for LLM instances (_llm = None, def _get_llm()) — same pattern works for global CircuitBreaker singleton

### Established Patterns
- All LLM calls go through LangChain's `.invoke()` method on ChatGoogleGenerativeAI instances
- Synchronous node functions run in thread pool via `asyncio.to_thread()` inside `with_audit_logging`
- AuditLogger hash chain for immutable audit trail — circuit breaker must not corrupt this
- CycleSnapshot persistence in data/cycles/ — new `degraded` field fits here

### Integration Points
- `src/graph/orchestrator.py` — `with_audit_logging` enhanced to call circuit breaker for LLM_NODES
- `src/core/circuit_breaker.py` — new module, standalone class
- `src/graph/agents/analysts.py` — MacroAnalyst, QuantModeler (LLM callers)
- `src/graph/agents/researchers.py` — BullishResearcher, BearishResearcher (LLM callers)
- `src/core/cycle_runner.py` — CycleSnapshot may need `degraded` field
- `src/graph/nodes/merit_updater.py` — skip merit update for soft-failed agents

</code_context>

<deferred>
## Deferred Ideas

- Circuit breakers for yfinance and PostgreSQL (SEC-08, deferred to v2)
- Automatic cycle retry with exponential backoff after recovery (SEC-09, deferred to v2)
- Circuit breaker state visible in replay CLI (nice-to-have, not required for Phase 28)

</deferred>

---

*Phase: 28-gemini-api-circuit-breaker*
*Context gathered: 2026-03-09*
