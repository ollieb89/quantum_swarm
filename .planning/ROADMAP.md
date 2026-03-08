---
updated: '2026-03-08'
---

# Roadmap: Quantum Swarm

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-03-06)
- ✅ **v1.1 Self-Improvement** — Phases 5-7, 12 (shipped 2026-03-08)
- ✅ **v1.2 Risk Governance** — Phases 8-11, 13-14 (shipped 2026-03-08)
- 🚧 **v1.3 MBS Persona System** — Phases 15-19 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-4) — SHIPPED 2026-03-06</summary>

- [x] Phase 1: Foundation & Orchestration (L1) — completed 2026-03-06
- [x] Phase 2: Cognitive Analysis & Risk Gating (L2) — completed 2026-03-06
- [x] Phase 3: Market Execution & Data (L3) — completed 2026-03-06
- [x] Phase 4: Memory & Institutional Compliance — completed 2026-03-06

See: `.planning/milestones/v1.0-ROADMAP.md` for full archive

</details>

<details>
<summary>✅ v1.1 Self-Improvement (Phases 5-7, 12) — SHIPPED 2026-03-08</summary>

- [x] Phase 5: Quant Alpha Intelligence — completed 2026-03-06
- [x] Phase 6: Stop-Loss Enforcement — completed 2026-03-07
- [x] Phase 7: Self-Improvement Loop — completed 2026-03-07
- [x] Phase 12: Wire MEM-03 End-to-End — completed 2026-03-08

See: `.planning/milestones/v1.1-ROADMAP.md` for full archive

</details>

<details>
<summary>✅ v1.2 Risk Governance (Phases 8-11, 13-14) — SHIPPED 2026-03-08</summary>

- [x] Phase 8: Portfolio Risk Governance — completed 2026-03-07
- [x] Phase 9: Structured Memory Registry — completed 2026-03-07
- [x] Phase 10: Rule Validation Harness — completed 2026-03-08
- [x] Phase 11: Explainability & Decision Cards — completed 2026-03-08
- [x] Phase 13: Wire InstitutionalGuard — completed 2026-03-08
- [x] Phase 14: Fix MEM-06 Validation Gate Call Order — completed 2026-03-08

See: `.planning/milestones/v1.2-ROADMAP.md` for full archive

</details>

### 🚧 v1.3 MBS Persona System (In Progress)

**Milestone Goal:** Give every L2 agent a persistent, character-consistent identity via the Mind-Body-Soul architecture — covering foundation (SoulLoader, soul files, LangGraph wiring), merit-based reward scoring (KAMI), agent self-evolution (MEMORY.md + Agent Church), Theory of Mind debate layer, and ARS drift auditing.

- [x] **Phase 15: Soul Foundation** - SoulLoader, soul files, SwarmState wiring, audit exclusion, deterministic test suite (completed 2026-03-08)
- [x] **Phase 16: KAMI Merit Index** - Multi-dimensional merit formula, EMA decay, SwarmState + PostgreSQL persistence, DebateSynthesizer rewiring (completed 2026-03-08)
- [x] **Phase 17: MEMORY.md Evolution + Agent Church** - Structured self-reflection log, SOUL.md diff proposals, standalone Agent Church approval gate (completed 2026-03-08)
- [x] **Phase 18: Theory of Mind Soul-Sync** - Pre-debate soul handshake node, public soul summaries, Empathetic Refutation few-shots (completed 2026-03-08)
- [x] **Phase 19: ARS Drift Auditor** - Five drift metrics from MEMORY.md logs, evolution_suspended column, warm-up period, strict scope boundary (completed 2026-03-08)
- [ ] **Phase 20: Wire Drift Flags Pipeline** - Replace hardcoded DRIFT_FLAGS 'none' with evaluated drift flags from SOUL.md Drift Guard; unblock DRIFT_STREAK trigger and ARS drift_flag_frequency metric
- [ ] **Phase 21: Consume Soul-Sync Context in Debate** - Wire soul_sync_context into debate_synthesizer so peer soul summaries influence debate output
- [ ] **Phase 22: Failure Path KAMI + Memory Logging** - Route order_router failure path through merit_updater and memory_writer so failed cycles update KAMI scores and MEMORY.md

