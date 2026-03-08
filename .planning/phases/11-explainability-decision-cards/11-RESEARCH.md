# Phase 11: Explainability & Decision Cards - Research

**Researched:** 2026-03-08
**Domain:** Immutable audit artifact generation, Pydantic data modelling, SHA-256 self-hashing, LangGraph node wiring
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Card Storage & Location**
- Single source of truth: `data/audit.jsonl` (append-only, same store used by Phase 10 rule validation events)
- No dual-write — cards are not duplicated into PostgreSQL or a trades table column
- Event type: `"decision_card_created"` (consistent with audit.jsonl event taxonomy)
- Queryability is nice-to-have only; no indexing or query infrastructure required in this phase
- Card is a Pydantic-validated `DecisionCard` model, serialized to JSON before append

**Cognitive Trace Scope**
- Agent outputs (all required): macro_report, quant_proposal, bullish_thesis, bearish_thesis, debate_resolution — all SwarmState agent fields included in the card
- Memory rules: active rule IDs only (e.g. `["mem_0001", "mem_0003"]`) — full rule content is not embedded; cross-reference via `data/memory_registry.json`
- Risk & compliance fields (all required): `consensus_score`, `risk_approval` full dict, `compliance_flags` list, `portfolio_risk_score` from Phase 8 InstitutionalGuard (if present; `null` if absent)
- Execution snapshot: `execution_result` dict (order_id, execution_price, success, message, metadata)
- Text depth: Claude's discretion — field-by-field whether to include full agent text or structured summaries; goal is compact but traceable

**Generation Trigger & Node**
- New dedicated LangGraph node: `decision_card_writer`
- Placed immediately after executor fan-in (after OrderRouter populates `execution_result`)
- Generate only for successfully executed trades: `execution_result.success == True`; skip node if trade failed
- New module: `src/core/decision_card.py`
  - `DecisionCard` Pydantic model with nested models
  - `build_decision_card(state: SwarmState) -> DecisionCard` builder function
  - `canonical_json(payload: dict) -> str` serialization helper
  - `verify_decision_card(card_dict: dict) -> bool` integrity verifier
- `audit_logger.py` handles persistence via a generic append call — `decision_card.py` does not own I/O
- State fields added to SwarmState: `decision_card_status`, `decision_card_error`, `decision_card_audit_ref`

**Failure Handling**
- Retry once on transient write failure
- If retry also fails: emit high-severity compliance incident to logs, set `decision_card_status = "failed"`, do NOT roll back or invalidate the executed trade
- Trade execution outcome and card generation outcome are explicitly separate statuses

**Card Identity & Immutability**
- `card_id`: UUID4
- `task_id`: retained as first-class field
- Self-hash: SHA-256 of the canonical JSON payload (excluding `content_hash` itself)
- `prev_audit_hash`: contains `entry_hash` of most recent PostgreSQL `audit_logs` row at write time; `null` if no prior entry
- `prev_audit_hash` is included in the bytes being hashed (altering it breaks the card hash)
- `verify_decision_card(card_dict: dict) -> bool` ships in Phase 11 — recomputes hash, returns True/False, never mutates the card
- Optional `explain_verification(card_dict)` helper: hash validity + `has_prev_audit_hash` + `schema_version`

**Testing**
- Unit tests: `tests/test_decision_card.py` — builder with synthetic SwarmState, all required fields, rule ID extraction, risk field mapping, deterministic canonical JSON, graceful handling of missing optional fields
- Integration tests: `decision_card_writer` node against a temp `audit.jsonl`; verify append, readability, hash validity, retry-once behavior, failure path setting `decision_card_status="failed"`
- Emphasis on unit tests; 1–3 focused integration tests for the write path

### Claude's Discretion
- Exact text depth per agent field (full text vs. summarized vs. structured metadata)
- Nested Pydantic model breakdown within DecisionCard
- Canonical JSON implementation details (sort_keys=True, ensure_ascii=False sufficient)
- Whether `explain_verification` is included alongside `verify_decision_card`

