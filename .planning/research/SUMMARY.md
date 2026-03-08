# Project Research Summary

**Project:** Quantum Swarm v1.3 — MBS Persona System
**Domain:** Multi-agent LLM persona persistence, merit-based reward, and drift governance for a financial analysis swarm
**Researched:** 2026-03-08
**Confidence:** HIGH

## Executive Summary

Quantum Swarm v1.3 adds a full Multi-agent Belief System (MBS) persona layer to an existing 260+ test LangGraph financial swarm that is already in production use. The research is unusually high-confidence because all four areas were grounded against live production code rather than hypotheticals: the entire stack is already installed (no new dependencies required whatsoever), all four KAMI signal sources exist in current SwarmState fields, the graph topology is known, and the pitfalls were identified from concrete interactions between the new design and the existing audit logger, DebateSynthesizer, and lru_cache mechanics.

The recommended approach follows a strict four-tier build order that matches the internal dependency graph of the features. Tier 1 (SoulLoader foundation) must be complete and green before any Tier 2 work begins — there is no safe way to reorder this. The highest-value change in the milestone is the DebateSynthesizer KAMI-weighted consensus rewiring (Tier 2a), which replaces the current character-length quality proxy with a multi-dimensional merit signal. This is also the highest-risk change because it modifies a node with currently passing tests. The ARS Drift Auditor (Tier 2d) must run out-of-band as a scheduled process and must never gate trade execution — conflating governance scope with the trading circuit breaker is the most operationally dangerous mistake identified.

The primary risks are not architectural novelty but integration precision: system prompt injection into the wrong SwarmState location corrupts the hash-chained MiFID II audit trail; lru_cache process-global state will contaminate the test suite without an autouse fixture; and EMA cold-start values of 0.5 will silently dilute established agent weights if skeleton soul directories are activated before their content is populated. Every one of these risks has a specific, low-cost prevention pattern that must be applied in Tier 1 before any later-tier work lands.

---

## Key Findings

### Recommended Stack

No new dependencies are required. Every feature in the MBS persona system is achievable with the libraries already in `pyproject.toml` and Python 3.12 stdlib. The implementation surface is: `functools.lru_cache` + `dataclasses.dataclass(frozen=True)` for the SoulLoader; `numpy` (already installed) for EMA arithmetic; `psycopg` (already installed, async) for KAMI PostgreSQL persistence; `re`, `pathlib`, `collections.deque` (all stdlib) for the ARS drift auditor; and `difflib.unified_diff` (stdlib) for Agent Church diff generation.

The one deliberate choice to hold: `sentence-transformers` is already in `pyproject.toml` but should not be used for ARS drift detection at v1.3 scale — it adds 200-500ms latency per audit run and 30s+ cold start. `collections.Counter` cosine similarity over MEMORY.md word frequencies is sufficient for coarse drift scoring. This can be revisited at v2.0 if finer-grained drift detection is needed.

**Core technologies:**
- Python 3.12 + `functools.lru_cache` + `dataclasses`: SoulLoader with immutable `AgentSoul` frozen dataclass — required for hashability and concurrent read safety
- `numpy.clip` + scalar arithmetic: EMA decay formula for KAMI Merit Index — already a project dependency, covers all cases
- `psycopg` (async): KAMI score persistence to `agent_merit_scores` PostgreSQL table — existing pattern, raw psycopg3 INSERT, no ORM
- LangGraph `>=0.2.0` (existing): Soul-Sync conditional node, Agent Church routing branch, `workflow.branches` + `workflow.edges` inspection
- `difflib.unified_diff` (stdlib): Agent Church SOUL.md diff generation for human-readable review

**Critical version note:** `asyncio.run()` inside node functions is a known project-breaking pattern (caused MEM-06 defect). All soul file I/O inside async contexts must use synchronous `Path.read_text()` — soul files are small and sync reads are appropriate.

### Expected Features

The feature set is organized across four tiers with strict prerequisite dependencies.

