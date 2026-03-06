# Roadmap: Quantum Swarm

## Phases

- [ ] **Phase 1: Foundation & Orchestration (L1)** - Establish the core communication framework, L1 orchestrator, and basic security guardrails.
- [ ] **Phase 2: Cognitive Analysis & Risk Gating (L2)** - Implement specialized L2 agents, adversarial debate, and mandatory risk management checks.
- [ ] **Phase 3: Market Execution & Data (L3)** - Connect the swarm to live/historical data, backtesting engine, and secure order routing.
- [ ] **Phase 4: Memory & Institutional Compliance** - Close the self-improvement loop and ensure full MiFID II / Finanstilsynet auditability.

## Phase Details

### Phase 1: Foundation & Orchestration (L1)
**Goal**: Build the skeletal hierarchical framework and inter-agent communication layer.
**Depends on**: Nothing
**Requirements**: ORCH-01, ORCH-02, ORCH-03, ORCH-04, SEC-01, SEC-02
**Success Criteria**:
  1. User can initiate a task through L1 and see it delegated to a child agent via filesystem "Blackboard" state.
  2. System executes shell commands within ClawGuard sandboxed environment.
  3. Sub-millisecond commands bypass LLM reasoning via deterministic dispatch.
  4. System automatically shuts down if token expenditure exceeds budget ceilings.
**Plans**:
- [ ] 01-01-PLAN.md — Orchestration Consolidation & Blackboard Implementation
- [ ] 01-02-PLAN.md — Security Guardrails (ClawGuard)
- [ ] 01-03-PLAN.md — Skill Discovery & Deterministic Bypass

### Phase 2: Cognitive Analysis & Risk Gating (L2)
**Goal**: Implement the reasoning core of the swarm with specialized domain managers and bias reduction.
**Depends on**: Phase 1
**Requirements**: ANALY-01, ANALY-02, ANALY-03, ANALY-04, RISK-01, RISK-02, RISK-03, ORCH-05
**Success Criteria**:
  1. System produces a "Council-as-a-Judge" consensus recommendation derived from independent Macro and Quant signals.
  2. Trade proposals are automatically rejected by the Risk Manager if they violate the 10x leverage hard limit.
  3. Every trade recommendation includes an adversarial "Bull vs. Bear" debate summary to reduce consensus bias.
  4. Every proposed trade has a calculated stop-loss and verified exit strategy.
**Plans**: TBD

### Phase 3: Market Execution & Data (L3)
**Goal**: Enable real-world interaction through data ingestion, performance simulation, and order routing.
**Depends on**: Phase 2
**Requirements**: EXEC-01, EXEC-02, EXEC-03, RISK-04, SEC-03
**Success Criteria**:
  1. L3 Data Fetcher consolidates information from at least two market sources (Technical + Fundamental/News).
  2. Backtester produces a performance report for a strategy using historical data with slippage and commission friction.
  3. Order Router successfully places a test order on a simulated exchange (CCXT/NautilusTrader).
  4. System-wide circuit breakers trigger and halt activity on API degradation or anomalous strategy behavior.
**Plans**: TBD

### Phase 4: Memory & Institutional Compliance
**Goal**: Implement the long-term learning loop and regulatory explainability requirements.
**Depends on**: Phase 3
**Requirements**: MEM-01, MEM-02, MEM-03, SEC-04
**Success Criteria**:
  1. Every trade signal generates an immutable audit trail showing the full "Chain of Reasoning" for MiFID II compliance.
  2. Weekly review loop automatically identifies performance gaps and appends new behavioral rules to `MEMORY.md`.
  3. System maintains an exhaustive `trades.json` log with multi-dimensional context capture.
**Plans**: TBD

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1: Foundation & Orchestration (L1) | 0/3 | In Progress | - |
| 2: Cognitive Analysis & Risk (L2) | 0/0 | Not started | - |
| 3: Market Execution & Data (L3) | 0/0 | Not started | - |
| 4: Memory & Institutional Compliance | 0/0 | Not started | - |
