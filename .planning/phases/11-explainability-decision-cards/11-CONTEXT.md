# Phase 11: Explainability & Decision Cards - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate an immutable JSON "decision card" for every successfully executed trade, capturing the full cognitive trace: which agents contributed, which memory rules were consulted, and what risk scores drove the decision. Cards are appended to `data/audit.jsonl` and are self-verifying via a content hash. Displaying or querying cards through a UI/API is out of scope.

</domain>

<decisions>
## Implementation Decisions

### Card Storage & Location
- Single source of truth: `data/audit.jsonl` (append-only, same store used by Phase 10 rule validation events)
- No dual-write — cards are not duplicated into PostgreSQL or a trades table column
- Event type: `"decision_card_created"` (consistent with audit.jsonl event taxonomy)
- Queryability is nice-to-have only; no indexing or query infrastructure required in this phase
- Card is a Pydantic-validated `DecisionCard` model, serialized to JSON before append

### Cognitive Trace Scope
- **Agent outputs (all required):** macro_report, quant_proposal, bullish_thesis, bearish_thesis, debate_resolution — all SwarmState agent fields included in the card
- **Memory rules:** active rule IDs only (e.g. `["mem_0001", "mem_0003"]`) — full rule content is not embedded; cross-reference via `data/memory_registry.json`
- **Risk & compliance fields (all required):**
  - `consensus_score` (weighted, 0.0–1.0)
  - `risk_approval` full dict from RiskManager (includes reasoning, flags, stop-loss level)
  - `compliance_flags` list
  - `portfolio_risk_score` from Phase 8 InstitutionalGuard (if present in state; `null` if absent)
- **Execution snapshot:** `execution_result` dict (order_id, execution_price, success, message, metadata)
- **Text depth:** Claude's discretion — implementation decides field-by-field whether to include full agent text or structured summaries; goal is compact but traceable

### Generation Trigger & Node
- New dedicated LangGraph node: `decision_card_writer`
- Placed immediately after executor fan-in (after OrderRouter populates `execution_result`)
- **Generate only for successfully executed trades:** `execution_result.success == True`; skip node if trade failed
- New module: `src/core/decision_card.py`
  - `DecisionCard` Pydantic model with nested models for agent contributions, rule IDs, risk snapshot, execution snapshot, and integrity fields
  - `build_decision_card(state: SwarmState) -> DecisionCard` builder function
  - `canonical_json(payload: dict) -> str` serialization helper
  - `verify_decision_card(card_dict: dict) -> bool` integrity verifier
- `audit_logger.py` handles persistence via a generic append call — `decision_card.py` does not own I/O
- **State fields added to SwarmState:**
  - `decision_card_status: Literal["pending", "written", "failed"]`
  - `decision_card_error: Optional[str]`
  - `decision_card_audit_ref: Optional[str]` (card_id stored back into state on success)

### Failure Handling
- Retry once on transient write failure (`audit.jsonl` append error)
- If retry also fails:
  - Emit high-severity compliance incident to logs
  - Set `decision_card_status = "failed"` in state
  - Do **not** roll back or invalidate the executed trade
- Trade execution outcome and card generation outcome are explicitly separate statuses
- Missing card after retry = post-trade compliance incident, not a trade failure

### Card Identity & Immutability
- `card_id`: UUID4 — stable, collision-resistant, independent of content or timing
- `task_id`: retained as first-class field for traceability back to SwarmState
- **Self-hash:** SHA-256 of the canonical JSON payload (excluding `content_hash` itself); stored as `content_hash` field inside the card
- **Cross-store linkage:** `prev_audit_hash` field contains the `entry_hash` of the most recent PostgreSQL `audit_logs` row at write time — bridges file-based card to DB-backed chain
  - `prev_audit_hash` is included in the bytes being hashed (altering it breaks the card hash)
  - If no prior DB entry exists: `prev_audit_hash = null` (explicit, tested edge case)
- Hashing flow:
  1. Populate all card fields including `prev_audit_hash`
  2. Serialize to canonical JSON excluding `content_hash`
  3. Compute SHA-256 → store as `content_hash`
- `verify_decision_card(card_dict: dict) -> bool` ships in Phase 11: recomputes hash, returns True/False — never mutates the card
- Optional `explain_verification(card_dict)` helper: hash validity + `has_prev_audit_hash` + `schema_version`

