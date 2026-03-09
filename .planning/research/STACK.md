# Technology Stack

**Project:** Quantum Swarm v1.5 -- Reliable Infrastructure
**Researched:** 2026-03-09
**Confidence:** HIGH

---

## Verdict: ZERO New Dependencies

v1.5 is an infrastructure stabilization milestone. Every feature builds on the existing stack. Adding dependencies in a "reliability" milestone would be contradictory to the project's stdlib-first philosophy.

| Feature | Implementation | New Dep? |
|---------|---------------|----------|
| PersonaScore 5D LLM-as-Judge | Pydantic + `with_structured_output()` on existing Gemini | None |
| Token cost tracking per cycle | Extend existing `BudgetManager` + `CycleSnapshot` | None |
| Gemini API circuit breaker | stdlib (`threading`, `time`, `enum`) | None |
| ChromaDB pruning / archive-to-Obsidian | Existing ChromaDB 1.5.2 delete/filter API via `MemoryService` | None |
| Dependency fixes (ccxt, chromadb, pytest-asyncio) | Version fixes / reinstalls only | None |

---

## Existing Stack (Confirmed Installed 2026-03-09)

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12 | Runtime |
| LangGraph | 1.0.10 | StateGraph orchestrator |
| langchain-google-genai | 4.2.1 | Gemini LLM integration |
| langchain-core | 1.2.17 | AIMessage, UsageMetadata |
| langchain-community | 0.4.1 | Community integrations |
| PostgreSQL 17 | psycopg 3.3.3 | Persistence, audit trail |
| ChromaDB | 1.5.2 | Vector memory store |
| structlog | 25.5.0 | Structured logging |
| Rich | 14.3.3 | CLI rendering |
| Pydantic | 2.12.5 | Data validation |
| pytest-asyncio | 1.3.0 | Async test support |
| ccxt | 4.5.41 (BROKEN) | Crypto exchange connectivity |
| scipy | installed | Spearman correlation in calibration |

---

## Feature-by-Feature Stack Decisions

### 1. PersonaScore 5D LLM-as-Judge (SOUL-09)

**Stack used:** `ChatGoogleGenerativeAI.with_structured_output()` + `pydantic.BaseModel`

**Why no new dependencies:**
- langchain-google-genai 4.2.1 supports `.with_structured_output()` via Gemini's native structured output mode
- Pydantic 2.12.5 defines the score schema
- This is the same pattern used by LangChain's `openevals` `create_llm_as_judge` -- we just do it directly without the wrapper package

| Component | Technology | Already Installed |
|-----------|-----------|-------------------|
| Judge LLM | `ChatGoogleGenerativeAI` (gemini-2.5-flash) | Yes |
| Score schema | `pydantic.BaseModel` | Yes |
| Prompt template | `langchain_core.prompts.ChatPromptTemplate` | Yes |
| Result storage | PostgreSQL `agent_merit_scores` table (JSONB) | Yes |

**Pydantic schema:**

```python
class PersonaScore(BaseModel):
    """5D persona fidelity score from LLM-as-Judge."""
    consistency: float = Field(ge=0.0, le=1.0, description="Adherence to stated persona identity")
    tone: float = Field(ge=0.0, le=1.0, description="Voice/style match to SOUL.md personality")
    logic: float = Field(ge=0.0, le=1.0, description="Reasoning follows persona's stated methodology")
    depth: float = Field(ge=0.0, le=1.0, description="Analysis depth matches persona's expertise claims")
    bias: float = Field(ge=0.0, le=1.0, description="Appropriate bias alignment (bull/bear/neutral)")
    rationale: str = Field(description="Brief justification for scores")
```

**Integration point:** Call after each L2 node completes (in `merit_updater_node` or new `persona_evaluator_node`). Pass agent's output text + agent's SOUL.md content as evaluation context. The composite PersonaScore feeds into KAMI's delta (Fidelity) dimension, replacing the current basic fidelity signal.