**Must have — Tier 1 (table stakes, v1.3.0):**
- `SoulLoader` with `lru_cache`, path-traversal guard (`../`, `/abs`, `\back` cases), `AgentSoul` frozen dataclass — foundation for everything
- 5-file soul directory per agent (SOUL.md, IDENTITY.md, AGENTS.md, USER.md, MEMORY.md) — `macro_analyst` fully populated; 4 others as populated skeletons
- SwarmState fields: `active_persona`, `system_prompt` (NOT in `messages` reducer) — injection surface for all Tier 2
- `macro_analyst_node` soul injection — reference implementation and test anchor
- Drift Guard embedded in each agent's IDENTITY.md — cheapest persona stability mechanism, runs inside the model's reasoning loop
- Deterministic test suite with zero LLM calls — CI gate for the entire persona layer

**Must have — Tier 2a (KAMI Merit Index, v1.3.1):**
- Multi-dimensional merit formula: `Merit = α·Accuracy + β·Recovery + γ·Consensus + δ·Fidelity` (default weights: α=0.30, β=0.35, γ=0.25, δ=0.10)
- EMA decay with configurable λ (default 0.9 for financial domain), cold start 0.5, bounds [0.1, 1.0]
- `merit_scores: Dict[str, float]` in SwarmState (prerequisite — must land before DebateSynthesizer rewiring)
- DebateSynthesizer KAMI-weighted consensus (breaking change — replaces character-length proxy)
- PostgreSQL persistence for merit scores across sessions

**Should have — Tier 2b-2d (v1.3.2+):**
- Per-agent MEMORY.md structured log append (post-task, capped at 50 entries, with machine-readable markers)
- SOUL.md diff proposal format + Agent Church approval gate (standalone script, not LangGraph node) + `load_soul.cache_clear()` on approval
- Soul-Sync Handshake via `soul_sync_node` before researcher fan-out (reads from lru_cache, writes `peer_soul_contexts` to state)
- Empathetic Refutation few-shot examples in researcher system prompts (prompt engineering, no code)
- ARS Drift Auditor (5 observable metrics, scheduled process, evolution-only scope)

**Defer to v2+:**
- Emotional state model (valence/arousal, HMM-based) — no existing observable event hooks in v1.2 swarm
- SoulZip relational USER.md history — requires accumulated MEMORY.md cross-session peer data to populate
- PersonaScore 5D LLM-as-Judge fidelity evaluation — cost/benefit decision needed; Fidelity KAMI dimension covers the key signal
- HEXACO-6 automated diversity enforcement gate — deferred until all 4 researcher personas are fully populated

**Confirmed anti-features (do not build):**
- LLM-as-Judge for ARS drift detection — circular evaluation, shared base model blind spots, adds API cost to background audit
- Global SOUL.md (one shared swarm identity) — collapses adversarial diversity, defeats the debate architecture
- Real-time SOUL.md mutation mid-graph-run — lru_cache race condition with fan-out concurrent reads
- `merit_scores` stored in `messages` list — `operator.add` reducer causes unbounded accumulation

### Architecture Approach

The MBS system adds components in layers on top of the existing graph topology without restructuring it. The v1.2 graph remains intact; new nodes are inserted at specific points, and two nodes are modified. The SoulLoader is not a graph node — it is called inside each L2 node as the first operation, leveraging the lru_cache to make this effectively free after warmup. The DebateSynthesizer node is modified to use KAMI weights instead of character length. One new pre-debate node (`soul_sync_handshake`) is inserted between the researcher fan-in and the synthesizer. One new intent branch (`soul_evolution -> agent_church_node`) is added to the classify_intent router. The ARS Auditor and Agent Church operate entirely out-of-band.

**Major components:**
1. `src/core/soul_loader.py` — Load, cache, and invalidate AgentSoul from filesystem; shared primitive for all tiers
2. `src/core/souls/[agent_id]/` — Per-agent soul directories (5 files each); immutable at runtime, mutable only via Agent Church
3. `src/core/merit_index.py` — KAMI formula, EMA decay, dimension weights, bounds; computes per-agent merit deltas post-cycle
4. `src/core/ars_auditor.py` — Scheduled out-of-band drift detection from MEMORY.md logs; governs evolution only, never trade execution
5. `soul_sync_handshake` node — Pre-debate barrier node that reads peer soul summaries (public-facing only) into state before fan-out
6. `agent_church_node` — L1 routing branch for `soul_evolution` intent; LLM-as-Judge for SOUL.md diff proposals; out-of-band, not inline
7. `merit_update_node` — Post-cycle merit computation and PostgreSQL persistence; wired after `write_trade_memory`
8. Modified `src/graph/debate.py` — DebateSynthesizer reads `merit_scores` from state for weighted consensus (breaking change)
9. Modified `src/graph/state.py` — Four new fields: `active_persona`, `system_prompt`, `merit_scores`, `soul_sync_context`