### Deferred Ideas (OUT OF SCOPE)
- Displaying or querying decision cards through a UI or API endpoint — future phase
- Batch verification utility for all cards in audit.jsonl — post Phase 11
- Forensic replay tools building on verify_decision_card — post Phase 11
- Decision-card-failure audit events for attempted-but-failed (non-success) trades — deferred
- Cross-store audit chain validation sweep (PostgreSQL + audit.jsonl integrity check) — future phase
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXEC-04 | Every execution result is accompanied by a JSON decision card in the audit log identifying which memory rules and risk scores influenced the trade | Fully addressed: `build_decision_card()` builder extracts agent outputs + rule IDs + risk snapshot from SwarmState; `canonical_json()` + SHA-256 provide the immutable artifact; `decision_card_writer` node wired after `order_router` appends to `data/audit.jsonl` |
</phase_requirements>

---

## Summary

Phase 11 is a pure Python, no-LLM service that slots into the existing LangGraph orchestration as a post-execution audit artifact writer. It creates a self-verifying JSON record of every successful trade's cognitive trace — which agents contributed, which memory rules were active, and what risk scores drove the decision.

The technical scope is narrow and well-bounded: one new module (`src/core/decision_card.py`), one new LangGraph node (`decision_card_writer`), three new SwarmState fields, and one new audit.jsonl event type. All dependencies are already in the codebase. The hashing pattern (`json.dumps(sort_keys=True)` + `hashlib.sha256`) is identical to what `AuditLogger._calculate_hash()` already uses. The jsonl append pattern is identical to what `RuleValidator._write_audit()` already uses.

The one material discovery is that `portfolio_risk_score` (documented in CONTEXT.md as coming from Phase 8 InstitutionalGuard) is NOT a top-level SwarmState field. InstitutionalGuard writes it into `state["metadata"]["trade_risk_score"]`. The builder must read from `state.get("metadata", {}).get("trade_risk_score")` and map it to the card's `portfolio_risk_score` field, defaulting to `null`.

The cross-store linkage (`prev_audit_hash`) requires an async DB read from `audit_logs` at write time. Since `decision_card_writer` runs in the LangGraph async context, this is straightforward — follow the same `get_pool()` pattern used by `AuditLogger` and `InstitutionalGuard`.

**Primary recommendation:** Follow `RuleValidator` as the structural template for `decision_card.py` (pure Python service, instance-attribute redirect for test isolation, jsonl append owned by the service layer). Follow `AuditLogger._calculate_hash()` as the exact hash implementation to replicate.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | Already in project (v2) | `DecisionCard` model + field validation | Same pattern as `AuditLogEntry`, `MemoryRule` |
| hashlib (stdlib) | Python 3.12 | SHA-256 hashing | Already used in `AuditLogger._calculate_hash()` |
| json (stdlib) | Python 3.12 | Canonical JSON serialization | `sort_keys=True, ensure_ascii=False` |
| uuid (stdlib) | Python 3.12 | UUID4 card_id generation | Same as `task_id` generation in orchestrator |
| datetime (stdlib) | Python 3.12 | `generated_at` timestamp | `datetime.now(timezone.utc)` pattern already in use |
| pathlib (stdlib) | Python 3.12 | `audit.jsonl` path management | Same as `RuleValidator.audit_path` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| psycopg3 (asyncpg) | Already in project | Fetch `prev_audit_hash` from `audit_logs` | Used in `decision_card_writer` node to query last `entry_hash` |
| logging (stdlib) | Python 3.12 | High-severity compliance incident on failure | Standard project pattern |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `json.dumps(sort_keys=True)` | `orjson` for canonical serialization | `orjson` is faster but not in project; `json` stdlib is sufficient and avoids a new dep |
| UUID4 `card_id` | Content-addressed ID (hash of payload) | UUID4 is independent of content; avoids bootstrapping problem where id depends on hash |

