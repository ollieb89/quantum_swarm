# Phase 4 Context & Constraints

## Strategic Goals
- Transform the "swarm" into an **auditable institutional platform**.
- Enable **cross-session learning** (agents remember mistakes/successes indefinitely).
- Enforce **strict compliance** (no execution without provenance).

## Technical Constraints
- **State**: Must move off ephemeral in-memory checkpoints to durable Postgres.
- **Performance**: Audit logging must not block execution (async).
- **Immutability**: Logs must be tamper-evident (hash chains).
- **Stack**: Python 3.12+, PostgreSQL, DuckDB, LangGraph.

## Key Decisions
- **Decision Provenance**: Every `ExecutionResult` must link back to a `GraphDecision` and specific `ResearchNotes`.
- **Regime Tagging**: Auto-tagging of market regimes (volatility, trend) to improve agent memory retrieval.
