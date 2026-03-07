# Requirements: Quantum Swarm

**Defined:** 2026-03-06 (v1.0), updated 2026-03-06 (v1.1), updated 2026-03-07 (v1.2)
**Core Value:** Institutional-quality trade signal generation through adversarial AI debate, with immutable audit trails and hard compliance guardrails

## Validated Requirements (v1.0 — Shipped 2026-03-06)

### Orchestration & Framework (ORCH)
- ✓ **ORCH-01**: L1 Strategic Orchestrator using LangGraph StateGraph — v1.0
- ✓ **ORCH-02**: Filesystem blackboard for inter-agent communication — v1.0
- ✓ **ORCH-03**: Deterministic bypass for sub-ms procedural task execution — v1.0
- ✓ **ORCH-04**: Progressive skill disclosure via YAML metadata — v1.0
- ✓ **ORCH-05**: Council-as-Judge consensus with weighted confidence scoring — v1.0

### Analysis & Reasoning (ANALY)
- ✓ **ANALY-01**: L2 MacroAnalyst ReAct agent — v1.0
- ✓ **ANALY-02**: L2 QuantModeler ReAct agent — v1.0
- ✓ **ANALY-04**: Adversarial debate layer (BullishResearcher vs BearishResearcher) — v1.0

### Execution & Tools (EXEC)
- ✓ **EXEC-01**: L3 DataFetcher (yfinance, ccxt, news, economic calendar) — v1.0
- ✓ **EXEC-02**: L3 Backtester (NautilusTrader BacktestEngine) — v1.0
- ✓ **EXEC-03**: L3 OrderRouter (paper, IB equities, Binance crypto) — v1.0

### Risk & Compliance (RISK)
- ✓ **RISK-01**: RiskManager mandatory gate (consensus_score > 0.6) — v1.0
- ✓ **RISK-02**: Hard leverage limits (max 10x) and restricted asset blocklist — v1.0

### Memory & Improvement (MEM)
- ✓ **MEM-01**: Exhaustive execution logging to PostgreSQL trade warehouse — v1.0

### Security & Safety (SEC)
- ✓ **SEC-01**: ClawGuard verifiable guardrails for agent shell execution — v1.0
- ✓ **SEC-02**: Budget ceilings via BudgetedTool wrapper — v1.0
- ✓ **SEC-04**: Immutable hash-chained audit trail (SHA-256, MiFID II) — v1.0

---

## v1.1 Requirements

Requirements for the Self-Improvement Loop milestone. Each maps to roadmap phases.

### Analytics (ANALY)

- [x] **ANALY-03**: Swarm can compute RSI, MACD, and Bollinger Bands technical indicators via centralized `quant-alpha-intelligence` registered skill

### Risk Management (RISK)

- [x] **RISK-03**: System calculates ATR-based stop-loss for every trade before order submission
- [x] **RISK-05**: OrderRouter rejects any trade execution missing a valid stop-loss calculation (hard gate, no exception)
- [x] **RISK-06**: Stop-loss level is recorded in the trade's PostgreSQL audit log entry alongside entry price and position size

### Memory / Self-Improvement (MEM)

- [x] **MEM-02**: Weekly review agent compares actual live P&L against backtested projections and writes a structured performance drift report
- [x] **MEM-03**: Rule generator reads weekly review output and appends PREFER/AVOID/CAUTION rules to MEMORY.md for future swarm context

---

## v1.2 Requirements

Requirements for the Structured Memory Registry milestone. Each maps to roadmap phases.

### Memory / Self-Improvement (MEM)

- [x] **MEM-04**: Structured JSON registry (`data/memory_registry.json`) serves as the primary machine-readable rule store, superseding the flat MEMORY.md format. Rules are Pydantic-validated with id, type, condition, action, evidence, status, version, and timestamps.
- [x] **MEM-05**: Lifecycle controls enforce one-way status transitions (proposed → active → deprecated/rejected) with version incrementing and INFO-level audit logging on every transition. Terminal states (deprecated, rejected) cannot be reversed.

---

## v1.3 Requirements

Requirements for the Rule Validation Harness milestone. Each maps to roadmap phases.

### Memory / Self-Improvement (MEM)

- [x] **MEM-06**: Proposed memory rules are automatically backtested before promotion; rules only transition to active if they pass a 2-of-3 metric evaluation harness (Sharpe ratio delta, max drawdown delta, win rate delta). Failing rules are moved to rejected. All promotion/rejection events are appended to `data/audit.jsonl` with full metric evidence.

---

## Future Requirements

Deferred from current scope. Tracked but not in v1.2 roadmap.

### Analytics
- **ANALY-05**: Reinforcement Learning optimization for order flow — post v1.1

### Security
- **SEC-03**: System-wide circuit breakers for API degradation or anomalous strategy behavior — post v1.1

### Memory
- **MEM-07**: Regime-aware vector memory for recognizing long-term historical parallels — v2.0

### Orchestration
- **ORCH-06**: Multi-modal input support (chart image analysis) — v2.0

## Out of Scope

Explicit exclusions. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| High-frequency / sub-second trading loops | Swarm is cognitive, not latency-optimized |
| RL optimization for order flow | Deferred to v2.0 |
| Multi-modal chart image analysis | Deferred to v2.0 |
| Direct retail account management | Institutional mandate only |
| Real-time stop-loss auto-triggering | v1.1 calculates and gates at submission; live monitoring is post-v1.1 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

### v1.0 Requirements

All v1.0 requirements covered by Phases 1-4 (shipped 2026-03-06).

### v1.1 Requirements

| Requirement | Phase | Status |
|-------------|-------|--------|
| ANALY-03 | Phase 5 | Complete |
| RISK-03 | Phase 6 | Complete |
| RISK-05 | Phase 6 | Complete |
| RISK-06 | Phase 6 | Complete |
| MEM-02 | Phase 7 | Complete |
| MEM-03 | Phase 7 | Complete |

**Coverage:**
- v1.1 requirements: 6 total
- Mapped to phases: 6
- Unmapped: 0 ✓

### v1.2 Requirements

| Requirement | Phase | Status |
|-------------|-------|--------|
| MEM-04 | Phase 9 | In Progress |
| MEM-05 | Phase 9 | In Progress |

**Coverage:**
- v1.2 requirements: 2 total
- Mapped to phases: 2
- Unmapped: 0 ✓

### v1.3 Requirements

| Requirement | Phase | Status |
|-------------|-------|--------|
| MEM-06 | Phase 10 | Complete |

**Coverage:**
- v1.3 requirements: 1 total
- Mapped to phases: 1
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-06 (v1.0)*
*Last updated: 2026-03-07 — v1.2 added (MEM-04, MEM-05); former MEM-04 (regime-aware vector memory) renumbered to MEM-07*
