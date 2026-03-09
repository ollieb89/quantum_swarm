# Architecture Patterns

**Domain:** Integration of PersonaScore 5D, token cost tracking, circuit breakers, and ChromaDB pruning into existing LangGraph multi-agent swarm
**Researched:** 2026-03-09
**Confidence:** HIGH (based on codebase analysis of orchestrator.py, kami.py, cycle_runner.py, budget_manager.py, analysts.py, memory_writer.py + LangChain/LangGraph docs)

## Recommended Architecture

### Integration Overview

```
EXISTING GRAPH (unchanged edges/nodes -- topology preserved):
    merit_loader -> classify_intent -> [fan-out L2] -> soul_sync -> debate ->
    write_research_memory -> risk_manager -> ... -> order_router ->
    decision_card_writer -> merit_updater -> memory_writer -> trade_logger ->
    write_trade_memory -> synthesize -> END

MODIFIED GRAPH (one new node inserted):
    ... -> merit_updater -> memory_writer -> persona_eval -> trade_logger -> ...
    (persona_eval_node evaluates all 5 agents' output fidelity)

NEW COMPONENTS (by layer):

src/core/ (Import Layer Law compliant -- no graph imports):
    circuit_breaker.py       -- GeminiCircuitBreaker (three-state, singleton)
    token_tracker.py         -- CycleTokenTracker (LangChain callback handler)
    persona_scorer.py        -- PersonaScore5D evaluator (LLM-as-Judge, pure function)
    chroma_pruner.py         -- Prune-to-Obsidian logic (reads ChromaDB, writes markdown)

src/graph/nodes/ (graph layer):
    persona_eval.py          -- persona_eval_node (calls persona_scorer for all agents)

src/core/cycle_runner.py (modified):
    -- Injects CycleTokenTracker callback into graph config
    -- Extracts token summary after ainvoke
    -- Persists token costs to CycleSnapshot

config/swarm_config.yaml (extended):
    circuit_breaker:          -- thresholds, cooldown, failure window
    kami:                     -- rebalanced weights (alpha -> 0.08, delta -> 0.32)
    persona_score:            -- judge model, 5D dimension config

CLI (new subcommand):
    python -m src.main prune  -- Prune-to-Obsidian manual trigger
```

### Component Boundaries

| Component | Responsibility | Communicates With | Layer |
|-----------|---------------|-------------------|-------|
| `GeminiCircuitBreaker` | Tracks Gemini API failures; opens circuit on threshold; soft-fail on OPEN | `with_audit_logging` wrapper in orchestrator.py | `src/core/` |
| `CycleTokenTracker` | LangChain callback handler accumulating input/output tokens per cycle | LangChain callback system via graph config, `CycleRunner` reads summary | `src/core/` |
| `PersonaScore5D` | LLM-as-Judge evaluation of agent output against soul identity | `soul_loader`, Gemini API (single call per agent) | `src/core/` |
| `persona_eval_node` | Graph node running PersonaScore5D for all agents with output | `persona_scorer` (core), writes `persona_scores` to SwarmState | `src/graph/nodes/` |
| `ChromaPruner` | Archive old ChromaDB vectors to Obsidian markdown, delete from collection | `MemoryService` (via dependency injection), filesystem | `src/core/` |
| KAMI weight config | Rebalanced weights; PersonaScore composite replaces binary fidelity | `swarm_config.yaml`, `kami.py`, `merit_updater.py` | `config/` + `src/core/` |

### Data Flow Changes

**1. PersonaScore 5D -- New graph node after memory_writer, before trade_logger:**

```
Current:  ... -> merit_updater -> memory_writer -> trade_logger -> ...
Proposed: ... -> merit_updater -> memory_writer -> persona_eval -> trade_logger -> ...
```

The `persona_eval_node`:
- Runs AFTER memory_writer because it is not on the critical trade path (trade is already logged)
- Runs BEFORE trade_logger so the persona_scores are available in the CycleSnapshot
- Evaluates ALL agents that produced output (checks canonical fields: macro_report, quant_proposal, bullish_thesis, bearish_thesis, risk_approval)
- Writes `persona_scores: Dict[str, Dict[str, float]]` to SwarmState
- Each entry: `{"consistency": 0.8, "tone": 0.9, "logic": 0.7, "depth": 0.8, "bias": 0.85, "composite": 0.81}`

