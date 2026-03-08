# Architecture Patterns: MBS Persona System Integration

**Domain:** Multi-Agent Financial Swarm — Persona / Identity Layer
**Researched:** 2026-03-08
**Project:** Quantum Swarm v1.3

---

## Scope

This document answers five concrete integration questions for the v1.3 MBS Persona System milestone, then derives a build order that respects both the existing graph topology and the internal dependencies of the new components.

---

## Existing Graph Topology (v1.2 Baseline)

```
classify_intent
    │ (conditional: macro | quant | end)
    ▼
macro_analyst ──────────┐
quant_modeler ──────────┤  fan-out
                        ▼
          bullish_researcher ──┐
          bearish_researcher ──┘  fan-in
                        ▼
              debate_synthesizer
                        │
              write_research_memory
                        │ (conditional: >0.6 | hold)
                        ▼
                  risk_manager
                        │
                  claw_guard
                        │
              institutional_guard
                        │ (conditional: approved | rejected→synthesize)
                        ▼
                  data_fetcher
                  write_external_memory
                  knowledge_base
                  backtester
                  order_router
                        │ (conditional: success→decision_card | trade_logger)
                  decision_card_writer
                  trade_logger
                  write_trade_memory
                        │
                    synthesize ──▶ END
```

**Key constraints on integration:**
- All nodes are registered via `workflow.add_node()` in `create_orchestrator_graph()`.
- `with_audit_logging()` wraps every node. Any new node must also be wrapped.
- `SwarmState` is a `TypedDict`. New fields require explicit additions; no dynamic keys.
- The `DebateSynthesizer` is a pure aggregation function with no LLM calls. Its scoring formula (character-length proxy) is the current weighted consensus mechanism.
- Soul files live on disk. `lru_cache` on `load_soul()` means soul data is process-stable after first read.

---

## Integration Question Answers

### Q1: Where does SoulLoader call live — before node, inside node, or graph-level middleware?

**Answer: Inside each L2 node, as the first operation before LLM invocation.**

Rationale grounded in the existing graph:

- LangGraph has no middleware layer between the graph runtime and individual node functions. The `with_audit_logging()` wrapper is the closest analogue, but it is a node-level decorator, not a graph-level intercept. There is no pre-node hook exposed in the LangGraph `StateGraph` API that would allow a single "SoulLoader node" to inject into the state before every other node fires.
- A dedicated `soul_loader` node inserted before each L2 node would double the edge count in the fan-out section and require a new conditional edge for each agent path. That complexity has no benefit: `load_soul()` is cached via `lru_cache` and runs in microseconds after warmup.
- The correct pattern, as specified in `persona_plan.md`, is: the L2 node calls `load_soul(agent_id)` at its top, writes `active_persona` and `system_prompt` to the returned state partial, then uses `system_prompt` to prefix the LLM call. This keeps the graph topology unchanged while ensuring the soul is always current for the executing node.
- `warmup_soul_cache()` is called once in `create_orchestrator_graph()` before `workflow.compile()`. This makes the first `load_soul()` call inside any node effectively free.

**Modification required:** Each L2 node function (`macro_analyst_node`, `quant_modeler_node`, `bullish_researcher_node`, `bearish_researcher_node`) gains a two-line preamble. No new graph edges.

```
graph init:  warmup_soul_cache()
node start:  soul = load_soul("macro_analyst")
             state_update["active_persona"] = soul.agent_id
             state_update["system_prompt"]  = soul.system_prompt_injection
node LLM:    messages = [{"role": "system", "content": state["system_prompt"]}, *state["messages"]]
```

### Q2: How should KAMI scores be stored — SwarmState field, PostgreSQL table, or both?

**Answer: Both, with SwarmState as the live session surface and PostgreSQL as the durable ledger.**

Rationale:

