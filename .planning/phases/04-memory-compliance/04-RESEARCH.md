# Phase 4: Memory & Institutional Compliance — Research

**Researched:** 2026-03-07 (retroactive — phase already complete as of 2026-03-06)
**Domain:** PostgreSQL persistence, hash-chained audit logging, institutional guardrails, ChromaDB vector memory, trade warehouse
**Confidence:** HIGH (based on direct inspection of all implementation files and test suites)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **State**: Must move off ephemeral in-memory checkpoints to durable Postgres.
- **Performance**: Audit logging must not block execution (async).
- **Immutability**: Logs must be tamper-evident (hash chains).
- **Stack**: Python 3.12+, PostgreSQL, DuckDB, LangGraph.
- **Decision Provenance**: Every `ExecutionResult` must link back to a `GraphDecision` and specific `ResearchNotes`.
- **Regime Tagging**: Auto-tagging of market regimes (volatility, trend) to improve agent memory retrieval.

### Claude's Discretion
- (No explicit discretion areas listed in CONTEXT.md)

### Deferred Ideas (OUT OF SCOPE)
- Redis cache layer (mentioned in early research but not delivered)
- Kafka/Redpanda event bus (listed as optional/future)
- pgvector (replaced by ChromaDB)
- S3/MinIO remote storage (listed as production future state)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MEM-01 | Cross-session persistent memory so agents retain knowledge across runs | Delivered by MemoryService (ChromaDB) + AsyncPostgresSaver (LangGraph state) |
| SEC-01 | Restricted asset blocklist enforced before order routing | Delivered by InstitutionalGuard.check_compliance() restricted_assets check |
| SEC-02 | Maximum leverage hard limit before order routing | Delivered by InstitutionalGuard max_leverage check |
| SEC-04 | Compliance flags propagate through SwarmState for downstream visibility | Delivered by institutional_guard_node writing to state["compliance_flags"] |
| RISK-02 | Pre-trade risk scoring to quantify exposure before execution | Delivered by InstitutionalGuard.calculate_risk_score() (0.0–1.0 normalized score) |
</phase_requirements>

---

## Summary

Phase 4 transforms the quantum swarm from a stateless research prototype into an auditable institutional-grade platform. The implementation delivers five distinct subsystems: PostgreSQL-backed LangGraph checkpointing, hash-chained immutable audit logs, a structured vector memory service, an institutional guardrails gate, and a trade warehouse with full signal-to-execution provenance.

**Persistence** is handled by `langgraph-checkpoint-postgres` (`AsyncPostgresSaver`) with a `psycopg_pool.AsyncConnectionPool` (min=2, max=10) pointing at PostgreSQL 16 on port 5433. The pool uses lazy initialisation (`open=False`) so no database connection is needed at import time. Schema setup is called once via `setup_persistence()` at application startup.

**Audit trail** uses two complementary mechanisms: (1) `src/core/audit_logger.py` — a PostgreSQL-backed SHA-256 hash chain where each row's `entry_hash` is computed from the row payload plus the prior row's `entry_hash`, making single-row tampering detectable on chain replay; and (2) `src/memory/audit.py` — a lightweight append-only JSONL file written by `MemoryService` for every store/search/delete/deduplicate operation, providing a fast, filesystem-based secondary audit trail.

**Vector memory** is handled by a purpose-built `MemoryService` class (`src/memory/service.py`) that is the sole interface to ChromaDB. It supports three typed sources (`TRADE`, `RESEARCH`, `EXTERNAL_DATA`), enforces required metadata per source, chunks documents using a three-tier fallback strategy (paragraph → sentence → hard character split), generates deterministic document IDs, and deduplicates by SHA-256 content hash.

**Institutional guardrails** (`src/security/institutional_guard.py`) run after the domain `RiskManager` and before the `OrderRouter`. They enforce max leverage, restricted asset blocklist, max concurrent trades, max notional exposure, and asset concentration limits — all sourced from `swarm_config.yaml`. A normalized risk score (0.0–1.0) is also calculated and written to `state["metadata"]`.

