# Phase 4: Memory & Knowledge Store

## Summary

Phase 4 introduces a persistent semantic memory layer backed by ChromaDB.

`MemoryService` is the sole interface to the vector store and provides `store()`,
`search()`, and retrieval operations. Documents are stored as chunked embeddings with
deterministic IDs and source-specific metadata.

Agents access memory in three ways:
- **L1** — routing enrichment via direct service call
- **L2** — ReAct tool retrieval during reasoning
- **L3** — post-trade outcome persistence

Writes occur synchronously in dedicated graph nodes, while reads are bounded and
recency-filtered. All operations emit structured audit events to an append-only JSONL
log. Maintenance tasks (deduplication and orphan cleanup) run weekly via the indexer job.

---

## Goals

- Give agents persistent recall of past trades, research, and market data across runs
- Single unified ChromaDB collection with source-tagged metadata for filtered retrieval
- Clear service boundary — no vector DB details leak into agents
- Minimal compliance scope: append-only audit log recording every store/search/delete

## Non-Goals

- Position limit enforcement (deferred)
- Regulatory reporting (deferred)
- Full document versioning (latest-version-only; audit log is the history)
- Multi-collection ChromaDB (metadata filtering is sufficient)

---

## Architecture

### Module Layout

```
src/memory/
  __init__.py
  service.py      # MemoryService — public API, validation, read/write/search
  tools.py        # LangChain Tool wrappers for L2 ReAct injection
  indexer.py      # Weekly deduplication and orphan cleanup
  audit.py        # Append-only JSONL audit writer (called only by MemoryService)
```

### Dependency Injection

`MemoryService` is constructed once in `main.py` and passed into the LangGraph graph
via the `configurable` dict — the idiomatic LangGraph pattern for shared services. No
process-global singleton.

```python
# main.py
memory = MemoryService(chroma_path="data/chroma_db")
graph.invoke(initial_state, config={"configurable": {"memory": memory}})
```

A single helper retrieves it inside any node:

```python
def get_memory_service(config: RunnableConfig) -> MemoryService:
    return cast(MemoryService, config["configurable"]["memory"])
```

---

## MemoryService Interface

```python
class MemorySource(str, Enum):
    TRADE = "trade"
    RESEARCH = "research"
    EXTERNAL_DATA = "external_data"

@dataclass
class MemoryHit:
    document_id: str
    chunk_id: str
    content: str
    source: MemorySource
    metadata: dict[str, Any]
    score: float  # normalized relevance; higher is better

@dataclass
class StoredDocument:
    document_id: str
    chunks: list[str]   # ordered by chunk_index
    source: MemorySource
    metadata: dict[str, Any]

class MemoryService:
    def __init__(self, chroma_path: str | None = None, collection=None): ...

    def store(
        self,
        content: str,
        source: MemorySource,
        metadata: dict[str, Any],
        document_id: str | None = None,
    ) -> str:
        """Store or update a logical document and its chunks. Writes audit event."""

    def search(
        self,
        query: str,
        source_filter: MemorySource | None = None,
        k: int = 5,
    ) -> list[MemoryHit]:
        """Return ranked memory hits. score is normalized relevance (higher = better)."""

    def get(self, document_id: str) -> StoredDocument | None:
        """Fetch and reassemble a stored logical document from its chunks."""

    def delete(self, document_id: str) -> None:
        """Delete all chunks for a document. Writes audit event."""

    def deduplicate(self) -> DeduplicationResult:
        """Remove duplicate and orphaned chunks. Called by indexer."""

    def health_check(self) -> bool:
        """Verify ChromaDB connectivity."""
```

---

## Document Identity

### Deterministic IDs

```python
# trade:         sha256(f"{symbol}:{timestamp_utc}:{run_id}")
# research:      sha256(f"{run_id}:{agent}:{timestamp_utc}")
# external_data: sha256(f"{source_name}:{data_type}:{title_or_url_or_external_id}:{timestamp_utc}")
#
# All IDs: f"{source_prefix}_{hash[:24]}"
# Examples:
#   trade_a3f9c2b1d4e8f01234567890
#   research_7d2c4b9e1f3a8c0056789012
#   external_data_5e1b3d7f9c2a4e6078901234
#
# Fallback: f"{source_prefix}_{uuid4().hex[:24]}" if caller does not provide one
```

### Upsert Semantics (latest-version-only)

On `store()` with an existing `document_id`:
1. Fetch current chunk IDs for `document_id`
2. Compute new chunks
3. Delete stale chunk IDs not present in the new set
4. Upsert all new/current chunks
5. Write audit event recording the replacement

---

## Chunking Model

Chunking is internal to `service.py` — callers always pass full document text.