**Cost:** One extra Gemini call per agent per cycle (~4 calls x ~500 input tokens = ~2000 tokens/cycle, ~$0.0002/cycle). Negligible vs existing 4-agent fan-out.

**LLM lazy init pattern (MUST follow):** The evaluator LLM must use the project's lazy init pattern (getter function, not module-level instantiation) because `ChatGoogleGenerativeAI` validates the API key at instantiation. See existing pattern in researchers.py.

**Confidence:** HIGH -- `with_structured_output` on ChatGoogleGenerativeAI verified in langchain-google-genai 4.x docs.

---

### 2. Token/Cost Tracking per Cycle (OBS-02)

**Stack used:** Existing `BudgetManager` + `AIMessage.usage_metadata` + `CycleSnapshot`

**Why no new dependencies:**
- Token capture already works: `analysts.py:155-160` and `researchers.py:196-197` read `usage_metadata` from AIMessage and call `budget.record_usage()`
- `BudgetManager.summary()` already returns `{session_input_tokens, session_output_tokens, total_tokens, session_usd}` as a dict
- `CycleSnapshot` already persists to PostgreSQL + filesystem
- Just need to: (a) call `budget.reset_session()` at cycle start, (b) include `budget.summary()` in CycleSnapshot, (c) display in replay CLI

| Component | Technology | Already Exists |
|-----------|-----------|----------------|
| Token capture | `AIMessage.usage_metadata` | Yes (analysts.py, researchers.py) |
| Accumulation | `BudgetManager.summary()` | Yes (budget_manager.py) |
| Per-cycle storage | `CycleSnapshot` Pydantic model | Yes (persistence.py) |
| Persistence | PostgreSQL `cycle_snapshots` JSONB | Yes |
| Display | Rich table in replay CLI | Yes |

**What NOT to add:**
- `langfuse` -- heavyweight observability SaaS/self-hosted platform; overkill for per-cycle cost column
- `langchain-token-usage` PyPI package -- thin wrapper over direct `usage_metadata` access which is already implemented
- `opentelemetry` -- wrong abstraction layer for simple cost aggregation
- `GoogleGenAICallbackHandler` -- does NOT exist in langchain-community 0.4.1; the direct `usage_metadata` approach is correct

**Confidence:** HIGH -- usage_metadata already working in codebase, verified.

---

### 3. Gemini API Circuit Breaker (SEC-03)

**Stack used:** Python stdlib (`threading.Lock`, `time.monotonic`, `enum.Enum`)