**Primary recommendation:** The four-layer architecture (Postgres checkpoints + hash-chain audit + ChromaDB memory + guard gate) is the correct institutional foundation. The only gap identified is that the tests for the PostgreSQL-dependent subsystems require a live database and cannot run in CI without the Docker container.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| psycopg | 3.2.x | Async PostgreSQL driver (psycopg3) | Native async support, psycopg2 is legacy |
| psycopg-pool | 3.2.x | Async connection pool for psycopg3 | Required companion to psycopg3 |
| langgraph-checkpoint-postgres | (pinned with langgraph) | AsyncPostgresSaver for distributed LangGraph state | Official LangGraph adapter |
| chromadb | (project-pinned) | Embedded vector store for MemoryService | No separate server needed, EphemeralClient available for tests |
| pydantic | v2 | AuditLogEntry and TradeRecord data contracts | Already in project stack |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| duckdb | (project-pinned) | Read-only analytical queries against historical OHLCV | KnowledgeBase.query_historical_stats() |
| hashlib (stdlib) | Python 3.12 | SHA-256 for audit chain and content deduplication | No external dependency needed |
| fcntl (stdlib) | Python 3.12 | Advisory file locking for InterAgentBlackboard | Concurrent agent writes on Linux/macOS |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ChromaDB | pgvector | pgvector co-locates vectors in Postgres (fewer moving parts) but requires Postgres extension; ChromaDB runs embedded and is easier to test |
| Filesystem JSONL audit | PostgreSQL-only audit | JSONL is zero-dependency and survives DB outages; Postgres audit has richer querying |
| psycopg3 pool | SQLAlchemy async | psycopg3 pool is lighter and directly required by langgraph-checkpoint-postgres |

### Installation
```bash
pip install psycopg[binary,pool] langgraph-checkpoint-postgres chromadb duckdb
docker compose up -d  # starts postgres:16-alpine on port 5433
```

---

## Architecture Patterns

### Actual Project Structure (Phase 4 deliverables)
```
src/
├── core/
│   ├── db.py                  # Global AsyncConnectionPool, DB_URL
│   ├── persistence.py         # get_checkpointer(), setup_persistence()
│   ├── audit_logger.py        # AuditLogger (Postgres hash chain)
│   ├── blackboard.py          # InterAgentBlackboard (session-scoped filesystem KV)
│   └── budget_manager.py      # Token spend tracking + SafetyShutdown
├── memory/
│   ├── service.py             # MemoryService — sole ChromaDB interface
│   ├── audit.py               # AuditLog (JSONL append-only writer)
│   ├── config.py              # Chunking constants + collection name
│   ├── indexer.py             # run_deduplication()
│   └── tools.py               # make_memory_search_tool(), filter_hits_by_recency()
├── security/
│   └── institutional_guard.py # InstitutionalGuard + institutional_guard_node
├── graph/
│   └── nodes/
│       ├── institutional_guard.py  # (stub — 1-line re-export)
│       ├── knowledge_base.py        # Async node: DuckDB + ChromaDB query
│       ├── write_trade_memory.py    # Sync node: store trade outcome to MemoryService
│       ├── write_research_memory.py # Sync node: store debate resolution
│       └── write_external_memory.py # Sync node: store data_fetcher_result
├── models/
│   ├── audit.py               # AuditLogEntry (Pydantic)
│   └── data_models.py         # TradeRecord, MarketData, etc. (Pydantic)
└── tools/
    └── knowledge_base.py      # KnowledgeBase class (legacy, uses old singleton pattern)
```

### Pattern 1: Lazy Pool Initialization
**What:** The global `AsyncConnectionPool` in `src/core/db.py` is created with `open=False`. The pool object exists at module load time but no TCP connection is made until the first `async with pool.connection()` call.
**When to use:** Any module-level database resource. Required because `GOOGLE_API_KEY` and `DATABASE_URL` may not be present at import time in test environments.

```python
# src/core/db.py
_pool: AsyncConnectionPool = None

def get_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(conninfo=DB_URL, open=False, min_size=2, max_size=10)
    return _pool
```

### Pattern 2: Hash-Chain Audit Log
**What:** Each audit log row stores `entry_hash = SHA-256(payload_json + prev_entry_hash)`. Chain integrity is verified by replaying all rows in insertion order and recomputing hashes.
**When to use:** Any append-only log requiring tamper evidence. Used by `AuditLogger.log_transition()`.