**Key patterns to follow:**
- Lazy soul system prompt composition: each L2 node composes `system_prompt` via `soul.system_prompt_injection` property; never stored in `state["messages"]`
- Dual-layer persistence: `merit_scores` in SwarmState (live session) + `agent_merit_scores` PostgreSQL table (durable across sessions)
- Out-of-band governance: Agent Church runs as standalone script analogous to `PerformanceReviewAgent`; ARS Auditor runs on existing systemd timer
- Cache invalidation protocol: `load_soul.cache_clear()` + `warmup_soul_cache()` immediately after any approved SOUL.md diff; never during a graph run

### Critical Pitfalls

The top pitfalls, ordered by severity and phase impact:

1. **System prompt injected into `state["messages"]`** — `messages` uses `operator.add` reducer; soul content accumulates across nodes, corrupts `DebateSynthesizer` message extraction, and pollutes the hash-chained MiFID II audit record. Prevention: `system_prompt` goes exclusively in its dedicated SwarmState field; assembled inline at LLM call time; never written to `messages`. Test assertion required: `soul.system_prompt_injection not in [m.get("content","") for m in state["messages"]]`.

2. **`lru_cache` process-global state contaminates test suite** — Soul content cached across tests causes order-dependent failures in the 260+ test suite. Prevention: `autouse` pytest fixture calling `load_soul.cache_clear()` before and after every test; must be added to `tests/core/conftest.py` before any soul test is written.

3. **`system_prompt` field included in hash-chained audit records** — `AuditLogger.log_transition()` captures all SwarmState fields; a 500-token soul injection across 10+ node transitions adds ~5,000 tokens per task cycle to PostgreSQL JSONB and `audit.jsonl`. Once in production, this cannot be retroactively removed without violating audit immutability. Prevention: add `AUDIT_EXCLUDED_FIELDS = {"system_prompt", "active_persona", "peer_soul_contexts"}` before wiring `macro_analyst_node` into the audit-logged graph.

4. **KAMI Recovery metric gameable via intentional failure farming** — Recovery is weighted highest (beta=0.35) but all recoveries are treated equally regardless of whether the failure was self-induced (`INVALID_INPUT`) or external (`INSUFFICIENT_DATA`). Prevention: error classification must feed KAMI from day one; self-induced failures penalize rather than reward; cap Recovery credits at 2 per debate round.

5. **EMA cold start 0.5 dilutes established agent weights when skeleton agents are activated** — Skeleton agents with empty soul files receive Merit=0.5 and immediately influence DebateSynthesizer weighting. Prevention: gate KAMI weighting on `soul.identity != ""`; skeleton agents receive `weight_multiplier = 0.0` until IDENTITY.md is populated with minimum required fields.

6. **Agent Church as blocking LangGraph node creates deadlock and conflict-of-interest** — L1 Orchestrator cannot be its own governance arbiter; inline approval blocks trade cycles. Prevention: implement Agent Church as a standalone script (`python -m src.core.agent_church`); L1 self-proposals require `RequiresHumanApproval` exception; proposals accumulate without blocking trade execution.

7. **ARS drift false positives block production trading if scope is not strictly limited** — ARS suspension applied to the trade execution path (e.g., via `route_after_institutional_guard`) stops live trades when ARS fires on a new agent with no baseline. Prevention: ARS governs MEMORY.md evolution writes only; no code path connects ARS suspension to `order_router_node` or `route_after_institutional_guard`; warm-up period of 30 cycles before alerts fire.

---

## Implications for Roadmap

Based on research, the dependency graph is deterministic. There is only one valid build order. The phase structure below reflects the actual prerequisite chain identified across all four research files.

### Phase 1: Soul Foundation (Tier 1)

**Rationale:** SoulLoader and AgentSoul are the shared primitive for every subsequent phase. KAMI Fidelity dimension reads AGENTS.md via AgentSoul. Soul-Sync reads SOUL.md via AgentSoul. ARS reads MEMORY.md from soul directories. Nothing in Tier 2 is implementable without this. This phase has zero dependency on runtime behavior — all tests are deterministic string assertions with no LLM calls.

