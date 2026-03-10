# Phase 29: PersonaScore 5D + KAMI Fidelity Wiring - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Each agent's persona fidelity is quantitatively evaluated every cycle via LLM-as-Judge, producing a 5-dimensional PersonaScore (Consistency, Tone, Logic, Depth, Bias) with rationale. The composite score replaces the current binary 0/1 fidelity signal in KAMI. Evaluation runs as a CycleRunner post-cycle hook, outside graph topology and audit hash chain.

</domain>

<decisions>
## Implementation Decisions

### Evaluation prompt & rubric
- LLM-as-Judge receives **full soul files** (IDENTITY.md + SOUL.md + AGENTS.md) as persona reference
- Judge compares agent's **primary output field** against soul definition (AXIOM->macro_report, SIGMA->quant_proposal, MOMENTUM->bullish_thesis, CASSANDRA->bearish_thesis)
- 5 dimensions scored as **0.0-1.0 floats**: Consistency, Tone, Logic, Depth, Bias
- **One LLM call per agent** (4 calls total), run in **parallel** via asyncio.gather()
- Composite PersonaScore = **simple average** of the 5 dimension floats
- Only **4 LLM agents** evaluated: AXIOM, MOMENTUM, CASSANDRA, SIGMA (GUARDIAN excluded — rules-only, no LLM output)

### Score persistence & schema
- **New `persona_scores` PostgreSQL table** (not extending agent_merit_scores)
- Columns: id, cycle_id, soul_handle, consistency, tone, logic, depth, bias, composite, rationale (TEXT), scored_at
- **Full history** retained — one row per agent per cycle (4 rows/cycle), enabling trend analysis
- **Rationale string stored** alongside scores for debugging and replay
- PersonaScore results **embedded in CycleSnapshot** (filesystem JSON) for offline replay without DB

### Post-cycle hook design
- Fires **after snapshot persist** — cycle data is safe before evaluation begins
- 4 evaluations run in **parallel** (asyncio.gather)
- After evaluation completes, results written to DB and snapshot file updated
- **Skip for failed cycles** (no agent output to evaluate), **evaluate for rejected cycles** (agent memos exist, fidelity still meaningful)

### Failure & fallback behavior
- On LLM evaluation failure: **fall back to previous cycle's PersonaScore composite** for that agent
- **Reuse Phase 28 circuit breaker** — if circuit is open, skip evaluation entirely (fallback to previous score)
- **Persist partial results** — if some agents succeed and others fail, store successful scores and use fallback for failures; log which agents fell back
- Never crash or block cycle completion due to evaluation failure

### Claude's Discretion
- Exact LLM prompt template and rubric wording for the 5 dimensions
- PersonaScore Pydantic model design
- How snapshot file is updated after post-cycle evaluation (rewrite vs append)
- DB migration script structure
- How `_extract_fidelity_signal()` in kami.py is rewired to read PersonaScore composite

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for LLM-as-Judge evaluation patterns.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/core/kami.py`: `_extract_fidelity_signal()` — currently binary, needs rewiring to read PersonaScore composite from previous cycle
- `src/core/kami.py`: `apply_ema()` — EMA update function, will be used with new continuous fidelity signal
- `src/core/cycle_runner.py`: `CycleRunner.run_cycle()` — post-cycle hook attaches here after `_write_snapshot_file()` and `_update_cycle_row()`
- `src/core/cycle_snapshot.py`: `CycleSnapshot` Pydantic model — needs `persona_scores` field added
- `src/core/soul_loader.py`: `load_soul()` with `@lru_cache` — provides soul files for judge prompt
- `src/core/circuit_breaker.py`: Circuit breaker from Phase 28 — reuse for evaluation LLM calls

### Established Patterns
- **Lazy LLM init**: `_llm = None; def _get_llm()` pattern required for module-level instances (Gemini validates API key at instantiation)
- **Synchronous file I/O in nodes**: asyncio.run() inside nodes is project-breaking
- **DB-first persistence**: merit_updater persists to DB before updating state (consistency pattern)
- **AUDIT_EXCLUDED_FIELDS**: PersonaScore should be excluded from MiFID II hash chain (infrastructure metadata)

### Integration Points
- `src/graph/nodes/merit_updater.py`: `_extract_fidelity_signal()` call site — currently called with agent_id, will need to read from DB/state instead
- `config/swarm_config.yaml`: KAMI config section — delta weight (currently 0.10) consumed by merit_updater
- `src/core/persistence.py`: DB pool access pattern — `ensure_pool_open()` for PostgreSQL operations
- `src/core/db.py`: Connection pool management

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 29-personascore-5d-kami-fidelity-wiring*
*Context gathered: 2026-03-09*