- **SwarmState field (`merit_scores: dict[str, float]`):** Scores must be readable by `DebateSynthesizer` during the same graph invocation that generates them. LangGraph's fan-in pattern means `debate_synthesizer` executes after both researchers complete — it can read `merit_scores` from state to weight their contributions. Storing only in PostgreSQL would require an async DB read inside `DebateSynthesizer`, making a currently LLM-free aggregation node dependent on I/O.
- **PostgreSQL table (`agent_merit_scores`):** Merit scores are cumulative EMA values that persist across sessions. They cannot live only in ephemeral state — the next graph invocation would cold-start every agent at 0.5. A dedicated table (columns: `agent_id`, `score`, `accuracy`, `recovery`, `consensus`, `fidelity`, `updated_at`) is the correct durability layer.
- **Load pattern:** At graph init (or inside `classify_intent_node`), load current merit scores from PostgreSQL into `initial_state["merit_scores"]`. The `DebateSynthesizer` reads them. After the cycle completes, a `merit_update_node` (or the existing `write_trade_memory` hook) writes updated scores back to PostgreSQL.
- **Confidence:** HIGH — this dual-layer pattern mirrors how `institutional_guard` handles portfolio heat: computed in-state, persisted to PostgreSQL audit record.

**SwarmState additions:**

```python
merit_scores: Optional[dict]   # {"macro_analyst": 0.72, "bullish_researcher": 0.65, ...}
```

**PostgreSQL table (new, in existing schema):**

