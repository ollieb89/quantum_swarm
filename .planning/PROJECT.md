# Project: Quantum Swarm

## What This Is

A production-grade hierarchical multi-agent financial analysis swarm built on LangGraph. Specialized cognitive agents with persistent Mind-Body-Soul personas (Macro Analyst, Quant Modeler, adversarial Bull/Bear researchers) synthesize market intelligence through structured debate with merit-weighted consensus, apply institutional risk gating with portfolio-level constraints, execute trades via a multi-venue order router, and continuously self-improve through backtested rule generation and per-agent evolution logs — all with full MiFID II audit provenance, immutable decision cards, out-of-band drift auditing, persisted cycle snapshots, and a CLI replay interface for reviewing swarm cognition.

## Core Value

Institutional-quality trade signal generation through adversarial AI debate, with self-improving memory rules validated by backtesting, hard compliance guardrails, and immutable per-trade audit trails — from market data ingestion to PostgreSQL-persisted execution records.

## Current State (v1.5 shipped)

- **Runtime:** Python 3.12, LangGraph StateGraph, uv-managed
- **Infrastructure:** PostgreSQL 17 (AsyncPostgresSaver + Trade Warehouse + cycle_snapshots, port 5433)
- **LLM:** Google Gemini (`gemini-2.5-flash`) via `langchain-google-genai`
- **Tests:** 680+ passing, 0 failures
- **LOC:** ~33,098 Python
- **CLI:** `python -m src.main analyze BTC --mode paper` (end-to-end pipeline)
- **Replay:** `python -m src.main replay list|show|compare` (cycle review)

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
PostgreSQL (LangGraph checkpoints + audit_logs + trades + decision_cards + agent_merit_scores + ars_state + cycle_snapshots)

CycleRunner (external wrapper):
    Allocates cycle_id → runs graph → captures CycleSnapshot → persists to DB + filesystem
    → data/cycles/{padded_id}/snapshot.json

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

Replay CLI (read-only):
    list_cycles() → handle_list() → rich table with filters
    load_cycle() → handle_show() → step-through with merit bar charts
    handle_compare() → side-by-side delta with directional arrows
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

### Validated (v1.4)

- ✓ PERS-01: MOMENTUM (BullishResearcher) fully authored with distinct price/flow personality — v1.4 Phase 23
- ✓ PERS-02: CASSANDRA (BearishResearcher) fully authored with distinct tail-risk personality — v1.4 Phase 23
- ✓ PERS-03: SIGMA (QuantModeler) fully authored with distinct quantitative personality — v1.4 Phase 23
- ✓ PERS-04: GUARDIAN (RiskManager) fully authored with distinct risk-control personality — v1.4 Phase 23
- ✓ PERS-05: HEXACO-6 diversity profiles with minimum pairwise distance >1.0 — v1.4 Phase 23
- ✓ PERS-06: Functional YAML drift_guard blocks enabling ARS drift detection — v1.4 Phase 23
- ✓ CYCL-01: Pipeline runs persist complete cycle artifacts to numbered folders — v1.4 Phase 24
- ✓ CYCL-02: CycleSnapshot Pydantic model defines canonical artifact schema — v1.4 Phase 24
- ✓ CYCL-03: PostgreSQL cycle_snapshots table with monotonic numbering — v1.4 Phase 24
- ✓ CYCL-04: Cycle manifest includes timestamp, symbol, status, cycle_id — v1.4 Phase 24
- ✓ PIPE-01: Full pipeline from "Analyze BTC" to persisted decision card — v1.4 Phase 25
- ✓ PIPE-02: Data fetcher with caching/retry layer for yfinance resilience — v1.4 Phase 25
- ✓ PIPE-03: Messages list bounded to prevent checkpoint bloat — v1.4 Phase 25
- ✓ PIPE-04: Structured logging (structlog) for production debugging — v1.4 Phase 25
- ✓ PIPE-05: Soul cache hot-reload without process restart — v1.4 Phase 25
- ✓ REPL-01: List all cycles with summary metadata — v1.4 Phase 26
- ✓ REPL-02: Step through cycle (memos → debate → consensus → decision card) — v1.4 Phase 26
- ✓ REPL-03: Navigate between cycles (previous/next) — v1.4 Phase 26
- ✓ REPL-04: Merit weights visualized per cycle — v1.4 Phase 26
- ✓ REPL-05: Drift flags and ARS signals displayed — v1.4 Phase 26
- ✓ REPL-06: Compare two cycles side-by-side — v1.4 Phase 26

