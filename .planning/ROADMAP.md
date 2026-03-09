---
updated: '2026-03-09'
---

# Roadmap: Quantum Swarm

## Milestones

- ✅ **v1.0 MVP** -- Phases 1-4 (shipped 2026-03-06)
- ✅ **v1.1 Self-Improvement** -- Phases 5-7, 12 (shipped 2026-03-08)
- ✅ **v1.2 Risk Governance** -- Phases 8-11, 13-14 (shipped 2026-03-08)
- ✅ **v1.3 MBS Persona System** -- Phases 15-22 (shipped 2026-03-08)
- ✅ **v1.4 Beta: Observable Swarm** -- Phases 23-26 (shipped 2026-03-09)
- **v1.5 Reliable Infrastructure** -- Phases 27-31 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-4) -- SHIPPED 2026-03-06</summary>

- [x] Phase 1: Foundation & Orchestration (L1) -- completed 2026-03-06
- [x] Phase 2: Cognitive Analysis & Risk Gating (L2) -- completed 2026-03-06
- [x] Phase 3: Market Execution & Data (L3) -- completed 2026-03-06
- [x] Phase 4: Memory & Institutional Compliance -- completed 2026-03-06

See: `.planning/milestones/v1.0-ROADMAP.md` for full archive

</details>

<details>
<summary>v1.1 Self-Improvement (Phases 5-7, 12) -- SHIPPED 2026-03-08</summary>

- [x] Phase 5: Quant Alpha Intelligence -- completed 2026-03-06
- [x] Phase 6: Stop-Loss Enforcement -- completed 2026-03-07
- [x] Phase 7: Self-Improvement Loop -- completed 2026-03-07
- [x] Phase 12: Wire MEM-03 End-to-End -- completed 2026-03-08

See: `.planning/milestones/v1.1-ROADMAP.md` for full archive

</details>

<details>
<summary>v1.2 Risk Governance (Phases 8-11, 13-14) -- SHIPPED 2026-03-08</summary>

- [x] Phase 8: Portfolio Risk Governance -- completed 2026-03-07
- [x] Phase 9: Structured Memory Registry -- completed 2026-03-07
- [x] Phase 10: Rule Validation Harness -- completed 2026-03-08
- [x] Phase 11: Explainability & Decision Cards -- completed 2026-03-08
- [x] Phase 13: Wire InstitutionalGuard -- completed 2026-03-08
- [x] Phase 14: Fix MEM-06 Validation Gate -- completed 2026-03-08

See: `.planning/milestones/v1.2-ROADMAP.md` for full archive

</details>

<details>
<summary>v1.3 MBS Persona System (Phases 15-22) -- SHIPPED 2026-03-08</summary>

- [x] Phase 15: Soul Foundation -- completed 2026-03-08
- [x] Phase 16: KAMI Merit Index -- completed 2026-03-08
- [x] Phase 17: MEMORY.md Evolution + Agent Church -- completed 2026-03-08
- [x] Phase 18: Theory of Mind Soul-Sync -- completed 2026-03-08
- [x] Phase 19: ARS Drift Auditor -- completed 2026-03-08
- [x] Phase 20: Wire Drift Flags Pipeline -- completed 2026-03-08
- [x] Phase 21: Consume Soul-Sync Context in Debate -- completed 2026-03-08
- [x] Phase 22: Failure Path KAMI + Memory Logging -- completed 2026-03-08

See: `.planning/milestones/v1.3-ROADMAP.md` for full archive

</details>

<details>
<summary>v1.4 Beta: Observable Swarm (Phases 23-26) -- SHIPPED 2026-03-09</summary>

- [x] Phase 23: Full Persona Population (4/4 plans) -- completed 2026-03-09
- [x] Phase 24: Cycle Persistence (2/2 plans) -- completed 2026-03-09
- [x] Phase 25: End-to-End Pipeline Runner (2/2 plans) -- completed 2026-03-09
- [x] Phase 26: Replay CLI (2/2 plans) -- completed 2026-03-09

See: `.planning/milestones/v1.4-ROADMAP.md` for full archive

</details>

### v1.5 Reliable Infrastructure (In Progress)

**Milestone Goal:** Stabilize the foundation -- fix broken deps, add Gemini API resilience, introduce 5D persona fidelity evaluation, rebalance KAMI merit, track token costs, and archive ChromaDB to Obsidian.

- [x] **Phase 27: Environment Stabilization** - Restore all broken dependencies and green-light 13 failing tests (completed 2026-03-09)
- [x] **Phase 28: Gemini API Circuit Breaker** - Safety net for LLM call failures with 3-state soft-fail pause (completed 2026-03-09)
- [x] **Phase 29: PersonaScore 5D + KAMI Fidelity Wiring** - LLM-as-Judge persona evaluation with continuous fidelity signal (completed 2026-03-09)
- [ ] **Phase 30: KAMI Weight Rebalance + Token Tracking** - Merit weight redistribution and per-cycle cost observability
- [ ] **Phase 31: ChromaDB Prune-to-Obsidian** - Archive old vectors to Markdown with rule-aware safety

## Phase Details

### Phase 27: Environment Stabilization
**Goal**: All tests pass with zero environment-related failures
**Depends on**: Nothing (first phase of v1.5)
**Requirements**: ENV-01, ENV-02, ENV-03, ENV-04
**Success Criteria** (what must be TRUE):
  1. Running `pytest` produces 0 failures from ccxt import errors (lighter_client resolved or ccxt pinned)
  2. Running `pytest` produces 0 failures from chromadb import or configuration errors
  3. Running `pytest` produces 0 failures from pytest-asyncio mode configuration issues
  4. CI test suite reports 13 previously-broken tests now passing
