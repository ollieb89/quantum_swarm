---
phases:
- number: 1
  name: Foundation & Orchestration (L1)
  status: complete
  milestone: v1.0
  started: 2026-03-06
  completed: 2026-03-06
- number: 2
  name: Cognitive Analysis & Risk Gating (L2)
  status: complete
  milestone: v1.0
  started: 2026-03-06
  completed: 2026-03-06
- number: 3
  name: Market Execution & Data (L3)
  status: complete
  milestone: v1.0
  started: 2026-03-06
  completed: 2026-03-06
- number: 4
  name: Memory & Institutional Compliance
  status: complete
  milestone: v1.0
  started: 2026-03-06
  completed: 2026-03-06
- number: 5
  name: Quant Alpha Intelligence
  status: not_started
  milestone: v1.1
  started: ''
  completed: ''
- number: 6
  name: Stop-Loss Enforcement
  status: not_started
  milestone: v1.1
  started: ''
  completed: ''
- number: 7
  name: Self-Improvement Loop
  status: not_started
  milestone: v1.1
  started: ''
  completed: ''
updated: '2026-03-06'
---

# Roadmap: Quantum Swarm

## Milestones

- **v1.0 MVP** — Phases 1-4 (shipped 2026-03-06)
- **v1.1 Self-Improvement** — Phases 5-7 (planned)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-4) — SHIPPED 2026-03-06</summary>

- [x] Phase 1: Foundation & Orchestration (L1) — completed 2026-03-06
  - LangGraph StateGraph, ClawGuard, skill registry, deterministic bypass
- [x] Phase 2: Cognitive Analysis & Risk Gating (L2) — completed 2026-03-06
  - MacroAnalyst, QuantModeler, adversarial debate, weighted consensus gate
- [x] Phase 3: Market Execution & Data (L3) — completed 2026-03-06
  - DataFetcher, NautilusTrader backtester, multi-venue OrderRouter, TradeLogger
- [x] Phase 4: Memory & Institutional Compliance — completed 2026-03-06
  - PostgreSQL persistence, hash-chained audit, institutional guardrails, trade warehouse

See: `.planning/milestones/v1.0-ROADMAP.md` for full archive

</details>

### v1.1 Self-Improvement (Planned)

- [ ] **Phase 5: Quant Alpha Intelligence** — Centralized technical indicator skill available to all agents
- [ ] **Phase 6: Stop-Loss Enforcement** — ATR-based stop-loss calculated, gated, and audited on every trade
- [ ] **Phase 7: Self-Improvement Loop** — Weekly review and automated rule generation from live performance

## Phase Details

### Phase 5: Quant Alpha Intelligence
**Goal**: Any agent in the swarm can compute RSI, MACD, and Bollinger Bands through a single registered skill, eliminating duplicate implementations.
**Depends on**: Phase 4 (skill registry infrastructure)
**Milestone**: v1.1
**Requirements**: ANALY-03
**Success Criteria** (what must be TRUE):
  1. Calling the `quant-alpha-intelligence` skill with a price series returns RSI, MACD, and Bollinger Band values without error
  2. The skill is registered in the YAML skill registry and discoverable by the L1 orchestrator via progressive disclosure
  3. QuantModeler can invoke the skill via its tool interface and receive structured indicator output it uses in analysis
  4. Unit tests cover each indicator calculation and pass against known reference values
**Plans**: TBD

### Phase 6: Stop-Loss Enforcement
**Goal**: Every trade the swarm submits has an ATR-derived stop-loss calculated before submission, is rejected at the OrderRouter if that stop-loss is missing, and has the stop-loss level written to the PostgreSQL audit record.
**Depends on**: Phase 5 (ATR calculation provided by quant-alpha-intelligence skill)
**Milestone**: v1.1
**Requirements**: RISK-03, RISK-05, RISK-06
**Success Criteria** (what must be TRUE):
  1. A trade submitted without a stop-loss field is rejected by OrderRouter with an explicit error before any venue call is made
  2. A trade submitted through the normal flow has an ATR-based stop-loss value present in the order payload
  3. After a trade is logged, the PostgreSQL audit record for that trade contains stop_loss_level, entry_price, and position_size columns populated
  4. Attempting to bypass the gate (e.g., empty or null stop-loss) is caught and logged as a compliance violation, not silently ignored
**Plans**: TBD

### Phase 7: Self-Improvement Loop
**Goal**: The swarm reviews its own live-vs-backtested performance weekly and automatically writes PREFER/AVOID/CAUTION rules to MEMORY.md that future sessions load as context.
**Depends on**: Phase 6 (requires real execution records with stop-loss data in trade warehouse)
**Milestone**: v1.1
**Requirements**: MEM-02, MEM-03
**Success Criteria** (what must be TRUE):
  1. Running the weekly review agent produces a structured performance drift report comparing actual P&L to backtested projections for each completed trade
  2. The drift report identifies which strategies are over-performing, under-performing, or within expected variance
  3. Running the rule generator after a review produces at least one PREFER, AVOID, or CAUTION entry appended to MEMORY.md
  4. Rules written to MEMORY.md follow a consistent, parseable format that future swarm sessions can load as context
  5. The full pipeline (review → rule generation → MEMORY.md append) can be triggered as a single command and completes without manual intervention
**Plans**: TBD

## Progress

| Phase | Milestone | Status | Completed |
|-------|-----------|--------|-----------|
| 1. Foundation & Orchestration | v1.0 | Complete | 2026-03-06 |
| 2. Cognitive Analysis & Risk Gating | v1.0 | Complete | 2026-03-06 |
| 3. Market Execution & Data | v1.0 | Complete | 2026-03-06 |
| 4. Memory & Institutional Compliance | v1.0 | Complete | 2026-03-06 |
| 5. Quant Alpha Intelligence | v1.1 | Not started | — |
| 6. Stop-Loss Enforcement | v1.1 | Not started | — |
| 7. Self-Improvement Loop | v1.1 | Not started | — |
