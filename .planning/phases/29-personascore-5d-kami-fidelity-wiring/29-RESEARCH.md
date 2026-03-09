# Phase 29: PersonaScore 5D + KAMI Fidelity Wiring - Research

**Researched:** 2026-03-09
**Domain:** LLM-as-Judge persona evaluation, KAMI merit integration, async post-cycle hooks
**Confidence:** HIGH

## Summary

Phase 29 introduces quantitative persona fidelity evaluation via LLM-as-Judge, producing a 5-dimensional PersonaScore (Consistency, Tone, Logic, Depth, Bias) for each of the 4 LLM agents (AXIOM, MOMENTUM, CASSANDRA, SIGMA) after every cycle. The composite score replaces the current binary 0/1 fidelity signal in KAMI. The evaluation runs as a CycleRunner post-cycle hook, entirely outside the graph topology and audit hash chain.

The codebase has clean integration points: `CycleRunner.run_cycle()` has a clear seam after `_write_snapshot_file()` and `_update_cycle_row()` where the hook attaches. The existing `_extract_fidelity_signal()` in `kami.py` is a simple binary check (soul.identity non-empty -> 1.0, else 0.0) that must be rewired to read the previous cycle's PersonaScore composite from the database. The circuit breaker from Phase 28 is reusable for resilience around the judge LLM calls.

**Primary recommendation:** Build a standalone `src/core/persona_scorer.py` module (pure core, no graph imports) that encapsulates the LLM-as-Judge logic, Pydantic models, and DB persistence. Wire it into `CycleRunner` as an async post-cycle method. Rewire `_extract_fidelity_signal()` to query the `persona_scores` table.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- LLM-as-Judge receives **full soul files** (IDENTITY.md + SOUL.md + AGENTS.md) as persona reference
- Judge compares agent's **primary output field** against soul definition (AXIOM->macro_report, SIGMA->quant_proposal, MOMENTUM->bullish_thesis, CASSANDRA->bearish_thesis)
- 5 dimensions scored as **0.0-1.0 floats**: Consistency, Tone, Logic, Depth, Bias
- **One LLM call per agent** (4 calls total), run in **parallel** via asyncio.gather()
- Composite PersonaScore = **simple average** of the 5 dimension floats
- Only **4 LLM agents** evaluated: AXIOM, MOMENTUM, CASSANDRA, SIGMA (GUARDIAN excluded)
- **New `persona_scores` PostgreSQL table** (not extending agent_merit_scores)
- Columns: id, cycle_id, soul_handle, consistency, tone, logic, depth, bias, composite, rationale (TEXT), scored_at
- **Full history** retained — one row per agent per cycle (4 rows/cycle)
- **Rationale string stored** alongside scores
- PersonaScore results **embedded in CycleSnapshot** (filesystem JSON) for offline replay
- Fires **after snapshot persist** — cycle data is safe before evaluation begins
- 4 evaluations run in **parallel** (asyncio.gather)
- After evaluation, results written to DB and snapshot file updated
- **Skip for failed cycles**, **evaluate for rejected cycles**
- On LLM failure: **fall back to previous cycle's PersonaScore composite**
- **Reuse Phase 28 circuit breaker** for evaluation LLM calls
- **Persist partial results** — successful scores stored, failures use fallback
- Never crash or block cycle completion

### Claude's Discretion
- Exact LLM prompt template and rubric wording for the 5 dimensions
- PersonaScore Pydantic model design
- How snapshot file is updated after post-cycle evaluation (rewrite vs append)
- DB migration script structure
- How `_extract_fidelity_signal()` in kami.py is rewired to read PersonaScore composite

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SOUL-09 | PersonaScore 5D evaluates persona fidelity across Consistency, Tone, Logic, Depth, and Bias dimensions using LLM-as-Judge | LLM-as-Judge prompt design, Pydantic structured output, soul_loader integration |
| SOUL-10 | PersonaScore runs as CycleRunner post-cycle hook (not a graph node) | CycleRunner.run_cycle() seam after line 279, async method attachment |
| SOUL-11 | PersonaScore evaluates 4 LLM agents (AXIOM, MOMENTUM, CASSANDRA, SIGMA) | HANDLE_TO_AGENT_ID mapping, _CANONICAL_FIELD_MAP for output fields |
| SOUL-12 | PersonaScore results persist to PostgreSQL and are available to KAMI fidelity | New persona_scores table, _extract_fidelity_signal() rewiring |
| SOUL-13 | PersonaScore uses structured output (Pydantic schema) with 5 float dimensions + rationale | Pydantic model design, Gemini structured output via with_structured_output() |
| KAMI-05 | KAMI fidelity dimension consumes PersonaScore continuous signal (replaces binary 0/1) | _extract_fidelity_signal() rewire to DB query, EMA integration unchanged |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langchain-google-genai | existing | LLM calls for judge evaluation | Project's LLM provider (Gemini 2.5 Flash) |
| pydantic | existing | PersonaScore structured output model | Already used for CycleSnapshot, structured output |
| psycopg | existing | PostgreSQL persistence for persona_scores | Project's DB driver |
| asyncio | stdlib | Parallel evaluation (gather) | Project pattern for concurrent I/O |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog/logging | existing | Evaluation event logging | All persona scoring events |

