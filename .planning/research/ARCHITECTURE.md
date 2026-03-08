# Architecture Patterns

**Domain:** Observable multi-agent trading swarm (v1.4 Beta)
**Researched:** 2026-03-08
**Confidence:** HIGH (based on existing codebase analysis + LangGraph official docs)

## Recommended Architecture

Four integration areas building on the existing LangGraph StateGraph. The core principle is: **the existing graph topology stays unchanged**. New features wrap, extend, or consume -- they do not restructure the pipeline.

```
EXISTING GRAPH (unchanged topology)
    merit_loader -> classify_intent -> analysts -> researchers -> soul_sync
    -> debate_synthesizer -> risk_manager -> ... -> trade_logger -> synthesize -> END

NEW: Cycle Persistence Layer (wraps existing graph invocation)
    CycleRunner.run(user_input)
        -> assigns cycle_id (UUID)
        -> invokes existing graph via ainvoke()
        -> extracts CycleSnapshot from final_state (post-invocation)
        -> persists snapshot to PostgreSQL cycle_snapshots table
        -> returns cycle_id for downstream replay

NEW: Cycle Replay CLI (read-only consumer of cycle_snapshots)
    swarm-replay list                    -> query cycle_snapshots table
    swarm-replay show <cycle_id>         -> load + render full snapshot
    swarm-replay diff <cycle_a> <cycle_b> -> side-by-side comparison
    swarm-replay timeline <symbol>       -> merit/tension over time for symbol

NEW: Full Persona Population (filesystem only, no code changes)
    src/core/souls/bullish_researcher/  -> MOMENTUM fully authored
    src/core/souls/bearish_researcher/  -> CASSANDRA fully authored
    src/core/souls/quant_modeler/       -> SIGMA fully authored
    src/core/souls/risk_manager/        -> GUARDIAN fully authored
    Each: IDENTITY.md, SOUL.md (with drift_guard YAML), AGENTS.md

NEW: End-to-End Pipeline Runner (replaces main.py simulation)
    src/runner.py
        -> initializes PostgreSQL persistence (setup_persistence())
        -> constructs LangGraphOrchestrator with AsyncPostgresSaver
        -> wraps invocation with CycleRunner
        -> paper mode by default
        -> structured logging + cycle_id tracking
```

### Component Boundaries

| Component | Responsibility | Communicates With | New/Modified |
|-----------|---------------|-------------------|--------------|
| `CycleRunner` | Wraps graph invocation, assigns cycle_id, captures full state post-invocation | LangGraphOrchestrator.run_cycle_async() | **NEW** (`src/core/cycle_runner.py`) |
| `extract_cycle_snapshot()` | Extracts curated snapshot from final SwarmState dict | CycleRunner | **NEW** (function in cycle_runner.py) |
| `cycle_snapshots` table | Stores per-cycle artifact bundle (JSONB) | CycleRunner (write), ReplayCLI (read) | **NEW** (DDL in persistence.py) |
| `swarm-replay` CLI | Reads cycle_snapshots, renders formatted output | PostgreSQL | **NEW** (`src/cli/replay.py`) |
| Soul persona files (4 agents) | HEXACO-diverse persona content with drift_guard YAML | SoulLoader (existing, unchanged code) | **MODIFIED** (content only) |
| `src/runner.py` | End-to-end pipeline entry point | CycleRunner, persistence.py | **NEW** |
| `LangGraphOrchestrator` | Existing graph wrapper | CycleRunner calls it | **MODIFIED** (add run_cycle_async method) |
| `SwarmState` | Graph state TypedDict | All nodes | **MODIFIED** (add cycle_id field) |
| `persistence.py` | Schema setup | Existing tables + cycle_snapshots DDL | **MODIFIED** |
| `decision_card.py` | Immutable audit artifact | Optionally includes cycle_id | **MODIFIED** (optional field) |

### Data Flow: Cycle Persistence