```python
# src/core/audit_logger.py
def _calculate_hash(self, entry: Dict, prev_hash: Optional[str]) -> str:
    data_string = json.dumps({...}, sort_keys=True)
    hasher = hashlib.sha256()
    hasher.update(data_string.encode('utf-8'))
    if prev_hash:
        hasher.update(prev_hash.encode('utf-8'))
    return hasher.hexdigest()
```

### Pattern 3: Memory Write Nodes (Fire-and-Forget)
**What:** The three write-memory graph nodes (`write_trade_memory`, `write_research_memory`, `write_external_memory`) call `memory.store()` and return `{}` — no state changes. They catch all exceptions so a ChromaDB failure never halts the trading flow.
**When to use:** Any side-effect node that should not block or fail the main graph path.

```python
# src/graph/nodes/write_trade_memory.py
def write_trade_memory_node(state: SwarmState, memory: MemoryService) -> SwarmState:
    try:
        memory.store(content=..., source=MemorySource.TRADE, metadata=..., node="write_trade_memory")
    except Exception as exc:
        logger.error("write_trade_memory: failed to store trade result: %s", exc)
    return {}  # never propagates failure to SwarmState
```

### Pattern 4: MemoryService Dependency Injection
**What:** `MemoryService` accepts an optional `collection` argument in `__init__`. When provided, it bypasses the `chromadb.PersistentClient` and uses the injected collection directly. Tests use `chromadb.EphemeralClient()` for an in-memory store with no filesystem side effects.
**When to use:** Any service wrapping an external store. Makes tests hermetic without mocking the entire ChromaDB API.

### Pattern 5: InstitutionalGuard Gate Ordering
**What:** The guard runs after the domain `RiskManager` node but before `OrderRouter`. It enforces limits from `swarm_config.yaml["risk_limits"]` and writes to `state["compliance_flags"]` and `state["metadata"]`. An approved result does NOT set `risk_approved` — that is already set by the upstream `RiskManager`.
**When to use:** Final pre-execution compliance check.

### Anti-Patterns to Avoid
- **Global singleton at module level for ChromaDB (`kb = KnowledgeBase()` in `src/tools/knowledge_base.py`):** This instantiates ChromaDB at import time, causing failures in test environments where `chromadb` is absent. The `src/memory/service.py` lazy import pattern is correct; the legacy `knowledge_base.py` singleton is a known tech debt item.
- **Pool opened without `open=False`:** If `AsyncConnectionPool` is created without `open=False`, it attempts a TCP connection immediately on import, breaking test isolation.
- **Hash chain with session-local `_last_hash`:** `AuditLogger._last_hash` is instance-scoped. If multiple `AuditLogger` instances are created in the same session, each starts its own chain from the last DB entry but they are not synchronized. Only one shared `AuditLogger` instance should be used per session.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LangGraph state checkpointing | Custom Postgres serializer | `langgraph-checkpoint-postgres` AsyncPostgresSaver | Handles schema creation, thread-based resume, concurrent writes |
| Vector similarity search | SQL LIKE or cosine function | ChromaDB MemoryService | Handles embedding, HNSW index, metadata filtering |
| Document chunking | Simple character split | `_split_into_chunks()` (paragraph→sentence→hard) | Preserves semantic boundaries, handles edge cases |
| Duplicate memory detection | Timestamp comparison | SHA-256 content hash + `run_deduplication()` | Content-addressed deduplication is deterministic across sessions |
| Concurrent file writes | Global lock or queue | `fcntl.flock` advisory locks in `InterAgentBlackboard` | OS-level locking, works across processes |

**Key insight:** The compliance gate and audit trail are exactly the kind of "looks simple but isn't" problems where custom solutions accumulate edge cases. PostgreSQL's `SERIAL` + `TIMESTAMPTZ` + `JSONB` schema is sufficient — no specialized append-only database is needed for institutional audit volumes.

---

## Common Pitfalls

### Pitfall 1: PostgreSQL Tests Require Live Database
**What goes wrong:** `test_persistence.py` and `test_audit_chain.py` open real connections to `postgresql://quantum_user:quantum_password@localhost:5433/quantum_swarm`. If the Docker container is not running, these tests fail with connection refused.
**Why it happens:** No mock or in-memory Postgres substitute was introduced. The choice was deliberate — the tests exercise the real schema.
**How to avoid:** Run `docker compose up -d` before the test suite. Use `TRUNCATE audit_logs RESTART IDENTITY CASCADE` in test fixtures (already done in `test_audit_chain.py`).
**Warning signs:** `psycopg.OperationalError: connection refused` or `pool timeout` in test output.

