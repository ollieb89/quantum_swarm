---
updated: '2026-03-09'
---

# Roadmap: Quantum Swarm

## Milestones

- ✅ **v1.0 MVP** — Phases 1-4 (shipped 2026-03-06)
- ✅ **v1.1 Self-Improvement** — Phases 5-7, 12 (shipped 2026-03-08)
- ✅ **v1.2 Risk Governance** — Phases 8-11, 13-14 (shipped 2026-03-08)
- ✅ **v1.3 MBS Persona System** — Phases 15-22 (shipped 2026-03-08)
- **v1.4 Beta: Observable Swarm** — Phases 23-26 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-4) — SHIPPED 2026-03-06</summary>

- [x] Phase 1: Foundation & Orchestration (L1) — completed 2026-03-06
- [x] Phase 2: Cognitive Analysis & Risk Gating (L2) — completed 2026-03-06
- [x] Phase 3: Market Execution & Data (L3) — completed 2026-03-06
- [x] Phase 4: Memory & Institutional Compliance — completed 2026-03-06

See: `.planning/milestones/v1.0-ROADMAP.md` for full archive

</details>

<details>
<summary>v1.1 Self-Improvement (Phases 5-7, 12) — SHIPPED 2026-03-08</summary>

- [x] Phase 5: Quant Alpha Intelligence — completed 2026-03-06
- [x] Phase 6: Stop-Loss Enforcement — completed 2026-03-07
- [x] Phase 7: Self-Improvement Loop — completed 2026-03-07
- [x] Phase 12: Wire MEM-03 End-to-End — completed 2026-03-08

See: `.planning/milestones/v1.1-ROADMAP.md` for full archive

</details>

<details>
<summary>v1.2 Risk Governance (Phases 8-11, 13-14) — SHIPPED 2026-03-08</summary>

- [x] Phase 8: Portfolio Risk Governance — completed 2026-03-07
- [x] Phase 9: Structured Memory Registry — completed 2026-03-07
- [x] Phase 10: Rule Validation Harness — completed 2026-03-08
- [x] Phase 11: Explainability & Decision Cards — completed 2026-03-08
- [x] Phase 13: Wire InstitutionalGuard — completed 2026-03-08
- [x] Phase 14: Fix MEM-06 Validation Gate — completed 2026-03-08

See: `.planning/milestones/v1.2-ROADMAP.md` for full archive

</details>

<details>
<summary>v1.3 MBS Persona System (Phases 15-22) — SHIPPED 2026-03-08</summary>

- [x] Phase 15: Soul Foundation — completed 2026-03-08
- [x] Phase 16: KAMI Merit Index — completed 2026-03-08
- [x] Phase 17: MEMORY.md Evolution + Agent Church — completed 2026-03-08
- [x] Phase 18: Theory of Mind Soul-Sync — completed 2026-03-08
- [x] Phase 19: ARS Drift Auditor — completed 2026-03-08
- [x] Phase 20: Wire Drift Flags Pipeline — completed 2026-03-08
- [x] Phase 21: Consume Soul-Sync Context in Debate — completed 2026-03-08
- [x] Phase 22: Failure Path KAMI + Memory Logging — completed 2026-03-08

See: `.planning/milestones/v1.3-ROADMAP.md` for full archive

</details>

### v1.4 Beta: Observable Swarm (In Progress)

**Milestone Goal:** Make the institution observable — fully populate all personas, run end-to-end against real market data, persist cycles, and replay the swarm's thinking.

- [ ] **Phase 23: Full Persona Population** - Populate all 4 skeleton agents with HEXACO-6 diverse personalities and drift_guard YAML
- [ ] **Phase 24: Cycle Persistence** - CycleSnapshot schema, PostgreSQL cycle_snapshots table, CycleRunner wrapper
- [ ] **Phase 25: End-to-End Pipeline Runner** - Production runner with retry, caching, structured logging, message trimming
- [ ] **Phase 26: Replay CLI** - Read-only CLI for listing, stepping through, and comparing persisted cycles

## Phase Details

### Phase 23: Full Persona Population
**Goal**: Every agent in the swarm has a distinct, fully authored personality that produces differentiated reasoning
**Depends on**: Nothing (content authoring, zero code dependencies)
**Requirements**: PERS-01, PERS-02, PERS-03, PERS-04, PERS-05, PERS-06
**Success Criteria** (what must be TRUE):
  1. User can run any L2 agent and observe reasoning that reflects its unique personality (MOMENTUM talks price action and flow, CASSANDRA talks tail risk and fragility, SIGMA talks quantitative models, GUARDIAN talks risk limits and exposure)
  2. Each persona's SOUL.md contains a valid YAML drift_guard block that ARS drift detection can parse and evaluate
  3. HEXACO-6 profiles exist for all 5 agents with pairwise Euclidean distance exceeding 1.0 on the normalized 0.0-1.0 scale
  4. warmup_soul_cache() loads all 5 agents without errors at graph creation time