```
CycleRunner.run(user_input)
    |
    +-> cycle_id = uuid4()[:8]
    +-> inject cycle_id into initial_state
    +-> (decision, final_state) = await orchestrator.run_cycle_async(user_input, cycle_id)
    +-> snapshot = extract_cycle_snapshot(cycle_id, final_state)
    +-> await persist_snapshot(snapshot)   # INSERT INTO cycle_snapshots
    +-> return CycleResult(cycle_id, decision, snapshot_summary)
```

### Data Flow: Replay CLI

```
swarm-replay show <cycle_id>
    |
    +-> SELECT snapshot FROM cycle_snapshots WHERE cycle_id = ?
    +-> deserialize JSONB -> CycleSnapshot dict
    +-> render_snapshot(snapshot)
    |   +-> Agent Memos section (macro_report, quant_proposal, bullish/bearish theses)
    |   +-> Debate section (consensus_score, debate_tension, soul_sync_context)
    |   +-> Risk section (risk_approved, compliance_flags)
    |   +-> Execution section (execution_result, decision_card_audit_ref)
    |   +-> Merit section (merit_scores at cycle end, per-agent deltas)
    +-> print to stdout (or write to file with --output flag)
```

## Cycle Snapshot Schema

The snapshot is the core data contract between CycleRunner (producer) and ReplayCLI (consumer). It is a curated extraction from SwarmState -- not the raw state.

```python
CycleSnapshot = {
    # Identity
    "cycle_id": str,              # UUID assigned by CycleRunner
    "task_id": str,               # from SwarmState (LangGraph thread_id)
    "timestamp": str,             # ISO 8601 UTC
    "user_input": str,
    "intent": str,
    "symbol": str,                # extracted from quant_proposal or user_input

    # Agent memos (raw outputs from L2 nodes)
    "macro_report": dict | None,
    "quant_proposal": dict | None,
    "bullish_thesis": dict | None,
    "bearish_thesis": dict | None,

    # Debate
    "debate_resolution": dict | None,
    "weighted_consensus_score": float | None,
    "debate_history": list[dict],
    "soul_sync_context": dict | None,

    # Risk gating
    "risk_approved": bool | None,
    "risk_notes": str | None,
    "compliance_flags": list[str],

    # Execution
    "execution_result": dict | None,
    "execution_mode": str,
    "decision_card_status": str | None,
    "decision_card_audit_ref": str | None,

    # Merit (full KAMI scores at cycle end)
    "merit_scores": dict | None,

    # Derived observability fields (computed at extraction time)
    "debate_tension": float | None,  # abs(bull_merit - bear_merit)
    "drift_flags": dict,             # {handle: "flags_string"} from latest MEMORY.md
    "final_decision": dict | None,
    "cycle_outcome": str,            # "executed" | "hold" | "rejected" | "unknown_intent"
}
```

**Fields explicitly excluded from snapshot:**
- `messages` -- unbounded list from operator.add reducer, multi-MB, not useful for replay
- `system_prompt` -- soul content, excluded from audit trail per AUDIT_EXCLUDED_FIELDS
- `active_persona` -- changes per-node during fan-out; final value is not meaningful
- `trade_history` -- cumulative across sessions; snapshot only needs current cycle's trade
- `total_tokens` -- operational metric, not observability

## PostgreSQL Table: cycle_snapshots

```sql
CREATE TABLE IF NOT EXISTS cycle_snapshots (
    cycle_id        VARCHAR(64) PRIMARY KEY,
    task_id         VARCHAR(64) NOT NULL,
    timestamp       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    symbol          VARCHAR(32),
    intent          VARCHAR(32),
    user_input      TEXT,
    cycle_outcome   VARCHAR(32),           -- executed/hold/rejected/unknown_intent
    decision        VARCHAR(16),           -- BUY/SELL/HOLD from final_decision
    consensus_score NUMERIC(6, 4),
    debate_tension  NUMERIC(6, 4),         -- for fast query/sort
    merit_scores    JSONB,                 -- KAMI scores at cycle end
    snapshot        JSONB NOT NULL         -- full CycleSnapshot
);
CREATE INDEX IF NOT EXISTS idx_cycle_timestamp ON cycle_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_cycle_symbol ON cycle_snapshots(symbol);
CREATE INDEX IF NOT EXISTS idx_cycle_outcome ON cycle_snapshots(cycle_outcome);
```