### Card Schema (key fields)
```
card_id: str                    # UUID4
schema_version: str             # "1.0"
event_type: str                 # "decision_card_created"
task_id: str
generated_at: datetime
execution_result: dict
agent_contributions:
  macro_report: dict | None
  quant_proposal: dict | None
  bullish_thesis: dict | None
  bearish_thesis: dict | None
  debate_resolution: dict | None
applied_rule_ids: list[str]     # active MemoryRule IDs at execution time
risk_snapshot:
  consensus_score: float
  risk_approval: dict
  compliance_flags: list[str]
  portfolio_risk_score: float | None
prev_audit_hash: str | None     # last PostgreSQL audit_logs.entry_hash
hash_algorithm: str             # "sha256"
content_hash: str               # SHA-256 of canonical payload excluding this field
```

### Testing
- Unit tests (`tests/test_decision_card.py`): builder with synthetic SwarmState, all required fields present, rule ID extraction, risk field mapping, deterministic canonical JSON, graceful handling of missing optional fields
- Integration tests: `decision_card_writer` node against a temp `audit.jsonl`; verify append, readability, hash validity, retry-once behavior, and failure path setting `decision_card_status="failed"`
- Emphasis on unit tests; 1–3 focused integration tests for the write path

### Claude's Discretion
- Exact text depth per agent field (full text vs. summarized vs. structured metadata)
- Nested Pydantic model breakdown within DecisionCard
- Canonical JSON implementation details (sort_keys=True, ensure_ascii=False sufficient)
- Whether `explain_verification` is included alongside `verify_decision_card`

</decisions>

<specifics>
## Specific Ideas

- Card must be self-verifying: anyone can recompute the hash from the JSON payload alone without external state
- "Execution outcome and decision-card outcome are separate statuses" — never retroactively invalidate a filled order because post-trade audit writing failed
- "Trade succeeded, explainability artifact failed" is the explicit error framing for compliance reporting
- `prev_audit_hash` is included in the hashed payload — altering the DB-link reference breaks the card hash
- `null` `prev_audit_hash` must be an explicit, tested case (not a silent omission)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/core/audit_logger.py` — existing async logger for PostgreSQL `audit_logs`; extend or complement with a jsonl append method for `data/audit.jsonl`
- `src/models/audit.py` — `AuditLogEntry` with `entry_hash` field; fetch last entry hash from this table to populate `prev_audit_hash` in the card
- `data/audit.jsonl` — append-only event log established in Phase 10; same file, new event type `"decision_card_created"`
- `src/graph/state.py` — `SwarmState` TypedDict; add `decision_card_status`, `decision_card_error`, `decision_card_audit_ref` optional fields
- `src/core/memory_registry.py` — `MemoryRegistry.get_active_rules()` returns list of `MemoryRule` objects; extract `.id` fields for `applied_rule_ids`
- `src/agents/rule_validator.py` — pattern for a standalone core service (no LLM, pure Python); follow same structure for `decision_card.py`

### Established Patterns
- Pydantic model + JSON serialization: `AuditLogEntry`, `MemoryRule` — same pattern for `DecisionCard`
- Lazy init not needed — `decision_card.py` is a pure Python service, no LLM calls
- Instance attribute redirection for test isolation (RuleValidator, RuleGenerator pattern): apply same approach to builder dependencies in `decision_card.py`
- `audit.jsonl` append: Phase 10 already writes JSON lines here; reuse same append mechanics

### Integration Points
- `src/graph/orchestrator.py` — add `decision_card_writer` node; wire after executor fan-in with a conditional edge (success path only)
- `src/graph/state.py` — add three new optional fields: `decision_card_status`, `decision_card_error`, `decision_card_audit_ref`
- `src/core/audit_logger.py` — extend with jsonl append if not already present from Phase 10
- `data/audit.jsonl` — new event type `"decision_card_created"` appended here

</code_context>

<deferred>
## Deferred Ideas

- Displaying or querying decision cards through a UI or API endpoint — future phase
- Batch verification utility for all cards in audit.jsonl — post Phase 11
- Forensic replay tools building on verify_decision_card — post Phase 11
- Decision-card-failure audit events for attempted-but-failed (non-success) trades — deferred; do not scope into Phase 11
- Cross-store audit chain validation sweep (PostgreSQL + audit.jsonl integrity check) — future phase

</deferred>

---

*Phase: 11-explainability-decision-cards*
*Context gathered: 2026-03-08*