## Phase Details

### Phase 15: Soul Foundation
**Goal**: Every L2 agent has a persistent, file-backed identity that is injected into its LLM system prompt at execution time — without corrupting the MiFID II audit trail or the test suite
**Depends on**: Phase 14
**Requirements**: SOUL-01, SOUL-02, SOUL-03, SOUL-04, SOUL-05, SOUL-06, SOUL-07
**Success Criteria** (what must be TRUE):
  1. `SoulLoader.load_soul("macro_analyst")` returns a populated `AgentSoul` frozen dataclass with all five soul-file fields; a path-traversal attempt (e.g., `"../etc/passwd"`) raises `ValueError` without touching the filesystem
  2. `macro_analyst_node` writes `system_prompt` and `active_persona` into `SwarmState` before invoking the LLM, and neither field appears in any hash-chained audit record captured by `AuditLogger`
  3. `warmup_soul_cache()` completes without error with all five soul directories present (macro_analyst fully populated, four skeletons with minimum viable content)
  4. The deterministic test suite passes with zero LLM calls; an `autouse` fixture calls `load_soul.cache_clear()` before and after every test so no cached soul leaks between tests
**Plans**: 3 plans

Plans:
- [ ] 15-01-PLAN.md — SoulLoader module (AgentSoul dataclass, load_soul, warmup) + test scaffold (conftest, 3 test file stubs)
- [ ] 15-02-PLAN.md — All 15 soul files: AXIOM fully-populated + 4 skeleton directional stubs
- [ ] 15-03-PLAN.md — Integration wiring: SwarmState fields, audit exclusion, node injection, orchestrator warmup, full suite green

### Phase 16: KAMI Merit Index
**Goal**: Agent reliability is measured by a multi-dimensional merit score that decays with time, persists across sessions, and replaces the character-length proxy in DebateSynthesizer consensus weighting
**Depends on**: Phase 15
**Requirements**: KAMI-01, KAMI-02, KAMI-03, KAMI-04
**Success Criteria** (what must be TRUE):
  1. `compute_merit(agent_id, signals)` returns a float in `[0.1, 1.0]` using the formula `α·Accuracy + β·Recovery + γ·Consensus + δ·Fidelity` with weights read from `swarm_config.yaml`; a self-induced `INVALID_INPUT` error decreases the Recovery dimension rather than rewarding it
  2. An agent's merit score starts at 0.5 (cold start), updates via EMA with configurable λ (default 0.9), and persists to the `agent_merit_scores` PostgreSQL table after each cycle; the value loaded at session start matches the last persisted value
  3. `DebateSynthesizer` uses KAMI merit scores from `SwarmState["merit_scores"]` for consensus weighting; a skeleton agent with an empty `IDENTITY.md` receives `weight_multiplier=0.0` and cannot dominate consensus
  4. `SwarmState` carries `merit_scores: Dict[str, float]` as a dedicated field; the field survives a full LangGraph cycle without accumulation or duplication
**Plans**: 3 plans

Plans:
- [ ] 16-01-PLAN.md — kami.py pure arithmetic core (KAMIDimensions, compute_merit, apply_ema, signal helpers) + config section + DB table DDL + SwarmState field + TDD test suite
- [ ] 16-02-PLAN.md — merit_loader node (session-start DB read → state) + merit_updater node (post-execution EMA → DB persist) + orchestrator wiring
- [ ] 16-03-PLAN.md — DebateSynthesizer surgical rewire (len() → merit scores) + thesis_records stub + audit hash test + full phase verification

