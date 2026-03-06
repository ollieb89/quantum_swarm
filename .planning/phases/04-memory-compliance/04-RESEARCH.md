# Phase 4: Memory & Institutional Compliance — Research

**Researched:** 2026-03-06
**Domain:** Institutional Memory, Audit Logging, Decision Provenance, Compliance Guardrails
**Status:** IN PROGRESS (Awaiting schemas and detailed implementation specs)

---

## 1. Architectural Vision

The goal is to transition from a research prototype to a **mini institutional trading platform**.
Core philosophy: **Provenances, Persistence, and Gating**.

### The "Four Subsystems" Model

1.  **Persistent Memory Layer**: Three-tier state storage.
    *   *Operational State*: Postgres + Redis for resuming runs (LangGraph checkpoints).
    *   *Research Memory*: Vector store (pgvector/Qdrant) for cross-session learning.
    *   *Trade History*: Warehouse (DuckDB/Parquet) for strategy evaluation.
2.  **Immutable Audit Logging**: "Why was this trade placed?"
    *   Chain of custody for every decision.
    *   Append-only logs with hash chains for tamper-proofing.
3.  **Institutional Guardrails**: Pre-execution enforcement.
    *   Risk Limits (drawdown, leverage, position size).
    *   Compliance Rules (restricted lists, wash trading).
    *   Operational Controls (health checks).
4.  **Decision Provenance System**: The critical institutional feature.
    *   Graph linking: Trade → Risk Approval → Signal → Research Evidence.
    *   Enables full replay and regulatory audits.

---

## 2. Infrastructure Stack Candidates

*   **Database**: PostgreSQL (State), pgvector (Memory), DuckDB (Analytics/Warehouse), Redis (Cache).
*   **Logging**: structlog (Structured), OpenTelemetry (Tracing), Parquet (Archive).
*   **Storage**: Local Filesystem (Initial), S3/MinIO (Production).
*   **Bus**: Kafka/Redpanda (Optional/Future).

---

## 3. Implementation Waves (Proposed)

*   **Wave 1: Persistent Run Storage** — Postgres schema + LangGraph checkpoint adapter.
*   **Wave 2: Audit Log Pipeline** — Structured logs + append-only tables + hash chaining.
*   **Wave 3: Trade Warehouse** — Order/Fill/Portfolio schemas in DuckDB/Postgres.
*   **Wave 4: Vector Research Memory** — pgvector integration for researcher agents.
*   **Wave 5: Compliance Guardrail Engine** — Pre-execution policy enforcement hooks.

---

## 4. Pending Resources (Requested)

To finalize this research and move to planning, we are waiting for:
1.  **Hedge Fund Database Schemas**: Exact tables for trade audit trails.
2.  **Tamper-Proof Audit Chain**: Implementation logic for the hash chain.
3.  **Production-Grade Folder Architecture**: Recommended Phase 4 directory structure.