```sql
CREATE TABLE agent_merit_scores (
    agent_id        TEXT PRIMARY KEY,
    score           FLOAT NOT NULL DEFAULT 0.5,
    accuracy        FLOAT NOT NULL DEFAULT 0.5,
    recovery        FLOAT NOT NULL DEFAULT 0.5,
    consensus       FLOAT NOT NULL DEFAULT 0.5,
    fidelity        FLOAT NOT NULL DEFAULT 0.5,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### Q3: Where does Theory of Mind Soul-Sync Handshake fit — before DebateSynthesizer or as a new node between L2 fan-out and DebateSynthesizer?

**Answer: As a new node inserted between the fan-in join and `debate_synthesizer`, replacing the direct `[bullish_researcher, bearish_researcher] → debate_synthesizer` edge.**

Rationale:

- The Soul-Sync Handshake (TOM-01) requires that both researcher nodes have already completed — it reads each agent's `SOUL.md` summary and appends it to `debate_history` so that `DebateSynthesizer` (and downstream agents) can see the persona context behind each position. This is a fan-in dependency, so it must execute after both researchers.
- The Empathetic Refutation step (TOM-02) does not require an additional node — it is prompt content injected into the researcher nodes' system prompts via the soul's `USER.md` peer-modelling section. When `bullish_researcher_node` loads its soul, `USER.md` will contain a truncated summary of the bearish researcher's soul. This means TOM-02 is delivered via the same SoulLoader mechanism as Tier 1, without graph topology changes.
- Inserting `soul_sync_handshake` as an explicit node (rather than folding the logic into `DebateSynthesizer`) keeps `DebateSynthesizer` pure-aggregation. It has no LLM calls today; mixing soul-exchange logic into it would add conditional logic and make it harder to test in isolation.

**Graph change:**

```
Before:  [bullish_researcher, bearish_researcher] → debate_synthesizer
After:   [bullish_researcher, bearish_researcher] → soul_sync_handshake → debate_synthesizer
```

`soul_sync_handshake` is a deterministic node (no LLM calls): it loads the SOUL.md summaries for both researchers via `load_soul()`, appends them to `debate_history`, and writes an optional `soul_sync_context` field to state for downstream visibility.

### Q4: Where does ARS Auditor run — inline in graph or as a separate scheduled process?

**Answer: As a separate scheduled process, not inline in the graph.**

Rationale:

- ARS drift detection (ARS-01, ARS-02) operates by comparing an agent's current SOUL.md and MEMORY.md evolution log against a baseline. This is a longitudinal analysis that spans multiple sessions, not a single-run computation. It has no natural position in the single-task graph because it requires historical data that accumulates across invocations.
- The existing self-improvement pipeline (PerformanceReviewAgent, RuleGenerator, RuleValidator) runs on the same weekly-scheduled pattern and is invoked via the `/review` command, not via graph nodes. ARS Auditor follows the same pattern: a standalone Python module (`src/core/ars_auditor.py`) run by the existing systemd timer or triggered manually.
- Inline placement would add latency to every graph execution for a check whose value is proportional to accumulated history. At cold start it produces no signal.
- When the ARS Auditor detects a drift threshold breach (ARS-02), the alert mechanism is: (a) write a WARN-level entry to `data/audit.jsonl` with the affected `agent_id`, (b) set a flag in the PostgreSQL `agent_merit_scores` table (`evolution_suspended: bool`). The next graph invocation's soul-loading step reads this flag and skips MEMORY.md evolution writes for the flagged agent.

**New file:** `src/core/ars_auditor.py`
**Invocation:** `python -m src.core.ars_auditor` — same pattern as `src/agents/review_agent.py`

### Q5: How does Agent Church approval gate integrate — sync during `/sg:save` or async review loop?

**Answer: As an async review loop implemented inside the L1 Orchestrator node, triggered by a special intent classification.**

Rationale:

- The Agent Church (EVOL-02) reviews proposed SOUL.md diffs written by agents to their per-agent `MEMORY.md`. "Sync during `/sg:save`" implies a blocking operation inside the graph execution path, which contradicts the existing pattern: the self-improvement pipeline runs outside the hot graph path to avoid latency impact on trade signal generation.
- The L1 Orchestrator (`classify_intent_with_registry`) already handles special intents (`trade`, `analysis`, `macro`, `risk`). A new intent class — `soul_evolution` — routes to a dedicated `agent_church_node` that:
  1. Reads proposed diffs from all per-agent `MEMORY.md` files.
  2. Uses an LLM-as-Judge call (Gemini, same lazy-init pattern) to evaluate each diff against alignment constraints.
  3. Applies approved diffs to the corresponding `SOUL.md` file, invalidates `lru_cache` for that agent via `load_soul.cache_clear()`.
  4. Writes rejected diffs with reason back to `MEMORY.md`.
  5. Appends an audit record to `data/audit.jsonl`.
- This intent is triggered by the `/sg:save` command (which maps to a graph invocation with `user_input: "/sg:save"`), making it user-initiated but processed through the standard graph machinery. It does not block trade analysis runs.
- `lru_cache` invalidation is the critical detail: after a SOUL.md diff is applied, `load_soul.cache_clear()` must be called so the next graph run picks up the new content. The cache is process-scoped; a production deployment would need a file-watcher or explicit invalidation signal if multiple workers share the same process space.

**Graph change:** New conditional branch from `classify_intent`:

```python
# route_by_intent extended:
if intent == "soul_evolution":
    return "agent_church"
```

**New node:** `agent_church_node` registered in `create_orchestrator_graph()`.

---

## Recommended Component Boundaries

| Component | Responsibility | Communicates With | New/Modified |
|-----------|---------------|-------------------|-------------|
| `src/core/soul_loader.py` | Load, cache, and invalidate AgentSoul from filesystem | All L2 nodes, `soul_sync_handshake`, `agent_church_node` | **New** |
| `src/core/souls/[agent_id]/` | Persona files (SOUL.md, IDENTITY.md, AGENTS.md, USER.md, MEMORY.md) | `soul_loader.py` | **New** |
| `src/core/merit_index.py` | Compute and update Merit Index (EMA, dimensions, bounds) | `merit_update_node`, `debate_synthesizer` | **New** |
| `src/core/ars_auditor.py` | Periodic drift/ego-hijacking detection across MEMORY.md logs | PostgreSQL (`agent_merit_scores`), `audit.jsonl` | **New** |
| `src/graph/state.py` | SwarmState TypedDict | Entire graph | **Modified** (new fields) |
| `src/graph/orchestrator.py` | Graph construction, node registration, routing | All nodes | **Modified** (new nodes, new edges, warmup call) |
| `src/graph/debate.py` | DebateSynthesizer — aggregate researcher outputs | `soul_sync_handshake`, `write_research_memory` | **Modified** (reads `merit_scores` for weighting) |
| `soul_sync_handshake` node | Exchange truncated SOUL.md summaries before debate | `bullish_researcher`, `bearish_researcher`, `debate_synthesizer` | **New** |
| `agent_church_node` | L1 soul-evolution intent handler; approve/reject SOUL.md diffs | All per-agent `MEMORY.md` files, `lru_cache`, `audit.jsonl` | **New** |
| `merit_update_node` | Post-cycle merit score computation and PostgreSQL persistence | `agent_merit_scores` table, SwarmState | **New** |

---

## Data Flow Changes

### Tier 1 — Soul injection (per L2 node execution)

```
create_orchestrator_graph()
  └─ warmup_soul_cache()          (all souls loaded into lru_cache)