**Installation:** No new dependencies required.

---

## Architecture Patterns

### Recommended Project Structure

```
src/core/
├── audit_logger.py      # existing — extend with jsonl append method
├── decision_card.py     # NEW — DecisionCard model + builder + serialization + verifier
├── memory_registry.py   # existing — get_active_rules() for applied_rule_ids
└── db.py                # existing — get_pool() for prev_audit_hash query

tests/
└── test_decision_card.py  # NEW — unit + integration tests
```

### Pattern 1: DecisionCard Pydantic Model with Nested Sub-models

**What:** Nested Pydantic models for each logical grouping (agent contributions, risk snapshot, execution snapshot). Top-level `DecisionCard` holds them plus identity/integrity fields.

**When to use:** Always — mirrors the `AuditLogEntry` / `MemoryRule` pattern already in `src/models/`.

**Example:**
```python
# Mirrors src/models/audit.py and src/models/memory.py patterns
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
import uuid

class AgentContributions(BaseModel):
    macro_report: Optional[dict] = None
    quant_proposal: Optional[dict] = None
    bullish_thesis: Optional[dict] = None
    bearish_thesis: Optional[dict] = None
    debate_resolution: Optional[dict] = None

class RiskSnapshot(BaseModel):
    consensus_score: float
    risk_approval: dict
    compliance_flags: list[str]
    portfolio_risk_score: Optional[float] = None

class DecisionCard(BaseModel):
    card_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: str = "1.0"
    event_type: str = "decision_card_created"
    task_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    execution_result: dict
    agent_contributions: AgentContributions
    applied_rule_ids: list[str]
    risk_snapshot: RiskSnapshot
    prev_audit_hash: Optional[str] = None
    hash_algorithm: str = "sha256"
    content_hash: str = ""  # populated after canonical_json()

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
```

### Pattern 2: Canonical JSON + SHA-256 (mirrors AuditLogger exactly)

**What:** Serialize the card dict (excluding `content_hash`) with `json.dumps(sort_keys=True, ensure_ascii=False, default=str)`, then SHA-256 the UTF-8 bytes.

**When to use:** Always — deterministic output is required for `verify_decision_card()` to be callable from any environment.

**Example:**
```python
import json, hashlib

def canonical_json(payload: dict) -> str:
    """Deterministic JSON serialization. sort_keys=True is sufficient."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)

def _compute_hash(card_dict: dict) -> str:
    """SHA-256 of canonical JSON, excluding the content_hash field itself."""
    payload = {k: v for k, v in card_dict.items() if k != "content_hash"}
    raw = canonical_json(payload)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def verify_decision_card(card_dict: dict) -> bool:
    """Recompute hash, compare to stored content_hash. Never mutates card."""
    expected = _compute_hash(card_dict)
    return card_dict.get("content_hash") == expected
```

### Pattern 3: jsonl Append (mirrors RuleValidator._write_audit exactly)

**What:** Open file in append mode, write one JSON line, flush. The `audit_logger.py` owns the append call; `decision_card.py` passes the serialized string.

**When to use:** When persisting to `data/audit.jsonl`.

**Example:**
```python
# In AuditLogger (extend with new method) or inline in the node:
def append_jsonl(self, audit_path: Path, line: str) -> None:
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_path, "a") as f:
        f.write(line + "\n")
```

### Pattern 4: Instance-Attribute Redirect for Test Isolation (mirrors RuleValidator)

**What:** Store mutable paths and registry handles as instance attributes (`self.audit_path`, `self.registry`) so tests can redirect them to temp files without patching internals.

**When to use:** Always for `decision_card_writer` node dependencies.

### Pattern 5: Conditional LangGraph Edge (success path only)

**What:** A routing function checks `state["execution_result"].get("success") == True` and routes to `decision_card_writer` only on success, otherwise falls through to `trade_logger` / `synthesize`.

