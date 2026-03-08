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
  status: complete
  milestone: v1.1
  started: 2026-03-06
  completed: 2026-03-06
- number: 6
  name: Stop-Loss Enforcement
  status: complete
  milestone: v1.1
  started: 2026-03-06
  completed: 2026-03-06
- number: 7
  name: Self-Improvement Loop
  status: complete
  milestone: v1.1
  started: 2026-03-06
  completed: 2026-03-06
- number: 8
  name: Portfolio Risk Governance
  status: in_progress
  milestone: v1.2
  started: 2026-03-07
  completed: ''
- number: 9
  name: Structured Memory Registry
  status: complete
  milestone: v1.2
  started: 2026-03-06
  completed: 2026-03-06
- number: 10
  name: Rule Validation Harness
  status: not_started
  milestone: v1.2
  started: ''
  completed: ''
- number: 11
  name: Explainability & Decision Cards
  status: not_started
  milestone: v1.2
  started: ''
  completed: ''
updated: '2026-03-08'
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
- [x] **Phase 6: Stop-Loss Enforcement** — ATR-based stop-loss calculated, gated, and audited on every trade (completed 2026-03-07)
- [x] **Phase 7: Self-Improvement Loop** — PerformanceReviewAgent + RuleGenerator with lazy LLM init, SelfLearningPipeline, dual-source memory injection, --review CLI (completed 2026-03-07)

## Phase Details

### Phase 5: Quant Alpha Intelligence
**Goal**: Any agent in the swarm can compute RSI, MACD, and Bollinger Bands through a single registered skill, eliminating duplicate implementations.
**Depends on**: Phase 4 (skill registry infrastructure)
**Milestone**: v1.1
**Requirements**: ANALY-03
**Success Criteria** (what must be TRUE):
  1. Calling the `quant-alpha-intelligence` skill with a price series returns RSI, MACD, and Bollinger Band values without error
  2. The skill is registered in the YAML skill registry and discoverable by the L1 orchestrator via progressive disclosure
  3. QuantModeler can invoke the skill via its tool interface and receive structured output it uses in analysis
  4. Unit tests cover each indicator calculation and pass against known reference values
**Plans**: [PLAN.md](phases/05-quant-alpha-intelligence/PLAN.md)


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
**Plans**: [PLAN.md](phases/06-stop-loss-enforcement/PLAN.md)

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
**Plans**: [PLAN.md](phases/07-self-improvement-loop/PLAN.md)

## Progress

| Phase | Milestone | Status | Completed |
|-------|-----------|--------|-----------|
| 1. Foundation & Orchestration | v1.0 | Complete | 2026-03-06 |
| 2. Cognitive Analysis & Risk Gating | v1.0 | Complete | 2026-03-06 |
| 3. Market Execution & Data | v1.0 | Complete | 2026-03-06 |
| 4. Memory & Institutional Compliance | 3/3 | Complete   | 2026-03-07 |
| 5. Quant Alpha Intelligence | 2/3 | In Progress|  |
| 6. Stop-Loss Enforcement | 1/1 | Complete   | 2026-03-07 |
| 7. Self-Improvement Loop | 2/2 | Complete   | 2026-03-07 |
| 8. Portfolio Risk Governance | 2/2 | Complete   | 2026-03-07 |
| 9. Structured Memory Registry | 2/2 | Complete   | 2026-03-07 |
| 10. Rule Validation Harness | 4/4 | Complete    | 2026-03-07 |
| 11. Explainability & Decision Cards | v1.2 | Not started | — |

## Milestone v1.2: Risk Governance and Rule Validation
Institutional hardening of risk controls and verification of self-improvement rules.

### Phase 8: Portfolio Risk Governance
**Goal**: Enforce aggregate portfolio constraints (exposure, concentration, drawdown) at the InstitutionalGuard gate.
**Depends on**: Phase 6
**Milestone**: v1.2
**Requirements**: RISK-07, RISK-08
**Success Criteria**:
  1. Orders exceeding max notional exposure or asset concentration are rejected.
  2. Drawdown circuit breaker rejects orders when daily or cumulative loss exceeds configured thresholds.
  3. Portfolio-level risk score is calculated and recorded for every trade via state["metadata"].
  4. _get_open_positions() SQL uses Phase 6 column names (position_size, entry_price).
  5. idx_trades_exit_time index exists on trades table.
**Plans**: 2 plans
Plans:
- [ ] 08-01-PLAN.md — Write failing test stubs (TDD RED): SQL column check, index check, drawdown rejection, metadata propagation
- [ ] 08-02-PLAN.md — Fix SQL bug, add exit_time index, implement drawdown circuit breaker (TDD GREEN)

### Phase 9: Structured Memory Registry
**Goal**: Transition MEMORY.md to a machine-readable JSON registry with lifecycle controls.
**Depends on**: Phase 7
**Milestone**: v1.2
**Requirements**: MEM-04, MEM-05
**Success Criteria**:
  1. Memory is stored in a versioned JSON format with status (proposed, active, deprecated).
  2. Agents load rules based on their lifecycle status.
  3. update_status() enforces one-way lifecycle transitions with version incrementing.
  4. Full round-trip verified: RuleGenerator writes proposed -> update_status promotes to active -> orchestrator injects it.
**Plans**: 2 plans
Plans:
- [ ] 09-01-PLAN.md — Add update_status() lifecycle method and atomic save() to MemoryRegistry; expand unit tests (MEM-05)
- [ ] 09-02-PLAN.md — Integration tests: RuleGenerator persist_rules() + orchestrator injection round-trip (MEM-04, MEM-05)

### Phase 10: Rule Validation Harness
**Goal**: Backtest or replay newly generated memory rules before promoting them to 'active'.
**Depends on**: Phase 9, Phase 3 (Backtester)
**Milestone**: v1.2
**Requirements**: MEM-06
**Success Criteria**:
  1. A validation run compares performance with and without a proposed rule.
  2. Rules only transition to 'active' if they pass the evaluation harness.
**Plans**: 3 plans
Plans:
- [ ] 10-01-PLAN.md — TDD RED: write test stubs (11 methods), add get_proposed_rules() to MemoryRegistry, add validation YAML config keys
- [ ] 10-02-PLAN.md — Implement RuleValidator class (two-run backtester, 2-of-3 metric check, audit writes) — turn 9 unit tests GREEN
- [ ] 10-03-PLAN.md — Wire persist_rules() -> validate_proposed_rules() and turn 2 integration tests GREEN

### Phase 11: Explainability & Decision Cards
**Goal**: Generate a compact, immutable "decision card" for every trade containing the full cognitive trace.
**Depends on**: Phase 4, Phase 8
**Milestone**: v1.2
**Requirements**: EXEC-04
**Success Criteria**:
  1. Every execution result is accompanied by a JSON decision card in the audit log.
  2. Decision card identifies which memory rules and risk scores influenced the trade.
**Plans**: 2 plans
Plans:
- [ ] 11-01-PLAN.md — TDD: DecisionCard Pydantic model, build_decision_card() builder, canonical_json(), verify_decision_card() — unit tests GREEN
- [ ] 11-02-PLAN.md — Wire decision_card_writer node into orchestrator; add SwarmState fields; integration tests (append, retry, failure path)