### Alternatives Considered
None -- all decisions are locked. The stack is entirely existing project dependencies.

**Installation:**
```bash
# No new dependencies required
```

## Architecture Patterns

### Recommended Project Structure
```
src/core/
├── persona_scorer.py       # NEW: LLM-as-Judge evaluator + Pydantic models + DB persist
├── kami.py                  # MODIFIED: _extract_fidelity_signal() rewired to read DB
├── cycle_runner.py          # MODIFIED: post-cycle hook calling persona_scorer
├── cycle_snapshot.py        # MODIFIED: persona_scores field added
└── persistence.py           # MODIFIED: persona_scores CREATE TABLE migration
```

### Pattern 1: Lazy LLM Initialization
**What:** Module-level LLM instances must use lazy getter pattern because Gemini validates API key at instantiation.
**When to use:** Always for any module that creates a ChatGoogleGenerativeAI instance.
**Example:**
```python
# src/core/persona_scorer.py
from langchain_google_genai import ChatGoogleGenerativeAI

_judge_llm = None

def _get_judge_llm():
    global _judge_llm
    if _judge_llm is None:
        _judge_llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.0,  # deterministic judging
        )
    return _judge_llm
```

### Pattern 2: DB-First Persistence
**What:** Write to PostgreSQL before updating in-memory state or snapshot files. If DB write fails, skip state update.
**When to use:** All persona_scores persistence.
**Example:**
```python
# Pattern from merit_updater.py lines 117-126
try:
    await _persist_persona_score(soul_handle, score)
except Exception as e:
    logger.error("persona_scorer: DB persist failed for %s: %s", soul_handle, e)
    # Use fallback score, do NOT crash
```

### Pattern 3: Core Module Import Boundary
**What:** `src/core/*` must NOT import from `src/graph/*`. The persona_scorer module lives in core and receives data via function parameters, not by importing graph modules.
**When to use:** persona_scorer.py must follow this strictly.
**Key implication:** The soul handle -> output field mapping must be defined in persona_scorer.py (or kami.py), NOT imported from memory_writer.py (which is in graph/nodes).

### Pattern 4: AUDIT_EXCLUDED_FIELDS Extension
**What:** PersonaScore fields must be excluded from the MiFID II audit hash chain.
**When to use:** Any new SwarmState/CycleSnapshot fields that are infrastructure metadata.
**Example:**
```python
# In audit_logger.py -- add persona_scores to the exclusion set
AUDIT_EXCLUDED_FIELDS: frozenset[str] = frozenset({
    "system_prompt", "active_persona", "soul_sync_context",
    "soft_failed_nodes", "persona_scores",
})
```

### Pattern 5: Structured Output with Pydantic
**What:** Use `with_structured_output()` on the LLM to get typed PersonaScore responses.
**When to use:** The judge LLM call.
**Example:**
```python
from pydantic import BaseModel, Field

class PersonaScoreResult(BaseModel):
    """LLM-as-Judge evaluation result for one agent."""
    consistency: float = Field(ge=0.0, le=1.0, description="Alignment with soul's core beliefs and stated positions")
    tone: float = Field(ge=0.0, le=1.0, description="Match to soul's defined voice and communication style")
    logic: float = Field(ge=0.0, le=1.0, description="Reasoning quality and analytical rigor appropriate to role")
    depth: float = Field(ge=0.0, le=1.0, description="Thoroughness and detail level matching soul's defined depth")
    bias: float = Field(ge=0.0, le=1.0, description="Appropriate directional stance per role (1.0 = well-calibrated)")
    rationale: str = Field(description="Brief explanation of scores")

    @property
    def composite(self) -> float:
        return round((self.consistency + self.tone + self.logic + self.depth + self.bias) / 5.0, 4)

# Usage
judge = _get_judge_llm().with_structured_output(PersonaScoreResult)
result = await judge.ainvoke(prompt)
```