### Validated (v1.5)

- ✓ ENV-01: All environment dependencies fixed (ccxt, chromadb, pytest-asyncio); 13 broken tests restored — v1.5 Phase 27
- ✓ ENV-02: ChromaDB import/config issues fixed — v1.5 Phase 27
- ✓ ENV-03: pytest-asyncio mode auto configured — v1.5 Phase 27
- ✓ ENV-04: CI test suite green with 680 passing, 0 env failures — v1.5 Phase 27
- ✓ SEC-03: Gemini API circuit breaker with 3-state soft-fail pause — v1.5 Phase 28
- ✓ SEC-04: Circuit breaker returns empty dict in OPEN state — v1.5 Phase 28
- ✓ SEC-05: Circuit breaker integrated via single with_audit_logging wrapper — v1.5 Phase 28
- ✓ SEC-06: Circuit breaker state transitions logged via structlog — v1.5 Phase 28
- ✓ SEC-07: Circuit breaker configurable recovery_timeout — v1.5 Phase 28
- ✓ SOUL-09: PersonaScore 5D LLM-as-Judge fidelity evaluation (Consistency, Tone, Logic, Depth, Bias) — v1.5 Phase 29
- ✓ SOUL-10: PersonaScore as CycleRunner post-cycle hook (not graph node) — v1.5 Phase 29
- ✓ SOUL-11: PersonaScore evaluates 4 LLM agents (excludes RiskManager) — v1.5 Phase 29
- ✓ SOUL-12: PersonaScore persists to PostgreSQL — v1.5 Phase 29
- ✓ SOUL-13: PersonaScore structured output with 5 float dims + rationale — v1.5 Phase 29
- ✓ KAMI-05: KAMI fidelity consumes continuous PersonaScore composite (replaces binary 0/1) — v1.5 Phase 29
- ✓ KAMI-06: KAMI weights rebalanced (Accuracy 30%→8%, Fidelity 10%→32%) — v1.5 Phase 30
- ✓ KAMI-07: Weight transition via EMA absorption, no score reset — v1.5 Phase 30
- ✓ OBS-02: Per-agent token tracking with USD cost estimate — v1.5 Phase 30
- ✓ OBS-04: Token cost persisted to CycleSnapshot for replay — v1.5 Phase 30
- ✓ OBS-05: BudgetManager single authoritative token source — v1.5 Phase 30
- ✓ OBS-03: ChromaDB prune-to-Obsidian archival CLI — v1.5 Phase 31
- ✓ OBS-06: Prune respects active MemoryRegistry rules — v1.5 Phase 31
- ✓ OBS-07: Prune logs archived/deleted counts — v1.5 Phase 31

### Active (deferred / future)

- [ ] ANALY-05: RL optimization for order flow — v2.0
- [ ] MEM-07: Regime-aware vector memory for recognizing long-term historical parallels — v2.0
- [ ] ORCH-06: Multi-modal input support (chart image analysis) — v2.0
- [ ] OBS-01: Real-time WebSocket dashboard for live cycle monitoring

### Out of Scope

