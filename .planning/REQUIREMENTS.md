# Requirements: Quantum Swarm

**Defined:** 2026-03-09
**Core Value:** Institutional-quality trade signal generation through adversarial AI debate, with self-improving memory rules validated by backtesting, hard compliance guardrails, and immutable per-trade audit trails

## v1.5 Requirements

Requirements for v1.5 Reliable Infrastructure. Each maps to roadmap phases.

### Environment & Stability

- [ ] **ENV-01**: All ccxt-dependent tests pass after dependency fix (lighter_client packaging bug resolved or ccxt pinned to working version)
- [ ] **ENV-02**: All chromadb-dependent tests pass after dependency fix (verify installation, fix import/config issues)
- [ ] **ENV-03**: All pytest-asyncio-dependent tests pass after dependency fix (verify installation, fix mode configuration)
- [ ] **ENV-04**: CI test suite runs green with 0 env-related failures (13 previously broken tests restored)

### Resilience

- [ ] **SEC-03**: Gemini API circuit breaker detects transient failures (429, 503, timeout) and transitions through CLOSED → OPEN → HALF-OPEN states
- [ ] **SEC-04**: Circuit breaker in OPEN state returns soft-fail response (empty dict) instead of crashing the graph run
- [ ] **SEC-05**: Circuit breaker integrates into existing `with_audit_logging` wrapper as single integration point
- [ ] **SEC-06**: Circuit breaker state transitions are logged via structlog for debugging
- [ ] **SEC-07**: Circuit breaker recovery_timeout allows automatic probe after configurable cooldown period

### Merit System (KAMI + PersonaScore)

- [ ] **SOUL-09**: PersonaScore 5D evaluates persona fidelity across Consistency, Tone, Logic, Depth, and Bias dimensions using LLM-as-Judge
- [ ] **SOUL-10**: PersonaScore runs as CycleRunner post-cycle hook (not a graph node) to avoid circular evaluation and audit hash corruption
- [ ] **SOUL-11**: PersonaScore evaluates 4 LLM agents (AXIOM, MOMENTUM, CASSANDRA, SIGMA) — excludes RiskManager (rules-only)
- [ ] **SOUL-12**: PersonaScore results persist to PostgreSQL and are available to KAMI fidelity dimension in next cycle
- [ ] **SOUL-13**: PersonaScore uses structured output (Pydantic schema) with 5 float dimensions + rationale string
- [ ] **KAMI-05**: KAMI fidelity dimension consumes PersonaScore continuous signal (replaces binary 0/1)
- [ ] **KAMI-06**: KAMI weights rebalanced: Accuracy reduced from 30% to ~8%, fidelity increased to ~32%, with Recovery and Consensus adjusted proportionally
- [ ] **KAMI-07**: Weight transition uses EMA absorption (no score reset) to preserve merit history continuity

### Observability

- [ ] **OBS-02**: Token usage (prompt + completion) tracked per-agent per-cycle with USD cost estimate
- [ ] **OBS-04**: Token cost data persisted to CycleSnapshot for replay CLI visibility
- [ ] **OBS-05**: Token tracking uses single authoritative source (BudgetManager extension, not SwarmState reducer) to prevent double-counting
- [ ] **OBS-03**: CLI `prune` command archives ChromaDB entries older than configurable threshold to Obsidian-compatible Markdown files
- [ ] **OBS-06**: Prune operation respects active MemoryRegistry rules — never deletes vectors backing active rules
- [ ] **OBS-07**: Prune operation logs archived/deleted counts via structlog

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Observability

- **OBS-01**: Real-time WebSocket dashboard for live cycle monitoring
- **OBS-08**: Token cost alerting with configurable thresholds

### Merit System

- **KAMI-08**: thesis_records implementation for true Accuracy dimension signal
- **SOUL-14**: PersonaScore prompt calibration with human-labeled ground truth

### Resilience

- **SEC-08**: Circuit breakers for yfinance and PostgreSQL (non-LLM services)
- **SEC-09**: Automatic cycle retry with exponential backoff after circuit breaker recovery

## Out of Scope

| Feature | Reason |
|---------|--------|
| pybreaker/aiobreaker dependency | Stdlib implementation preferred per project philosophy (Counter cosine precedent) |
| PersonaScore as graph node | Circular evaluation risk, audit hash corruption, budget contamination |
| 5th KAMI dimension for PersonaScore | Cascading changes across 8+ files; merge into fidelity is simpler and sufficient |
| KAMI score reset on weight change | EMA absorption preserves merit history; reset would discard earned reputation |
| PersonaScore for RiskManager | Rules-only agent with no LLM call — no persona to evaluate |
| Langfuse/OpenTelemetry for token tracking | Heavyweight SaaS dependency; BudgetManager extension is sufficient |
| Real-time token cost alerting | Defer to v2 after baseline tracking validates cost patterns |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENV-01 | Pending | Pending |
| ENV-02 | Pending | Pending |
| ENV-03 | Pending | Pending |
| ENV-04 | Pending | Pending |
| SEC-03 | Pending | Pending |
| SEC-04 | Pending | Pending |
| SEC-05 | Pending | Pending |
| SEC-06 | Pending | Pending |
| SEC-07 | Pending | Pending |
| SOUL-09 | Pending | Pending |
| SOUL-10 | Pending | Pending |
| SOUL-11 | Pending | Pending |
| SOUL-12 | Pending | Pending |
| SOUL-13 | Pending | Pending |
| KAMI-05 | Pending | Pending |
| KAMI-06 | Pending | Pending |
| KAMI-07 | Pending | Pending |
| OBS-02 | Pending | Pending |
| OBS-03 | Pending | Pending |
| OBS-04 | Pending | Pending |
| OBS-05 | Pending | Pending |
| OBS-06 | Pending | Pending |
| OBS-07 | Pending | Pending |

**Coverage:**
- v1.5 requirements: 23 total
- Mapped to phases: 0
- Unmapped: 23

---
*Requirements defined: 2026-03-09*
*Last updated: 2026-03-09 after initial definition*
