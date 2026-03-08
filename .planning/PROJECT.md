# Project: Quantum Swarm

## What This Is

A production-grade hierarchical multi-agent financial analysis swarm built on LangGraph. Specialized cognitive agents with persistent Mind-Body-Soul personas (Macro Analyst, Quant Modeler, adversarial Bull/Bear researchers) synthesize market intelligence through structured debate with merit-weighted consensus, apply institutional risk gating with portfolio-level constraints, execute trades via a multi-venue order router, and continuously self-improve through backtested rule generation and per-agent evolution logs — all with full MiFID II audit provenance, immutable decision cards, and out-of-band drift auditing.

## Core Value

Institutional-quality trade signal generation through adversarial AI debate, with self-improving memory rules validated by backtesting, hard compliance guardrails, and immutable per-trade audit trails — from market data ingestion to PostgreSQL-persisted execution records.

## Current State (v1.3 shipped)

- **Runtime:** Python 3.12, LangGraph StateGraph, uv-managed
- **Infrastructure:** PostgreSQL 17 (AsyncPostgresSaver + Trade Warehouse, port 5433)
- **LLM:** Google Gemini (`gemini-2.0-flash`) via `langchain-google-genai`
- **Tests:** 300+ passing, 0 failures (excluding pre-existing env test files)
- **LOC:** ~30,600 Python

### Architecture

