# Requirements: Quantum Swarm

**Defined:** 2026-03-08
**Core Value:** Institutional-quality trade signal generation through adversarial AI debate, with self-improving memory rules validated by backtesting, hard compliance guardrails, and immutable per-trade audit trails — from market data ingestion to PostgreSQL-persisted execution records.

## v1.4 Requirements

Requirements for the Beta: Observable Swarm release. Each maps to roadmap phases.

### Persona Population

- [x] **PERS-01**: User can observe MOMENTUM (BullishResearcher) reasoning with distinct price/flow personality
- [x] **PERS-02**: User can observe CASSANDRA (BearishResearcher) reasoning with distinct tail-risk personality
- [x] **PERS-03**: User can observe SIGMA (QuantModeler) reasoning with distinct quantitative personality
- [x] **PERS-04**: User can observe GUARDIAN (RiskManager) reasoning with distinct risk-control personality
- [x] **PERS-05**: Each persona has HEXACO-6 diversity profile with minimum pairwise distance >1.0 on normalized 0.0-1.0 scale
- [x] **PERS-06**: Each persona has functional YAML drift_guard block enabling ARS drift detection

### Cycle Persistence

- [x] **CYCL-01**: Each pipeline run persists agent memos, debate, consensus, merit scores, and decision card to a numbered cycle folder
- [x] **CYCL-02**: CycleSnapshot Pydantic model defines the canonical artifact schema
- [x] **CYCL-03**: PostgreSQL cycle_snapshots table indexes cycles with monotonic numbering and queryable metadata
- [x] **CYCL-04**: Cycle manifest includes timestamp, symbol, status, and cycle_id

### End-to-End Pipeline

- [x] **PIPE-01**: User can run "Analyze BTC" and the full pipeline executes from intent to decision card
- [x] **PIPE-02**: Data fetcher has caching/retry layer resilient to yfinance rate limits
- [x] **PIPE-03**: Messages list is bounded to prevent checkpoint state bloat across cycles
- [x] **PIPE-04**: Structured logging (structlog) captures pipeline execution for production debugging
- [x] **PIPE-05**: Soul cache can be reloaded without process restart for development iteration

### Replay CLI

- [ ] **REPL-01**: User can list all available cycles with summary metadata
- [ ] **REPL-02**: User can step through a cycle (agent memos → debate → consensus → decision card)
- [ ] **REPL-03**: User can navigate between cycles (previous/next)
- [ ] **REPL-04**: Merit weights are visualized per cycle showing agent influence
- [ ] **REPL-05**: Drift flags and ARS signals are displayed when viewing a cycle
- [ ] **REPL-06**: User can compare two cycles side-by-side to see how the institution changed

## Future Requirements

### Observability Extensions

- **OBS-01**: Real-time WebSocket dashboard for live cycle monitoring
- **OBS-02**: Token cost tracking per cycle for budget analysis
- **OBS-03**: Obsidian vault integration for cycle data browsing

### Persona Extensions

- **PERS-07**: PersonaScore 5D LLM-as-Judge fidelity evaluation pipeline (SOUL-09)
- **PERS-08**: HEXACO-6 automated diversity enforcement gate

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time WebSocket dashboard | High complexity, beta is CLI-first |
| Global SOUL.md (shared swarm identity) | Collapses adversarial diversity |
| Real-time SOUL.md mutation mid-graph-run | lru_cache race condition |
| LLM-as-Judge for ARS drift | Circular evaluation, adds API cost |
| High-frequency trading | Swarm is cognitive, not latency-optimized |
| Mobile/web UI | CLI-first beta; UI deferred to post-beta |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PERS-01 | Phase 23 | Complete |
| PERS-02 | Phase 23 | Complete |
| PERS-03 | Phase 23 | Complete |
| PERS-04 | Phase 23 | Complete |
| PERS-05 | Phase 23 | Complete |
| PERS-06 | Phase 23 | Complete |
| CYCL-01 | Phase 24 | Complete |
| CYCL-02 | Phase 24 | Complete |
| CYCL-03 | Phase 24 | Complete |
| CYCL-04 | Phase 24 | Complete |
| PIPE-01 | Phase 25 | Complete |
| PIPE-02 | Phase 25 | Complete |
| PIPE-03 | Phase 25 | Complete |
| PIPE-04 | Phase 25 | Complete |
| PIPE-05 | Phase 25 | Complete |
| REPL-01 | Phase 26 | Pending |
| REPL-02 | Phase 26 | Pending |
| REPL-03 | Phase 26 | Pending |
| REPL-04 | Phase 26 | Pending |
| REPL-05 | Phase 26 | Pending |
| REPL-06 | Phase 26 | Pending |

**Coverage:**
- v1.4 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0

---
*Requirements defined: 2026-03-08*
*Last updated: 2026-03-08 after roadmap creation*