**Fidelity signal integration (lagged pattern):** PersonaScore from cycle N is used as the fidelity signal in cycle N+1. This is the same lagged pattern already used for Accuracy (which is frozen at 0.5 because trade resolution does not yet exist). The `_extract_fidelity_signal` function in `kami.py` is replaced: instead of checking if IDENTITY.md is non-empty (binary 0/1), it reads the previous cycle's PersonaScore composite from the DB. merit_loader already loads dimensions from `agent_merit_scores` JSONB, which will contain the persona_score composite written by persona_eval_node.

**Why NOT post-cycle/standalone:** Running inside the graph means PersonaScore is captured in CycleSnapshot alongside all other cycle artifacts. Running it outside would require a second pass over agent outputs, duplicating state extraction logic and breaking the "cycle is self-contained" invariant from v1.4.

**Why NOT merged into merit_updater:** merit_updater is already complex (EMA updates for 3 dimensions, DB persistence, error handling). Adding LLM-as-Judge (async, can fail, separate error modes) violates single responsibility. Also, merit_updater runs for the ACTIVE persona only; PersonaScore evaluates ALL agents.

**2. Token Cost Tracking -- LangChain callback injected at CycleRunner level:**

```python
# In CycleRunner.run_cycle():
from src.core.token_tracker import CycleTokenTracker

tracker = CycleTokenTracker()
config = {
    "configurable": {"thread_id": task_id},
    "callbacks": [tracker],
}
final_state = await self._graph.ainvoke(initial_state, config=config)
token_summary = tracker.summary()
# token_summary = {"input_tokens": 12340, "output_tokens": 3210,
#                   "total_cost_usd": 0.0019, "per_node": {...}}
```

This requires NO changes to any graph node. LangChain callbacks propagate through all LLM invocations inside the graph, including ReAct sub-agents in analysts.py and researchers.py.

`CycleTokenTracker` extends `BaseCallbackHandler` from langchain_core:
- `on_llm_end(response)`: reads `response.generations[0][0].message.usage_metadata` for token counts
- Accumulates per-node counts using the `run_id` to group by parent node
- `summary()`: returns aggregate dict with per-model cost calculation

**Known issue (MEDIUM confidence):** `ChatGoogleGenerativeAI` has documented issues with `llm_output` not being populated in callbacks. The `usage_metadata` is available on the AIMessage response object but may not flow through all callback mechanisms cleanly. Mitigation: the custom handler reads from `response.generations` which contains the raw AIMessage with usage_metadata attached.

**Relationship to BudgetManager:** BudgetManager tracks session-level budget ceilings and raises SafetyShutdown. CycleTokenTracker is read-only (never raises) and captures granular per-cycle token counts for cost analysis and archiving. They are complementary. Optionally, CycleTokenTracker could call `BudgetManager.record_usage()` to unify tracking, but this coupling is optional.

**token_usage is NOT a SwarmState field.** It is set by CycleRunner AFTER `ainvoke()` completes, so no graph node reads it. Store directly on CycleSnapshot (add field to Pydantic model) and optionally in the `cycle_snapshots` DB table as a JSONB column.

**3. Circuit Breaker -- Enhancement to existing with_audit_logging wrapper:**

```python
# src/core/circuit_breaker.py

class CircuitState(enum.Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Blocking calls
    HALF_OPEN = "half_open" # Probing

class GeminiCircuitBreaker:
    """Three-state circuit breaker: CLOSED -> OPEN -> HALF_OPEN -> CLOSED.

    CLOSED:    Normal. Track failures in sliding window.
    OPEN:      Too many failures. All calls return soft-fail immediately.
               After cooldown_seconds, transition to HALF_OPEN.
    HALF_OPEN: Allow ONE probe call. If succeeds -> CLOSED. If fails -> OPEN.

    Thread-safe via threading.Lock (nodes run in thread pool via asyncio.to_thread).
    """

    def __init__(self, failure_threshold=5, cooldown_seconds=60, failure_window_seconds=120):
        ...

    def should_allow(self) -> bool: ...
    def record_success(self) -> None: ...
    def record_failure(self) -> None: ...

# Module-level singleton
_breaker: Optional[GeminiCircuitBreaker] = None

def get_circuit_breaker() -> GeminiCircuitBreaker:
    global _breaker
    if _breaker is None:
        # Load config from swarm_config.yaml
        _breaker = GeminiCircuitBreaker(...)
    return _breaker
```

