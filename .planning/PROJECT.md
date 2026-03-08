# Project: Quantum Swarm

## What This Is

A production-grade hierarchical multi-agent financial analysis swarm built on LangGraph. Specialized cognitive agents (Macro Analyst, Quant Modeler, adversarial Bull/Bear researchers) synthesize market intelligence through structured debate, apply institutional risk gating with portfolio-level constraints, execute trades via a multi-venue order router, and continuously self-improve through backtested rule generation — all with full MiFID II audit provenance and immutable decision cards.

## Core Value

Institutional-quality trade signal generation through adversarial AI debate, with self-improving memory rules validated by backtesting, hard compliance guardrails, and immutable per-trade audit trails — from market data ingestion to PostgreSQL-persisted execution records.

## Current State (v1.2 shipped)

- **Runtime:** Python 3.12, LangGraph StateGraph, uv-managed
- **Infrastructure:** PostgreSQL 17 (AsyncPostgresSaver + Trade Warehouse, port 5433)
- **LLM:** Google Gemini (`gemini-2.0-flash`) via `langchain-google-genai`
- **Tests:** 260+ passing, 0 failures (excluding 2 known-broken env test files)
- **LOC:** ~23,500 Python

### Architecture

```
L1 Strategic Orchestrator (intent classifier, ClawGuard, skill registry)
    ↓ fan-out
L2 Domain Managers (MacroAnalyst, QuantModeler, BullishResearcher, BearishResearcher)
    ↓ fan-in → DebateSynthesizer → RiskManager gate (>0.6 threshold)
    ↓ if approved
    → InstitutionalGuard (portfolio constraints: exposure, concentration, drawdown)
    ↓ if approved
L3 Executors (DataFetcher → Backtester → OrderRouter → DecisionCardWriter → TradeLogger)
    ↓
PostgreSQL (LangGraph checkpoints + audit_logs + trades + decision_cards)

Self-Improvement Pipeline (weekly):
    PerformanceReviewAgent → RuleGenerator → MemoryRegistry (proposed)
    → RuleValidator (2-of-3 backtest harness) → active/rejected + audit.jsonl
    → orchestrator injects active rules into MacroAnalyst/QuantModeler context
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

- ✓ ANALY-03: `quant-alpha-intelligence` skill (RSI, MACD, Bollinger Bands, ATR) with `{name}_{period}` keying — v1.1 Phase 5
- ✓ RISK-03: ATR-based stop-loss calculated for every trade before submission — v1.1 Phase 6
- ✓ RISK-05: OrderRouter hard gate rejects any trade missing valid stop-loss — v1.1 Phase 6
- ✓ RISK-06: `stop_loss_level`, `entry_price`, `position_size` written to PostgreSQL audit record — v1.1 Phase 6
- ✓ MEM-02: Weekly PerformanceReviewAgent generates structured live-vs-backtested drift report — v1.1 Phase 7
- ✓ MEM-03: RuleGenerator writes PREFER/AVOID/CAUTION rules to MEMORY.md; rules promoted to `active` and injected into analyst context — v1.1 Phase 12

### Validated (v1.2)

- ✓ EXEC-04: DecisionCard tamper-evident audit trail (canonical JSON, SHA-256 hash, `audit.jsonl` append) — v1.2 Phase 11
- ✓ MEM-04: Structured JSON registry (`data/memory_registry.json`) with Pydantic-validated rules (id, type, condition, action, evidence, status, version, timestamps) — v1.2 Phase 9
- ✓ MEM-05: One-way lifecycle transitions (proposed → active → deprecated/rejected) with version incrementing and INFO-level audit logging — v1.2 Phase 9
- ✓ MEM-06: Proposed rules backtested before promotion; 2-of-3 metric harness (Sharpe, max drawdown, win rate); failing rules → `rejected`; all events → `data/audit.jsonl` — v1.2 Phase 10/14
- ✓ RISK-07: Aggregate portfolio constraints (max notional exposure, asset concentration, cumulative drawdown) enforced at `institutional_guard` gate on every trade — v1.2 Phase 8/13
- ✓ RISK-08: `state["metadata"]["trade_risk_score"]` and `state["metadata"]["portfolio_heat"]` set by `institutional_guard_node`, recorded in `DecisionCard.portfolio_risk_score` — v1.2 Phase 8/13

## Current Milestone: v1.3 MBS Persona System

**Goal:** Give every L2 agent a persistent, character-consistent identity via the Mind-Body-Soul architecture — covering foundation (SoulLoader, soul files, LangGraph wiring), merit-based reward scoring (KAMI), agent self-evolution (MEMORY.md + Agent Church), Theory of Mind debate layer, and ARS drift auditing.

**Target features:**
- Tier 1 — SoulLoader + `macro_analyst` reference persona + 4 skeleton soul dirs + SwarmState fields + LangGraph node injection + test suite
- Tier 2a — KAMI Merit Index: multi-dimensional reward (Accuracy + Recovery + Consensus + Fidelity), EMA decay [0.1–1.0], cold start 0.5, consensus weighting
- Tier 2b — MEMORY.md per-agent evolution log + self-reflection + Agent Church approval gate for SOUL.md diffs
- Tier 2c — Theory of Mind: Soul-Sync Handshake (truncated SOUL.md exchange before debate) + Empathetic Refutation
- Tier 2d — ARS Auditor: periodic drift/ego-hijacking detection across agent evolution logs

### Active (v1.3)

- [ ] SOUL-01: SoulLoader loads AgentSoul from files with path-traversal guard and lru_cache
- [ ] SOUL-02: `macro_analyst` persona files (IDENTITY.md, SOUL.md, AGENTS.md) fully populated with Drift Guard
- [ ] SOUL-03: 4 skeleton soul dirs (bullish_researcher, bearish_researcher, quant_modeler, risk_manager) created
- [ ] SOUL-04: SwarmState extended with `active_persona` and `system_prompt` fields
- [ ] SOUL-05: `macro_analyst_node` injects soul into SwarmState before LLM execution
- [ ] SOUL-06: `warmup_soul_cache()` called at graph creation
- [ ] SOUL-07: Deterministic test suite — no LLM calls (unit + content + integration)
- [ ] KAMI-01: Merit Index formula (Accuracy + Recovery + Consensus + Fidelity) with configurable weights
- [ ] KAMI-02: EMA decay with configurable λ; cold start 0.5; bounds [0.1, 1.0]
- [ ] KAMI-03: KAMI scores wired to `DebateSynthesizer` consensus weighting
- [ ] KAMI-04: KAMI scores stored in SwarmState and persisted to PostgreSQL
- [ ] EVOL-01: Per-agent MEMORY.md updated after each task cycle with self-reflection log
- [ ] EVOL-02: Agent proposes SOUL.md diffs in MEMORY.md; Agent Church (L1 Orchestrator) approval gate
- [ ] EVOL-03: Approved diffs applied; rejected diffs logged with reason
- [ ] TOM-01: Soul-Sync Handshake — agents exchange truncated SOUL.md summaries before debate
- [ ] TOM-02: Empathetic Refutation — agents address peer's persona logic rather than flat rejection
- [ ] ARS-01: ARS Auditor computes drift score from MEMORY.md evolution logs per agent
- [ ] ARS-02: Agents exceeding ARS drift threshold flagged; ops alert + evolution suspended

### Active (deferred from v1.2 / future)

- [ ] ANALY-05: RL optimization for order flow — v2.0
- [ ] SEC-03: System-wide circuit breakers for API degradation or anomalous strategy behavior
- [ ] MEM-07: Regime-aware vector memory for recognizing long-term historical parallels — v2.0
- [ ] ORCH-06: Multi-modal input support (chart image analysis) — v2.0

### Out of Scope

- High-frequency trading / sub-second reasoning loops (swarm is cognitive, not latency-optimized)
- Direct management of non-institutional retail accounts
- Real-time stop-loss auto-triggering (v1.1 gates at submission; live monitoring deferred)

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
| `{name}_{period}` result key convention in quant_alpha_intelligence | Multi-instance same indicator with different periods (rsi_14, rsi_28) | ✓ Good — locked in Phase 5 CONTEXT.md |
| RSI state annotation in handle() not TechnicalIndicators.rsi() | Keeps raw method signatures pure; post-processing in orchestration layer | ✓ Good — TechnicalIndicators stays reusable |
| INSUFFICIENT_DATA vs INVALID_INPUT error classification by message substring | Minimal change; avoids new exception subclasses | ✓ Good — classifiable without structural changes |
| MemoryRegistry atomic save (os.replace) | Prevents partial-write corruption on crash | ✓ Good — POSIX atomic rename pattern |
| RuleValidator 2-of-3 majority vote (Sharpe, drawdown, win rate) | Resilient to single metric noise | ✓ Good — balanced promotion gate |
| `persist_rules()` → proposed only; validator sole promoter | MEM-06 gate order; validator controls active transition | ✓ Good — prevents premature promotion bypass |
| InstitutionalGuard as mandatory graph node (not inline check) | Aggregate portfolio constraints enforced at graph level | ✓ Good — route_after_institutional_guard handles approved/rejected |
| Rejected trades route to synthesize (not END) | Explanatory summary before dead-end; explainability preserved | ✓ Good — Phase 13 design |
| DecisionCard portfolio_risk_score from state["metadata"]["trade_risk_score"] | Not top-level SwarmState field; avoids schema pollution | ✓ Good — Phase 11 design |

## Context

Shipped v1.2 on 2026-03-08 (6 phases, 14 plans, 260+ tests). Full risk governance stack live: portfolio constraints, structured memory registry, 2-of-3 backtest validation, MiFID II decision cards, and InstitutionalGuard wired into execution graph. MEM-06 async event loop defect fixed (`ThreadPoolExecutor` replaces `asyncio.run(asyncio.to_thread(...))`).
Known env issues: broken `ccxt`, missing `chromadb` and `pytest-asyncio` (~13 tests affected, not regressions).
Tech debt from v1.2: `risk_approved` stays `None` on institutional_guard approval path; Nyquist VALIDATION.md files missing for all v1.2 phases.

---
*Last updated: 2026-03-08 after v1.3 milestone start*
