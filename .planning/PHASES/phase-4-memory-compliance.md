# Implementation Plan: Phase 4 - Memory & Institutional Compliance

**Project:** Quantum Swarm LangGraph Migration
**Phase:** 4 (Memory & Institutional Compliance)
**Date:** 2026-03-06
**Status:** Ready for Execution

---

## ## Approach
- **Why this solution:** Transitioning from ephemeral memory to a persistent PostgreSQL backend ensures cross-session continuity and institutional-grade reliability. Implementing a hash-chained audit log provides non-repudiable decision provenance ("Why was this trade placed?"), which is a requirement for institutional compliance. The institutional guardrails add a final layer of safety by enforcing global risk limits (leverage, drawdown) before any order reaches the execution layer.
- **Alternatives considered:**
    - *File-based persistence (JSON/SQLite):* Rejected for production concurrency and lack of robust migration/query support compared to PostgreSQL.
    - *NoSQL Audit Logs (Elasticsearch):* Useful for search, but PostgreSQL's ACID compliance is preferred for the primary source of truth in trade auditing.

---

## ## Steps

### 1. Persistent Infrastructure & Checkpointing (180 min)
- [ ] **Dependencies:** Install `psycopg`, `langgraph-checkpoint-postgres`.
- [ ] **Database Setup:** 
    - [ ] Create `docker-compose.yml` for local PostgreSQL.
    - [ ] Define `src/core/db.py` for connection pooling.
- [ ] **LangGraph Integration:**
    - [ ] Replace `MemorySaver` with `PostgresSaver` in `src/graph/orchestrator.py`.
    - [ ] Implement a migration script to initialize LangGraph checkpoint tables.

### 2. Decision Provenance & Audit Logging (240 min)
- [ ] **Files to create:** `src/core/audit_logger.py`, `src/models/audit.py`
- [ ] **Implementation:**
    - [ ] Define `AuditLog` schema (timestamp, node_id, input, output, hash, prev_hash).
    - [ ] Create an async `AuditLogger` that writes to a dedicated `audit_logs` table.
    - [ ] Implement hash chaining: Each log entry includes a SHA-256 hash of (current_data + previous_entry_hash).
- [ ] **Orchestrator Wiring:**
    - [ ] Add a decorator or middleware to LangGraph nodes to automatically log every transition with provenance.

### 3. Institutional Guardrails (120 min)
- [ ] **Files to create:** `src/security/institutional_guard.py`
- [ ] **Implementation:**
    - [ ] Implement `InstitutionalGuard` node to run AFTER `risk_manager` and BEFORE `order_router`.
    - [ ] **Enforce Global Limits:**
        - [ ] Max Aggregate Leverage (across all sub-accounts).
        - [ ] Hard Equity Stop (kill switch if portfolio value < X).
        - [ ] Restricted Asset List (prevent trading prohibited symbols).
- [ ] **Wiring:** Update `src/graph/orchestrator.py` to include the `institutional_guard` node in the execution chain.

### 4. Trade Warehouse & Analytics (120 min)
- [ ] **Files to modify:** `src/agents/l3/trade_logger.py`
- [ ] **Implementation:**
    - [ ] Extend `trade_logger_node` to write to a structured `trades` table in PostgreSQL (in addition to existing logs).
    - [ ] Link every trade record to its corresponding `audit_log_id` for full "Decision -> Trade" trace.

### 5. Testing & Verification (120 min)
- [ ] **Test files to create:** `tests/test_persistence.py`, `tests/test_audit_chain.py`
- [ ] **Validation Scenarios:**
    - [ ] **Scenario A (Persistence):** Run a task, stop the process, restart, and verify the graph resumes from the correct checkpoint using `thread_id`.
    - [ ] **Scenario B (Audit Tamper):** Manually modify an audit log entry and verify the hash chain validation fails.
    - [ ] **Scenario C (Guardrail):** Attempt a trade that exceeds global leverage limits and verify the `InstitutionalGuard` blocks it.

---

## ## Timeline
| Phase | Duration |
| :--- | :--- |
| 1. Persistence | 180 min |
| 2. Audit Logging | 240 min |
| 3. Guardrails | 120 min |
| 4. Trade Warehouse | 120 min |
| 5. Testing | 120 min |
| **Total** | **13 hours** |

---

## ## Rollback Plan
1. **Fallback:** Revert `PostgresSaver` to `MemorySaver` in `orchestrator.py`.
2. **Revert:** Disable the `institutional_guard` node in the graph construction.

---

## ## Security Checklist
- [ ] [**Encryption**] Ensure database connections use TLS/SSL in production.
- [ ] [**Provenance**] Every order MUST have a valid audit trail ID before reaching the router.
- [ ] [**Immutability**] Use database triggers or application-level locks to prevent UPDATE/DELETE on audit tables.

## NEXT STEPS
```bash
# Phase 4 Plan Ready. Proceed to Implementation?
/cook @plans/phase-4-memory-compliance.md
```