**Integration point: `with_audit_logging` in orchestrator.py.**

The existing `with_audit_logging` wrapper already intercepts every node call. Circuit breaker logic is added here:

```python
from src.core.circuit_breaker import get_circuit_breaker

# Gemini API transient error types to catch
GEMINI_TRANSIENT_ERRORS = (
    # google.api_core.exceptions.ResourceExhausted (429)
    # google.api_core.exceptions.ServiceUnavailable (503)
    # google.api_core.exceptions.DeadlineExceeded (timeout)
    # google.api_core.exceptions.InternalServerError (500)
)

def with_audit_logging(node_fn, node_id: str):
    async def wrapped_node(state, **kwargs):
        cb = get_circuit_breaker()

        # Check circuit state before executing
        if not cb.should_allow():
            logger.warning("Circuit OPEN -- soft-fail for node %s", node_id)
            return {}  # Silent pass-through, no state mutation

        # ... existing audit logging logic ...

        try:
            result = await original_execution(state, **kwargs)
            cb.record_success()
            return result
        except GEMINI_TRANSIENT_ERRORS as e:
            cb.record_failure()
            logger.error("Gemini API error in %s: %s (circuit: %s)", node_id, e, cb.state)
            if not cb.should_allow():
                return {}  # Soft-fail after circuit opens
            raise  # Re-raise if circuit still closed (may be retried by upstream)

    return wrapped_node
```

**Why this approach:**
- Single integration point -- no changes to individual node implementations
- Circuit state is shared across all nodes (one breaker for all Gemini calls)
- Soft-fail returns `{}` instead of crashing the graph (nodes that return empty dict cause no state mutation)
- Only Gemini API transient errors (429, 503, timeout) trip the breaker, not business logic errors
- Complies with Import Layer Law (circuit_breaker.py is in core, orchestrator imports it)

**Why NOT per-node breakers:** Gemini API failures affect ALL nodes equally (same API key, same quota). Per-node breakers would allow 5x the failure threshold before any opens.

**Why NOT LangChain callback:** Callbacks are observational -- they cannot prevent the next call. The circuit breaker needs to BLOCK calls.

**Why NOT decorator on ChatGoogleGenerativeAI construction:** Construction validates the API key but does not make API calls. The breaker must wrap invocations.

**4. ChromaDB Pruning + Obsidian Export -- CLI command only:**

```
python -m src.main prune [--days 90] [--dry-run]
```

ChromaDB pruning is a maintenance operation that MUST NOT run during a trade cycle:
- Destructive (deletes vectors permanently)
- Slow (iterates entire collection, exports to filesystem)
- Not trade-relevant (no graph node depends on pruning having run)

`src/core/chroma_pruner.py`:
```python
class ChromaPruner:
    def __init__(self, memory_service: MemoryService, vault_path: str = "quantum-swarm/Archives"):
        ...

    def prune(self, max_age_days: int = 90, dry_run: bool = False) -> PruneReport:
        """
        1. Query ChromaDB for documents with metadata.timestamp older than cutoff
        2. Group by source (trade, research, external_data)
        3. Export each document to vault_path/memory/{source}/{date}-{id}.md
        4. Delete exported documents from ChromaDB collection
        5. Return PruneReport with counts
        """
        ...
```

Can also be triggered by systemd timer/cron (same pattern as ARS auditor).

**5. KAMI Weight Rebalancing -- Config + code constant update:**

Current weights: alpha=0.30 (Accuracy), beta=0.35 (Recovery), gamma=0.25 (Consensus), delta=0.10 (Fidelity)

