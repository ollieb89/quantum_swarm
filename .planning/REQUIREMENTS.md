# Requirements: Quantum Swarm

**Defined:** 2026-03-08
**Core Value:** Institutional-quality trade signal generation through adversarial AI debate, with self-improving memory rules validated by backtesting, hard compliance guardrails, and immutable per-trade audit trails

---

## v1.3 Requirements

Requirements for the MBS Persona System milestone. Each maps to roadmap phases starting at Phase 15.

### Soul Foundation (Tier 1)

- [x] **SOUL-01**: System loads an agent's soul from filesystem files with path-traversal guard and `lru_cache` so identity is consistent across all node invocations within a session
- [x] **SOUL-02**: `macro_analyst` has fully-populated IDENTITY.md (Drift Guard), SOUL.md (core beliefs + values), and AGENTS.md (output contract + workflow rules)
- [x] **SOUL-03**: Four skeleton soul dirs exist with minimum viable content (bullish_researcher, bearish_researcher, quant_modeler, risk_manager) so warmup_soul_cache() completes without error
- [x] **SOUL-04**: SwarmState carries `active_persona` and `system_prompt` as dedicated fields (not in `messages` list) so soul content never enters the `operator.add` message accumulator
- [x] **SOUL-05**: All five L2 nodes inject their agent soul into `system_prompt` before LLM execution; `system_prompt` and `active_persona` are excluded from hash-chained audit records
- [x] **SOUL-06**: Test suite has an autouse fixture that calls `load_soul.cache_clear()` before and after every test so cached souls do not contaminate test isolation
- [x] **SOUL-07**: Deterministic test suite covering SoulLoader unit, persona content fidelity, and macro_analyst_node integration — zero LLM calls; all tests are string assertions against static files

### KAMI Merit Index (Tier 2a)

- [x] **KAMI-01**: Agent merit is computed using a multi-dimensional formula (Accuracy + Recovery + Consensus + Fidelity) with configurable weights (default α=0.30, β=0.35, γ=0.25, δ=0.10) stored in swarm_config.yaml
- [x] **KAMI-02**: Merit score uses EMA decay (configurable λ, default 0.9), cold start 0.5, and is bounded to [0.1, 1.0]; self-induced tool failures (INVALID_INPUT) penalise rather than reward Recovery dimension
- [x] **KAMI-03**: `merit_scores: Dict[str, float]` field exists in SwarmState; scores are loaded from `agent_merit_scores` PostgreSQL table at session start and persisted after each cycle
- [x] **KAMI-04**: DebateSynthesizer uses KAMI merit scores for consensus weighting (replaces character-length proxy); skeleton agents with unpopulated IDENTITY.md receive weight_multiplier=0.0

### MEMORY.md Evolution + Agent Church (Tier 2b)

- [x] **EVOL-01**: After each task cycle, each active agent appends a structured self-reflection entry to its `src/core/souls/{agent_id}/MEMORY.md` (capped at 50 entries; includes `[KAMI_DELTA:]` and `[MERIT_SCORE:]` machine-readable markers)
- [x] **EVOL-02**: Agent can propose a SOUL.md diff stored as `data/soul_proposals/{agent_id}.json` (Pydantic-validated schema: agent_id, section, diff, rationale, proposed_at, status)
- [x] **EVOL-03**: Standalone `agent_church.py` script (not a LangGraph node) reviews proposals, applies approved diffs with `load_soul.cache_clear()` + `warmup_soul_cache()`, and raises RequiresHumanApproval for any L1 Orchestrator self-proposals

### Theory of Mind Soul-Sync (Tier 2c)

- [x] **TOM-01**: `soul_sync_handshake_node` runs before DebateSynthesizer as a barrier node; reads peer soul summaries from lru_cache into `soul_sync_context` SwarmState field; preserves parallel researcher fan-out topology
- [x] **TOM-02**: AgentSoul exposes `public_soul_summary()` method (excludes Drift Guard triggers and Core Wounds from peer view); researcher USER.md files contain Empathetic Refutation few-shot examples

### ARS Drift Auditor (Tier 2d)

- [x] **ARS-01**: Standalone ARS Auditor computes five observable drift metrics from MEMORY.md evolution logs (Diff Rejection Rate, KAMI Dimension Variance, Alignment Section Mutation Count, Self-Reflection Sentiment Shift, Role Boundary Vocabulary Violations) using stdlib regex + Counter cosine; integrates with existing systemd timer or `/ars:audit` CLI; 30-cycle warm-up before alerts fire
- [x] **ARS-02**: `evolution_suspended` boolean column in `agent_merit_scores` PostgreSQL table; ARS suspension gates MEMORY.md evolution writes only — no code path connects ARS suspension to order_router_node or route_after_institutional_guard

---

## v2+ Requirements

Deferred to future milestones. Tracked but not in v1.3 roadmap.

### Persona (future)

- **SOUL-08**: All four skeleton agent soul dirs fully populated with HEXACO-6 diverse personality profiles
- **SOUL-09**: PersonaScore 5D LLM-as-Judge fidelity evaluation pipeline

### Intelligence (future)

- **ANALY-05**: RL optimization for order flow
- **MEM-07**: Regime-aware vector memory for recognizing long-term historical parallels
- **ORCH-06**: Multi-modal input support (chart image analysis)

### Security (future)

- **SEC-03**: System-wide circuit breakers for API degradation or anomalous strategy behavior

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Emotional state model (valence/arousal, HMM) | No observable event hooks in v1.2 swarm; requires new data collection infrastructure |
| SoulZip relational USER.md history | Requires accumulated MEMORY.md cross-session peer data not yet available |
| LLM-as-Judge for ARS drift detection | Circular evaluation (shared base model blind spots); adds API cost to background audit |
| Global SOUL.md (shared swarm identity) | Collapses adversarial diversity; defeats the debate architecture |
| Real-time SOUL.md mutation mid-graph-run | lru_cache race condition with fan-out concurrent reads |
| HEXACO-6 automated diversity enforcement gate | Deferred until all 4 researcher personas are fully populated |
| Sentence-transformers for ARS | Cold-start latency not justified at v1.3 scale; Counter cosine sufficient |

---

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SOUL-01 | Phase 15 | Complete |
| SOUL-02 | Phase 15 | Complete |
| SOUL-03 | Phase 15 | Complete |
| SOUL-04 | Phase 15 | Complete |
| SOUL-05 | Phase 15 | Complete |
| SOUL-06 | Phase 15 | Complete |
| SOUL-07 | Phase 15 | Complete |
| KAMI-01 | Phase 16 | Complete |
| KAMI-02 | Phase 16 | Complete |
| KAMI-03 | Phase 16 | Complete |
| KAMI-04 | Phase 16 | Complete |
| EVOL-01 | Phase 17 | Complete |
| EVOL-02 | Phase 17 | Complete |
| EVOL-03 | Phase 17 | Complete |
| TOM-01 | Phase 18 | Complete |
| TOM-02 | Phase 18 | Complete |
| ARS-01 | Phase 19 | Complete |
| ARS-02 | Phase 19 | Complete |
| EVOL-02 | Phase 20 | Complete |
| ARS-01 | Phase 20 | Complete |
| TOM-01 | Phase 21 | Pending |
| KAMI-03 | Phase 22 | Pending |
| EVOL-01 | Phase 22 | Pending |

**Coverage:**
- v1.3 requirements: 18 total
- Mapped to phases: 18
- Gap closure phases: 3 (Phases 20-22, addressing 5 integration/flow gaps)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-08*
*Last updated: 2026-03-08 after roadmap creation (traceability confirmed)*