**Thresholds (config constants in `src/memory/config.py`):**

| Constant | Default |
|---|---|
| `CHUNK_SINGLE_THRESHOLD_TOKENS` | 512 |
| `CHUNK_MAX_TOKENS` | 400 |
| `CHUNK_OVERLAP_TOKENS` | 50 |

**Fallback splitter chain:** paragraph boundary → sentence boundary → hard token split

**Chunk IDs:** `{document_id}:{chunk_index:04d}` (e.g. `trade_abc123:0000`)

**Shared metadata on every chunk:**

```python
{
    "document_id": str,
    "chunk_id": str,
    "chunk_index": int,
    "chunk_count": int,
    "source": str,          # MemorySource value
    "content_hash": str,    # SHA-256 of normalized full document content
    "timestamp": str,       # UTC ISO 8601 with Z, source event time
    "ingested_at": str,     # UTC ISO 8601 with Z, system storage time
    # ...plus source-specific required fields below
}
```

**Content normalization for hashing:** strip leading/trailing whitespace, normalize line
endings to `\n`, Unicode NFC normalization, lowercase hex hash output.

---

## Metadata Contract Per Source

| Field | `trade` | `research` | `external_data` |
|---|---|---|---|
| `symbol` | required | required | optional |
| `timestamp` | required | required | required |
| `run_id` | required | required | — |
| `agent` | — | required | — |
| `data_type` | — | — | required (`news`/`economic`/`fundamental`) |
| `source_name` | — | — | required |
| `title_or_url` | — | — | required (for ID stability) |
| `content_hash` | required | required | required |
| `ingested_at` | required | required | required |
| `pnl` | optional | — | — |
| `direction` | optional | — | — |

All string fields are validated at the `MemoryService` boundary:
- `symbol`: uppercase string
- `timestamp` / `ingested_at`: UTC ISO 8601 with `Z`
- `agent`: constrained to known agent names
- `data_type`: `Literal["news", "economic", "fundamental"]`
- `content_hash`: lowercase hex string

---

## Agent Integration

### L1 — Routing Enrichment (direct call)

Before the strategic intent classifier routes a run, it queries memory for recent
similar setups. Recency is enforced: only hits with `timestamp >= now - 30d` are passed
to the prompt.

```python
hits = memory.search(query=f"{symbol} {intent}", k=3)
# Filter: hits where metadata["timestamp"] >= 30 days ago
# Format: max 2-3 hits, trimmed excerpts, timestamp + source + symbol per hit
```

### L2 — ReAct Tool Injection

`tools.py` wraps `MemoryService` as LangChain `Tool` objects injected at agent
construction time via factory functions:

```python
# agents/analysts.py
def build_macro_analyst(memory: MemoryService) -> Runnable:
    tools = [make_memory_search_tool(memory), ...]
    return _get_llm().bind_tools(tools)
```

Tool output is formatted as structured text so models receive consistent shape:

```
Memory result 1
Source: research | Timestamp: 2026-03-06T14:23:11Z | Document: research_xxx
Relevance: 0.91
Content: ...
```

Default `k=5`, max content length per hit enforced, results deduplicated by
`document_id` before formatting.

### L3 — Post-Trade Write (dedicated node)

Three dedicated write nodes sit after their respective source-producing nodes in the
graph:

| Write Node | Trigger | Source |
|---|---|---|
| `write_external_memory` | after `data_fetcher` (post-normalize) | `external_data` |
| `write_research_memory` | after `debate_synthesizer` | `research` |
| `write_trade_memory` | after `order_router` (confirmed outcome only) | `trade` |

All write nodes follow the same pattern:

```python
def write_trade_memory(state: SwarmState, config: RunnableConfig) -> SwarmState:
    memory = get_memory_service(config)
    try:
        memory.store(content=..., source=MemorySource.TRADE, metadata={...})
    except Exception as e:
        logger.error("memory write failed", extra={"error": str(e), "node": "write_trade_memory"})
    return state  # write is a side effect; state is unchanged
```

Memory failure does not interrupt the trading flow.

---

## Audit Log

**Location:** `data/audit.jsonl` — append-only, never overwritten.

Written **inside `MemoryService`** for every store/search/delete — callers never call
`audit.py` directly.

**Success event:**

```json
{
  "timestamp": "2026-03-06T14:23:11Z",
  "event": "store",
  "status": "success",
  "document_id": "trade_a3f9c2b1d4e8f01234567890",
  "source": "trade",
  "node": "write_trade_memory",
  "chunk_count": 2,
  "content_hash": "abc123...",
  "ingested_at": "2026-03-06T14:23:11Z"
}
```

**Error event:**