**Denormalized columns** (consensus_score, debate_tension, symbol, intent, cycle_outcome) exist for fast filtering and sorting in the replay CLI without parsing the JSONB blob.

## Patterns to Follow

### Pattern 1: Post-Graph Snapshot Extraction (not an in-graph node)

**What:** Extract the cycle snapshot AFTER `ainvoke()` returns, not as a graph node.

**When:** Always.

**Why:** The graph has four distinct exit paths:
1. Unknown intent -> END (no analysis)
2. Hold (consensus <= 0.6) -> END (no execution)
3. Institutional guard rejection -> synthesize -> END
4. Success path -> full L3 chain -> synthesize -> END

A snapshot node would need edges from all terminal paths. Post-invocation extraction is one line of code that handles all paths uniformly.

**Example:**
```python
class CycleRunner:
    def __init__(self, orchestrator: LangGraphOrchestrator):
        self.orchestrator = orchestrator

    async def run(self, user_input: str) -> CycleResult:
        cycle_id = str(uuid.uuid4())[:8]
        decision, final_state = await self.orchestrator.run_cycle_async(
            user_input, cycle_id=cycle_id
        )
        snapshot = extract_cycle_snapshot(cycle_id, final_state)
        await persist_snapshot(snapshot)
        return CycleResult(cycle_id=cycle_id, decision=decision, snapshot=snapshot)
```

### Pattern 2: LangGraphOrchestrator.run_cycle_async() Exposes Final State

**What:** Add a method that returns both GraphDecision and final_state dict.

**Why:** Current `run_task_async()` converts final_state to GraphDecision and discards the state. CycleRunner needs the raw state for snapshot extraction.

**Implementation:** Non-breaking refactor. Extract the core of `run_task_async()` into `run_cycle_async()` that returns a tuple. `run_task_async()` calls it and returns only the decision.

```python
async def run_cycle_async(self, user_input: str, cycle_id: str = None) -> tuple[GraphDecision, dict]:
    task_id = str(uuid.uuid4())[:8]
    initial_state = self._build_initial_state(task_id, user_input, cycle_id)
    config = {"configurable": {"thread_id": task_id}}
    final_state = await self.app.ainvoke(initial_state, config=config)
    decision = self._build_decision(task_id, final_state)
    return decision, final_state

async def run_task_async(self, user_input: str) -> GraphDecision:
    decision, _ = await self.run_cycle_async(user_input)
    return decision
```

### Pattern 3: Cycle ID Separate from Thread ID

**What:** `cycle_id` is a new plain field in SwarmState, distinct from the LangGraph `thread_id`.

**Why:** `thread_id` is used by LangGraph's checkpointer for checkpoint management. It is an internal concern. `cycle_id` is a domain concept: one complete analysis-to-decision pass. They currently have a 1:1 mapping (each invocation creates a new thread_id), but the concepts are different and should not be conflated.

### Pattern 4: Replay via Direct PostgreSQL (not LangGraph Time-Travel)

**What:** The replay CLI reads from `cycle_snapshots`, not from LangGraph's checkpoint history.

**Why:** LangGraph's `get_state_history()` returns checkpoints at every superstep (15-25 per cycle). Replay needs exactly one snapshot per cycle. Storing a denormalized snapshot is dramatically simpler and decouples the replay tool from LangGraph internals.

LangGraph time-travel via `get_state_history()` remains available for deep debugging of intermediate states within a single cycle, but is not the primary replay API.

### Pattern 5: Persona Population is Content-Only

**What:** The 4 skeleton personas need only markdown content changes.

**Why:** SoulLoader, KAMI fidelity signal, drift evaluation, ARS auditor, soul_sync_handshake -- all operate on file content loaded by `load_soul()`. No code changes activate a fully populated persona. The only structural requirement is a valid `drift_guard` YAML block in each SOUL.md (currently missing from skeletons -- this is documented tech debt from v1.3).

**Constraint:** `lru_cache` on `load_soul()` means persona changes require process restart. Intentional design -- frozen souls during trading.

### Pattern 6: Runner Entry Point Replaces Simulation