macro_analyst_node(state):
  └─ soul = load_soul("macro_analyst")          (lru_cache hit)
  └─ state_update["active_persona"] = soul.agent_id
  └─ state_update["system_prompt"]  = soul.system_prompt_injection
  └─ LLM call with [system_prompt_msg, *state["messages"]]
```

### Tier 2a — Merit Index flow

```
run_task_async():
  └─ initial_state["merit_scores"] = load_merit_scores_from_postgres()

[debate_synthesizer]:
  └─ reads state["merit_scores"] to weight bullish/bearish scores
  └─ weighted_consensus_score = merit-weighted formula (replaces char-length proxy)

[merit_update_node] (new, after write_trade_memory):
  └─ computes Merit delta for each contributing agent
  └─ applies EMA decay: Merit(t) = λ·Merit(t-1) + (1-λ)·NewSignal(t)
  └─ persists to PostgreSQL agent_merit_scores
  └─ writes updated scores to state["merit_scores"]
```

### Tier 2b — Evolution loop (triggered by /sg:save intent)

```
classify_intent → "soul_evolution" → agent_church_node
  └─ reads all per-agent MEMORY.md files for proposed diffs
  └─ LLM-as-Judge evaluates each diff
  └─ approved: apply diff to SOUL.md, call load_soul.cache_clear()
  └─ rejected: write reason back to MEMORY.md
  └─ all events → audit.jsonl
```

### Tier 2c — Theory of Mind (per debate cycle)

```
[bullish_researcher, bearish_researcher] fan-in
  └─ soul_sync_handshake_node
      └─ load_soul("bullish_researcher").identity[:200] → append to debate_history
      └─ load_soul("bearish_researcher").identity[:200] → append to debate_history
      └─ state_update["soul_sync_context"] = {both summaries}
  └─ debate_synthesizer (reads soul_sync_context)
```

### Tier 2d — ARS Auditor (scheduled, out-of-band)

```
systemd timer (weekly) or manual:
  src/core/ars_auditor.py
    └─ for each agent: read MEMORY.md evolution log
    └─ compute drift score vs SOUL.md baseline
    └─ if drift > threshold:
        └─ WARN entry → audit.jsonl
        └─ SET evolution_suspended = True IN agent_merit_scores
```

---

## New SwarmState Fields

```python
# v1.3 Persona System additions to src/graph/state.py

# Tier 1: Soul injection (set by each L2 node, read by LLM call layer)
active_persona: Optional[str]        # agent_id of the executing node's soul
system_prompt:  Optional[str]        # composed soul system prompt (NOT in messages)

# Tier 2a: Merit Index
merit_scores:   Optional[dict]       # {"agent_id": float, ...} — loaded at run start, updated post-cycle