```
L1 Strategic Orchestrator (intent classifier, ClawGuard, skill registry)
    ↓ merit_loader (KAMI scores from PostgreSQL)
    ↓ fan-out
L2 Domain Managers (MacroAnalyst, QuantModeler, BullishResearcher, BearishResearcher)
    │  └─ Each agent has Soul (IDENTITY.md, SOUL.md, AGENTS.md) injected as system_prompt
    ↓ fan-in → soul_sync_handshake (peer soul summaries exchanged)
    → DebateSynthesizer (merit-weighted consensus, not character-length)
    → RiskManager gate (>0.6 threshold)
    ↓ if approved
    → InstitutionalGuard (portfolio constraints: exposure, concentration, drawdown)
    ↓ if approved
L3 Executors (DataFetcher → Backtester → OrderRouter → DecisionCardWriter → MeritUpdater → MemoryWriter → TradeLogger)
    │  └─ OrderRouter failures also route through DecisionCardWriter → MeritUpdater → MemoryWriter
    ↓
PostgreSQL (LangGraph checkpoints + audit_logs + trades + decision_cards + agent_merit_scores + ars_state)

Self-Improvement Pipeline (weekly):
    PerformanceReviewAgent → RuleGenerator → MemoryRegistry (proposed)
    → RuleValidator (2-of-3 backtest harness) → active/rejected + audit.jsonl
    → orchestrator injects active rules into MacroAnalyst/QuantModeler context

Agent Evolution Pipeline (per-cycle):
    MemoryWriter → MEMORY.md (structured forensic log, 50-entry cap)
    → SoulProposal triggers (KAMI_SPIKE, DRIFT_STREAK, MERIT_FLOOR)
    → data/soul_proposals/{agent_id}.json

Agent Church (out-of-band, standalone script):
    Reviews pending soul proposals → applies/rejects SOUL.md diffs
    → L1 self-proposals → RequiresHumanApproval

ARS Drift Auditor (daily systemd timer):
    5 stdlib metrics from MEMORY.md → evolution_suspended if threshold exceeded
    → Never gates trade execution (strict scope boundary)
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
- ✓ MEM-04: Structured JSON registry (`data/memory_registry.json`) with Pydantic-validated rules — v1.2 Phase 9
- ✓ MEM-05: One-way lifecycle transitions (proposed → active → deprecated/rejected) — v1.2 Phase 9
- ✓ MEM-06: Proposed rules backtested before promotion; 2-of-3 metric harness — v1.2 Phase 10/14
- ✓ RISK-07: Aggregate portfolio constraints enforced at `institutional_guard` gate — v1.2 Phase 8/13
- ✓ RISK-08: `trade_risk_score` and `portfolio_heat` set by institutional_guard, recorded in DecisionCard — v1.2 Phase 8/13

### Validated (v1.3)

- ✓ SOUL-01: SoulLoader loads AgentSoul from files with path-traversal guard and lru_cache — v1.3 Phase 15
- ✓ SOUL-02: `macro_analyst` persona files fully populated with Drift Guard — v1.3 Phase 15
- ✓ SOUL-03: 4 skeleton soul dirs created with minimum viable content — v1.3 Phase 15
- ✓ SOUL-04: SwarmState extended with `active_persona` and `system_prompt` fields — v1.3 Phase 15
- ✓ SOUL-05: All 5 L2 nodes inject soul into SwarmState before LLM execution — v1.3 Phase 15
- ✓ SOUL-06: `warmup_soul_cache()` called at graph creation — v1.3 Phase 15
- ✓ SOUL-07: Deterministic test suite — no LLM calls — v1.3 Phase 15
- ✓ KAMI-01: Merit Index formula (Accuracy+Recovery+Consensus+Fidelity) with configurable weights — v1.3 Phase 16
- ✓ KAMI-02: EMA decay with configurable lambda; cold start 0.5; bounds [0.1, 1.0] — v1.3 Phase 16
- ✓ KAMI-03: KAMI scores wired to DebateSynthesizer and persisted to PostgreSQL — v1.3 Phase 16/22
- ✓ KAMI-04: DebateSynthesizer uses KAMI merit scores for consensus weighting — v1.3 Phase 16
- ✓ EVOL-01: Per-agent MEMORY.md updated after each task cycle with structured log — v1.3 Phase 17/22
- ✓ EVOL-02: Agent proposes SOUL.md diffs; Agent Church approval gate — v1.3 Phase 17/20
- ✓ EVOL-03: Approved diffs applied; rejected diffs logged with reason — v1.3 Phase 17
- ✓ TOM-01: Soul-Sync Handshake — agents exchange truncated soul summaries before debate — v1.3 Phase 18/21
- ✓ TOM-02: Empathetic Refutation — agents address peer's persona logic — v1.3 Phase 18
- ✓ ARS-01: ARS Auditor computes 5 drift metrics from MEMORY.md with 30-cycle warm-up — v1.3 Phase 19/20
- ✓ ARS-02: `evolution_suspended` gates MEMORY.md writes only; no trade path coupling — v1.3 Phase 19

### Active (deferred from v1.2 / future)

- [ ] SOUL-08: All 4 skeleton agent soul dirs fully populated with HEXACO-6 diverse profiles
- [ ] SOUL-09: PersonaScore 5D LLM-as-Judge fidelity evaluation pipeline
- [ ] ANALY-05: RL optimization for order flow — v2.0
- [ ] SEC-03: System-wide circuit breakers for API degradation or anomalous strategy behavior
- [ ] MEM-07: Regime-aware vector memory for recognizing long-term historical parallels — v2.0
- [ ] ORCH-06: Multi-modal input support (chart image analysis) — v2.0

### Out of Scope

- High-frequency trading / sub-second reasoning loops (swarm is cognitive, not latency-optimized)
- Direct management of non-institutional retail accounts
- Real-time stop-loss auto-triggering (v1.1 gates at submission; live monitoring deferred)
- Emotional state model (valence/arousal, HMM) — no observable event hooks
- SoulZip relational USER.md history — requires accumulated cross-session peer data
- LLM-as-Judge for ARS drift detection — circular evaluation, adds API cost
- Global SOUL.md (shared swarm identity) — collapses adversarial diversity
- Real-time SOUL.md mutation mid-graph-run — lru_cache race condition
- HEXACO-6 automated diversity enforcement gate — deferred until all personas fully populated
- Sentence-transformers for ARS — Counter cosine sufficient at current scale

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LangGraph StateGraph (migrated from custom) | Native fan-out/fan-in, checkpointing, graph visualization | ✓ Good |
| Adversarial debate (Bull vs Bear) before consensus | Forces stress-testing of every trade thesis | ✓ Good |
| Weighted consensus score (>0.6 threshold) | Quantifiable risk gate, tunable | ✓ Good |
| PostgreSQL AsyncPostgresSaver | Distributed checkpointing, crash recovery | ✓ Good |
| Hash-chained audit logs (SHA-256 + prev_hash) | Tamper-evident MiFID II compliance | ✓ Good |
| Google Gemini (gemini-2.0-flash) | Cost-effective, strong reasoning; lazy init required | ✓ Good |
| psycopg3 async (not psycopg2) | Native asyncio, no greenlets | ✓ Good |
| BudgetedTool + ToolCache wrapper | Budget ceilings + dedup tool calls | ✓ Good |
| MemoryRegistry atomic save (os.replace) | Prevents partial-write corruption on crash | ✓ Good |
| RuleValidator 2-of-3 majority vote | Resilient to single metric noise | ✓ Good |
| InstitutionalGuard as mandatory graph node | Aggregate portfolio constraints enforced at graph level | ✓ Good |
| Frozen AgentSoul dataclass with lru_cache | Hashability + concurrent fan-out read safety | ✓ Good |
| AUDIT_EXCLUDED_FIELDS for soul data | Prevents soul content entering MiFID II hash chain | ✓ Good |
| Agent Church as standalone script (not LangGraph node) | Avoids deadlock and L1 self-approval conflict-of-interest | ✓ Good |
| KAMI merit replaces character-length proxy | Earned merit vs arbitrary text length for consensus weight | ✓ Good |
| Synchronous file I/O in node functions | asyncio.run() inside nodes is project-breaking (MEM-06 defect) | ✓ Good |
| ARS suspension gates evolution only (not trades) | Strict scope boundary prevents safety layer from blocking revenue | ✓ Good |
| Counter cosine for ARS sentiment (no numpy) | stdlib only, no new dependencies for background audit | ✓ Good |
| Direct edge for failure path (no conditional routing) | Clean routing; failures always flow through KAMI+memory | ✓ Good |

## Context

Shipped v1.3 on 2026-03-08 (8 phases, 18 plans, 90 commits). Full Mind-Body-Soul persona system live: SoulLoader with frozen AgentSoul dataclass, KAMI merit-weighted consensus in DebateSynthesizer, per-agent MEMORY.md forensic logs, Agent Church approval gate for soul mutations, Theory of Mind soul-sync handshake before debate, ARS drift auditor with 5 stdlib metrics and daily systemd timer.
Known env issues: broken `ccxt`, missing `chromadb` and `pytest-asyncio` (~13 tests affected, not regressions).
Tech debt from v1.3: skeleton agents have no YAML drift_guard block, Nyquist VALIDATION.md partial/missing for phases 15-22, thesis_records/ stub for deferred Accuracy dimension.

---
*Last updated: 2026-03-08 after v1.3 milestone*