Problem: Accuracy is frozen at 0.5 (no trade resolution pipeline), so 30% of merit score is inert. Fidelity is binary (1.0 for all authored agents), so 10% is also effectively inert. 40% of the KAMI score carries no signal.

**Recommended approach: Merge PersonaScore INTO fidelity (delta), do NOT add 5th dimension.**

PersonaScore IS fidelity measurement, just at higher resolution. Adding a 5th dimension (epsilon) increases complexity in kami.py, merit_updater.py, merit_loader.py, KAMIDimensions dataclass, and all tests. Merging is simpler and semantically correct.

Proposed weights:
- alpha=0.08 (Accuracy -- still frozen at 0.5, minimized until trade resolution exists)
- beta=0.35 (Recovery -- unchanged, strong signal)
- gamma=0.25 (Consensus -- unchanged)
- delta=0.32 (Fidelity -- now PersonaScore5D composite, significantly upweighted from 0.10)
- Sum = 1.00

Weight propagation path:
1. `config/swarm_config.yaml` -- update `kami:` section
2. `src/core/kami.py` -- update DEFAULT_WEIGHTS dict
3. `src/core/kami.py` -- replace `_extract_fidelity_signal()` to read PersonaScore composite from state/DB instead of binary IDENTITY.md check
4. `src/graph/nodes/merit_updater.py` -- fidelity signal now comes from previous cycle's persona_scores (via merit_loader)
5. `agent_merit_scores.dimensions` JSONB -- already flexible, no schema change needed

## New SwarmState Fields

```python
# Add to SwarmState TypedDict in src/graph/state.py:

# Phase 27 (v1.5): PersonaScore 5D evaluation results per agent
# Plain dict field (NO operator.add reducer) -- written once by persona_eval_node.
# Excluded from AuditLogger hash chain (not trade-decision data).
persona_scores: Optional[Dict[str, Dict[str, float]]]
```

Add `"persona_scores"` to `AUDIT_EXCLUDED_FIELDS` in `audit_logger.py`.

token_usage does NOT go in SwarmState -- stored on CycleSnapshot only.

## New/Modified DB Schema

```sql
-- No new tables needed.
-- agent_merit_scores.dimensions JSONB already stores arbitrary dimension values.

-- Optional: Add token_usage column to cycle_snapshots for queryability:
ALTER TABLE cycle_snapshots ADD COLUMN IF NOT EXISTS token_usage JSONB;
```

## Patterns to Follow

### Pattern 1: Lagged Signal (same as Accuracy)

**What:** PersonaScore from cycle N is used as the fidelity signal in cycle N+1's KAMI computation.
**When:** Any metric that requires current cycle output to compute but also feeds into KAMI weighting.
**Why:** Eliminates circular dependency (KAMI weights influence debate output, PersonaScore evaluates that output).
**Example:**
```python
# merit_loader reads previous persona_score from DB as fidelity dimension
# persona_eval writes current cycle's scores to DB at end of cycle
# One-cycle lag, no circular dependency
```

### Pattern 2: Callback Injection at CycleRunner

**What:** Pass LangChain callbacks via graph config dict, not by modifying node code.
**When:** Cross-cutting concerns (token tracking, tracing) that apply to all LLM calls.
**Why:** Zero changes to graph nodes. Callbacks propagate through all nested invoke() calls including ReAct sub-agent loops.
**Example:**
```python
config = {"configurable": {"thread_id": task_id}, "callbacks": [tracker]}
final_state = await self._graph.ainvoke(initial_state, config=config)
```

### Pattern 3: Circuit Breaker as Wrapper Enhancement

**What:** Enhance existing `with_audit_logging` wrapper with circuit breaker checks.
**When:** Protecting all LLM-calling nodes from Gemini API outages.
**Why:** Single integration point. Shared circuit state. Soft-fail instead of crash. Only transient API errors trip the breaker.

### Pattern 4: CLI-only for Destructive Maintenance