# Tier 2c: Theory of Mind
soul_sync_context: Optional[dict]    # {"bullish": truncated_soul, "bearish": truncated_soul}
```

**Not added to SwarmState:** ARS drift scores, per-agent MEMORY.md content, evolution approval state. These live in PostgreSQL and filesystem respectively — they are not needed during a graph execution run.

---

## Patterns to Follow

### Pattern 1: Lazy Soul System Prompt Composition

Each L2 node composes `system_prompt` by calling `soul.system_prompt_injection` (a `@property` on `AgentSoul`). The property concatenates IDENTITY.md + SOUL.md + AGENTS.md. It does not read files on every call — the `AgentSoul` dataclass is frozen and loaded once by `load_soul()`.

```python
def macro_analyst_node(state: SwarmState, **kwargs) -> dict:
    soul = load_soul("macro_analyst")
    messages_with_soul = [
        {"role": "system", "content": soul.system_prompt_injection},
        *state.get("messages", []),
    ]
    # ... LLM call using messages_with_soul
    return {
        "active_persona": soul.agent_id,
        "system_prompt": soul.system_prompt_injection,
        # ... rest of state update
    }
```

### Pattern 2: Merit-Weighted Consensus (replaces char-length proxy in DebateSynthesizer)

```python
def DebateSynthesizer(state: SwarmState) -> dict:
    merit_scores = state.get("merit_scores") or {}
    bull_merit = merit_scores.get("bullish_researcher", 0.5)
    bear_merit = merit_scores.get("bearish_researcher", 0.5)
    # Weighted by merit rather than character length
    total = bull_strength * bull_merit + bear_strength * bear_merit
    weighted_consensus_score = (bull_strength * bull_merit) / total if total > 0 else 0.5
```

### Pattern 3: Cache Invalidation After Soul Evolution

```python
def agent_church_node(state: SwarmState) -> dict:
    # ... apply approved diff to SOUL.md file ...
    from src.core.soul_loader import load_soul
    load_soul.cache_clear()   # invalidate entire cache — simple, safe
    # Re-warm immediately so next invocation doesn't pay file-read latency
    from src.core.soul_loader import warmup_soul_cache
    warmup_soul_cache()
    return { ... }
```

### Pattern 4: Evolution Suspension Gate

```python
def _write_agent_memory(agent_id: str, reflection: str) -> None:
    """Only write MEMORY.md evolution log if agent is not suspended."""
    # Query agent_merit_scores for evolution_suspended flag
    if is_evolution_suspended(agent_id):
        logger.warning("Evolution suspended for %s — skipping MEMORY.md write", agent_id)
        return
    # ... write reflection to src/core/souls/{agent_id}/MEMORY.md
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Soul-Loader as a Separate Graph Node

**What goes wrong:** Inserting a `load_soul_node` between `classify_intent` and the L2 analysts creates a sequential bottleneck before the fan-out. The `soul_loader` node would need to write the soul for all agents into state simultaneously — but different agents have different souls, so the node would need to load all four and put them all into state at once. This pollutes state with content that is only relevant to one node at a time.

**Why bad:** Forces sequential soul-loading before parallel fan-out; loses the `active_persona` context that tells downstream nodes which soul is active right now.

**Instead:** Each node loads its own soul. Cache makes this effectively free after warmup.

### Anti-Pattern 2: Storing system_prompt in messages

**What goes wrong:** Appending the soul system prompt to `state["messages"]` causes it to accumulate in the message list across nodes. When `bullish_researcher` fires after `macro_analyst`, the message list already contains macro_analyst's soul system prompt — the bearish researcher now sees another agent's persona instructions in its context.

**Why bad:** Persona cross-contamination. Each agent reads a different soul; keeping them in the append-reducer `messages` list means every subsequent node inherits all previous agents' souls.

**Instead:** `system_prompt` is a standalone SwarmState field. Each node constructs its local message list as `[{"role": "system", "content": state["system_prompt"]}, *state["messages"]]` without writing the system prompt back to `state["messages"]`.

### Anti-Pattern 3: Inline ARS in the Hot Graph Path

**What goes wrong:** Running ARS drift detection inside `merit_update_node` (which is inline) requires reading all MEMORY.md files and computing a cosine similarity or embedding distance for every agent on every trade cycle.