### Pitfall 2: AuditLogger Chain Break on Concurrent Instances
**What goes wrong:** If two `AuditLogger` instances are created after the same last DB entry, both start a new chain link from that entry. When `verify_chain()` is called, the second chain will fail because `prev_hash` pointers diverge.
**Why it happens:** `_last_hash` is per-instance state, not per-connection state.
**How to avoid:** Treat `AuditLogger` as a session-level singleton. One instance per application lifecycle.
**Warning signs:** `verify_chain()` returning `False` immediately after two writers are active.

### Pitfall 3: ChromaDB Module-Level Singleton
**What goes wrong:** `src/tools/knowledge_base.py` instantiates `KnowledgeBase()` at module level (`kb = KnowledgeBase()`). This calls `chromadb.PersistentClient()` on import. In environments where `chromadb` is not installed, every import of that module fails.
**Why it happens:** Legacy pattern from pre-MemoryService design.
**How to avoid:** The `MemoryService` in `src/memory/service.py` uses a lazy import (`import chromadb` inside `__init__`). Do not add new module-level singletons for heavy dependencies.
**Warning signs:** `ModuleNotFoundError: No module named 'chromadb'` during test collection.

### Pitfall 4: InstitutionalGuard check_compliance is async but tests call it synchronously
**What goes wrong:** The actual `InstitutionalGuard.check_compliance()` in the production file is `async` (it calls `await self._get_open_positions()`). The test file `test_institutional_guard.py` calls it without `await`. This means the tests are exercising a stripped-down or older version of the guard that had synchronous checks only.
**Why it happens:** The guard was refactored during Phase 8 (Portfolio Risk Governance) to add async portfolio checks. The Phase 4 tests were not updated.
**How to avoid:** Any test of `check_compliance()` that involves portfolio limit checks must use `asyncio.run()` or `@pytest.mark.asyncio`.
**Warning signs:** Tests passing that should test async portfolio rejection logic but don't cover it.

### Pitfall 5: Trade Warehouse `exit_time` Column Missing
**What goes wrong:** `InstitutionalGuard._get_open_positions()` queries `WHERE exit_time IS NULL`. The `trades` table schema in `setup_persistence()` does not define an `exit_time` column. This query will fail with a column-not-found error at runtime when portfolio checks are attempted.
**Why it happens:** The `exit_time` column was added to `TradeRecord` (the Pydantic model) and referenced in guard logic but was not added to the `CREATE TABLE` DDL in `persistence.py`.
**How to avoid:** Add `exit_time TIMESTAMPTZ` to the `trades` table DDL. Mark this as a schema migration gap.
**Warning signs:** `psycopg.errors.UndefinedColumn: column "exit_time" does not exist` at runtime.

### Pitfall 6: docker-compose.yml Uses postgres:16 not postgres:17
**What goes wrong:** `04-01-SUMMARY.md` states "PostgreSQL 17" but `docker-compose.yml` uses `postgres:16-alpine`. The discrepancy is cosmetic (both work with the current schema) but can cause confusion.
**Why it happens:** Version was downgraded during implementation; summary was not updated.
**How to avoid:** Trust the actual `docker-compose.yml` as the source of truth.

---

## Code Examples

Verified patterns from direct source inspection:

### Setting Up Persistence (Application Startup)
```python
# src/core/persistence.py
from src.core.persistence import setup_persistence, get_checkpointer

# Called once at startup
await setup_persistence()

# Per-graph-run
async with get_checkpointer() as checkpointer:
    graph = create_orchestrator_graph(config, checkpointer=checkpointer)
    await graph.ainvoke(state, config={"configurable": {"thread_id": task_id}})
```

### Logging a Node Transition
```python
# src/core/audit_logger.py
audit = AuditLogger()
await audit.initialize()  # idempotent — creates table, loads last_hash

await audit.log_transition(
    task_id="task-abc",
    node_id="institutional_guard",
    input_data={"symbol": "BTC/USDT", "quantity": 1.0},
    output_data={"approved": True, "risk_score": 0.32}
)

is_valid = await audit.verify_chain()  # True if chain is intact
```