### Anti-Patterns to Avoid
- **PersonaScore as a graph node:** Would create circular evaluation, corrupt audit hash chain, and contaminate budget tracking. It is a post-cycle hook by design.
- **asyncio.run() inside nodes:** Project-breaking pattern. The persona_scorer runs in an already-async context (CycleRunner.run_cycle() is async).
- **Importing from src.graph in persona_scorer:** Violates Import Layer Law. Pass data as parameters.
- **Extending agent_merit_scores table:** Decision locked to new `persona_scores` table for history retention.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured LLM output parsing | Custom JSON parsing | `with_structured_output(PersonaScoreResult)` | Handles retries, validation, type coercion |
| Circuit breaker for judge calls | New breaker instance | Reuse Phase 28 `CircuitBreaker` class | Same transient error patterns (429, 503, timeout) |
| DB connection management | Manual pool management | `ensure_pool_open()` from `src/core/db.py` | Handles sticky unavailability flag, lazy init |
| Soul file loading | Manual file reads | `load_soul(agent_id)` from `soul_loader.py` | Cached, security-checked, includes all files |

**Key insight:** Every infrastructure piece needed (LLM wrapper, circuit breaker, DB pool, soul loading) already exists. This phase is purely new application logic wired into existing patterns.

## Common Pitfalls

### Pitfall 1: Snapshot File Update Race Condition
**What goes wrong:** CycleRunner writes snapshot.json, then persona scorer re-reads and re-writes it. If the process crashes between, the snapshot lacks persona_scores.
**Why it happens:** Two-phase write to the same file.
**How to avoid:** Read snapshot.json, add persona_scores field, rewrite atomically. Use `model_dump()` -> update dict -> `json.dumps()` -> write. The snapshot is already persisted safely before evaluation starts (locked decision), so partial update is acceptable.
**Warning signs:** Missing persona_scores in snapshot.json files.

### Pitfall 2: _extract_fidelity_signal() Circular Import
**What goes wrong:** `_extract_fidelity_signal()` in `kami.py` already does a lazy import of `soul_loader`. Rewiring it to query the DB could introduce new import chains.
**Why it happens:** kami.py is core; DB access is also core. But adding async DB queries to a currently-sync function changes its contract.
**How to avoid:** Keep `_extract_fidelity_signal()` synchronous. It should accept the previous PersonaScore composite as a parameter (injected by merit_updater), not query the DB itself. The merit_updater node (async) does the DB query and passes the value.
**Warning signs:** `_extract_fidelity_signal()` becoming async or importing DB modules.

### Pitfall 3: Parallel Evaluation Error Handling
**What goes wrong:** `asyncio.gather()` with `return_exceptions=False` (default) means one failed evaluation aborts all others.
**Why it happens:** Default gather behavior.
**How to avoid:** Use `asyncio.gather(*tasks, return_exceptions=True)` and check each result for isinstance(result, Exception). Successful results persist; failed results use fallback.
**Warning signs:** All 4 scores missing when only 1 LLM call failed.

### Pitfall 4: Agent Output Field is None (Degraded Cycle)
**What goes wrong:** In a degraded cycle (soft-failed nodes from circuit breaker), some agent output fields may be None. Passing None to the judge prompt produces nonsensical scores.
**Why it happens:** Phase 28 circuit breaker returns empty dict for soft-failed nodes.
**How to avoid:** Check the agent's output field before evaluation. If None, skip that agent (use fallback score). Only evaluate agents with non-None output.
**Warning signs:** PersonaScore for agents that didn't actually produce output.

### Pitfall 5: Judge Prompt Token Cost
**What goes wrong:** Full soul files (IDENTITY.md + SOUL.md + AGENTS.md) are ~2-4KB each. With 4 agents, that is 8-16KB of context per cycle just for evaluation.
**Why it happens:** Locked decision to include full soul files.
**How to avoid:** This is expected behavior. Log token usage for visibility. The cost is bounded (4 calls x ~3KB context + agent output per call).
**Warning signs:** Budget alerts during evaluation. Consider excluding AGENTS.md from the prompt if token cost becomes prohibitive (but this would require user decision change).

## Code Examples