**Why bad:** ARS signal requires accumulated history — running it per-invocation produces noise at low session counts and wastes compute at high session counts.

**Instead:** ARS runs on a schedule. The graph's `merit_update_node` only writes the current session's Merit delta. ARS reads the accumulated deltas from PostgreSQL at its scheduled interval.

### Anti-Pattern 4: Single Scalar Merit Score in State

**What goes wrong:** Storing only a single float `merit_score: float` instead of `merit_scores: dict[str, float]` means the graph only tracks one active agent's merit at a time.

**Why bad:** `DebateSynthesizer` needs merit scores for at minimum both researchers simultaneously to compute the weighted consensus. A single scalar cannot serve a multi-agent weighting function.

**Instead:** `merit_scores` is a dict keyed by agent_id. All contributing agents' scores are loaded at run start and available throughout the execution.

---

## Suggested Build Order

Dependencies flow upward: each tier depends on the one before it.

### Tier 1: Soul Foundation (SOUL-01 through SOUL-07)

**Build first. Everything else depends on this.**

1. `src/core/souls/` directory structure — all 5 agent directories, all 5 files per agent.
2. `src/core/soul_loader.py` — `AgentSoul`, `load_soul()`, `warmup_soul_cache()`.
3. `src/graph/state.py` — add `active_persona`, `system_prompt` (Optional[str] fields).
4. `macro_analyst_node` soul injection — proves the integration pattern.
5. Remaining L2 nodes (`quant_modeler`, `bullish_researcher`, `bearish_researcher`) — same pattern.
6. `warmup_soul_cache()` call in `create_orchestrator_graph()`.
7. Test suite (`tests/core/test_soul_loader.py`) — deterministic, no LLM calls.

**Rationale:** `lru_cache` and `AgentSoul` are the shared primitive for all later tiers. The `system_prompt` SwarmState field is the injection surface that Tier 2a Merit and Tier 2c ToM both extend.

### Tier 2a: KAMI Merit Index (KAMI-01 through KAMI-04)

**Build second. Depends on Tier 1 soul files (for Fidelity dimension) and PostgreSQL (already available).**

1. `src/core/merit_index.py` — Merit formula, EMA decay, dimension weights, bounds.
2. PostgreSQL `agent_merit_scores` table migration.
3. `src/graph/state.py` — add `merit_scores: Optional[dict]`.
4. Load merit scores at `run_task_async()` start (read from PostgreSQL into `initial_state`).
5. Modify `DebateSynthesizer` to use `merit_scores` for consensus weighting.
6. New `merit_update_node` — post-cycle Merit delta computation and PostgreSQL persistence.
7. Wire `merit_update_node` into graph after `write_trade_memory` (before `synthesize`).

**Rationale:** Merit weighting of `DebateSynthesizer` (KAMI-03) is the highest-value change — it directly improves trade signal quality. Build it before ToM (which builds on soul files already available) and before ARS (which needs accumulated Merit history to work).

### Tier 2b: MEMORY.md Evolution + Agent Church (EVOL-01 through EVOL-03)

**Build third. Depends on Tier 1 soul files and Tier 2a Merit scores (self-reflection includes Merit delta).**

1. Per-agent `MEMORY.md` write logic — appended after each task cycle, includes task outcome and Merit delta.
2. SOUL.md diff proposal format — agent writes proposed changes in MEMORY.md under a `## Proposed Evolution` section.
3. `agent_church_node` — LLM-as-Judge review loop, applies/rejects diffs, `cache_clear()` + `warmup_soul_cache()`.
4. Extend `route_by_intent()` to handle `soul_evolution` intent.
5. Wire `agent_church_node` in graph with `soul_evolution` conditional path.

**Rationale:** The Agent Church's cache invalidation depends on `load_soul()` existing (Tier 1). Its LLM-as-Judge quality signal is more meaningful once Merit deltas are available (Tier 2a), since the evolution log includes Merit context.