**Current orchestrator flow (from code inspection):**
```
order_router → trade_logger → write_trade_memory → synthesize → END
```

**Phase 11 insertion point** — `decision_card_writer` must be wired immediately after `order_router` populates `execution_result` but before `trade_logger` writes to PostgreSQL (or after — either is valid since the two are independent). The CONTEXT.md says "after executor fan-in (after OrderRouter populates `execution_result`)". The simplest safe insertion is between `order_router` and `trade_logger`:

```
order_router → decision_card_writer (conditional: success only) → trade_logger → ...
```

Or as a parallel branch that joins before `synthesize`. The conditional edge approach is cleaner:

```python
def route_after_order_router(state: SwarmState) -> str:
    result = state.get("execution_result") or {}
    if result.get("success") is True:
        return "decision_card_writer"
    return "trade_logger"  # skip card generation for failed trades
```

### Anti-Patterns to Avoid

- **Owning I/O in decision_card.py:** The module must expose builder + serializer + verifier only. Append to `audit.jsonl` via `audit_logger.py` or the node function, not inside `build_decision_card()`.
- **Embedding full rule content in the card:** Only active rule IDs go in `applied_rule_ids`. Full rule content lives in `data/memory_registry.json`.
- **Blocking the event loop in the node:** `decision_card_writer` is an async LangGraph node; any synchronous file I/O should be fine for jsonl (fast append), but the DB query for `prev_audit_hash` must use `await`.
- **Invalidating the trade on card failure:** `decision_card_status = "failed"` is logged; the fill stands. Do not raise an exception that propagates up through `order_router`'s result.
- **Using `content_hash` field in the hash computation:** Always exclude it from the payload before hashing — then store the result into `content_hash`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deterministic JSON | Custom serializer | `json.dumps(sort_keys=True, ensure_ascii=False, default=str)` | Already proven in `AuditLogger._calculate_hash()` |
| SHA-256 | Custom digest | `hashlib.sha256()` stdlib | Exact same implementation already in codebase |
| UUID generation | Timestamp-based IDs | `uuid.uuid4()` | Collision-resistant, no content dependency |
| Pydantic validation | Manual dict checks | `DecisionCard(**data)` + `.model_validate()` | Field presence and type guaranteed at construction |
| Atomic file writes | Direct open + write to final path | Use append (jsonl is append-only by design; atomicity not needed per line) | jsonl format tolerates partial trailing writes; recovery is read-until-valid-json |

**Key insight:** Every primitive needed for Phase 11 is already present in the codebase. The only new work is composition.

---

## Common Pitfalls

### Pitfall 1: `portfolio_risk_score` Is Not a Top-Level SwarmState Field

**What goes wrong:** Builder reads `state.get("portfolio_risk_score")` and always gets `None` even when InstitutionalGuard ran successfully.

**Why it happens:** Phase 8's `institutional_guard_node` writes `risk_score` into `state["metadata"]["trade_risk_score"]`, not as a dedicated SwarmState field. The CONTEXT.md refers to it as `portfolio_risk_score` (the card field name), but the state path is different.

**How to avoid:** In the builder, read:
```python
portfolio_risk_score = state.get("metadata", {}).get("trade_risk_score")
```
Map this to the card's `risk_snapshot.portfolio_risk_score`. Explicit `null` when absent.

**Warning signs:** `portfolio_risk_score` is always `null` in generated cards even on approved trades.

### Pitfall 2: `prev_audit_hash` Null Case Must Be an Explicit Tested Path

**What goes wrong:** Builder omits `prev_audit_hash` from the card dict silently when no PostgreSQL audit entry exists, causing hash verification to fail (hash was computed with `null` but dict has no key).

**Why it happens:** Python `None` and missing key are different in JSON — `{"prev_audit_hash": null}` vs `{}`.

**How to avoid:** Always include `prev_audit_hash` as a field in the card payload, even when its value is `None` (serializes to JSON `null`). Write a test that constructs a card with `prev_audit_hash=None` and asserts `verify_decision_card()` returns `True`.