### Storing Trade Memory
```python
# src/memory/service.py
from src.memory.service import MemoryService, MemorySource

svc = MemoryService()  # uses data/chroma_db by default
doc_id = svc.store(
    content="Bought 0.5 BTC at 42000. Consensus score 0.78. Stop-loss at 40000.",
    source=MemorySource.TRADE,
    metadata={"symbol": "BTC/USDT", "timestamp": "2026-03-06T12:00:00Z", "run_id": "task-abc"},
    node="write_trade_memory"
)

hits = svc.search("BTC strong buy momentum", source_filter=MemorySource.TRADE, k=5)
```

### Compliance Check
```python
# src/security/institutional_guard.py
guard = InstitutionalGuard(config={
    "risk_limits": {
        "restricted_assets": ["XRP/USDT"],
        "max_leverage": 10.0,
        "max_notional_exposure": 500000.0,
        "max_asset_concentration_pct": 0.20,
        "max_concurrent_trades": 10,
        "starting_capital": 1000000.0,
    }
})

# check_compliance is async — requires running event loop
result = await guard.check_compliance(state)
# result: {"approved": True, "risk_score": 0.31, "portfolio_heat": 0.12}
# or:     {"approved": False, "violation": "Asset XRP/USDT is restricted."}
```

### InterAgentBlackboard (Session-Scoped)
```python
# src/core/blackboard.py
from src.core.blackboard import InterAgentBlackboard

board = InterAgentBlackboard()  # uses data/inter_agent_comms/
board.write_state("session-123", "objective", {"symbol": "ETH", "intent": "trade"})
data = board.read_state("session-123", "objective")
keys = board.list_keys("session-123")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Ephemeral in-memory LangGraph state | AsyncPostgresSaver Postgres checkpointing | Phase 4 | Graph runs are resumable after any node failure |
| No audit trail | SHA-256 hash-chained `audit_logs` table + JSONL file | Phase 4 | Every node transition is tamper-evidently recorded |
| No vector memory | MemoryService (ChromaDB, 3-source, chunked) | Phase 4 | Cross-session learning; agents retrieve relevant prior decisions |
| No compliance gate | InstitutionalGuard (leverage, blocklist, portfolio limits) | Phase 4 / Phase 8 | Hard pre-execution enforcement independent of domain agents |
| No trade warehouse | `trades` PostgreSQL table with `audit_log_id` FK | Phase 4 | Full signal-to-execution provenance chain |
| Freeform MEMORY.md rules | Structured JSON registry with lifecycle states | Phase 9 | Rules are versioned, validated, and discoverable |

**Deprecated/outdated:**
- `src/tools/knowledge_base.py` singleton: predates MemoryService; wraps legacy KnowledgeBase with DuckDB + old ChromaDB collection. Still used by `knowledge_base_node` but is architectural debt. The `MemoryService` path is the correct pattern for all new memory work.
- Early research doc references to Redis, pgvector, Kafka, S3: all deferred or replaced.

---

## Open Questions

1. **`exit_time` column missing from `trades` DDL**
   - What we know: `InstitutionalGuard._get_open_positions()` queries `WHERE exit_time IS NULL`. `TradeRecord` Pydantic model has `exit_time: Optional[datetime]`. The `CREATE TABLE trades` DDL in `persistence.py` does not include `exit_time`.
   - What's unclear: Was this column added via a manual migration? Is the portfolio check tested end-to-end against a live DB?
   - Recommendation: Add `exit_time TIMESTAMPTZ` to DDL and create a migration; add a live-DB test for the portfolio rejection path.

2. **InstitutionalGuard async/sync mismatch in Phase 4 tests**
   - What we know: `test_institutional_guard.py` calls `guard.check_compliance(state)` synchronously. The current implementation is `async def check_compliance()`.
   - What's unclear: Are these tests actually running and passing, or silently skipped/broken?
   - Recommendation: Audit whether the 42 "new Phase 4 tests" count includes these guard tests passing correctly; if not, convert them to `@pytest.mark.asyncio`.

3. **AuditLogger cross-session chain continuity**
   - What we know: `AuditLogger.initialize()` calls `_get_last_hash()` to resume the chain from the last DB entry. This means a fresh instance in a new process correctly continues the chain.
   - What's unclear: If the database is wiped for test isolation (`TRUNCATE audit_logs`), the chain always restarts from `prev_hash=None`. There is no mechanism to archive or export the chain before truncation.
   - Recommendation: Document that test truncation is acceptable; production should never truncate, only archive to cold storage.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (Python 3.12) |
| Config file | None — run via `.venv/bin/python3.12 -m pytest` |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/test_institutional_guard.py tests/test_inter_agent_blackboard.py tests/test_budget_tracking.py tests/test_memory.py tests/test_memory_nodes.py -x` |
| Full suite command | `.venv/bin/python3.12 -m pytest tests/ -x` |
| DB-dependent tests | Require `docker compose up -d` first |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MEM-01 | ChromaDB store/retrieve persists across MemoryService instances | unit + integration | `pytest tests/test_memory.py -x` | Yes |
| MEM-01 | LangGraph state persisted and resumable from Postgres | integration (DB required) | `pytest tests/test_persistence.py::test_langgraph_persistence_postgres -x` | Yes |
| MEM-01 | Trade outcomes stored to vector memory via write_trade_memory_node | unit | `pytest tests/test_memory_nodes.py -x` | Yes |
| SEC-01 | Restricted asset blocked before order routing | unit | `pytest tests/test_institutional_guard.py::test_institutional_guard_restricted_asset -x` | Yes |
| SEC-02 | Leverage above max rejected | unit | `pytest tests/test_institutional_guard.py::test_institutional_guard_leverage -x` | Yes |
| SEC-04 | INSTITUTIONAL_VIOLATION flag written to SwarmState compliance_flags | unit | `pytest tests/test_institutional_guard.py::test_institutional_guard_node_logic -x` | Yes |
| RISK-02 | Risk score 0–1 calculated and written to state["metadata"] | unit | `pytest tests/test_institutional_guard.py::test_institutional_guard_node_logic -x` | Yes |
| Audit chain | SHA-256 chain verifies clean (3-entry sequence) | integration (DB required) | `pytest tests/test_audit_chain.py::test_audit_chain_integrity -x` | Yes |
| Audit chain | Tampered entry fails chain verification | integration (DB required) | `pytest tests/test_audit_chain.py::test_audit_chain_tamper_detection -x` | Yes |
| Trade warehouse | Trade written to `trades` table with correct symbol/quantity | integration (DB required) | `pytest tests/test_persistence.py::test_trade_warehouse_persistence -x` | Yes |
| Blackboard | Session isolation, concurrent write safety, fcntl locking | unit | `pytest tests/test_inter_agent_blackboard.py -x` | Yes |
| Budget | BudgetManager records tokens, SafetyShutdown on breach | unit | `pytest tests/test_budget_tracking.py -x` | Yes |
| Memory JSONL audit | store_success/store_error events written to .jsonl | unit | `pytest tests/test_memory.py::TestAuditLog -x` | Yes |
| MemoryService chunks | Long document splits into multiple chunks with overlap | unit | `pytest tests/test_memory.py::TestChunking -x` | Yes |
| MemoryService dedup | Duplicate by content_hash removed, orphans pruned | unit | `pytest tests/test_memory.py::TestIndexer -x` | Yes |
| KnowledgeBase node | knowledge_base_node returns structured dict (DuckDB+ChromaDB) | integration | `pytest tests/test_knowledge_base.py -x` | Yes |

