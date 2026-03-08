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
  completed: 2026-03-07
- number: 7
  name: Self-Improvement Loop
  status: complete
  milestone: v1.1
  started: 2026-03-06
  completed: 2026-03-07
- number: 8
  name: Portfolio Risk Governance
  status: complete
  milestone: v1.2
  started: 2026-03-07
  completed: 2026-03-07
- number: 9
  name: Structured Memory Registry
  status: complete
  milestone: v1.2
  started: 2026-03-06
  completed: 2026-03-07
- number: 10
  name: Rule Validation Harness
  status: complete
  milestone: v1.2
  started: 2026-03-07
  completed: 2026-03-08
- number: 11
  name: Explainability & Decision Cards
  status: complete
  milestone: v1.2
  started: 2026-03-07
  completed: 2026-03-08
- number: 12
  name: Wire MEM-03 End-to-End (Rule Lifecycle & Memory Forwarding)
  status: complete
  milestone: v1.1
  started: 2026-03-08
  completed: 2026-03-08
- number: 13
  name: Wire InstitutionalGuard into LangGraph Graph
  status: complete
  milestone: v1.2
  started: 2026-03-08
  completed: 2026-03-08
- number: 14
  name: Fix MEM-06 Validation Gate Call Order
  status: complete
  milestone: v1.2
  started: 2026-03-08
  completed: 2026-03-08
updated: '2026-03-08'
---

# Roadmap: Quantum Swarm

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-03-06)
- ✅ **v1.1 Self-Improvement** — Phases 5-7, 12 (shipped 2026-03-08)
- 🚧 **v1.2 Risk Governance** — Phases 8-11, 13-14 (complete, pending milestone close)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-03-06</summary>

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

<details>
<summary>✅ v1.1 Self-Improvement (Phases 5-7, 12) — SHIPPED 2026-03-08</summary>

- [x] Phase 5: Quant Alpha Intelligence — completed 2026-03-06
  - Centralized `quant-alpha-intelligence` skill: RSI, MACD, Bollinger Bands, ATR; `{name}_{period}` result keying
- [x] Phase 6: Stop-Loss Enforcement — completed 2026-03-07
  - ATR-based stop-loss gate, OrderRouter hard rejection on missing stop-loss, PostgreSQL audit columns
- [x] Phase 7: Self-Improvement Loop — completed 2026-03-07
  - PerformanceReviewAgent, RuleGenerator, SelfLearningPipeline, `--review` CLI, dual-source memory injection
- [x] Phase 12: Wire MEM-03 End-to-End — completed 2026-03-08
  - Gap closure: rules promoted to `active`, institutional memory forwarded to analyst sub-graphs (closes MC-01, MC-02)

See: `.planning/milestones/v1.1-ROADMAP.md` for full archive

</details>

### 🚧 v1.2 Risk Governance and Rule Validation

- [x] **Phase 8: Portfolio Risk Governance** — Institutional constraints enforced at `institutional_guard` gate (completed 2026-03-07)
- [x] **Phase 9: Structured Memory Registry** — Machine-readable JSON registry with lifecycle controls (completed 2026-03-07)
- [x] **Phase 10: Rule Validation Harness** — 2-of-3 backtest metric harness before rule promotion (completed 2026-03-08)
- [x] **Phase 11: Explainability & Decision Cards** — Immutable DecisionCard JSON for every trade (completed 2026-03-08)
- [x] **Phase 13: Wire InstitutionalGuard** — Gap closure: `institutional_guard_node` wired into execution graph (closes RISK-07, RISK-08) (completed 2026-03-08)
- [x] **Phase 14: Fix MEM-06 Validation Gate Call Order** — Gap closure: `persist_rules()` → `proposed` → validator → `active`/`rejected` (closes MEM-06) (completed 2026-03-08)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|---------------|--------|-----------|
| 1. Foundation & Orchestration | v1.0 | — | Complete | 2026-03-06 |
| 2. Cognitive Analysis & Risk Gating | v1.0 | — | Complete | 2026-03-06 |
| 3. Market Execution & Data | v1.0 | — | Complete | 2026-03-06 |
| 4. Memory & Institutional Compliance | v1.0 | — | Complete | 2026-03-06 |
| 5. Quant Alpha Intelligence | v1.1 | 2/2 | Complete | 2026-03-06 |
| 6. Stop-Loss Enforcement | v1.1 | 1/1 | Complete | 2026-03-07 |
| 7. Self-Improvement Loop | v1.1 | 2/2 | Complete | 2026-03-07 |
| 8. Portfolio Risk Governance | v1.2 | 2/2 | Complete | 2026-03-07 |
| 9. Structured Memory Registry | v1.2 | 2/2 | Complete | 2026-03-07 |
| 10. Rule Validation Harness | v1.2 | 4/4 | Complete | 2026-03-08 |
| 11. Explainability & Decision Cards | v1.2 | 2/2 | Complete | 2026-03-08 |
| 12. Wire MEM-03 End-to-End | v1.1 | 2/2 | Complete | 2026-03-08 |
| 13. Wire InstitutionalGuard | v1.2 | 2/2 | Complete | 2026-03-08 |
| 14. Fix MEM-06 Validation Gate Call Order | v1.2 | 2/2 | Complete | 2026-03-08 |