**Warning signs:** `verify_decision_card()` returns `False` for cards written when no prior DB entry existed.

### Pitfall 3: Datetime Serialization Breaking Determinism

**What goes wrong:** `generated_at` serializes differently between the write path and the verify path (e.g., with vs without microseconds, different timezone representations), causing hash mismatch.

**Why it happens:** Python's `datetime.isoformat()` and `json.dumps(default=str)` can produce different strings for the same datetime depending on microseconds.

**How to avoid:** Serialize `generated_at` to ISO string explicitly before hashing — convert once via `.isoformat()` and store the string, or use `default=str` consistently. The `canonical_json()` function must use `default=str` so datetime objects in nested dicts (agent outputs) are handled uniformly. The `model_dump()` output should be passed through `model_dump(mode="json")` which serializes datetimes via the model's `json_encoders`.

**Warning signs:** `verify_decision_card()` intermittently fails on cards that were just written.

### Pitfall 4: Hash Computed Before `prev_audit_hash` Is Populated

**What goes wrong:** `content_hash` is computed, then `prev_audit_hash` is fetched from the DB and added to the card — but the hash no longer covers `prev_audit_hash`.

**Why it happens:** Wrong ordering in the builder function.

**How to avoid:** Strictly follow the hashing flow from CONTEXT.md:
1. Populate ALL card fields including `prev_audit_hash`
2. Serialize to canonical JSON excluding `content_hash`
3. Compute SHA-256 → store as `content_hash`

### Pitfall 5: Retry Logic Accidentally Creating Duplicate Cards

**What goes wrong:** Retry on transient jsonl append failure writes two cards to `audit.jsonl` with the same `card_id` but (if the first write partially succeeded) leaves a corrupted line.

**Why it happens:** File append is not atomic at the OS level for large writes, though single JSON lines are typically atomic on Linux for writes < PIPE_BUF (4096 bytes).

**How to avoid:** Retry only when the first attempt raises an exception (write failed entirely). If the first write succeeded without raising, do not retry. A caught exception after a partial write is safe to retry because jsonl readers skip invalid lines. The `card_id` is stable across retries (built once before the try/except).

### Pitfall 6: LangGraph Node Returning Wrong State Update Shape

**What goes wrong:** `decision_card_writer` node returns a full state dict instead of only the updated keys — overwriting other state fields.

**Why it happens:** LangGraph merges returned dicts into state; returning extra keys is fine, but returning the entire state snapshot causes `Annotated` reducer fields (`messages`, `trade_history`, `debate_history`) to double-append.

**How to avoid:** Return only the three new fields:
```python
return {
    "decision_card_status": "written",
    "decision_card_audit_ref": card.card_id,
    "decision_card_error": None,
}
```

---

## Code Examples

Verified patterns from existing codebase:

### Existing Hash Pattern (from src/core/audit_logger.py)

```python
# Source: src/core/audit_logger.py:59-75
def _calculate_hash(self, entry: Dict[str, Any], prev_hash: Optional[str]) -> str:
    data_string = json.dumps({...}, sort_keys=True)
    hasher = hashlib.sha256()
    hasher.update(data_string.encode('utf-8'))
    if prev_hash:
        hasher.update(prev_hash.encode('utf-8'))
    return hasher.hexdigest()
```

Phase 11 uses the same stdlib approach but self-contained in `canonical_json()` + `_compute_hash()`.

### Existing jsonl Append Pattern (from src/agents/rule_validator.py)

```python
# Source: src/agents/rule_validator.py:149-171
def _write_audit(self, ...) -> None:
    event = {...}
    self.audit_path.parent.mkdir(parents=True, exist_ok=True)
    with open(self.audit_path, "a") as f:
        f.write(json.dumps(event) + "\n")
```

`decision_card_writer` follows this exact pattern.

