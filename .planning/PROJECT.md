# Project: Quantum Swarm

## Vision
To build a robust, hierarchical multi-agent financial analysis swarm using the OpenClaw framework that adapts to market changes, manages institutional risk, and executes trades autonomously with strict regulatory compliance.

## Core Value
The primary objective is the synthesis of specialized cognitive agents (Macro Analysis, Quant Modeling, Risk Management) into a unified, self-improving system for institutional capital deployment.

## Context
- **Framework:** OpenClaw (Self-hosted AI agent runtime).
- **Architecture:** 3-tier hierarchy:
  - **Level 1 (Strategic Orchestrator):** High-level intent, task delegation, global risk arbiter.
  - **Level 2 (Domain Managers):** Specialized analysis (Macro, Quant, Risk).
  - **Level 3 (Stateless Executors):** Data fetching, backtesting, order routing.
- **Key Features:** Filesystem-as-context, deterministic bypass for procedural tasks, self-improvement loop (weekly reviews), and ClawGuard security.

## Constraints
- **Regulatory:** Compliance with Finanstilsynet (Norway), MiFID II, and MAR.
- **Risk:** Absolute limits on position sizing and leverage (max 10x). Mandatory stop-losses.
- **Computational:** Budget ceilings on token expenditure.

## Success Criteria
- [ ] Swarm successfully ingests market data and generates a consensus recommendation.
- [ ] Trades are executed within risk parameters and regulatory limits.
- [ ] Self-improvement loop correctly identifies and implements performance-enhancing rules.
- [ ] System handles API failures and conflicting signals through deterministic circuit breakers.

## Requirements

### Validated
- ✓ Hierarchy Design (L1/L2/L3) defined.
- ✓ OpenClaw integration strategy established.

### Active
- [ ] Implement Level 1 Strategic Orchestrator with progressive disclosure.
- [ ] Implement Level 2 Domain Managers (Macro, Quant, Risk).
- [ ] Implement Level 3 Stateless Executors (Data Fetcher, Backtester, Order Router).
- [ ] Implement `quant-alpha-intelligence` skill.
- [ ] Implement self-improvement loop (logging, evaluation, rule generation).
- [ ] Implement regulatory and safety guardrails (Finanstilsynet/ClawGuard).

### Out of Scope
- Direct human-in-the-loop for every trade (Swarm is autonomous).
- High-frequency trading (Latency focus is on sub-millisecond procedural tasks, but overall swarm is cognitive/strategic).

## Key Decisions
| Decision | Rationale | Outcome |
|----------|-----------|---------|
| OpenClaw Framework | Deterministic routing and hierarchy support. | — Pending |
| Hierarchical Stratification | Prevents context overflow and optimizes token spend. | — Pending |
| Filesystem-as-Context | Atomic commits and mutex-based coordination. | — Pending |

---
*Last updated: March 6, 2026 after initialization via gsd:new-project --auto*