**What:** `src/runner.py` invokes the real LangGraph pipeline with real market data.

**Why:** The existing `src/main.py` is a simulation stub from before the graph architecture. It hardcodes pipeline results, calls `route_order()` directly, and bypasses the entire LangGraph graph. A proper runner needs to:
1. Initialize persistence (`setup_persistence()`)
2. Construct LangGraphOrchestrator with AsyncPostgresSaver
3. Wrap with CycleRunner
4. Accept user_input from CLI args
5. Log cycle_id and summary

## Anti-Patterns to Avoid

### Anti-Pattern 1: Snapshot Node Inside the Graph

**What:** Adding a `cycle_snapshot_writer` as a LangGraph node in the topology.

**Why bad:** Four exit paths require edges from each terminal node. If snapshot write fails, it blocks the graph or requires error-handling edges. Adds complexity with no benefit over post-invocation extraction.

**Instead:** Extract snapshot in CycleRunner after `ainvoke()` returns. All paths converge at the return point.

### Anti-Pattern 2: Storing Full SwarmState as Snapshot

**What:** Persisting `final_state` dict as-is.

**Why bad:** Contains `messages` (unbounded, multi-MB), `system_prompt` (large soul content, excluded from audit per AUDIT_EXCLUDED_FIELDS), and `trade_history` (cumulative across sessions). Creates bloated rows, violates audit exclusion expectations, makes replay queries slow.

**Instead:** Extract a curated CycleSnapshot with only replay-relevant fields. Compute derived fields (debate_tension, cycle_outcome) at extraction time.

### Anti-Pattern 3: Using LangGraph Time-Travel as Primary Replay

**What:** Using `graph.get_state_history(config)` for the cycle replay CLI.

**Why bad:** Returns every intermediate checkpoint (15-25 per cycle). Couples replay tool to LangGraph's checkpoint schema which may change across versions. Adds query complexity (iterate to find final state).

**Instead:** Single denormalized snapshot per cycle in a dedicated table. Time-travel reserved for debugging.

### Anti-Pattern 4: Modifying Orchestrator.run_task_async() Signature

**What:** Changing the return type of `run_task_async()` to include final_state.

**Why bad:** Breaking change for all existing callers (tests, potential external consumers).

**Instead:** Add a new `run_cycle_async()` method. Refactor `run_task_async()` to call it internally. Existing callers unchanged.

### Anti-Pattern 5: drift_guard YAML as Separate File

**What:** Moving drift_guard rules out of SOUL.md into a separate YAML file per agent.

**Why bad:** `parse_drift_guard_yaml()` in `src/core/drift_eval.py` already parses the YAML block from within SOUL.md. Creating a separate file would require changes to the parser, SoulLoader, and all tests. The existing inline pattern works and is tested.

**Instead:** Add the `drift_guard` YAML block to each agent's SOUL.md as part of persona population. Same format as macro_analyst's existing block.

## Integration Points: Detailed Change Analysis

### 1. LangGraphOrchestrator (src/graph/orchestrator.py)

**Change:** Add `run_cycle_async(user_input, cycle_id=None)` method. Refactor `run_task_async()` to delegate.

**Lines affected:** ~30 lines (new method + refactor of existing method).

**Risk:** LOW. Non-breaking; existing tests call `run_task_async()` which delegates to the new method.

### 2. SwarmState (src/graph/state.py)

**Change:** Add `cycle_id: Optional[str]` -- plain field, no reducer.

**Lines affected:** 3 (field + comment).

**Risk:** LOW. Optional with None default. No existing node reads it.

### 3. persistence.py (src/core/persistence.py)

**Change:** Add `cycle_snapshots` table DDL to `setup_persistence()`.

**Lines affected:** ~20 (CREATE TABLE + indexes).

**Risk:** LOW. New table, no impact on existing tables. Idempotent with IF NOT EXISTS.

### 4. DecisionCard (src/core/decision_card.py)

**Change:** Add optional `cycle_id: Optional[str] = None` to DecisionCard model. Populate from state in `build_decision_card()`.

**Lines affected:** 4 (field + extraction).