### Phase 17: MEMORY.md Evolution + Agent Church
**Goal**: Each agent maintains a capped structured self-reflection log after every task cycle, can propose edits to its own SOUL.md, and those proposals are reviewed by a standalone out-of-band Agent Church script before any soul file is mutated
**Depends on**: Phase 16
**Requirements**: EVOL-01, EVOL-02, EVOL-03
**Success Criteria** (what must be TRUE):
  1. After each task cycle, the active agent's `src/core/souls/{agent_id}/MEMORY.md` gains one new structured entry containing `[KAMI_DELTA:]` and `[MERIT_SCORE:]` machine-readable markers; the file is capped at 50 entries (oldest removed when limit is exceeded)
  2. An agent-proposed SOUL.md diff is written to `data/soul_proposals/{agent_id}.json` with the Pydantic-validated schema (agent_id, section, diff, rationale, proposed_at, status); the file is created atomically and does not block trade execution
  3. Running `python -m src.core.agent_church` reviews pending proposals, applies approved diffs and calls `load_soul.cache_clear()` + `warmup_soul_cache()`, logs rejected diffs with reason, and raises `RequiresHumanApproval` for any L1 Orchestrator self-proposal rather than auto-approving
**Plans**: 3 plans

Plans:
- [ ] 17-01-PLAN.md — memory_writer node: MEMORY.md file I/O, entry parse/cap, KAMI delta, phase17 config, RequiresHumanApproval
- [ ] 17-02-PLAN.md — SoulProposal Pydantic model, atomic write, proposal trigger logic (KAMI spike / drift streak / merit floor)
- [ ] 17-03-PLAN.md — Agent Church standalone script, H2 section replacement, cache refresh, orchestrator wiring

### Phase 18: Theory of Mind Soul-Sync
**Goal**: BullishResearcher and BearishResearcher exchange public soul summaries before the debate begins, enabling each agent to address its opponent's persona logic rather than arguing past it
**Depends on**: Phase 17
**Requirements**: TOM-01, TOM-02
**Success Criteria** (what must be TRUE):
  1. `soul_sync_handshake_node` runs as a barrier node before `DebateSynthesizer`; it reads peer soul summaries from `lru_cache` into `SwarmState["soul_sync_context"]` without making any LLM calls and without disrupting the parallel BullishResearcher/BearishResearcher fan-out topology
  2. `AgentSoul.public_soul_summary()` returns a truncated soul view that excludes Drift Guard triggers and Core Wounds; the excluded fields are not present in any audit record or debate message logged to `state["messages"]`
  3. Researcher `USER.md` files contain Empathetic Refutation few-shot examples that reference peer soul context, and the examples are loaded by `SoulLoader` as part of the agent's normal soul injection
**Plans**: 2 plans

Plans:
- [ ] 18-01-PLAN.md — Test scaffold (14 stubs, RED) + AgentSoul extension (users field, public_soul_summary, system_prompt) + SwarmState soul_sync_context field
- [ ] 18-02-PLAN.md — soul_sync_handshake_node implementation + orchestrator barrier rewiring + USER.md content files (MOMENTUM + CASSANDRA) + full suite GREEN

### Phase 19: ARS Drift Auditor
**Goal**: A scheduled out-of-band auditor detects ego-hijacking and persona drift across agent evolution logs, suspends evolution for flagged agents, and never gates trade execution
**Depends on**: Phase 17
**Requirements**: ARS-01, ARS-02
**Success Criteria** (what must be TRUE):
  1. `src/core/ars_auditor.py` computes all five drift metrics (Diff Rejection Rate, KAMI Dimension Variance, Alignment Section Mutation Count, Self-Reflection Sentiment Shift, Role Boundary Vocabulary Violations) from MEMORY.md evolution logs using stdlib regex and Counter cosine only; no LLM calls and no external dependencies beyond the project's existing `pyproject.toml`
  2. An agent that has accumulated 30+ evolution cycles and exceeds the drift threshold is flagged with an ops alert and has its `evolution_suspended` column set to `True` in the `agent_merit_scores` PostgreSQL table; no code path connects this suspension flag to `order_router_node` or `route_after_institutional_guard`
  3. Agents with fewer than 30 MEMORY.md entries do not trigger alerts regardless of metric values (warm-up period enforced); the auditor integrates with the existing systemd timer or responds to a `/ars:audit` CLI invocation
**Plans**: 2 plans