**What:** ChromaDB pruning and Obsidian export are CLI subcommands, never graph nodes.
**When:** Any operation that deletes data or has side effects outside the trade pipeline.
**Why:** Prevents accidental data loss during automated cycles. Human or cron must explicitly trigger.

### Pattern 5: Merge vs Add Dimensions

**What:** When a new signal improves an existing KAMI dimension, merge into that dimension rather than adding a new one.
**When:** The new signal measures the same underlying concept at higher resolution (PersonaScore is high-res fidelity).
**Why:** Avoids dimension proliferation in KAMIDimensions dataclass, compute_merit(), merit_updater, merit_loader, all tests, and config. Simpler is better.

## Anti-Patterns to Avoid

### Anti-Pattern 1: PersonaScore Inside merit_updater

**What:** Computing PersonaScore5D within the existing `merit_updater_node`.
**Why bad:** merit_updater is complex (EMA for 3 dims, DB persist, error handling). Adding LLM-as-Judge (async, can fail, separate error modes) violates SRP. Also, merit_updater runs for ACTIVE persona only; PersonaScore should evaluate ALL agents.
**Instead:** Separate `persona_eval_node`. One-cycle lag for fidelity signal.

### Anti-Pattern 2: Circuit Breaker Per-Node

**What:** Separate circuit breaker instances per graph node.
**Why bad:** Same API key, same quota. Per-node breakers allow 5x failure threshold before opening.
**Instead:** Single shared GeminiCircuitBreaker instance (module-level singleton).

### Anti-Pattern 3: Token Tracking via State Mutation

**What:** Each node manually adds token counts to `state["total_tokens"]`.
**Why bad:** ReAct sub-agents make multiple LLM calls within a single node -- manual tracking misses these. Requires every node author to remember to track. The operator.add reducer accumulates without per-node attribution.
**Instead:** LangChain callback handler automatically captures ALL LLM calls, zero node code changes.

### Anti-Pattern 4: ChromaDB Pruning as Graph Node

**What:** Adding `chroma_prune_node` to the trade pipeline.
**Why bad:** Slow, destructive, not trade-relevant. Executes every cycle, adds latency, risks data loss.
**Instead:** CLI subcommand or cron job. Decoupled from trade pipeline.

### Anti-Pattern 5: Importing from graph/ in core modules

**What:** Having circuit_breaker.py or persona_scorer.py import SwarmState or graph node types.
**Why bad:** Violates Import Layer Law enforced by test_import_boundaries.py.
**Instead:** Core modules are pure utilities. Graph layer imports them, not vice versa.

### Anti-Pattern 6: Adding PersonaScore as 5th KAMI Dimension

**What:** Adding `epsilon` weight and `persona_score` field to KAMIDimensions.
**Why bad:** Cascading changes across kami.py, merit_updater, merit_loader, KAMIDimensions dataclass, compute_merit, swarm_config.yaml, all KAMI tests. PersonaScore IS fidelity -- it measures the same concept at higher resolution.
**Instead:** Replace the binary fidelity signal with PersonaScore composite. Reuse existing delta weight.

## File Changes Summary

### New Files

| File | Layer | Purpose | Dependencies |
|------|-------|---------|--------------|
| `src/core/circuit_breaker.py` | core | GeminiCircuitBreaker singleton | stdlib only (threading, time, enum) |
| `src/core/token_tracker.py` | core | CycleTokenTracker callback handler | langchain_core.callbacks.base |
| `src/core/persona_scorer.py` | core | PersonaScore5D LLM-as-Judge | langchain_google_genai, soul_loader |
| `src/core/chroma_pruner.py` | core | Prune-to-Obsidian logic | MemoryService (injected) |
| `src/graph/nodes/persona_eval.py` | graph | persona_eval_node | persona_scorer, SwarmState |

### Modified Files