### PersonaScore Pydantic Model
```python
# src/core/persona_scorer.py
from pydantic import BaseModel, Field
from typing import Optional

class PersonaScoreResult(BaseModel):
    """Single agent's 5D persona fidelity evaluation."""
    consistency: float = Field(ge=0.0, le=1.0)
    tone: float = Field(ge=0.0, le=1.0)
    logic: float = Field(ge=0.0, le=1.0)
    depth: float = Field(ge=0.0, le=1.0)
    bias: float = Field(ge=0.0, le=1.0)
    rationale: str

    @property
    def composite(self) -> float:
        return round(
            (self.consistency + self.tone + self.logic + self.depth + self.bias) / 5.0,
            4,
        )

class PersonaScoreEntry(BaseModel):
    """Persistable entry for one agent in one cycle."""
    soul_handle: str
    consistency: float
    tone: float
    logic: float
    depth: float
    bias: float
    composite: float
    rationale: str
    fallback: bool = False  # True if this score is a fallback from previous cycle
```

### CycleRunner Post-Cycle Hook Integration Point
```python
# In CycleRunner.run_cycle(), after line 279 (await self._update_cycle_row(snapshot)):
# Add persona scoring hook

if snapshot.status != "failed":
    # Extract agent outputs from final_state for evaluation
    try:
        persona_results = await self._evaluate_persona_scores(
            cycle_id=snapshot.cycle_id,
            final_state=final_state,
            snapshot_path=Path(self._base_dir) / snapshot.padded_id() / "snapshot.json",
        )
    except Exception as e:
        logger.error("Persona scoring failed entirely: %s", e)
        # Never crash — cycle is already persisted
```

### _extract_fidelity_signal() Rewiring
```python
# kami.py — rewired version
def _extract_fidelity_signal(agent_id: str, persona_composite: Optional[float] = None) -> float:
    """Derive fidelity signal from PersonaScore composite (Phase 29).

    Falls back to binary soul check if no PersonaScore available (backward compat).
    """
    if persona_composite is not None:
        return persona_composite

    # Legacy fallback: binary soul identity check
    from src.core.soul_loader import load_soul
    try:
        soul = load_soul(agent_id)
    except Exception:
        return 0.0
    return 1.0 if soul.identity.strip() else 0.0
```

### DB Query for Previous Cycle's PersonaScore
```python
# Called by merit_updater to get previous composite for fidelity signal
async def get_latest_persona_composite(soul_handle: str) -> Optional[float]:
    """Fetch the most recent PersonaScore composite for a soul handle."""
    pool = await ensure_pool_open()
    if pool is None:
        return None
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT composite FROM persona_scores "
                "WHERE soul_handle = %s ORDER BY scored_at DESC LIMIT 1",
                (soul_handle,),
            )
            row = await cur.fetchone()
            return float(row[0]) if row else None
```