**Plans:** 2/2 plans complete
Plans:
- [ ] 27-01-PLAN.md -- Pin exact dependency versions, restore ccxt lazy init, fix Pydantic ConfigDict
- [ ] 27-02-PLAN.md -- Strip redundant @pytest.mark.asyncio decorators, verify full suite green

### Phase 28: Gemini API Circuit Breaker
**Goal**: LLM call failures degrade gracefully instead of crashing graph runs
**Depends on**: Phase 27
**Requirements**: SEC-03, SEC-04, SEC-05, SEC-06, SEC-07
**Success Criteria** (what must be TRUE):
  1. When Gemini returns 429/503/timeout errors repeatedly, the circuit opens and subsequent calls return empty dict immediately (no crash, no budget burn)
  2. After a configurable cooldown period, the circuit automatically probes with a single call and recovers to closed state on success
  3. Circuit breaker state transitions (closed/open/half-open) appear in structlog output
  4. Circuit breaker integrates through a single wrapper point (enhanced `with_audit_logging`) -- no per-node wiring needed
**Plans:** 2/2 plans complete
Plans:
- [ ] 28-01-PLAN.md -- Core CircuitBreaker class with state machine, error classification, and unit tests
- [ ] 28-02-PLAN.md -- Wire into with_audit_logging, extend SwarmState/CycleSnapshot, integration tests

### Phase 29: PersonaScore 5D + KAMI Fidelity Wiring
**Goal**: Each agent's persona fidelity is quantitatively evaluated every cycle and feeds into KAMI merit
**Depends on**: Phase 28
**Requirements**: SOUL-09, SOUL-10, SOUL-11, SOUL-12, SOUL-13, KAMI-05
**Success Criteria** (what must be TRUE):
  1. After a cycle completes, all 4 LLM agents (AXIOM, MOMENTUM, CASSANDRA, SIGMA) receive a PersonaScore with 5 float dimensions (Consistency, Tone, Logic, Depth, Bias) and a rationale string
  2. PersonaScore evaluation runs as a CycleRunner post-cycle hook (not visible in the graph topology or audit hash chain)
  3. PersonaScore results persist to PostgreSQL and are queryable for historical analysis
  4. KAMI fidelity dimension reads the previous cycle's PersonaScore composite instead of binary 0/1
  5. A cycle that fails PersonaScore evaluation (LLM error) falls back to previous score without crashing
**Plans:** 2/2 plans complete
Plans:
- [ ] 29-01-PLAN.md -- Core PersonaScore module: Pydantic models, LLM-as-Judge evaluator, DB schema, tests
- [ ] 29-02-PLAN.md -- Wire into CycleRunner post-cycle hook, rewire KAMI fidelity signal

### Phase 30: KAMI Weight Rebalance + Token Tracking
**Goal**: Merit weights reflect actual signal quality and every cycle reports its token cost
**Depends on**: Phase 29
**Requirements**: KAMI-06, KAMI-07, OBS-02, OBS-04, OBS-05
**Success Criteria** (what must be TRUE):
  1. KAMI DEFAULT_WEIGHTS show Accuracy at ~8% and Fidelity at ~32% (no longer 30% inert weight)
  2. Weight transition preserves existing merit scores via EMA absorption (no score reset)
  3. After a cycle completes, CycleSnapshot contains per-agent token usage (prompt + completion) with USD cost estimate
  4. Token cost data is visible in the replay CLI when showing a cycle
  5. BudgetManager is the single authoritative source for token counts (no SwarmState reducer double-counting)
**Plans**: TBD

### Phase 31: ChromaDB Prune-to-Obsidian
**Goal**: Old ChromaDB vectors are safely archived to searchable Obsidian Markdown and pruned from the database
**Depends on**: Phase 27
**Requirements**: OBS-03, OBS-06, OBS-07
**Success Criteria** (what must be TRUE):
  1. Running `python -m src.main prune --dry-run` shows what would be archived/deleted without modifying data
  2. Running `python -m src.main prune` archives ChromaDB entries older than the configured threshold to Obsidian-compatible Markdown files with YAML frontmatter
  3. Prune operation never deletes vectors backing active MemoryRegistry rules (rule-aware cutoff)
  4. Prune operation logs archived and deleted counts via structlog
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 27 -> 28 -> 29 -> 30 -> 31

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
| 23. Full Persona Population | v1.4 | 4/4 | Complete | 2026-03-09 |
| 24. Cycle Persistence | v1.4 | 2/2 | Complete | 2026-03-09 |
| 25. End-to-End Pipeline Runner | v1.4 | 2/2 | Complete | 2026-03-09 |
| 26. Replay CLI | v1.4 | 2/2 | Complete | 2026-03-09 |
| 27. Environment Stabilization | v1.5 | 2/2 | Complete | 2026-03-09 |
| 28. Gemini API Circuit Breaker | v1.5 | 2/2 | Complete | 2026-03-09 |
| 29. PersonaScore 5D + KAMI Fidelity | 2/2 | Complete    | 2026-03-09 | - |
| 30. KAMI Weight Rebalance + Token Tracking | v1.5 | 0/? | Not started | - |
| 31. ChromaDB Prune-to-Obsidian | v1.5 | 0/? | Not started | - |