Plans:
- [ ] 19-01-PLAN.md — ARS auditor core: 5 drift metrics, ars_state DDL, ars: config, CLI interface, flag-then-suspend escalation, test suite
- [ ] 19-02-PLAN.md — Suspension gate in memory_writer_node, systemd timer, trade path isolation verification

### Phase 20: Wire Drift Flags Pipeline
**Goal**: DRIFT_FLAGS in MEMORY.md entries reflect actual drift evaluation from SOUL.md Drift Guard, unblocking the DRIFT_STREAK evolution trigger and the ARS drift_flag_frequency metric
**Depends on**: Phase 19
**Requirements**: EVOL-02, ARS-01
**Gap Closure:** Closes INT-01 (hardcoded DRIFT_FLAGS) + FLOW-01 (Drift Detection and Escalation) from v1.3 audit
**Success Criteria** (what must be TRUE):
  1. `memory_writer._build_entry()` evaluates the active agent's SOUL.md Drift Guard section against the current cycle's outputs and writes evaluated drift flags (not hardcoded 'none') to `[DRIFT_FLAGS:]` in the MEMORY.md entry
  2. The DRIFT_STREAK trigger in `SoulProposal` fires when 3+ consecutive entries contain non-empty drift flags
  3. ARS `drift_flag_frequency` metric returns a non-zero value for agents with drift flags present in their MEMORY.md entries
**Plans**: 2 plans

Plans:
- [ ] 20-01-PLAN.md — DriftRule dataclass, YAML parser, evaluate_drift function, AgentSoul extension, AXIOM SOUL.md rules, test suite
- [ ] 20-02-PLAN.md — Wire drift evaluation into memory_writer._build_entry(), DRIFT_STREAK + ARS integration verification, full regression

### Phase 21: Consume Soul-Sync Context in Debate
**Goal**: debate_synthesizer reads soul_sync_context from SwarmState so peer soul summaries actually influence debate synthesis, completing the Theory of Mind data flow
**Depends on**: Phase 18
**Requirements**: TOM-01
**Gap Closure:** Closes INT-02 (soul_sync_context orphaned output) from v1.3 audit
**Success Criteria** (what must be TRUE):
  1. `debate_synthesizer` reads `SwarmState["soul_sync_context"]` and incorporates peer soul summaries into its prompt construction
  2. Debate output demonstrably differs when soul_sync_context is present vs absent (testable via mock comparison)

### Phase 22: Failure Path KAMI + Memory Logging
**Goal**: Failed order_router cycles still flow through merit_updater and memory_writer so agent learning and KAMI scoring capture failure signals
**Depends on**: Phase 17
**Requirements**: KAMI-03, EVOL-01
**Gap Closure:** Closes INT-03 (failure path bypass) from v1.3 audit
**Success Criteria** (what must be TRUE):
  1. When `order_router_node` returns a failure, the execution path still routes through `decision_card_writer → merit_updater → memory_writer` before reaching `trade_logger`
  2. The Recovery dimension in KAMI receives a penalty signal for failed cycles
  3. MEMORY.md gains a structured entry for failed cycles (with appropriate failure markers)

## Progress

**Execution Order:** 15 → 16 → 17 → 18 → 19

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
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
| 14. Fix MEM-06 Validation Gate | v1.2 | 2/2 | Complete | 2026-03-08 |
| 15. Soul Foundation | v1.3 | 3/3 | Complete | 2026-03-08 |
| 16. KAMI Merit Index | 3/3 | Complete    | 2026-03-08 | - |
| 17. MEMORY.md Evolution + Agent Church | 3/3 | Complete    | 2026-03-08 | - |
| 18. Theory of Mind Soul-Sync | 2/2 | Complete    | 2026-03-08 | - |
| 19. ARS Drift Auditor | 2/2 | Complete    | 2026-03-08 | - |
| 20. Wire Drift Flags Pipeline | 1/2 | In Progress|  | - |
| 21. Consume Soul-Sync Context in Debate | v1.3 | 0/0 | Planned | - |
| 22. Failure Path KAMI + Memory Logging | v1.3 | 0/0 | Planned | - |