### Key Mappings (Must Be Duplicated in Core)
```python
# These mappings exist in memory_writer.py (graph/nodes) but persona_scorer.py (core)
# cannot import from graph. Must be duplicated.

# Soul handle -> agent_id directory name
HANDLE_TO_AGENT_ID = {
    "AXIOM": "macro_analyst",
    "MOMENTUM": "bullish_researcher",
    "CASSANDRA": "bearish_researcher",
    "SIGMA": "quant_modeler",
}

# Soul handle -> SwarmState output field
HANDLE_TO_OUTPUT_FIELD = {
    "AXIOM": "macro_report",
    "MOMENTUM": "bullish_thesis",
    "CASSANDRA": "bearish_thesis",
    "SIGMA": "quant_proposal",
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Binary fidelity (soul exists -> 1.0) | 5D PersonaScore composite (0.0-1.0) | Phase 29 | Fidelity becomes meaningful signal instead of constant 1.0 for all agents |
| Fidelity at 10% weight (delta=0.10) | Same weight, richer signal | Phase 29 | Merit differentiation increases; agents with poor persona adherence see real penalty |
| No post-cycle evaluation | LLM-as-Judge after every cycle | Phase 29 | New LLM cost per cycle (4 judge calls); new DB table |

**Note:** KAMI weight rebalancing (KAMI-06, KAMI-07) is Phase 30 scope, not Phase 29.

## Open Questions

1. **Judge LLM Temperature**
   - What we know: Temperature 0.0 is standard for evaluation/classification tasks to reduce variance.
   - What's unclear: Whether exactly 0.0 or a small value (0.1) produces better rubric adherence with Gemini 2.5 Flash.
   - Recommendation: Start with 0.0. Can adjust post-deployment based on score variance analysis.

2. **Circuit Breaker Sharing vs Isolation**
   - What we know: Phase 28 circuit breaker is a single instance for graph LLM nodes.
   - What's unclear: Should persona scoring share the same circuit breaker instance, or use a separate one?
   - Recommendation: Use a **separate CircuitBreaker instance** for persona scoring. The graph breaker protects in-cycle nodes; the persona scorer runs post-cycle. A graph-tripped breaker should not block evaluation, and vice versa.

3. **Snapshot File Update Strategy**
   - What we know: Snapshot is written once by CycleRunner, then persona_scores need to be added.
   - What's unclear: Whether to rewrite the full file or use a sidecar file.
   - Recommendation: **Rewrite the full snapshot.json** after adding persona_scores to the dict. The file is small (tens of KB) and atomic rewrite is simpler than managing sidecar files for replay CLI compatibility.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via `.venv/bin/python3.12 -m pytest`) |
| Config file | `pyproject.toml` or project root |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/core/test_persona_scorer.py -x` |
| Full suite command | `.venv/bin/python3.12 -m pytest -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SOUL-09 | 5D evaluation produces 5 floats + rationale for each agent | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_scorer.py::test_evaluate_produces_5d_scores -x` | No - Wave 0 |
| SOUL-10 | Evaluation fires as CycleRunner post-cycle hook, not graph node | integration | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_runner.py::test_post_cycle_persona_hook -x` | No - Wave 0 |
| SOUL-11 | Only AXIOM, MOMENTUM, CASSANDRA, SIGMA evaluated (not GUARDIAN) | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_scorer.py::test_evaluates_4_agents_only -x` | No - Wave 0 |
| SOUL-12 | Results persist to persona_scores table and snapshot JSON | integration | `.venv/bin/python3.12 -m pytest tests/core/test_persona_scorer.py::test_persist_to_db -x` | No - Wave 0 |
| SOUL-13 | Structured output with Pydantic validates 5 floats [0,1] + rationale | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_scorer.py::test_pydantic_validation -x` | No - Wave 0 |
| KAMI-05 | KAMI fidelity reads PersonaScore composite instead of binary | unit | `.venv/bin/python3.12 -m pytest tests/core/test_merit_updater.py::test_fidelity_reads_persona_composite -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python3.12 -m pytest tests/core/test_persona_scorer.py tests/core/test_cycle_runner.py tests/core/test_merit_updater.py -x`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/core/test_persona_scorer.py` -- covers SOUL-09, SOUL-11, SOUL-12, SOUL-13
- [ ] New test cases in `tests/core/test_cycle_runner.py` -- covers SOUL-10
- [ ] New test cases in `tests/core/test_merit_updater.py` -- covers KAMI-05
- [ ] Shared fixtures for mocking judge LLM responses (in test files or conftest)

## Sources

### Primary (HIGH confidence)
- `src/core/kami.py` -- current _extract_fidelity_signal() implementation (lines 220-241), KAMIDimensions, apply_ema
- `src/core/cycle_runner.py` -- CycleRunner.run_cycle() flow, post-persist seam (lines 278-285)
- `src/core/cycle_snapshot.py` -- CycleSnapshot Pydantic model, validate_completed()
- `src/core/soul_loader.py` -- load_soul(), AgentSoul dataclass, system_prompt property
- `src/core/circuit_breaker.py` -- CircuitBreaker class, is_transient_llm_error()
- `src/graph/nodes/merit_updater.py` -- merit_updater_node(), _persist_merit(), _extract_fidelity_signal() call site
- `src/graph/nodes/memory_writer.py` -- HANDLE_TO_AGENT_ID, _CANONICAL_FIELD_MAP mappings
- `src/core/persistence.py` -- DB schema migrations, existing table patterns
- `src/core/db.py` -- ensure_pool_open(), connection pool management
- `src/core/audit_logger.py` -- AUDIT_EXCLUDED_FIELDS pattern
- `config/swarm_config.yaml` -- KAMI weights (delta=0.10), budget config

### Secondary (MEDIUM confidence)
- LangChain structured output documentation -- `with_structured_output()` API for Pydantic models with Gemini

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project, no new dependencies
- Architecture: HIGH -- integration points verified in source code, patterns established
- Pitfalls: HIGH -- derived from actual code analysis (gather semantics, circuit breaker state, import boundaries)

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable -- no external dependency changes expected)