### Test Subsystem Coverage

#### Postgres-Dependent Tests (require Docker)
- `tests/test_persistence.py` — 2 tests: LangGraph resume + trade warehouse write
- `tests/test_audit_chain.py` — 2 tests: chain integrity + tamper detection
- **Gap:** No test for `InstitutionalGuard._get_open_positions()` against real DB

#### In-Memory / No-DB Tests (always runnable)
- `tests/test_institutional_guard.py` — 3 tests: restricted asset, leverage, node state output
  - **Important caveat:** These tests call `guard.check_compliance(state)` synchronously. The current production method is `async def check_compliance()`. If the tests pass, it implies an older synchronous code path is still being exercised. Verify against live code.
- `tests/test_inter_agent_blackboard.py` — 5 tests: write/read, session isolation, list_keys, concurrent writes
- `tests/test_budget_tracking.py` — 3 tests: token accumulation, USD cost, SafetyShutdown trigger
- `tests/test_memory.py` — 23+ tests across MemoryService core, chunking, ID generation, audit log, indexer, tools, recency filter, integration
- `tests/test_memory_nodes.py` — 12 tests: write_trade_memory, write_research_memory, write_external_memory nodes (mock MemoryService injection)
- `tests/test_knowledge_base.py` — 3 tests: node output structure, sentiment query, missing symbol