### Existing prev_audit_hash Query Pattern (from src/core/audit_logger.py)

```python
# Source: src/core/audit_logger.py:52-57
async def _get_last_hash(self, conn) -> Optional[str]:
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT entry_hash FROM audit_logs ORDER BY id DESC LIMIT 1"
        )
        row = await cur.fetchone()
        return row[0] if row else None
```

Use this exact query (or call `AuditLogger._get_last_hash()` directly if refactored) to populate `prev_audit_hash`.

### Existing Conditional Edge Pattern (from src/graph/orchestrator.py)

```python
# Source: src/graph/orchestrator.py:52-73
def route_after_debate(state: SwarmState) -> str:
    score = state.get("weighted_consensus_score")
    if score is not None and score > 0.6:
        return "risk_manager"
    return "hold"

workflow.add_conditional_edges(
    "write_research_memory",
    route_after_debate,
    {"risk_manager": "risk_manager", "hold": END},
)
```

Mirror for `decision_card_writer`:
```python
def route_after_order_router(state: SwarmState) -> str:
    result = state.get("execution_result") or {}
    return "decision_card_writer" if result.get("success") is True else "trade_logger"

workflow.add_conditional_edges(
    "order_router",
    route_after_order_router,
    {"decision_card_writer": "decision_card_writer", "trade_logger": "trade_logger"},
)
workflow.add_edge("decision_card_writer", "trade_logger")
```

### Existing Test Isolation Pattern (from tests/test_rule_validator.py)

```python
# Source: tests/test_rule_validator.py — instance attribute redirect
validator = RuleValidator.__new__(RuleValidator)
validator.audit_path = Path(tmp_dir) / "audit.jsonl"
validator.registry = MemoryRegistry(tmp_registry_path)
```

`decision_card_writer` tests redirect `audit_path` the same way.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat audit string logs | Structured JSON lines in `audit.jsonl` | Phase 10 (2026-03-08) | Same file is now the established event log for compliance artifacts |
| Hash chain only in PostgreSQL | Self-verifying card hash in jsonl + cross-link to DB entry_hash | Phase 11 | Anyone can verify a card from the jsonl alone without DB access |

**Deprecated/outdated:**
- `AuditLogEntry.prev_hash` (PostgreSQL chain): Remains in DB for the DB-side chain. The decision card's `prev_audit_hash` is a one-way pointer FROM the card TO the DB chain (not a two-way link). Phase 11 does not extend the DB chain.

---

## Open Questions

1. **Should `decision_card_writer` be wrapped with `with_audit_logging()`?**
   - What we know: Every other node in the orchestrator is wrapped. The node writes to `audit.jsonl` itself.
   - What's unclear: Wrapping it would also write a PostgreSQL `audit_logs` entry, which is technically correct but adds one more DB write per trade and means the card's own node execution gets a DB audit entry.
   - Recommendation: Yes — wrap with `with_audit_logging()` for consistency. The node's PostgreSQL `audit_logs` entry will appear before the card is written (since the card is written during node execution). This means the `prev_audit_hash` fetched inside the node will be the entry for the previous node (`order_router`), not for `decision_card_writer` itself. This is correct behavior.

2. **Where exactly in the chain to insert `decision_card_writer`?**
   - What we know: Must be after `order_router` (which sets `execution_result`). CONTEXT.md says "immediately after executor fan-in."
   - What's unclear: Before or after `trade_logger` (which writes to PostgreSQL)?
   - Recommendation: After `order_router`, before `trade_logger`. The card captures the raw `execution_result` dict before the PostgreSQL write adds additional metadata. The `prev_audit_hash` query gets the `order_router` node's `audit_logs` entry.

3. **How to handle `prev_audit_hash` when PostgreSQL is unavailable (test/paper mode)?**
   - What we know: `get_pool()` raises if pool not initialized. Tests mock this with `AsyncMock`.
   - What's unclear: Whether paper-mode runs always have a DB pool.
   - Recommendation: Wrap the DB query in try/except; on exception log a warning and set `prev_audit_hash = None`. This is an explicit tested edge case per CONTEXT.md and maintains the stated rule that `null` prev_audit_hash is valid.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + unittest (both used in project) |