```json
{
  "timestamp": "2026-03-06T14:23:11Z",
  "event": "store",
  "status": "error",
  "source": "trade",
  "node": "write_trade_memory",
  "error_type": "ChromaWriteError",
  "error_message": "..."
}
```

**Search event** includes `query`, `source_filter`, `k`, `hits_returned`, and top hit
`document_id` values — no raw content.

---

## Ingestion Pipeline

### Hot Path (synchronous, best-effort)

Writes run synchronously inside write nodes. Exceptions are caught at the node
boundary, logged structurally, and the run continues.

### Scheduled Maintenance (weekly, Monday 9AM)

`indexer.py` is added to the existing `run_obsidian_tracking_update.sh` wrapper and
runs via the existing systemd timer.

**Deduplication:** scan for duplicate `content_hash` values → keep earliest by
`ingested_at`, delete the rest.

**Orphan detection:** for each `document_id`, verify chunk indexes form a complete set
`0..chunk_count-1` with no gaps, duplicates, or conflicting `chunk_count` values →
delete orphaned chunks.

**Output:** summary written to audit log as `event: "deduplicate"`.

---

## Testing Plan

Two new test files targeting ~30 tests total.

### `tests/test_memory.py`

| Test | Area |
|---|---|
| `test_store_creates_chunks_with_stable_ids` | MemoryService core |
| `test_store_upsert_replaces_stale_tail_chunks` | MemoryService core |
| `test_store_writes_audit_event_on_success` | MemoryService core |
| `test_store_writes_audit_error_event_on_failure` | MemoryService core |
| `test_store_failure_does_not_raise` | MemoryService core |
| `test_search_returns_memory_hits_not_raw_chroma` | MemoryService core |
| `test_search_score_higher_is_better` | MemoryService core |
| `test_search_source_filter_applied` | MemoryService core |
| `test_get_reassembles_chunks_in_order` | MemoryService core |
| `test_delete_removes_all_chunks` | MemoryService core |
| `test_chunking_short_document_single_chunk` | Chunking |
| `test_chunking_long_document_overlap_respected` | Chunking |
| `test_chunking_paragraph_fallback_sentence_split` | Chunking |
| `test_chunking_sentence_fallback_token_split` | Chunking |
| `test_trade_document_id_deterministic` | ID generation |
| `test_research_document_id_deterministic` | ID generation |
| `test_external_document_id_deterministic` | ID generation |
| `test_audit_event_shape_success` | Audit log |
| `test_audit_event_shape_error` | Audit log |
| `test_audit_append_only` | Audit log |
| `test_deduplicate_keeps_earliest_by_ingested_at` | Indexer |
| `test_orphan_detection_missing_chunk_index` | Indexer |
| `test_deduplicate_noop_on_clean_store` | Indexer |
| `test_memory_search_tool_formats_structured_output` | Tools |
| `test_memory_search_tool_handles_empty_results` | Tools |
| `test_search_recency_filter_applied` | L1 recency |

### `tests/test_memory_nodes.py`

| Test | Area |
|---|---|
| `test_write_trade_memory_calls_store_with_correct_source` | Write nodes |
| `test_write_research_memory_calls_store_with_correct_source` | Write nodes |
| `test_write_external_memory_calls_store_with_correct_source` | Write nodes |
| `test_write_node_does_not_raise_on_store_failure` | Write nodes |

### Integration Tests (fake ChromaDB backend)

`MemoryService.__init__` accepts an injected `collection` parameter for testing without
a real ChromaDB instance. Two integration tests exercise the full pipeline end-to-end:

- `test_integration_store_and_retrieve_trade`
- `test_integration_deduplication_removes_duplicate`

---

## Deliverables

- `src/memory/service.py` — `MemoryService`, `MemoryHit`, `StoredDocument`, `MemorySource`
- `src/memory/tools.py` — `make_memory_search_tool()`, agent factory helpers
- `src/memory/indexer.py` — `deduplicate()`, orphan cleanup, indexer entry point
- `src/memory/audit.py` — append-only JSONL writer (internal to service)
- `src/memory/config.py` — chunking constants and configurable defaults
- `src/graph/nodes/write_external_memory.py`
- `src/graph/nodes/write_research_memory.py`
- `src/graph/nodes/write_trade_memory.py`
- Updated `src/graph/orchestrator.py` — new write nodes wired into graph
- Updated `main.py` — `MemoryService` constructed and injected via config
- Updated `scripts/run_obsidian_tracking_update.sh` — indexer added to weekly job
- `data/chroma_db/` — ChromaDB persistence directory (gitignored)
- `data/audit.jsonl` — audit log (gitignored)
- `tests/test_memory.py` — ~26 tests
- `tests/test_memory_nodes.py` — ~4 tests