### Specific Test Scenarios

#### Happy Path — Full Compliance Approval
1. `InstitutionalGuard` receives proposal for `BTC/USDT` (not restricted)
2. Portfolio position count is below max_concurrent
3. Notional exposure is below max_notional_exposure
4. Concentration for BTC/USDT is below 20%
5. Expected: `{"approved": True, "risk_score": <float>, "portfolio_heat": <float>}`

#### Edge Cases
- Symbol at exactly max leverage: ensure boundary condition is tested (`leverage == max_leverage`)
- Empty quant_proposal: guard should handle gracefully (no KeyError)
- Portfolio heat at exactly 1.0: `calculate_risk_score` should return 1.0

#### Compliance Rejection Scenarios
- `symbol in restricted_assets`: returns `{"approved": False, "violation": "Asset X is restricted."}`
- `len(open_positions) >= max_concurrent`: returns violation with count
- `(current_total_notional + new_notional) > max_notional_exposure`: returns notional violation
- `(asset_notional + new_notional) / starting_capital > max_concentration`: returns concentration violation

#### Audit Chain Test Scenarios
- Insert 3 entries, verify_chain() returns True (covered)
- Tamper output_data of row 1, verify_chain() returns False (covered)
- Empty chain: verify_chain() returns True (not covered — edge case)
- New session continuing existing chain: verify_chain() returns True (not covered)

### Sampling Rate
- **Per task commit:** `.venv/bin/python3.12 -m pytest tests/test_institutional_guard.py tests/test_memory.py tests/test_memory_nodes.py tests/test_inter_agent_blackboard.py -x`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest tests/ -x` (requires Docker for DB tests)
- **Phase gate:** All 42+ Phase 4 tests green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_institutional_guard.py` — needs conversion to `@pytest.mark.asyncio` for `check_compliance()` portfolio-level tests (current tests may be exercising a stale sync code path)
- [ ] No test for `InstitutionalGuard._get_open_positions()` with real DB (covers the `exit_time` bug surface)
- [ ] No test for `AuditLogger` session continuity (new instance picks up chain from last DB row)
- [ ] No test for `setup_persistence()` schema idempotency (CREATE TABLE IF NOT EXISTS + index)
- [ ] No test for empty audit chain `verify_chain()` — should return True

---

## Sources

### Primary (HIGH confidence)
- Direct file inspection: `src/core/persistence.py`, `src/core/audit_logger.py`, `src/core/db.py`, `src/core/blackboard.py`, `src/core/budget_manager.py`
- Direct file inspection: `src/security/institutional_guard.py`
- Direct file inspection: `src/memory/service.py`, `src/memory/audit.py`, `src/memory/config.py`, `src/memory/indexer.py`, `src/memory/tools.py`
- Direct file inspection: `src/graph/nodes/write_trade_memory.py`, `knowledge_base.py`, `institutional_guard.py`
- Direct file inspection: `src/models/audit.py`, `src/models/data_models.py`
- Direct file inspection: `docker-compose.yml`
- Direct file inspection: `.planning/phases/04-memory-compliance/04-CONTEXT.md`, `04-01-SUMMARY.md`

### Secondary (MEDIUM confidence)
- Test file analysis: `tests/test_persistence.py`, `tests/test_audit_chain.py`, `tests/test_institutional_guard.py`, `tests/test_inter_agent_blackboard.py`, `tests/test_budget_tracking.py`, `tests/test_memory.py`, `tests/test_memory_nodes.py`, `tests/test_knowledge_base.py`
- `.planning/STATE.md` — 155 total tests passing post-Phase 4 (now 176 at Phase 9)
- `.planning/ROADMAP.md` — phase status and requirements mapping

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed by direct import inspection in source files
- Architecture: HIGH — documented from actual source, not proposed design
- Pitfalls: HIGH for identified bugs (exit_time gap, async/sync mismatch); MEDIUM for chain continuity edge case
- Test coverage: HIGH for what exists; MEDIUM for gap analysis (async guard test behavior unconfirmed without running suite)

**Research date:** 2026-03-07
**Valid until:** 2026-06-07 (stable stack; ChromaDB API is the fastest-moving component)