### Tier 2c: Theory of Mind (TOM-01, TOM-02)

**Build fourth. Depends on Tier 1 soul files (reads SOUL.md summaries).**

1. `src/graph/state.py` — add `soul_sync_context: Optional[dict]`.
2. `soul_sync_handshake_node` — load soul summaries for both researchers, append to `debate_history`, set `soul_sync_context`.
3. Update researcher soul `USER.md` files to contain peer soul summaries (TOM-02 — enables Empathetic Refutation via prompt content, no additional node needed).
4. Replace direct `[bullish_researcher, bearish_researcher] → debate_synthesizer` edge with `→ soul_sync_handshake → debate_synthesizer`.

**Rationale:** This is graph topology surgery on the existing fan-in. Do it after the soul files and Merit Index are stable so the `soul_sync_handshake` node has accurate, populated soul content to work with.

### Tier 2d: ARS Auditor (ARS-01, ARS-02)

**Build last. Depends on accumulated MEMORY.md evolution logs (Tier 2b) and PostgreSQL Merit history (Tier 2a).**

1. `src/core/ars_auditor.py` — drift score computation from MEMORY.md logs.
2. `evolution_suspended` column in `agent_merit_scores` PostgreSQL table.
3. Gate in MEMORY.md write logic: check `evolution_suspended` before writing.
4. Integration with existing systemd timer or standalone `/ars:audit` command.

**Rationale:** ARS produces signal only after MEMORY.md evolution logs have accumulated across multiple sessions. Building it last ensures there is meaningful data to audit by the time it runs.

---

## Scalability Considerations

| Concern | Current (v1.2) | v1.3 Addition | Mitigation |
|---------|---------------|---------------|------------|
| Soul file reads per invocation | Zero | 4 × `lru_cache` hits after warmup | `warmup_soul_cache()` at startup; cache is process-scoped |
| PostgreSQL Merit reads per run | Zero | 1 SELECT (all agents) at run start | Single query loading all agent scores into state |
| DebateSynthesizer latency | Deterministic, microseconds | Adds dict lookup for merit_scores | Negligible — dict is already in state |
| Agent Church LLM-as-Judge calls | N/A | 1 LLM call per proposed diff | Triggered only on `soul_evolution` intent, not on every trade run |
| ARS Auditor compute | N/A | File reads + MEMORY.md comparison per agent | Scheduled, out-of-band — no impact on hot path |
| lru_cache invalidation | N/A | `cache_clear()` + `warmup_soul_cache()` on SOUL.md change | Rare operation (Agent Church only); warmup is < 10ms for 5 agents |

---

## Sources

| Source | Confidence | Informs |
|--------|------------|---------|
| `src/graph/orchestrator.py` (v1.2) | HIGH — production code | Graph topology, node registration pattern, routing functions |
| `src/graph/state.py` (v1.2) | HIGH — production code | SwarmState schema, existing field conventions |
| `src/graph/debate.py` (v1.2) | HIGH — production code | DebateSynthesizer internals, consensus scoring |
| `.planning/PHASES/persona_plan.md` | HIGH — design doc | SoulLoader API, file structure, SwarmState additions, node injection pattern |
| `docs/SOT_PERSONA_REWARD_SYSTEM.md` | HIGH — finalized SOT | MBS architecture, KAMI components, ToM handshake, ARS, evolution loop |
| `claudedocs/research_soul_rewards_deep_dive_20260305.md` | HIGH — deep research | Merit formula, EMA decay, cold start, bounds, KAMI naming conflict |
| `claudedocs/research_agent_persona_soul_20260305.md` | MEDIUM — initial research | MBS architecture overview, SoulZip, ToM pattern |
| `claudedocs/research_personas_merit_20260305.md` | MEDIUM — initial research | Merit-based routing, KAMI consensus weighting |
| `.planning/PROJECT.md` (v1.3 requirements) | HIGH — authoritative | SOUL-0x, KAMI-0x, EVOL-0x, TOM-0x, ARS-0x requirement IDs |