| File | Change | Risk |
|------|--------|------|
| `src/graph/orchestrator.py` | Add persona_eval node + edge after memory_writer; add circuit breaker to with_audit_logging | MEDIUM |
| `src/graph/state.py` | Add `persona_scores: Optional[Dict[str, Dict[str, float]]]` | LOW |
| `src/core/audit_logger.py` | Add `persona_scores` to AUDIT_EXCLUDED_FIELDS | LOW |
| `src/core/cycle_runner.py` | Inject CycleTokenTracker callback; extract token summary post-ainvoke | MEDIUM |
| `src/core/cycle_snapshot.py` | Add `token_usage` and `persona_scores` optional fields | LOW |
| `src/core/kami.py` | Update DEFAULT_WEIGHTS (alpha: 0.08, delta: 0.32); replace `_extract_fidelity_signal` | MEDIUM |
| `src/graph/nodes/merit_updater.py` | Fidelity signal reads persona_score composite from previous cycle | MEDIUM |
| `config/swarm_config.yaml` | Add circuit_breaker section; update kami weights; add persona_score config | LOW |
| `src/core/persistence.py` | Add token_usage column migration to cycle_snapshots | LOW |
| `src/main.py` | Add `prune` CLI subcommand | LOW |

### Dependency Build Order

```
1. ENV-FIX (no architecture impact -- restore broken deps)
   |
2. Circuit Breaker (core utility, no graph topology change)
   |  New: circuit_breaker.py
   |  Modified: orchestrator.py (with_audit_logging)
   |
3. Token Cost Tracking (callback injection, no graph topology change)
   |  New: token_tracker.py
   |  Modified: cycle_runner.py, cycle_snapshot.py
   |
4. KAMI Weight Rebalancing (config + core, prerequisite for PersonaScore)
   |  Modified: swarm_config.yaml, kami.py, merit_updater.py
   |
5. PersonaScore 5D (new graph node, depends on KAMI rebalancing)
   |  New: persona_scorer.py, persona_eval.py
   |  Modified: orchestrator.py (add node + edge), state.py, audit_logger.py
   |
6. ChromaDB Pruning + Obsidian Export (standalone, no graph deps)
   |  New: chroma_pruner.py
   |  Modified: main.py (CLI subcommand)
```

Steps 2 and 3 are independent and can be built in parallel.
Steps 4 and 5 are sequential (PersonaScore replaces fidelity signal).
Step 6 is fully independent.

## Scalability Considerations

| Concern | At 10 cycles/day | At 100 cycles/day | At 1000 cycles/day |
|---------|------------------------|--------------------|---------------------|
| PersonaScore LLM cost | 5 evals/cycle, ~$0.01/cycle | ~$1/day | ~$10/day -- cache PersonaScore for agents with unchanged output |
| Token tracking overhead | Negligible (in-memory callback) | Negligible | Negligible |
| Circuit breaker state | Single instance, 3 fields in memory | Same | Same -- stateless across restarts; consider Redis for multi-process |
| ChromaDB growth without pruning | ~500 docs/month | ~5000 docs/month | ~50000 docs/month -- MUST prune regularly |
| CycleSnapshot size increase | +200 bytes (token_usage) + ~2KB (persona_scores) | Negligible | Negligible |

## Sources

- [LangChain UsageMetadataCallbackHandler](https://python.langchain.com/api_reference/core/callbacks/langchain_core.callbacks.usage.UsageMetadataCallbackHandler.html) -- HIGH confidence
- [ChatGoogleGenerativeAI usage_metadata](https://reference.langchain.com/python/integrations/langchain_google_genai/ChatGoogleGenerativeAI/) -- MEDIUM confidence (known issues with llm_output population in callbacks)
- [ChatGoogleGenerativeAI usage_metadata issue #927](https://github.com/langchain-ai/langchain-google/issues/927) -- documents the callback gap
- [pybreaker circuit breaker](https://github.com/danielfm/pybreaker) -- HIGH confidence (pattern reference, not using as dependency)
- [aiobreaker async circuit breaker](https://github.com/arlyon/aiobreaker) -- MEDIUM confidence (pattern reference)
- [circuitbreaker PyPI](https://pypi.org/project/circuitbreaker/) -- HIGH confidence (pattern reference)
- Existing codebase: orchestrator.py, budget_manager.py, kami.py, cycle_runner.py, merit_updater.py, memory_writer.py, audit_logger.py, state.py, analysts.py -- HIGH confidence