**Delivers:** `src/core/soul_loader.py`, all 5 soul directories with `macro_analyst` fully populated and 4 skeletons, SwarmState fields `active_persona` + `system_prompt`, `macro_analyst_node` soul injection, Drift Guard in all IDENTITY.md files, deterministic test suite.

**Addresses:** SOUL-01 through SOUL-07; all 4 remaining L2 nodes get the same injection pattern after the reference implementation is validated.

**Avoids:** Pitfalls 1, 2, 3, 11 — all Tier 1 pitfalls must be prevented here before any Tier 2 work begins. The audit exclusion list must be defined in this phase even though `system_prompt` is populated in Tier 1 data — the exclusion must exist before the field exists in a graph-run state snapshot.

**Research flag:** Standard patterns. No additional research needed. All implementation details are fully specified in persona_plan.md and SOT_PERSONA_REWARD_SYSTEM.md.

### Phase 2: KAMI Merit Index (Tier 2a)

**Rationale:** Merit weighting of DebateSynthesizer is the highest-value change in the milestone — it directly improves trade signal quality by replacing a character-length proxy with actual agent reliability signal. It depends on Tier 1 soul files (for the Fidelity dimension's AGENTS.md output contract check) and PostgreSQL (already available). The `merit_scores` SwarmState field must land before the DebateSynthesizer rewiring because the synthesizer will KeyError without it.

**Delivers:** `src/core/merit_index.py`, `agent_merit_scores` PostgreSQL table, `merit_scores` in SwarmState, DebateSynthesizer KAMI-weighted consensus, `merit_update_node` wired after `write_trade_memory`, PostgreSQL persistence with session load at `run_task_async()` start.

**Uses:** `numpy.clip` for EMA arithmetic (existing), `psycopg` async for persistence (existing), LangGraph conditional edges for merit update routing.

**Implements:** KAMI-01 through KAMI-04; `merit_index.py` architecture component.

**Avoids:** Pitfalls 4 and 5 — error classification taxonomy and skeleton agent weight gating must be implemented here, not deferred.

**Research flag:** Standard patterns. EMA formula is straightforward; dual-layer state+PostgreSQL persistence mirrors the existing `institutional_guard` portfolio heat pattern.

### Phase 3: MEMORY.md Evolution and Agent Church (Tier 2b)

**Rationale:** Per-agent MEMORY.md structured logs are the prerequisite for both the Agent Church (which reads proposals from MEMORY.md) and the ARS Auditor (which reads evolution history from MEMORY.md). The self-reflection content is also more meaningful with Merit delta context available, making Tier 2a a natural upstream dependency. The Agent Church must be implemented as a standalone script in this phase — not a LangGraph node — to prevent the conflict-of-interest and blocking pitfalls.

**Delivers:** Per-agent MEMORY.md structured log append (post-task, async, capped at 50 entries, machine-readable `[KAMI_DELTA:]` markers), SOUL.md diff proposal format in `data/soul_proposals/{agent_id}.json`, `agent_church_node` LangGraph routing branch for `soul_evolution` intent, standalone `agent_church.py` script with `RequiresHumanApproval` guard for L1 self-proposals, `load_soul.cache_clear()` + `warmup_soul_cache()` on approved diffs.

**Avoids:** Pitfalls 6 and 7 — Agent Church as blocking node must be avoided; MEMORY.md unbounded growth must be controlled before EVOL-01 starts writing.

**Research flag:** Moderate complexity on the Agent Church out-of-band pattern and the structured proposal JSON lifecycle. The `MemoryRegistry` atomic save pattern (already in codebase) should be reused for soul proposals. May benefit from a short research-phase to confirm the JSON proposal lifecycle against the existing registry pattern before implementation.

### Phase 4: Theory of Mind Soul-Sync (Tier 2c)

**Rationale:** Soul-Sync depends on Tier 1 soul files (reads SOUL.md summaries via AgentSoul) and benefits from populated Merit scores in the soul summary (makes the opponent's reliability visible). It requires graph topology surgery — replacing the direct `[bullish_researcher, bearish_researcher] -> debate_synthesizer` edge with a `soul_sync_handshake` pre-debate barrier node. Doing this after Merit (Tier 2a) and Evolution (Tier 2b) ensures the soul content and scores are stable before the handshake reads them.

**Delivers:** `soul_sync_context: Optional[dict]` SwarmState field, `soul_sync_handshake_node` (deterministic, no LLM calls, reads from lru_cache), `public_soul_summary()` method on AgentSoul (excludes Core Wounds and Drift Guard triggers from peer view), updated researcher `USER.md` files with peer soul summaries for Empathetic Refutation, graph edge update replacing direct fan-in with handshake node.

**Avoids:** Pitfalls 8 and 9 — soul_sync_handshake as a pre-debate barrier preserves parallel fan-out; `public_soul_summary()` prevents Core Wounds leakage into debate history and audit records.

**Research flag:** Standard patterns once `public_soul_summary()` API is defined. The graph topology change (replacing one edge with a node + two edges) is a routine LangGraph operation.

### Phase 5: ARS Drift Auditor (Tier 2d)

**Rationale:** ARS produces meaningful signal only after MEMORY.md evolution logs have accumulated across multiple sessions (Tier 2b). It reads `[KAMI_DELTA:]` markers from structured logs — if those markers are not present or the format is inconsistent, all five drift metrics degrade to noise. Building this last ensures there is data to audit. The warm-up period logic (30 cycles before alerts fire) is critical and must be in the ARS spec before a line of code is written.

**Delivers:** `src/core/ars_auditor.py` with five observable drift metrics (Diff Rejection Rate, KAMI Dimension Variance, Persona Section Mutation Count, Self-Reflection Sentiment Shift, Role Boundary Vocabulary), `evolution_suspended` column in `agent_merit_scores` PostgreSQL table, evolution suspension gate in MEMORY.md write logic, integration with existing systemd timer or `/ars:audit` CLI command, warm-up period with data-driven threshold derivation (mean + 2 std dev, not hardcoded constant).

**Avoids:** Pitfall 10 — warm-up period and strict scope boundary (evolution-only, never trade gate) must be built-in from the start; ARS suspension flag must have no code path to `order_router_node` or `route_after_institutional_guard`.

**Research flag:** Low complexity for the drift metric computation (pure stdlib). The per-agent cross-domain vocabulary lists (for Role Boundary Vocabulary metric) will need to be defined by domain knowledge rather than library research.

### Phase Ordering Rationale

- Tier 1 before everything: SoulLoader and AgentSoul are the shared runtime primitive; no Tier 2 component can be tested or implemented without them.
- Tier 2a before 2b-2d: Merit scores must populate SwarmState before the evolution loop writes Merit deltas to MEMORY.md (Tier 2b self-reflection includes Merit context) and before Soul-Sync includes Merit in peer summaries (Tier 2c).
- Tier 2b before 2c and 2d: MEMORY.md structured logs are the data source for both the ARS Auditor (Tier 2d) and the Agent Church's USER.md peer context accumulation.
- Tier 2c before 2d is flexible — these two tiers have no direct dependency. If ARS baseline accumulation needs more time, Tier 2c can ship first. The order above (2c then 2d) is preferred because the Soul-Sync graph topology change is reversible; the ARS audit database schema additions are harder to undo.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Agent Church):** The out-of-band proposal lifecycle should be validated against the existing `MemoryRegistry` atomic save pattern before implementation. Confirm whether `data/soul_proposals/` JSON files or MEMORY.md append-only format is the right machine-readable medium for proposals.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Soul Foundation):** Fully specified in persona_plan.md and SOT_PERSONA_REWARD_SYSTEM.md. lru_cache + frozen dataclass is textbook Python.
- **Phase 2 (KAMI Merit Index):** EMA arithmetic is standard; dual-layer state/PostgreSQL mirrors existing patterns in the codebase.
- **Phase 4 (Theory of Mind):** Pre-debate barrier node is a standard LangGraph fan-in pattern; public_soul_summary() API is straightforward once scope is defined.
- **Phase 5 (ARS Auditor):** All five metrics are pure stdlib regex + arithmetic; no library research required.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All capabilities verified against live `pyproject.toml`; no new dependencies; version constraints checked against existing installs |
| Features | HIGH | Grounded in `persona_plan.md` and `SOT_PERSONA_REWARD_SYSTEM.md` (primary sources of truth); four claudedocs deep-dive research files; live codebase inspection of `debate.py` and `state.py` |
| Architecture | HIGH | Derived from live production code (`orchestrator.py`, `state.py`, `debate.py`); integration questions answered against actual graph topology with concrete code patterns |
| Pitfalls | HIGH | Grounded in concrete interactions between new design and live system components (audit_logger.py, DebateSynthesizer, operator.add reducer, lru_cache lifecycle); not generic LLM pitfalls |

