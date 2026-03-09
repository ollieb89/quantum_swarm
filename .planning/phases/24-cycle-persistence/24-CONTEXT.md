# Phase 24: Cycle Persistence - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Every pipeline run produces a complete, queryable cycle snapshot stored outside SwarmState. CycleSnapshot Pydantic model defines the canonical schema. PostgreSQL cycle_snapshots table indexes cycles with monotonic numbering. Cycle data is self-contained so LangGraph checkpoints don't bloat across runs. The end-to-end pipeline runner (Phase 25) and replay CLI (Phase 26) are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Snapshot schema & contents
- Agent memos captured verbatim from SwarmState fields: macro_report, quant_proposal, bullish_thesis, bearish_thesis (dict-typed, no transformation)
- Full debate_history list (all rounds with provenance) plus debate_resolution dict — enables step-through replay
- Merit scores and soul_sync_context both included in snapshot — essential for replay CLI merit visualization (REPL-04) and drift flag display (REPL-05)
- Weighted consensus score included

### Decision card handling
- Claude's Discretion: whether to inline the full DecisionCard dict or reference by card_id — choose based on implementation trade-offs

### Storage strategy
- Hybrid: PostgreSQL cycle_snapshots table for metadata + filesystem for full snapshot
- Cycle numbering: monotonic integer (PostgreSQL SERIAL), zero-padded for filesystem (data/cycles/0042/)
- Single file per cycle: data/cycles/{zero_padded_id}/snapshot.json containing the full CycleSnapshot
- PostgreSQL table stores queryable metadata (cycle_id, symbol, timestamp, status, consensus_score, task_id) — exact column set is Claude's discretion based on what replay CLI needs

### CycleRunner wrapper
- External wrapper pattern: CycleRunner sits outside the graph, calls graph.ainvoke(), then extracts SwarmState fields to build CycleSnapshot
- No changes to existing graph nodes — persistence is a post-graph concern
- CycleRunner resets SwarmState between runs to prevent messages list and debate_history from growing across cycles (addresses PIPE-03 at the boundary)
- Module: src/core/cycle_runner.py (infrastructure, not graph logic)
- CycleSnapshot Pydantic model: src/core/cycle_snapshot.py (separate module, mirrors DecisionCard pattern)

### Failure & partial cycles
- Failed runs persist with status='failed' — save whatever state exists at failure time for debugging
- Risk-rejected cycles persist with status='rejected' — full cognitive trace (memos, debate, consensus) but no execution_result or decision card
- Status taxonomy: 'completed' | 'rejected' | 'failed'
- Optional fields strategy: agent memos and debate are required (always run); post-risk-gate fields (execution_result, decision card) are Optional. CYCL-02 constraint ("no Optional fields left as None") applies only to status='completed' cycles
- Structured error_context field (Optional dict) on failed cycles: error_type, message, failed_node, traceback_summary

### Claude's Discretion
- Exact PostgreSQL table column set beyond the core fields
- Whether decision card is inlined or referenced
- CycleSnapshot field naming and nesting structure
- How zero-padding width is determined
- Filesystem directory creation strategy (eager vs lazy)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/core/decision_card.py`: DecisionCard Pydantic model — structural template for CycleSnapshot (nested models, SHA-256 integrity hash pattern)
- `src/core/persistence.py`: setup_persistence() with idempotent CREATE TABLE pattern — add cycle_snapshots table here
- `src/core/db.py`: DB_URL, get_pool(), get_db_connection() — connection infrastructure ready to use
- `src/graph/state.py`: SwarmState TypedDict with all agent output fields — CycleRunner extracts from this

### Established Patterns
- Pydantic models for validated artifacts (DecisionCard, AgentContributions, RiskSnapshot)
- PostgreSQL tables created idempotently in setup_persistence() with CREATE TABLE IF NOT EXISTS
- AUDIT_EXCLUDED_FIELDS pattern for separating persona data from audit data
- Lazy LLM init pattern (getter functions for module-level instances)
- Core modules are leaf imports — no upward imports from core to graph (enforced by test_import_boundaries.py)

### Integration Points
- `setup_persistence()` in src/core/persistence.py — add cycle_snapshots CREATE TABLE
- `src/graph/orchestrator.py` — CycleRunner wraps create_orchestrator_graph() output
- SwarmState fields — CycleRunner reads macro_report, quant_proposal, bullish_thesis, bearish_thesis, debate_history, debate_resolution, merit_scores, soul_sync_context, weighted_consensus_score, execution_result, decision_card_audit_ref, risk_approved, risk_notes, compliance_flags
- `data/cycles/` — new filesystem location for snapshot JSON files
- `tests/core/test_import_boundaries.py` — add cycle_snapshot.py and cycle_runner.py to core leaf import tests

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 24-cycle-persistence*
*Context gathered: 2026-03-09*