**Why stdlib, not a library:**
- Project philosophy is stdlib-first (Counter cosine for ARS instead of numpy, manual retry in yfinance_client instead of tenacity)
- Circuit breaker is ~60 lines of code for 3-state machine (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
- Only one integration point (Gemini API via ChatGoogleGenerativeAI)

| Library Evaluated | Why Rejected |
|-------------------|-------------|
| `pybreaker` 1.2.0 | Tornado dependency; heavyweight for one integration point |
| `circuitbreaker` 2.0.0 | Decorator-based, no async support, poor fit for LangChain's invoke pattern |
| `aiobreaker` 1.3.0 | asyncio fork of pybreaker; reasonable but ~60 LOC does not justify new dependency |

**Implementation sketch:**

```python
import enum
import threading
import time

class CircuitState(enum.Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing -- reject calls, enter soft-fail pause
    HALF_OPEN = "half_open" # Recovery probe -- allow one call to test

class GeminiCircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 60.0):
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._last_failure_time: float = 0.0
        self._lock = threading.Lock()

    def pre_call(self) -> None:
        """Check if call is allowed. Raises CircuitOpenError if breaker is OPEN."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._last_failure_time > self._recovery_timeout:
                    self._state = CircuitState.HALF_OPEN  # Allow probe
                else:
                    raise CircuitOpenError(
                        f"Gemini API circuit breaker OPEN -- "
                        f"soft-fail pause for {self._recovery_timeout}s"
                    )

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN
```

**Soft-fail behavior (per PROJECT.md: "soft-fail pause, not blind retry"):**
- When circuit is OPEN, graph nodes return a graceful "service unavailable" state update
- The node output indicates the pause reason for downstream recording
- DecisionCardWriter and MeritUpdater handle the `circuit_open` status appropriately
- structlog logs the circuit state transition with timestamp for debugging

**Integration:** Wrap the LLM call site, not the HTTP layer. A single `GeminiCircuitBreaker` instance shared via `BudgetManager`-like pattern (instantiate in orchestrator, pass through state or closure).

**Thread safety:** Uses `threading.Lock` matching `BudgetManager`'s existing pattern. LangGraph's fan-out runs L2 nodes concurrently -- the circuit breaker must be thread-safe.

**Confidence:** HIGH -- well-understood pattern, stdlib-only, no novel dependencies.

---

### 4. ChromaDB Pruning / Archive-to-Obsidian (OBS-03)

**Stack used:** ChromaDB 1.5.2 native API + existing `MemoryService` + `pathlib`

**Why no new dependencies:**
- ChromaDB 1.5.2 has `collection.get(where=...)` for metadata-filtered queries and `collection.delete(ids=[...])` for removal
- WAL auto-pruning is enabled by default in ChromaDB 1.5.x -- no manual WAL cleanup needed
- `MemoryService` (src/memory/service.py) is already the sole ChromaDB interface -- pruning belongs there
- Obsidian markdown generation already exists (generate_transclusion_indexes.py pattern)

| Library Evaluated | Why Rejected |
|-------------------|-------------|
| `chromadb-ops` CLI | CLI tool for standalone maintenance; we need programmatic pruning integrated in the pipeline |

**Pruning strategy:**

1. Query documents older than N days via `collection.get(where={"timestamp": {"$lt": cutoff_iso}})`
2. Export each document to Markdown in Obsidian vault (`quantum-swarm/Archive/Memory/{date}/{document_id}.md`)
3. Delete from ChromaDB via `collection.delete(ids=[...])`
4. ChromaDB auto-handles WAL compaction

**New method on MemoryService:**

```python
@dataclass
class PruneResult:
    documents_archived: int
    documents_deleted: int
    archive_path: str

def prune_old_documents(self, cutoff_days: int = 90) -> PruneResult:
    """Archive old documents to Obsidian vault and delete from ChromaDB."""
```

**Metadata requirement:** The existing `MemorySource` types all require `timestamp` in metadata (enforced by `_REQUIRED_FIELDS` dict). This timestamp is the pruning key.

**Confidence:** HIGH -- ChromaDB delete and metadata filtering are stable, well-documented APIs.

---

### 5. Dependency Fixes (ENV-01)

#### ccxt (BROKEN -- ModuleNotFoundError)

**Problem:** ccxt 4.5.41 fails at import: `ModuleNotFoundError: No module named 'ccxt.static_dependencies.lighter_client'`. The Lighter exchange integration's native library is not properly bundled in the pip package.

**Fix strategy:**

```bash
# Step 1: Try force reinstall of current version
uv pip install --force-reinstall ccxt

# Step 2: If still broken, check if latest version fixes it
uv pip install --upgrade ccxt

# Step 3: If still broken, pin to last known pre-Lighter version
# (ccxt GitHub issue #23307 shows similar static_dependencies packaging bugs
#  with starkware in 4.3.x, resolved in later patches)
uv pip install "ccxt>=4.4,<4.5"
```

**Confidence:** MEDIUM -- the lighter_client error is not widely documented; may need version bisection. Similar `static_dependencies` packaging bugs have occurred before (starkware in 4.3.71) and were patched.

#### chromadb

**Status:** Actually INSTALLED (1.5.2 confirmed via `uv pip list`). The "missing" designation in project memory may refer to:
- Tests failing because `sentence-transformers` model download required at first run
- Import path issues in test mocking
- `KnowledgeBase.__init__` in `src/tools/knowledge_base.py` imports chromadb eagerly (not lazy) -- could fail if chromadb has import-time issues

**Fix:** Verify actual test failure messages. If sentence-transformers model not cached, either (a) add model warmup to test fixtures, or (b) mock the embedding function in tests.

**Confidence:** MEDIUM -- need to diagnose actual test failures rather than assume missing package.

#### pytest-asyncio

**Status:** Actually INSTALLED (1.3.0 confirmed via `uv pip list`). Version 1.3.0 is current (released late 2025) and supports `asyncio_mode = "auto"` as configured in pyproject.toml.

**Fix:** Verify test failures. Potential issues:
- Ensure pytest >= 8.2 (pytest-asyncio 1.3.0 requirement) -- check with `uv pip list | grep pytest`
- Confirm no leftover `@pytest.mark.asyncio` decorators conflicting with auto mode
- Check if tests using `asyncio.run()` conflict with pytest-asyncio's event loop management

**Confidence:** MEDIUM -- versions look correct; need to diagnose actual test failures.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| LLM-as-Judge | Pydantic + `with_structured_output` | `openevals` package | Adds dependency for one evaluation call; structured output does the same thing directly |
| LLM-as-Judge | Pydantic + `with_structured_output` | `deepeval` | Heavy testing framework; overkill for single fidelity evaluation |
| Token tracking | BudgetManager + usage_metadata | Langfuse | Heavyweight SaaS/self-hosted observability platform for a single cost column |
| Token tracking | BudgetManager + usage_metadata | `langchain-token-usage` PyPI | Thin wrapper; direct usage_metadata access is simpler and already implemented |
| Circuit breaker | stdlib implementation | `pybreaker` | Tornado dependency; 60 LOC vs new dependency for single integration point |
| Circuit breaker | stdlib implementation | `aiobreaker` | Reasonable but unnecessary dependency; project prefers stdlib |
| Circuit breaker | stdlib implementation | `tenacity` with retry+circuit | tenacity is retry-focused, not circuit-breaker-focused; conflates two patterns |
| ChromaDB pruning | Direct ChromaDB API | `chromadb-ops` | CLI tool, not programmatic; need integration in cycle pipeline |
| PersonaScore storage | PostgreSQL JSONB | Separate evaluation DB | Over-engineering; JSONB in existing merit table is sufficient |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|------------|
| `openevals` / `agentevals` | LangChain evaluation packages add dependency for what amounts to a structured output call + prompt template | Direct `with_structured_output(PersonaScore)` |
| `langfuse` | Full observability platform (self-hosted or SaaS) for simple per-cycle cost tracking | `BudgetManager.summary()` dict in CycleSnapshot |
| `pybreaker` / `aiobreaker` / `circuitbreaker` | External circuit breaker library for a single LLM integration point | 60-line stdlib implementation |
| `tenacity` | Retry library for what is already handled by manual backoff in yfinance_client.py | Existing manual retry pattern |
| `chromadb-ops` | CLI maintenance tool when programmatic API access is needed | `collection.get()` + `collection.delete()` |
| `opentelemetry` | Distributed tracing framework for simple cost aggregation | structlog context + BudgetManager |
| `numpy` for PersonaScore aggregation | Arithmetic mean of 5 floats does not need numpy | `sum(scores) / len(scores)` |

---

## Installation

```bash
# No new packages needed for v1.5 features!

# Fix broken ccxt:
uv pip install --force-reinstall ccxt

# Verify all deps resolve:
uv sync

# Verify key packages:
uv pip list | grep -iE 'ccxt|chromadb|pytest-asyncio'
```

**No changes to pyproject.toml required** (unless ccxt needs version pinning).

---

## Integration Points with Existing Stack

| New Component | Integrates With | How |
|---------------|----------------|-----|
| PersonaScore evaluator | `merit_updater_node` (src/graph/nodes/merit_updater.py) | New `_evaluate_persona_fidelity()` called during KAMI update; result feeds delta dimension |
| PersonaScore evaluator | `soul_loader.py` | Reads agent's SOUL.md content as evaluation context |
| PersonaScore evaluator | `kami.py` DEFAULT_WEIGHTS | Rebalance: alpha (Accuracy) drops from 0.30 to 0.05-0.10, delta (Fidelity/PersonaScore) absorbs the difference |
| Token tracking per cycle | `BudgetManager` (src/core/budget_manager.py) | Add `summary()` snapshot to CycleSnapshot at cycle completion |
| Token tracking per cycle | `cycle_runner.py` | Call `budget.reset_session()` at cycle start; `budget.summary()` at cycle end |
| Token tracking display | Replay CLI handlers | New column in cycle list table; new section in cycle show |
| Circuit breaker | New `src/core/circuit_breaker.py` | Shared instance accessible from L2 agent nodes |
| Circuit breaker | L2 agent nodes (analysts.py, researchers.py) | Wrap `llm.invoke()` / `llm.ainvoke()` with `breaker.pre_call()` / `breaker.record_success()` / `breaker.record_failure()` |
| Circuit breaker | `structlog` | Log state transitions (CLOSED->OPEN, OPEN->HALF_OPEN, HALF_OPEN->CLOSED) |
| ChromaDB pruner | `MemoryService` (src/memory/service.py) | New `prune_old_documents()` method |
| ChromaDB pruner | Obsidian vault generation scripts | Export archived documents as Markdown before deletion |

---

## Sources

- [ChatGoogleGenerativeAI reference](https://reference.langchain.com/python/integrations/langchain_google_genai/ChatGoogleGenerativeAI/) -- HIGH confidence
- [langchain_core UsageMetadata API](https://python.langchain.com/api_reference/core/messages/langchain_core.messages.ai.UsageMetadata.html) -- HIGH confidence
- [LangChain LLM-as-Judge docs](https://docs.langchain.com/langsmith/llm-as-judge) -- HIGH confidence
- [openevals LLM-as-Judge evaluators](https://github.com/langchain-ai/openevals) -- MEDIUM confidence (evaluated, not adopted)
- [ChromaDB delete data docs](https://docs.trychroma.com/docs/collections/delete-data) -- HIGH confidence
- [ChromaDB WAL pruning cookbook](https://cookbook.chromadb.dev/core/advanced/wal-pruning/) -- MEDIUM confidence
- [ChromaDB maintenance cookbook](https://cookbook.chromadb.dev/running/maintenance/) -- MEDIUM confidence
- [pybreaker GitHub](https://github.com/danielfm/pybreaker) -- evaluated, rejected
- [circuitbreaker PyPI](https://pypi.org/project/circuitbreaker/) -- evaluated, rejected
- [aiobreaker docs](https://aiobreaker.netlify.app/) -- evaluated, rejected
- [ccxt static_dependencies issue #23307](https://github.com/ccxt/ccxt/issues/23307) -- MEDIUM confidence (analogous bug)
- [pytest-asyncio PyPI](https://pypi.org/project/pytest-asyncio/) -- HIGH confidence
- Codebase: `src/graph/agents/analysts.py:155-160` -- usage_metadata already consumed
- Codebase: `src/core/budget_manager.py` -- BudgetManager tracks tokens + USD with thread-safe counters
- Codebase: `src/memory/service.py` -- MemoryService is sole ChromaDB interface with timestamp metadata
- Codebase: `src/core/kami.py` -- DEFAULT_WEIGHTS shows alpha=0.30 (Accuracy) needs rebalancing
- Environment: `uv pip list` output 2026-03-09 -- all versions confirmed

---

*Stack research for: Quantum Swarm v1.5 Reliable Infrastructure*
*Researched: 2026-03-09*