- High-frequency trading / sub-second reasoning loops (swarm is cognitive, not latency-optimized)
- Direct management of non-institutional retail accounts
- Real-time stop-loss auto-triggering (v1.1 gates at submission; live monitoring deferred)
- Emotional state model (valence/arousal, HMM) — no observable event hooks
- SoulZip relational USER.md history — requires accumulated cross-session peer data
- LLM-as-Judge for ARS drift detection — circular evaluation, adds API cost
- Global SOUL.md (shared swarm identity) — collapses adversarial diversity
- Real-time SOUL.md mutation mid-graph-run — lru_cache race condition
- HEXACO-6 automated diversity enforcement gate — deferred until persona fidelity pipeline exists
- Sentence-transformers for ARS — Counter cosine sufficient at current scale

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LangGraph StateGraph (migrated from custom) | Native fan-out/fan-in, checkpointing, graph visualization | ✓ Good |
| Adversarial debate (Bull vs Bear) before consensus | Forces stress-testing of every trade thesis | ✓ Good |
| Weighted consensus score (>0.6 threshold) | Quantifiable risk gate, tunable | ✓ Good |
| PostgreSQL AsyncPostgresSaver | Distributed checkpointing, crash recovery | ✓ Good |
| Hash-chained audit logs (SHA-256 + prev_hash) | Tamper-evident MiFID II compliance | ✓ Good |
| Google Gemini (gemini-2.5-flash) | Cost-effective, strong reasoning; lazy init required | ✓ Good |
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
| CycleSnapshot inline decision_card (no FK) | Simpler schema; cycle artifacts self-contained | ✓ Good |
| SERIAL PK with 'running' default for cycle_snapshots | Placeholder row pattern enables pre-allocation of cycle_id | ✓ Good |
| structlog ProcessorFormatter wraps stdlib loggers | Unified structured logging across project + third-party libs | ✓ Good |
| Disk cache write-always, read with QS_DEV_CACHE=1 | Production always fetches fresh; dev iteration uses cache | ✓ Good |
| DB-with-filesystem-fallback for cycle listing | Graceful degradation when PostgreSQL unavailable | ✓ Good |
| Console/stdout injection for CLI testability | Handlers accept optional console/stdout params for testing | ✓ Good |
| Separate CircuitBreaker for judge calls (threshold=3, cooldown=30s) | Isolates persona evaluation failures from graph circuit breaker | ✓ Good |
| PersonaScore excluded from audit hash chain | Infrastructure metadata, not MiFID II trade decisions | ✓ Good |
| Fallback spreads previous composite across 5 dims (or 0.5) | Evaluation failures degrade gracefully without crashing | ✓ Good |
| Stdlib-only CircuitBreaker (no pybreaker) | Consistent with Counter cosine precedent; no new deps | ✓ Good |
| Single integration point via with_audit_logging | All LLM nodes get circuit breaker without per-node wiring | ✓ Good |
| KAMI weight shift: Accuracy 30%→8%, Fidelity 10%→32% | Eliminates inert Accuracy placeholder; PersonaScore now dominant signal | ✓ Good |
| EMA absorption for weight transition (no score reset) | Preserves earned merit history across weight changes | ✓ Good |
| BudgetManager as single authoritative token source | Prevents double-counting between SwarmState reducer and budget tracking | ✓ Good |
| Archive-then-delete prune pattern with rule-aware cutoff | Conservative safety: never prunes vectors backing active memory rules | ✓ Good |
| pyyaml added for YAML frontmatter in prune output | Minimal new dep; necessary for Obsidian-compatible Markdown output | ✓ Good |

## Context

Shipped v1.5 on 2026-03-10 (5 phases, 10 plans, ~67 commits). Infrastructure milestone stabilized the foundation: all 680 tests pass green, Gemini API failures degrade gracefully via circuit breaker, PersonaScore 5D evaluation gives continuous fidelity signal to KAMI merit, token costs are tracked per agent per cycle, and old ChromaDB vectors can be archived to Obsidian Markdown.

Known tech debt: `merit_updater._get_weights()` fallback defaults stale (doesn't match rebalanced weights); `LangGraphOrchestrator.run_task_async()` missing `soft_failed_nodes: []` init; Nyquist VALIDATION.md partial/missing for phases 15-31.

---
*Last updated: 2026-03-10 after v1.5 milestone*
