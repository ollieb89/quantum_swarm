# Project Research Summary

**Project:** Quantum Swarm
**Domain:** Quantitative Finance / Multi-Agent Systems (MAS)
**Researched:** 2026-03-06
**Confidence:** HIGH

## Executive Summary

Quantum Swarm is a hierarchical multi-agent financial analysis system designed for institutional capital deployment. It utilizes a three-tier architecture (L1 Strategic Orchestrator, L2 Domain Managers, and L3 Stateless Executors) to manage complexity, prevent context overflow, and ensure regulatory compliance (Finanstilsynet/MiFID II). The system focuses on high-level cognitive tasks such as macro analysis and quantitative modeling, combined with deterministic execution for data fetching and order routing.

The recommended approach centers on an asynchronous directed acyclic graph (DAG) implemented via LangGraph, enabling sophisticated features like adversarial debate (Bull vs. Bear agents) and rigorous risk gating. Key risks include synchronized feedback loops that could trigger flash crashes, regulatory breaches in short-selling (SSR) compliance, and the "black-box" explainability gap. These are mitigated through instrument-level circuit breakers, mandatory "locate" verification steps, and immutable audit trails of agent reasoning.

Overall, the research indicates that a specialized, hierarchical approach is superior to monolithic LLM designs, particularly in high-stakes financial environments where auditability and risk control are paramount.

## Key Findings

### Recommended Stack

The stack is designed for reliability, scalability, and strict state management. Python serves as the primary language for orchestration and financial modeling, while TypeScript/Bun is used for specialized browser-based automation.

**Core technologies:**
- **LangGraph:** Agent orchestration — Provides the DAG-based state management and cyclic workflow support.
- **Python 3.12+:** Core logic — Standard for quantitative finance with robust library support.
- **Nautilus Trader:** Backtesting & Execution — High-performance trading engine for deterministic execution.
- **ccxt / yfinance:** Data Ingestion — Broad connectivity to crypto exchanges and traditional market data.
- **Bun / TypeScript:** Specialized Agents — Used for the "Dexter" agent to handle web-based tasks and CLI interactions.

### Expected Features

Research highlights a shift toward "adversarial" and "reflective" agentic systems in the 2024-2025 SOTA.

**Must have (table stakes):**
- **Role Specialization** — Separate experts for Macro, Quant, and Risk to prevent hallucinations.
- **Hierarchical Architecture** — Separation of data ingestion, analysis, and execution.
- **Audit Trail (Explainability)** — Chain of reasoning logs for every trade signal (MiFID II requirement).
- **Basic Risk Gating** — Hard stop-losses and position sizing constraints.

**Should have (competitive):**
- **Adversarial Debate** — Bullish vs. Bearish agents to reduce consensus bias.
- **Self-Correction & Reflection** — Post-trade analysis to update long-term memory.
- **Regime-Aware Memory** — Recognizing market conditions (e.g., Bull vs. Bear regimes).

**Defer (v2+):**
- **Reinforcement Learning (RL) Optimization** — Start with statistical models; add RL for fine-tuning later.
- **High-Frequency Trading (HFT)** — Focus on Intraday/Swing timeframes due to LLM latency.

### Architecture Approach

The system follows a Hierarchical Orchestration pattern implemented as an asynchronous DAG. This ensures that high-level strategy is separated from low-level execution, preventing "God Agent" syndrome.

**Major components:**
1. **L1 Strategic Orchestrator** — Handles intent classification and final consensus synthesis.
2. **L2 Domain Managers** — Specialized analysis (Macro/Quant) and adversarial debate layer.
3. **L3 Stateless Executors** — Deterministic tools for data fetching, backtesting, and order routing.

### Critical Pitfalls

Research identified significant regulatory and systemic risks in autonomous trading swarms.