**Plans**: 4 plans

Plans:
- [ ] 23-01-PLAN.md — Test scaffolding + ROADMAP/REQUIREMENTS threshold update
- [ ] 23-02-PLAN.md — Author MOMENTUM and CASSANDRA personas
- [ ] 23-03-PLAN.md — Author SIGMA and GUARDIAN personas
- [ ] 23-04-PLAN.md — HEXACO-6 profiles for all 5 agents + final validation

### Phase 24: Cycle Persistence
**Goal**: Every pipeline run produces a complete, queryable cycle snapshot stored outside SwarmState
**Depends on**: Phase 23 (meaningful agent output needed for snapshot content)
**Requirements**: CYCL-01, CYCL-02, CYCL-03, CYCL-04
**Success Criteria** (what must be TRUE):
  1. After a pipeline run completes, a numbered cycle folder contains agent memos, debate transcript, consensus result, merit scores, and decision card
  2. CycleSnapshot Pydantic model validates all cycle artifacts with no Optional fields left as None for completed cycles
  3. PostgreSQL cycle_snapshots table stores cycle metadata queryable by cycle_id, symbol, timestamp, and status
  4. Cycle data lives in dedicated storage (not in SwarmState) so LangGraph checkpoints do not bloat across runs
**Plans**: TBD

Plans:
- [ ] 24-01: TBD
- [ ] 24-02: TBD

### Phase 25: End-to-End Pipeline Runner
**Goal**: User can run the full swarm against real market data and get a persisted, observable cycle
**Depends on**: Phase 24 (CycleRunner and snapshot persistence must exist)
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05
**Success Criteria** (what must be TRUE):
  1. User can run a command like "Analyze BTC" and the pipeline executes from intent classification through to a persisted decision card without manual intervention
  2. Data fetcher retries on yfinance rate limits with exponential backoff and falls back to cached data during development
  3. Messages list is trimmed between cycles so checkpoint size stays bounded regardless of how many cycles have run
  4. Pipeline execution emits structured JSON logs (structlog) that capture each node entry/exit with timing for production debugging
  5. Soul cache can be reloaded without restarting the process so persona edits take effect during development iteration
**Plans**: TBD

Plans:
- [ ] 25-01: TBD
- [ ] 25-02: TBD

### Phase 26: Replay CLI
**Goal**: User can review and compare past swarm decisions through a terminal interface
**Depends on**: Phase 25 (real cycle data must exist in cycle_snapshots)
**Requirements**: REPL-01, REPL-02, REPL-03, REPL-04, REPL-05, REPL-06
**Success Criteria** (what must be TRUE):
  1. User can list all cycles and see summary metadata (cycle_id, symbol, timestamp, status, consensus score)
  2. User can step through a single cycle in execution order: agent memos, then debate, then consensus, then decision card
  3. User can view merit weights per cycle showing each agent's KAMI-derived influence on the consensus
  4. User can view drift flags and ARS suspension status when reviewing a cycle
  5. User can compare two cycles side-by-side to see how agent reasoning, merit weights, and consensus shifted between runs
**Plans**: TBD

Plans:
- [ ] 26-01: TBD
- [ ] 26-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 23 > 24 > 25 > 26

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation & Orchestration | v1.0 | -- | Complete | 2026-03-06 |
| 2. Cognitive Analysis & Risk Gating | v1.0 | -- | Complete | 2026-03-06 |
| 3. Market Execution & Data | v1.0 | -- | Complete | 2026-03-06 |
| 4. Memory & Institutional Compliance | v1.0 | -- | Complete | 2026-03-06 |
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
| 16. KAMI Merit Index | v1.3 | 3/3 | Complete | 2026-03-08 |
| 17. MEMORY.md Evolution + Agent Church | v1.3 | 3/3 | Complete | 2026-03-08 |
| 18. Theory of Mind Soul-Sync | v1.3 | 2/2 | Complete | 2026-03-08 |
| 19. ARS Drift Auditor | v1.3 | 2/2 | Complete | 2026-03-08 |
| 20. Wire Drift Flags Pipeline | v1.3 | 2/2 | Complete | 2026-03-08 |
| 21. Consume Soul-Sync Context in Debate | v1.3 | 1/1 | Complete | 2026-03-08 |
| 22. Failure Path KAMI + Memory Logging | v1.3 | 2/2 | Complete | 2026-03-08 |
| 23. Full Persona Population | 1/4 | In Progress|  | - |
| 24. Cycle Persistence | v1.4 | 0/? | Not started | - |
| 25. End-to-End Pipeline Runner | v1.4 | 0/? | Not started | - |
| 26. Replay CLI | v1.4 | 0/? | Not started | - |