**Risk:** LOW. Optional field. `canonical_json` and `_compute_hash` handle it transparently.

### 5. KAMI Fidelity Signal (src/core/kami.py)

**Change:** None to code.

**Impact:** After persona population, `_extract_fidelity_signal()` returns 1.0 for all agents (non-empty IDENTITY.md). Current skeletons return 1.0 already (they have content), so impact is limited to drift_guard YAML availability for drift evaluation.

### 6. ARS Drift Auditor (src/core/ars_auditor.py)

**Change:** None. Fully populated SOUL.md files with drift_guard blocks mean ARS produces meaningful alerts instead of skipping agents with no rules.

### 7. memory_writer_node (src/graph/nodes/memory_writer.py)

**Change:** None. Richer persona content means thesis_summary extraction produces better output. drift_flags evaluation works because drift_guard YAML exists.

## Suggested Build Order

Dependencies flow strictly downward:

```
Phase 1: Full Persona Population
    No code deps. Unlocks fidelity scoring + drift evaluation.
    Content-only: 4 agents x 3 files (IDENTITY.md, SOUL.md with drift_guard, AGENTS.md)
    |
    v
Phase 2: Cycle Persistence Infrastructure
    SwarmState.cycle_id + cycle_snapshots table + CycleRunner + extract_cycle_snapshot()
    Depends on: nothing new (uses existing orchestrator + PostgreSQL)
    |
    v
Phase 3: End-to-End Pipeline Runner
    src/runner.py with AsyncPostgresSaver + CycleRunner integration
    Depends on: CycleRunner (Phase 2)
    Exercises full graph with real data, populates cycle_snapshots
    |
    v
Phase 4: Replay CLI
    src/cli/replay.py -- list, show, diff, timeline commands
    Depends on: cycle_snapshots table (Phase 2) + data from Phase 3 runs
    Read-only consumer -- build last so real data exists to test against
```

**Phase ordering rationale:**
- Personas first: zero code risk, pure content, and all subsequent phases benefit from richer agent output.
- Cycle persistence second: it is the core infrastructure. Without snapshots, there is nothing to replay.
- Runner third: actually exercises the full pipeline and validates integration.
- Replay CLI last: read-only consumer of data from phases 2-3. Building it with real data available makes testing straightforward.

## Scalability Considerations

| Concern | At 10 cycles/day | At 100 cycles/day | At 1000 cycles/day |
|---------|-------------------|--------------------|--------------------|
| cycle_snapshots row size | ~5 KB JSONB, negligible | ~500 KB/day, negligible | ~5 MB/day, vacuum weekly |
| PostgreSQL connections | Current pool (min=2, max=10) sufficient | Sufficient | May need max=20 |
| MEMORY.md cap | 50-entry cap per agent, fine | Same cap, faster rotation | Cap is per-agent; fine |
| LangGraph checkpoints | ~25 per cycle, auto-managed | ~2500/day, monitor size | Add checkpoint pruning |
| Replay query latency | <10ms with index | <10ms with index | <50ms; add pagination |
| Snapshot extraction | <1ms (dict extraction) | <1ms | <1ms |

## Sources

- Codebase analysis: `src/graph/orchestrator.py`, `src/graph/state.py`, `src/core/persistence.py`, `src/core/soul_loader.py`, `src/graph/nodes/memory_writer.py`, `src/graph/nodes/merit_updater.py`, `src/graph/debate.py`, `src/core/audit_logger.py`, `src/core/kami.py`, `src/core/decision_card.py`, `src/graph/agents/l3/trade_logger.py`
- [LangGraph Persistence Documentation](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Time Travel (get_state_history)](https://docs.langchain.com/oss/python/langgraph/use-time-travel)
- [AsyncPostgresSaver Reference](https://reference.langchain.com/python/langgraph.checkpoint.postgres/aio/AsyncPostgresSaver)
- [LangGraph Checkpoint Package](https://pypi.org/project/langgraph-checkpoint-postgres/)
- [Persistence in LangGraph -- Deep Practical Guide (Jan 2026)](https://pub.towardsai.net/persistence-in-langgraph-deep-practical-guide-36dc4c452c3b)