1. **Synchronized Feedback Loops** — Multiple agents reacting to the same signal can trigger flash crashes; requires circuit breakers.
2. **SSR Compliance Breaches** — Risk of illegal short selling without "locate" verification; requires hard-coded checks.
3. **Explainability Gap** — Regulators (Finanstilsynet) require "understandable" algorithms; requires immutable rationale logs.
4. **State Drift** — Loss of strategic intent as information passes through layers; requires strictly typed schemas.

## Implications for Roadmap

Based on research, the project should follow a dependency-aware phase structure that prioritizes core orchestration and safety.

### Phase 1: Graph Skeleton (L1)
**Rationale:** Establishing the LangGraph framework and state schema is necessary before any agents can communicate.
**Delivers:** Core orchestration engine and intent classification.
**Addresses:** Hierarchical Architecture (Table Stake).
**Avoids:** State Drift (Pitfall).

### Phase 2: Core Analysis & Adversarial Layer (L2)
**Rationale:** Domain expertise and bias reduction (debate) are the primary value-adds of the swarm.
**Delivers:** Macro/Quant analysts and Bull/Bear research fanning.
**Uses:** LangChain and file-based blackboard context.
**Implements:** Adversarial Debate (Differentiator).

### Phase 3: Functional Tools & Execution (L3)
**Rationale:** Connecting the brain to the market requires stateless executors that can be tested independently.
**Delivers:** Data fetchers, Nautilus Trader integration, and paper trading.
**Addresses:** Multi-Source Data Integration.
**Avoids:** SSR Compliance Breach (Pitfall) via hard-coded gates.

### Phase 4: Observability & Compliance
**Rationale:** Finalizing the audit trail and dashboard ensures the system is ready for institutional capital.
**Delivers:** Real-time monitoring and "Inspector" agent logs.
**Addresses:** Audit Trail (Explainability).
**Avoids:** Black-Box Explainability Gap (Pitfall).

### Phase Ordering Rationale

- **Foundation First:** Building the L1 skeleton first ensures a stable communication protocol (File-based/Blackboard) before adding complex L2 logic.
- **Risk Mitigation:** Risk Gating and SSR compliance are built into the L3 execution chain from the start rather than added as an afterthought.
- **Strategic Depth:** Adversarial layers (L2) are implemented before live execution (L3) to ensure all trade proposals are sufficiently stress-tested.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (L3 Execution):** Integration with specific brokerage APIs (Interactive Brokers) and handling T+2 settlement cycles.
- **Phase 4 (Compliance):** Mapping agent rationale logs to specific MiFID II Article 17 requirements.

Phases with standard patterns (skip research-phase):
- **Phase 1 (L1 Skeleton):** Standard LangGraph implementation patterns are well-documented.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Aligns with existing codebase and industry standards for Python/MAS. |
| Features | HIGH | Based on SOTA research (arXiv 2025) and TradingAgents framework. |
| Architecture | HIGH | Hierarchical pattern is a proven solution for context window management. |
| Pitfalls | HIGH | Verified against recent (2025) regulatory enforcement actions. |

**Overall confidence:** HIGH

### Gaps to Address

- **Latency Optimization:** The impact of multi-layer reasoning (L1->L2->L3) on trade execution timing needs measurement.
- **Prompt Sensitivity:** Adversarial debate performance is highly dependent on prompt engineering to avoid "polite consensus".
- **Data Provenance:** Ensuring data quality across technical, fundamental, and sentiment sources.

## Sources

### Primary (HIGH confidence)
- **Finanstilsynet (Norway):** Enforcement actions (2025) regarding SSR and algorithmic trading.
- **ESMA:** MiFID II Art. 17 Regulatory Technical Standards.
- **TradingAgents Framework:** EMNLP 2024 / cyberarctica.com.
- **LangGraph Documentation:** Official orchestration patterns.

### Secondary (MEDIUM confidence)
- **QuantAgents Simulated Trading:** arXiv 2025.
- **Year of the Agent (2025) Trends:** osintteam.blog / towardsai.net.

### Tertiary (LOW confidence)
- **MAST Framework Pitfalls:** plainenglish.io.

---
*Research completed: 2026-03-06*
*Ready for roadmap: yes*
