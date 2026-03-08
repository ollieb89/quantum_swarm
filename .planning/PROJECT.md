# Project: Quantum Swarm

## What This Is

A production-grade hierarchical multi-agent financial analysis swarm built on LangGraph. Specialized cognitive agents (Macro Analyst, Quant Modeler, adversarial Bull/Bear researchers) synthesize market intelligence through structured debate, apply institutional risk gating, and execute trades via a multi-venue order router with full MiFID II audit provenance.

## Core Value

Institutional-quality trade signal generation through adversarial AI debate, with immutable audit trails and hard compliance guardrails — from market data ingestion to PostgreSQL-persisted execution records.

## Current Milestone: v1.1 Self-Improvement Loop

**Goal:** Close the feedback loop — enforce stop-losses at execution time, centralize quant alpha math, and teach the swarm to learn from its own live-vs-backtested performance.

**Target features:**
- ANALY-03: `quant-alpha-intelligence` skill (centralized RSI, MACD, financial math)
- RISK-03: Mandatory stop-loss calculation and verification per execution
- MEM-02: Weekly review loop evaluating live vs backtested performance
- MEM-03: Automated rule generator updating MEMORY.md with PREFER/AVOID/CAUTION

## Current State (v1.0)

- **Runtime:** Python 3.12, LangGraph StateGraph, uv-managed
- **Infrastructure:** PostgreSQL 17 (AsyncPostgresSaver + Trade Warehouse, port 5433)
- **LLM:** Google Gemini (`gemini-2.0-flash`) via `langchain-google-genai`
- **Tests:** 155 passing, 0 failures
- **LOC:** ~14,600 Python

### Architecture

```
L1 Strategic Orchestrator (intent classifier, ClawGuard, skill registry)
    ↓ fan-out
L2 Domain Managers (MacroAnalyst, QuantModeler, BullishResearcher, BearishResearcher)
    ↓ fan-in → DebateSynthesizer → RiskManager gate (>0.6 threshold)
    ↓ if approved
L3 Executors (DataFetcher → Backtester → OrderRouter → TradeLogger)
    ↓
PostgreSQL (LangGraph checkpoints + audit_logs + trades)
```

## Constraints

- **Regulatory:** Finanstilsynet (Norway), MiFID II, MAR compliance
- **Risk:** Max 10x leverage, mandatory position size caps, institutional asset blocklist
- **Computational:** Budget ceilings on token expenditure (BudgetedTool wrapper)

## Requirements

### Validated (v1.0)

- ✓ ORCH-01: L1 Strategic Orchestrator with LangGraph StateGraph — v1.0
- ✓ ORCH-02: Filesystem blackboard for inter-agent communication — v1.0
- ✓ ORCH-03: Deterministic bypass for sub-ms procedural task execution — v1.0
- ✓ ORCH-04: Progressive skill disclosure via YAML metadata — v1.0
- ✓ ORCH-05: Council-as-Judge consensus with weighted confidence scoring — v1.0
- ✓ ANALY-01: L2 MacroAnalyst ReAct agent — v1.0
- ✓ ANALY-02: L2 QuantModeler ReAct agent — v1.0
- ✓ ANALY-04: Adversarial debate layer (BullishResearcher vs BearishResearcher) — v1.0
- ✓ EXEC-01: L3 DataFetcher (yfinance, ccxt, news, economic calendar) — v1.0
- ✓ EXEC-02: L3 Backtester (NautilusTrader BacktestEngine) — v1.0
- ✓ EXEC-03: L3 OrderRouter (paper, IB equities, Binance crypto) — v1.0
- ✓ RISK-01: RiskManager mandatory gate (consensus_score > 0.6) — v1.0
- ✓ RISK-02: Hard leverage limits (max 10x) and restricted asset blocklist — v1.0
- ✓ MEM-01: Exhaustive execution logging to PostgreSQL trade warehouse — v1.0
- ✓ SEC-01: ClawGuard verifiable guardrails for agent shell execution — v1.0
- ✓ SEC-02: Budget ceilings via BudgetedTool wrapper — v1.0
- ✓ SEC-04: Immutable hash-chained audit trail (SHA-256, MiFID II) — v1.0

### Validated (v1.1)

- ✓ ANALY-03: `quant-alpha-intelligence` skill (centralized RSI, MACD, financial math) — Phase 5
- ✓ RISK-03: Mandatory stop-loss calculation and verification per execution — Phase 6
- ✓ MEM-02: Weekly review loop evaluating live vs backtested performance — Phase 7
- ✓ MEM-03: Automated rule generator updating MEMORY.md with PREFER/AVOID/CAUTION — Phase 7

### Active

### Out of Scope

- High-frequency trading / sub-second reasoning loops (swarm is cognitive, not latency-optimized)
- Direct management of non-institutional retail accounts
- Multi-modal input (chart image analysis) — deferred to v2.0
- RL optimization for order flow — deferred to v2.0

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LangGraph StateGraph (migrated from custom) | Native fan-out/fan-in, checkpointing, graph visualization | ✓ Good — simplified orchestration significantly |
| Adversarial debate (Bull vs Bear) before consensus | Forces stress-testing of every trade thesis | ✓ Good — catches overconfident signals |
| Weighted consensus score (>0.6 threshold) | Quantifiable risk gate, tunable | ✓ Good — clean conditional routing |
| PostgreSQL AsyncPostgresSaver | Distributed checkpointing, crash recovery | ✓ Good — enables async orchestrator |
| Hash-chained audit logs (SHA-256 + prev_hash) | Tamper-evident MiFID II compliance | ✓ Good — verified by test suite |
| Google Gemini (gemini-2.0-flash) | Cost-effective, strong reasoning | ✓ Good — lazy init pattern required |
| Lazy LLM init (getter functions) | Allows import without GOOGLE_API_KEY | ✓ Good — essential for test suite |
| psycopg3 async (not psycopg2) | Native asyncio, no greenlets | ✓ Good — no compatibility shims needed |
| BudgetedTool + ToolCache wrapper | Budget ceilings + dedup tool calls | ✓ Good — SEC-02 compliance, cost control |
| `{name}_{period}` result key convention in quant_alpha_intelligence | Allows multi-instance same indicator with different periods (rsi_14, rsi_28) | ✓ Good — locked in Phase 5 CONTEXT.md |
| RSI state annotation in handle() not TechnicalIndicators.rsi() | Keeps raw method signatures pure; post-processing in orchestration layer | ✓ Good — TechnicalIndicators stays reusable |
| INSUFFICIENT_DATA vs INVALID_INPUT error classification by message substring | Minimal change; avoids new exception subclasses | ✓ Good — classifiable without structural changes |

## Context

Shipped v1.0 in 2 days (2026-03-05 → 2026-03-06), 67 commits, 155 tests.
Next: v1.1 focuses on self-improvement loop (MEM-02/03) and stop-loss enforcement (RISK-03).

---
*Last updated: 2026-03-08 — Phase 5 complete (ANALY-03 validated)*