**Overall confidence:** HIGH

### Gaps to Address

- **KAMI lambda parameter tuning:** The recommended lambda=0.9 (slow decay for financial domain) has not been validated against actual weekly trade cycle frequency. With sparse weekly updates, lambda=0.9 may cause excessive decay between sessions — the performance trap research flags lambda > 0.7 as risky at weekly cadence. Validate lambda calibration in Tier 2a against actual session frequency before shipping.
- **Soul content for 4 skeleton agents:** The research specifies content requirements (HEXACO-6 personality diversity, opposing trait profiles for BullishResearcher vs BearishResearcher) but does not draft the actual IDENTITY.md, SOUL.md, AGENTS.md files for the 4 non-macro agents. These must be authored during Tier 1 implementation, not deferred to later tiers, because `warmup_soul_cache()` will error on malformed files.
- **KAMI weight defaults (alpha=0.30, beta=0.35, gamma=0.25, delta=0.10):** These weights are sourced from EMNLP 2025 and UCL MARL research for general multi-agent settings. They have not been validated for the specific financial swarm context. The Recovery weight (beta=0.35) may be too high given the gaming risk identified in Pitfall 4. Treat as configurable from day one and plan to tune after the first 10-20 live cycles.
- **Agent Church LLM-as-Judge prompt:** The Church uses Gemini Flash to evaluate soul evolution proposals against alignment constraints. The evaluation prompt itself is not specified in any research file. This will need to be drafted carefully during Tier 2b implementation — a poorly constrained judge prompt is worse than no judge at all.