| Config file | None detected — run directly |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py -x -q` |
| Full suite command | `.venv/bin/python3.12 -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXEC-04 (builder) | `build_decision_card()` populates all required fields from SwarmState | unit | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py::TestDecisionCardBuilder -x` | Wave 0 |
| EXEC-04 (rule IDs) | `applied_rule_ids` contains active rule IDs from MemoryRegistry | unit | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py::TestDecisionCardBuilder::test_applied_rule_ids -x` | Wave 0 |
| EXEC-04 (hash) | `canonical_json()` is deterministic; `verify_decision_card()` returns True on freshly built card | unit | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py::TestHashing -x` | Wave 0 |
| EXEC-04 (null prev_hash) | Card with `prev_audit_hash=None` passes `verify_decision_card()` | unit | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py::TestHashing::test_verify_null_prev_hash -x` | Wave 0 |
| EXEC-04 (write path) | Card is appended to `audit.jsonl`; line is valid JSON with event_type `"decision_card_created"` | integration | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py::TestDecisionCardWriter -x` | Wave 0 |
| EXEC-04 (retry) | On first write failure, retries once; on second failure sets `decision_card_status="failed"` | integration | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py::TestDecisionCardWriter::test_retry_behavior -x` | Wave 0 |
| EXEC-04 (success-only) | Node is skipped when `execution_result.success != True` | unit | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py::TestDecisionCardWriter::test_skips_failed_trades -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/bin/python3.12 -m pytest tests/test_decision_card.py -x -q`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_decision_card.py` — covers all EXEC-04 behaviors above; does not exist yet (confirmed via Glob)
- [ ] No new framework install needed — pytest + unittest already in use

---

## Sources

### Primary (HIGH confidence)

- `src/core/audit_logger.py` — SHA-256 hashing implementation, `_get_last_hash()` DB query, `log_transition()` structure; inspected directly
- `src/core/memory_registry.py` — `get_active_rules()` API, returns `List[MemoryRule]` with `.id` attribute; inspected directly
- `src/graph/state.py` — Full SwarmState field inventory; `portfolio_risk_score` confirmed absent as top-level field; inspected directly
- `src/security/institutional_guard.py` — Confirmed `trade_risk_score` stored in `state["metadata"]["trade_risk_score"]`, not as a SwarmState field; inspected directly
- `src/graph/orchestrator.py` — Exact current graph wiring (order_router → trade_logger → write_trade_memory → synthesize); insertion point confirmed; inspected directly
- `src/agents/rule_validator.py` — jsonl append pattern, test isolation pattern; structural template for `decision_card.py`; inspected directly
- `src/models/audit.py` — `AuditLogEntry` Pydantic model pattern; inspected directly
- `src/models/memory.py` — `MemoryRule` + `MemoryRegistrySchema` Pydantic model pattern; inspected directly
- `data/audit.jsonl` — Confirmed existing event taxonomy; confirmed `"event"` key naming; inspected directly

### Secondary (MEDIUM confidence)

- Phase 10 STATE.md accumulated context — confirmed `asyncio.run()` requirement for Python 3.12; confirmed `.venv/bin/python3.12 -m pytest` invocation pattern
- CONTEXT.md card schema — authoritative spec for all field names and types (produced by `/gsd:discuss-phase`)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already present; no new deps
- Architecture: HIGH — insertion point confirmed from live orchestrator code; all patterns verified from existing codebase
- Pitfalls: HIGH — `portfolio_risk_score` location confirmed from source; datetime serialization issue is a known Python gotcha verified against the existing hash implementation
- Test map: HIGH — test file confirmed absent; framework confirmed present

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable Python stdlib + project-internal patterns; no external library version risk)