---

## Sources

### Primary (HIGH confidence)
- `.planning/PHASES/persona_plan.md` — SoulLoader API, 5-file soul directory format, SwarmState fields, node injection pattern, test strategy
- `docs/SOT_PERSONA_REWARD_SYSTEM.md` — MBS architecture, KAMI formula and components, ToM/ARS specification, Agent Church governance
- `src/graph/orchestrator.py` (v1.2 live code) — Graph topology, node registration, routing functions, `with_audit_logging` wrapper
- `src/graph/state.py` (v1.2 live code) — SwarmState schema, reducer patterns, existing fields
- `src/graph/debate.py` (v1.2 live code) — DebateSynthesizer internals, message extraction, character-length scoring
- `src/core/audit_logger.py` (v1.2 live code) — State snapshot inclusion logic; grounding for Pitfall 11
- `pyproject.toml` (current) — Verified installed dependency set; confirms zero new dependencies
- Python 3.12 docs — `functools.lru_cache`, `dataclasses`, `pathlib`, `difflib`, `collections`

### Secondary (MEDIUM confidence)
- `claudedocs/research_soul_rewards_deep_dive_20260305.md` — KAMI naming, 4-dimensional merit formula, PersonaScore 5D, HEXACO-6 rationale
- `claudedocs/research_personas_merit_20260305.md` — Merit-based routing, ARS security requirements, adversarial RLAF approach
- `claudedocs/research_agent_persona_soul_20260305.md` — MBS architecture overview, SoulZip, Theory of Mind pattern
- PersonaGym (arxiv:2407.18416) — Drift Guard design, PersonaScore 5 evaluation dimensions
- BIG5-CHAT (ACL 2025) — Prompting insufficiency for deep persona traits; Drift Guard necessity
- EMNLP 2025 "Reward-driven Self-organizing LLM-based Multi-Agent System" — Multi-dimensional reward rationale
- UCL RLC 2024 Trust-based Consensus MARL — Binary consensus reward formula
- Reflexion (2023) — Self-reflection as downstream performance improver; basis for EVOL-01

### Tertiary (LOW confidence)
- arxiv:2511.08042 (real KAMI paper) — Confirms naming conflict with project's internal use of "KAMI"; the underlying mechanism is valid regardless of naming
- arxiv:2511.20657 (affective state survey) — Emotional state model rationale; deferred to v2.0

---
*Research completed: 2026-03-08*
*Ready for roadmap: yes*
