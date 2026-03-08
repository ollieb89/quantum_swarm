# Phase 16: KAMI Merit Index - Research

**Researched:** 2026-03-08
**Domain:** Multi-dimensional EMA merit scoring, LangGraph node wiring, PostgreSQL persistence
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Signal Inputs — Accuracy**
- Ground truth: Post-trade resolved P&L outcome — binary hit/miss (+1 / -1 / 0)
- Scoring rule: `+1` advocated direction matched profitable P&L; `-1` matched losing P&L; `0` neutral/no clear stance
- Sparsity is correct: Accuracy is sparse and delayed; "hard to observe" is evidence of correctness
- Thesis record emitted at debate time: `{agent_id (soul handle), decision_id, instrument, direction, timestamp}`
- Update path: Deferred async — Accuracy EMA updates only when a trade resolves, NOT in-cycle

**Signal Inputs — Recovery**
- Measures: Self-induced operational reliability — clean-call rate
- Scoring rule: `+1` clean invocation; `0` error invocation
- Self-induced errors (`INVALID_INPUT`, schema failures, malformed outputs, tool invocation errors) penalise caller's Recovery
- Upstream-induced errors attributed to producer via `producer_agent_id` provenance, NOT consumer
- EMA gives bounce-back implicitly — no streak detection needed

**Signal Inputs — Consensus**
- Measures: Convergence contribution — reduces uncertainty and strengthens argument quality
- NOT directional agreement with majority (would create sycophancy incentive and penalise CASSANDRA)
- Positive signal: reduces uncertainty, strengthens argument quality, changes confidence in right direction
- Operational proxy: confidence resolution delta from `debate_resolution` — argument novelty, evidence quality, synthesizer confidence shift
- Evaluated at cycle close, not per-message

**Signal Inputs — Fidelity**
- Measures: Structural soul presence — binary gate
- `IDENTITY.md exists AND size > 0` → `1.0`; otherwise → `0.0`
- Phase 17–18 evolution path for richer checks. Do NOT attempt LLM-judged or keyword-pattern Fidelity in Phase 16

**EMA Architecture**
- Per-dimension EMA, then compose:
  ```
  EMA_acc = λ * acc_t + (1-λ) * EMA_acc_prev
  EMA_rec = λ * rec_t + (1-λ) * EMA_rec_prev
  EMA_con = λ * con_t + (1-λ) * EMA_con_prev
  EMA_fid = λ * fid_t + (1-λ) * EMA_fid_prev
  merit = α·EMA_acc + β·EMA_rec + γ·EMA_con + δ·EMA_fid
  ```
- λ configurable from `swarm_config.yaml`, default `0.9`; architecture must support per-dimension λ in future
- Cold start: uniform initial merit 0.5 — NOT seeded from `reliability_weight`
- Merit range: `[0.1, 1.0]`

**EMA Update Trigger and Timing**
- In-cycle EMA update fires after `execution_result` is written, in a new `merit_updater` node placed after `decision_card_writer`
- Dimensions updated in-cycle: Recovery, Consensus, Fidelity
- Accuracy: NOT updated in-cycle — deferred async when trade resolves
- Aborted cycles (no `execution_result`): No KAMI update
- Update frequency: once per completed evaluable cycle

**DebateSynthesizer Rewiring**
- Character-length proxy removed entirely — `len(text)` no longer used for strength
- New formula: `weighted_consensus_score = merit[bullish_agent] / (merit[bullish_agent] + merit[bearish_agent])`
  - Generalised: `sum(merit of bullish agents) / (sum(merit of bullish agents) + sum(merit of bearish agents))`
- Cold start fallback: both sides zero or missing → `weighted_consensus_score = 0.5`
- Merit key: soul handles (AXIOM, MOMENTUM, CASSANDRA, SIGMA, GUARDIAN)
- Merit load point: session start via `merit_loader` node — DebateSynthesizer reads from state only

**merit_scores in SwarmState**
- New field: `merit_scores: Dict[str, Any]` — keyed by soul handle
- Audit inclusion: `merit_scores` IS included in MiFID II audit hash — NOT in `AUDIT_EXCLUDED_FIELDS`
- Canonicalize with `round(score, 4)` before hashing to prevent float jitter
- Contrast with soul fields: `system_prompt` and `active_persona` excluded; `merit_scores` is numeric operational state

**PostgreSQL Persistence**
- Table: `agent_merit_scores` (new, created in `setup_persistence()`)
- Follows existing `psycopg`/`AsyncConnectionPool` pattern from `src/core/db.py` and `src/core/persistence.py`
- Write after each in-cycle EMA update; read at session start into `SwarmState["merit_scores"]`

**reliability_weight Disposition**
- Preserved as separate concern — not removed, not merged with KAMI
- `reliability_weight` = static orchestration prior (routing hint, budget allocation, tie-break fallback)
- `merit_scores` (KAMI) = dynamic earned merit — owned by KAMI, read by DebateSynthesizer
- DebateSynthesizer reads KAMI only post-Phase 16

### Claude's Discretion

- Exact `swarm_config.yaml` schema for KAMI weights (α, β, γ, δ) and λ values
- `agent_merit_scores` table schema (columns, indexes)
- Whether per-dimension EMA values are persisted to DB as separate columns or as a JSONB blob
- `SwarmState["merit_scores"]` internal structure (flat composite float vs. nested dimension dict)
- How Consensus dimension signal is computed from `debate_resolution` in practice (confidence delta proxy implementation)
- Exact error classification logic for Recovery blame attribution (producer provenance tagging mechanism)
- Whether `merit_updater` is a LangGraph node or a post-node hook
- How deferred Accuracy updates are triggered (async task, next-session reconciliation, or explicit resolution event)

### Deferred Ideas (OUT OF SCOPE)

- Semantic Fidelity (LLM-judged persona adherence) — Phase 18 (Theory of Mind)
- Per-dimension λ (different decay rates per dimension) — Phase 17+
- Adaptive KAMI weights (α/β/γ/δ) — future phase
- `reliability_weight` deprecation — not a Phase 16 decision
- Accuracy resolution event infrastructure at scale — future phase
- Merit dashboard / observability UI — future phase
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| KAMI-01 | Agent merit computed via multi-dimensional formula (Accuracy + Recovery + Consensus + Fidelity) with configurable weights (default α=0.30, β=0.35, γ=0.25, δ=0.10) stored in `swarm_config.yaml` | `compute_merit()` function in `src/core/kami.py`; `kami:` config section in `swarm_config.yaml` |
| KAMI-02 | Merit uses EMA decay (configurable λ, default 0.9), cold start 0.5, bounded to [0.1, 1.0]; self-induced tool failures penalise Recovery dimension | Per-dimension EMA struct; `_apply_ema()` helper; Recovery signal extraction from execution_result; floor/ceiling clamp |
| KAMI-03 | `merit_scores: Dict[str, float]` in SwarmState; loaded from `agent_merit_scores` PostgreSQL table at session start, persisted after each cycle | `merit_loader` node; `merit_updater` node; `agent_merit_scores` table in `setup_persistence()` |
| KAMI-04 | DebateSynthesizer uses KAMI scores for consensus weighting; skeleton agents with empty IDENTITY.md receive weight_multiplier=0.0 | Surgical `len()` replacement in `debate.py`; Fidelity gate producing 0.0 merit for empty IDENTITY.md |
</phase_requirements>

---

## Summary

Phase 16 adds a multi-dimensional earned-merit layer (KAMI) to the swarm. Four signal dimensions — Accuracy (deferred P&L outcome), Recovery (operational clean-call rate), Consensus (convergence contribution), and Fidelity (structural soul presence) — each evolve as independent EMAs before being composed into a single composite score. The composite is bounded to `[0.1, 1.0]` and replaces character-length as the weighting signal in DebateSynthesizer.

The implementation splits cleanly into five deliverables: (1) a pure `compute_merit()` function in a new `src/core/kami.py` module; (2) a `merit_loader` node that reads persisted scores from PostgreSQL into `SwarmState["merit_scores"]` at session start; (3) a `merit_updater` node placed after `decision_card_writer` that computes in-cycle EMA updates for Recovery, Consensus, and Fidelity, then persists to DB; (4) a surgical rewire of `DebateSynthesizer` to use KAMI scores instead of `len(text)`; and (5) a new `agent_merit_scores` table in `setup_persistence()`.

The codebase is well-prepared for this phase. `SwarmState`, `persistence.py`, `soul_loader.py`, and `audit_logger.py` all have stable, understood patterns that the planner can extend directly. The two key design decisions left to the planner are: whether `merit_scores` stores flat composite floats or nested dimension dicts in state, and how the Consensus signal is practically computed from `debate_resolution`.

**Primary recommendation:** Implement `src/core/kami.py` as a pure-Python module with no LLM calls, wire `merit_loader` and `merit_updater` as standard LangGraph nodes, and persist per-dimension EMAs as a JSONB blob so dimension history is recoverable without schema migration.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| psycopg (psycopg3) | project-pinned | Async PostgreSQL — `agent_merit_scores` read/write | Already used in `persistence.py` and `db.py`; `psycopg_pool.AsyncConnectionPool` pattern established |
| psycopg_pool | project-pinned | Connection pool for async DB access | `AsyncConnectionPool` already used in `setup_persistence()` |
| Python `functools` (stdlib) | 3.12 | EMA state could use dataclasses; no external dep needed | All merit math is simple floats; stdlib is sufficient |
| Python `pathlib` (stdlib) | 3.12 | Fidelity check — `Path(...).stat().st_size > 0` | Same pattern used in `soul_loader.py` |
| PyYAML / yaml (project dep) | project-pinned | Load α, β, γ, δ, λ from `swarm_config.yaml` | Already used in `orchestrator.py` via `yaml.safe_load()` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `dataclasses` (stdlib) | 3.12 | `KAMIScores` frozen dataclass for per-agent dimension EMAs | Structuring the per-agent score bundle; frozen for cache safety |
| `json` (stdlib) | 3.12 | JSONB serialization for per-dimension EMA blob | If planner chooses JSONB column for dimension storage |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSONB blob for dimensions | Separate numeric columns | Columns give SQL-queryable history but require migration; JSONB is more flexible for future dimensions |
| Plain `Dict` for KAMIScores | `@dataclass(frozen=True)` | Dataclass gives type safety and IDE support; dict is lighter |
| `merit_loader` as orchestrator init step | LangGraph node | Node approach keeps the graph self-contained and testable in isolation |

**Installation:** No new packages required. All dependencies are in the existing `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

```
src/core/
├── kami.py              # compute_merit(), KAMIDimensions dataclass, EMA update logic
src/graph/nodes/
├── merit_loader.py      # Session-start node: reads agent_merit_scores → SwarmState
├── merit_updater.py     # Post-execution node: EMA update + DB persist
src/graph/
├── debate.py            # Surgical edit: replace len(text) with merit score lookup
├── state.py             # Add merit_scores: Optional[Dict[str, Any]] plain field
src/core/
├── persistence.py       # Add CREATE TABLE IF NOT EXISTS agent_merit_scores block
config/
├── swarm_config.yaml    # Add kami: section (α, β, γ, δ, λ, default_merit)
tests/
├── test_kami.py         # Unit tests for compute_merit, EMA, floor/ceil, cold start
tests/core/
├── test_merit_loader.py # Integration: mock DB, verify state field populated
├── test_merit_updater.py # Integration: mock state, verify EMA update + DB write
```

### Pattern 1: Pure `compute_merit()` Function

**What:** Stateless function accepts current dimension EMA values and weights, returns a clamped composite float.
**When to use:** Called by `merit_updater` after EMA update step; also called directly in unit tests.

```python
# src/core/kami.py
from dataclasses import dataclass
from typing import Dict

DEFAULT_MERIT = 0.5
MERIT_FLOOR = 0.1
MERIT_CEIL = 1.0


@dataclass(frozen=True)
class KAMIDimensions:
    """Per-agent EMA state snapshot. Frozen for test isolation and cache safety."""
    accuracy: float = DEFAULT_MERIT
    recovery: float = DEFAULT_MERIT
    consensus: float = DEFAULT_MERIT
    fidelity: float = DEFAULT_MERIT


def compute_merit(dims: KAMIDimensions, weights: Dict[str, float]) -> float:
    """Return composite merit in [0.1, 1.0].

    weights keys: alpha (accuracy), beta (recovery), gamma (consensus), delta (fidelity)
    """
    raw = (
        weights["alpha"] * dims.accuracy
        + weights["beta"] * dims.recovery
        + weights["gamma"] * dims.consensus
        + weights["delta"] * dims.fidelity
    )
    return max(MERIT_FLOOR, min(MERIT_CEIL, raw))


def apply_ema(prev: float, signal: float, lam: float) -> float:
    """Single-step EMA update: lam * signal + (1 - lam) * prev."""
    return lam * signal + (1.0 - lam) * prev
```

### Pattern 2: `merit_loader` Node

**What:** Session-start node that reads `agent_merit_scores` from PostgreSQL and writes `merit_scores` into `SwarmState`. No LLM calls. Follows `write_research_memory_node` pattern.
**When to use:** Registered in orchestrator graph before `classify_intent` (or as the true entry point), ensuring all downstream nodes have merit data.

```python
# src/graph/nodes/merit_loader.py
async def merit_loader_node(state: SwarmState) -> dict:
    """Load persisted merit scores from DB into SwarmState at session start."""
    scores: Dict[str, Any] = {}
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT soul_handle, composite, dimensions FROM agent_merit_scores"
            )
            async for row in cur:
                soul_handle, composite, dimensions = row
                scores[soul_handle] = {
                    **(dimensions or {}),
                    "composite": float(composite),
                }
    # Fill in cold-start defaults for any soul not yet in DB
    for handle in ALL_SOUL_HANDLES:
        if handle not in scores:
            scores[handle] = {
                "accuracy": DEFAULT_MERIT, "recovery": DEFAULT_MERIT,
                "consensus": DEFAULT_MERIT, "fidelity": DEFAULT_MERIT,
                "composite": DEFAULT_MERIT,
            }
    return {"merit_scores": scores}
```

### Pattern 3: `merit_updater` Node

**What:** Post-execution node placed after `decision_card_writer`. Extracts Recovery/Consensus/Fidelity signals from state, applies EMA update, persists to DB, returns updated `merit_scores`.
**When to use:** Fires only when `execution_result` is present. If absent (aborted cycle), returns empty dict (no-op).

```python
# src/graph/nodes/merit_updater.py
async def merit_updater_node(state: SwarmState) -> dict:
    """In-cycle KAMI EMA update for Recovery, Consensus, Fidelity dimensions."""
    if not state.get("execution_result"):
        return {}  # Aborted cycle — no KAMI update

    active_handle = state.get("active_persona", "")
    if not active_handle:
        return {}

    current_scores = state.get("merit_scores") or {}
    agent_entry = current_scores.get(active_handle, {})

    recovery_signal = _extract_recovery_signal(state)
    consensus_signal = _extract_consensus_signal(state)
    fidelity_signal = _extract_fidelity_signal(active_handle)

    lam = _get_lambda()  # from swarm_config.yaml kami.lambda
    new_rec = apply_ema(agent_entry.get("recovery", DEFAULT_MERIT), recovery_signal, lam)
    new_con = apply_ema(agent_entry.get("consensus", DEFAULT_MERIT), consensus_signal, lam)
    new_fid = apply_ema(agent_entry.get("fidelity", DEFAULT_MERIT), fidelity_signal, lam)
    new_acc = agent_entry.get("accuracy", DEFAULT_MERIT)  # Accuracy unchanged in-cycle

    dims = KAMIDimensions(accuracy=new_acc, recovery=new_rec,
                          consensus=new_con, fidelity=new_fid)
    composite = compute_merit(dims, _get_weights())

    updated_entry = {
        "accuracy": round(new_acc, 4), "recovery": round(new_rec, 4),
        "consensus": round(new_con, 4), "fidelity": round(new_fid, 4),
        "composite": round(composite, 4),
    }
    await _persist_merit(active_handle, updated_entry)

    new_scores = {**current_scores, active_handle: updated_entry}
    return {"merit_scores": new_scores}
```

### Pattern 4: DebateSynthesizer Rewire

**What:** Replace `len(bullish_text)` and `len(bearish_text)` with merit score lookups from `state["merit_scores"]`. Preserve all other DebateSynthesizer logic unchanged.

```python
# src/graph/debate.py — surgical replacement
DEFAULT_MERIT = 0.5

def DebateSynthesizer(state: SwarmState) -> dict[str, Any]:
    merit_scores = state.get("merit_scores") or {}

    # Use active_persona tags on messages OR fallback to known handle mapping
    bullish_handle = _resolve_handle(state, _BULLISH_SOURCE)  # e.g. "MOMENTUM"
    bearish_handle = _resolve_handle(state, _BEARISH_SOURCE)  # e.g. "CASSANDRA"

    bullish_merit = merit_scores.get(bullish_handle, {})
    bearish_merit = merit_scores.get(bearish_handle, {})

    bull_w = float(bullish_merit.get("composite", DEFAULT_MERIT)) if bullish_merit else DEFAULT_MERIT
    bear_w = float(bearish_merit.get("composite", DEFAULT_MERIT)) if bearish_merit else DEFAULT_MERIT

    total = bull_w + bear_w
    raw_score = (bull_w / total) if total > 0.0 else 0.5
    weighted_consensus_score = max(0.0, min(1.0, raw_score))
    ...
```

### Pattern 5: `agent_merit_scores` Table Schema

**What:** New table in `setup_persistence()`, following the existing `CREATE TABLE IF NOT EXISTS` pattern.

```sql
CREATE TABLE IF NOT EXISTS agent_merit_scores (
    soul_handle    VARCHAR(64) PRIMARY KEY,
    composite      NUMERIC(6, 4) NOT NULL DEFAULT 0.5,
    dimensions     JSONB,            -- {"accuracy":0.5,"recovery":0.5,"consensus":0.5,"fidelity":0.5}
    updated_at     TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    evolution_suspended BOOLEAN DEFAULT FALSE  -- ARS-02 pre-declaration (Phase 19)
);
CREATE INDEX IF NOT EXISTS idx_merit_soul_handle ON agent_merit_scores(soul_handle);
```

**Note on `evolution_suspended`:** REQUIREMENTS.md (ARS-02) requires this column in `agent_merit_scores`. Pre-declaring it in Phase 16 avoids an ALTER TABLE migration in Phase 19.

### Pattern 6: `swarm_config.yaml` KAMI Section

```yaml
# In config/swarm_config.yaml — add under top-level keys
kami:
  # Composite formula weights — must sum to 1.0
  alpha: 0.30   # Accuracy weight
  beta: 0.35    # Recovery weight
  gamma: 0.25   # Consensus weight
  delta: 0.10   # Fidelity weight
  # EMA decay rate — higher = more weight on recent signal
  lambda: 0.9
  # Cold-start and floor/ceiling
  default_merit: 0.5
  merit_floor: 0.1
  merit_ceil: 1.0
```

### Pattern 7: SwarmState Field Addition

**What:** Add `merit_scores` as a plain `Optional[Dict[str, Any]]` field — no `Annotated` reducer. Follows same pattern as `macro_report`, `risk_approved`, `system_prompt`.

```python
# src/graph/state.py — add to SwarmState
# Phase 16: KAMI Merit Index — earned dynamic merit keyed by soul handle.
# Plain dict field (no operator.add reducer) — merit_loader sets at session start,
# merit_updater overwrites per cycle. Included in MiFID II audit hash.
merit_scores: Optional[Dict[str, Any]]
```

**CRITICAL:** Do NOT use `Annotated[Dict, operator.add]`. That pattern is for accumulating lists (messages, trade_history, debate_history). A plain field is correct here.

### Anti-Patterns to Avoid

- **Character-length residue:** Removing `bullish_strength = float(len(bullish_text))` is not enough — also remove `"strength": bullish_strength` from `debate_history` entries or it resurrects the proxy. Replace with merit composite value.
- **`operator.add` on merit_scores:** If `merit_scores` gets an `Annotated[Dict, operator.add]` reducer, LangGraph will try to merge two dicts by addition — which is a type error. Plain field only.
- **LLM calls in merit_updater:** Merit computation is pure arithmetic. No LLM calls. The node must remain a pure Python side-effect node.
- **DB read inside DebateSynthesizer:** DebateSynthesizer is a pure aggregation node. Merit DB reads must happen only in `merit_loader` at session start; DebateSynthesizer reads from `state["merit_scores"]` only.
- **float jitter in audit hash:** Round merit values to 4 decimal places before they enter the audit hash. Use `round(score, 4)` consistently in `merit_updater` before writing to state.
- **`asyncio.run()` inside node functions:** The project MEMORY.md explicitly flags this as a project-breaking pattern (MEM-06 defect). All DB calls in nodes use `await` within the already-async node function.
- **Updating Accuracy in-cycle:** Accuracy is deferred. No code path in `merit_updater` should modify the accuracy dimension. Any accuracy update logic goes in a separate async path.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| EMA decay math | Custom rolling-window tracker, streak detection | Simple `lam * signal + (1-lam) * prev` | EMA naturally gives bounce-back; streak detection adds complexity for no benefit |
| PostgreSQL upsert | Custom INSERT + UPDATE logic | `INSERT ... ON CONFLICT (soul_handle) DO UPDATE SET ...` | psycopg3 supports upsert natively; avoids race conditions on session reconnect |
| Config loading | Ad-hoc `open(yaml_path)` in kami.py | Follow `orchestrator.py` pattern — load yaml once at init, pass config dict to nodes | Consistent with existing config loading pattern; avoids repeated file I/O |
| Fidelity check | LLM-based persona evaluation | `Path(soul_dir / agent_id / "IDENTITY.md").stat().st_size > 0` | Phase 16 fidelity is binary structural check only; LLM judging deferred to Phase 18 |
| Merit key resolution | Custom agent ID → soul handle mapping | `state["active_persona"]` already set by Phase 15 soul injection | Phase 15 wrote the soul handle into state; KAMI just reads it |

**Key insight:** KAMI is pure arithmetic on floats stored in state and DB. Any complexity creep (streaks, anomaly detection, LLM scoring) belongs to later phases. Phase 16 establishes the numeric foundation that Phase 17-19 extend.

---

## Common Pitfalls

### Pitfall 1: DebateSynthesizer Handle Resolution

**What goes wrong:** Bullish and bearish researchers are identified by message `name` tags (`bullish_research`, `bearish_research`), but KAMI merit keys are soul handles (`MOMENTUM`, `CASSANDRA`). The synthesizer needs to bridge from message tag to soul handle to do the merit lookup.

**Why it happens:** Phase 15 added `active_persona` to `SwarmState` but it's a single field (the last-set agent). It doesn't record which soul handle each researcher ran as.

**How to avoid:** Two options — (a) add `bullish_soul_handle` / `bearish_soul_handle` fields to state during researcher node execution; or (b) use a static mapping `{_BULLISH_SOURCE: "MOMENTUM", _BEARISH_SOURCE: "CASSANDRA"}` since the soul handle is deterministic per researcher role. Option (b) is simpler and correct for Phase 16 since researcher-to-soul mapping is stable.

**Warning signs:** DebateSynthesizer always getting `DEFAULT_MERIT` (0.5) for both sides — means handle lookup is falling back, probably due to key mismatch.

### Pitfall 2: `merit_scores` Field Missing from Initial State

**What goes wrong:** `merit_loader` node runs and populates `merit_scores`, but if `merit_scores` is not initialized to `None` in `run_task_async()`, LangGraph may raise a TypedDict validation error or silently skip the field.

**Why it happens:** `orchestrator.py` builds `initial_state` dict explicitly. Every new `SwarmState` field must be added to this dict in `run_task_async()`. Phase 15 established this pattern for `system_prompt` and `active_persona`.

**How to avoid:** Add `"merit_scores": None` to `initial_state` dict in `run_task_async()`. The `merit_loader` node then overwrites it before any downstream consumer reads it.

**Warning signs:** `KeyError: 'merit_scores'` in DebateSynthesizer or `merit_updater`.

### Pitfall 3: merit_updater Placed Before decision_card_writer

**What goes wrong:** If `merit_updater` is placed before `decision_card_writer` in the graph edge order, merit update reflects a cycle where the decision card may not yet have been written. This is a subtle ordering bug.

**Why it happens:** It's tempting to place `merit_updater` immediately after `order_router` for symmetry. But the locked decision says: "after `decision_card_writer`."

**How to avoid:** Graph edge: `decision_card_writer` → `merit_updater` → `trade_logger`. Replace the existing `decision_card_writer` → `trade_logger` edge.

**Warning signs:** Merit updates firing on cycles where decision card write failed.

### Pitfall 4: Float Jitter in Audit Hash

**What goes wrong:** Two runs with identical inputs produce different audit hashes because floating-point EMA results differ in the 12th decimal place.

**Why it happens:** Python floating-point arithmetic is deterministic within a single run but can differ across platforms or Python version micro-updates. JSON serialization of floats is also implementation-specific.

**How to avoid:** Apply `round(score, 4)` to all merit values before writing to `merit_scores` in state (in `merit_updater`). The audit logger then serializes `0.7312` not `0.7312499999999999...`.

**Warning signs:** `verify_chain()` returning `False` intermittently for entries containing merit scores.

### Pitfall 5: Merit DB Write Failing Silently

**What goes wrong:** `merit_updater` DB write fails (transient connection error, DB unavailable) and the in-memory `merit_scores` update proceeds — so state is updated but persistence is lost. On next session start, `merit_loader` reads stale values.

**Why it happens:** Pattern of silently logging errors and continuing (used in `write_research_memory_node`) is appropriate for memory writes but problematic for merit persistence where "the value loaded at session start matches the last persisted value" is a hard KAMI-03 requirement.

**How to avoid:** In `merit_updater`, persist to DB first, then return state update. If DB write fails, log error and return empty dict (no state update). This keeps state and DB in sync. The trade-off: a DB failure means no merit update for that cycle, which is acceptable.

**Warning signs:** `merit_scores` in state diverging from what `merit_loader` would read on next session.

### Pitfall 6: `merit_loader` Running on Every Cycle vs. Once Per Session

**What goes wrong:** If `merit_loader` is placed as a normal graph node that runs every cycle, it overwrites any in-cycle `merit_updater` updates on the next node execution.

**Why it happens:** LangGraph session = a `thread_id`. `merit_loader` is a session-start operation. If the graph loops or is re-invoked within the same thread_id, `merit_loader` could overwrite updated scores with the stale DB values from session start.

**How to avoid:** `merit_loader` should check if `state["merit_scores"]` is already populated (not None). If populated, skip DB load and return empty dict. This makes it idempotent and safe for repeated graph invocations.

**Warning signs:** merit_updater updates being immediately overwritten.

### Pitfall 7: ARS-02 Column Missing

**What goes wrong:** Phase 19 (ARS Drift Auditor) requires `evolution_suspended BOOLEAN` column in `agent_merit_scores`. If Phase 16 creates the table without it, Phase 19 must run an ALTER TABLE migration — which is risky on live data.

**Why it happens:** REQUIREMENTS.md ARS-02 explicitly names `agent_merit_scores` as the table that carries this column.

**How to avoid:** Pre-declare `evolution_suspended BOOLEAN DEFAULT FALSE` in the Phase 16 `CREATE TABLE` statement. It's a no-op until Phase 19 writes to it.

---

## Code Examples

Verified patterns from existing codebase:

### Existing `setup_persistence()` Pattern to Follow

```python
# src/core/persistence.py — existing pattern for new table creation
async with pool.connection() as conn:
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS agent_merit_scores (
        soul_handle    VARCHAR(64) PRIMARY KEY,
        composite      NUMERIC(6, 4) NOT NULL DEFAULT 0.5,
        dimensions     JSONB,
        updated_at     TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        evolution_suspended BOOLEAN DEFAULT FALSE
    );
    CREATE INDEX IF NOT EXISTS idx_merit_soul_handle ON agent_merit_scores(soul_handle);
    """)
```

### Existing `write_research_memory_node` Pattern (Template for merit_updater)

```python
# src/graph/nodes/write_research_memory.py — pattern for lightweight post-node
def write_research_memory_node(state: SwarmState, memory: "MemoryService") -> SwarmState:
    if not state.get("debate_resolution"):
        return state          # guard — same pattern as "no execution_result → no KAMI update"
    ...
    return {}                 # no state changes; write is a side effect only
```

### Upsert Pattern for agent_merit_scores

```python
# Idiomatic psycopg3 upsert for merit persistence
await conn.execute(
    """
    INSERT INTO agent_merit_scores (soul_handle, composite, dimensions, updated_at)
    VALUES (%s, %s, %s, NOW())
    ON CONFLICT (soul_handle) DO UPDATE SET
        composite   = EXCLUDED.composite,
        dimensions  = EXCLUDED.dimensions,
        updated_at  = EXCLUDED.updated_at
    """,
    (soul_handle, composite, json.dumps(dimensions))
)
```

### Fidelity Check Using soul_loader

```python
# Option A — via AgentSoul.identity (lru_cached, preferred)
from src.core.soul_loader import load_soul, SoulNotFoundError
def _extract_fidelity_signal(agent_id: str) -> float:
    try:
        soul = load_soul(agent_id)
        return 1.0 if soul.identity.strip() else 0.0
    except SoulNotFoundError:
        return 0.0

# Option B — direct file size check (no cache dependency)
from pathlib import Path
from src.core.soul_loader import SOULS_DIR
def _extract_fidelity_signal(agent_id: str) -> float:
    identity_path = SOULS_DIR / agent_id / "IDENTITY.md"
    try:
        return 1.0 if identity_path.stat().st_size > 0 else 0.0
    except (FileNotFoundError, OSError):
        return 0.0
```

**Recommendation:** Use Option A (via `load_soul`) to stay consistent with Phase 15 infrastructure. Option B is a safe fallback if cache behavior causes issues during testing.

### Consensus Signal Extraction

```python
# Practical proxy: confidence resolution delta from debate_resolution
def _extract_consensus_signal(state: SwarmState) -> float:
    """Extracts Consensus signal from debate_resolution.

    Proxy: distance from neutral (0.5) in weighted_consensus_score.
    High confidence in either direction → agent contributed to convergence.
    Score near 0.5 → inconclusive debate → no positive consensus contribution.
    """
    score = state.get("weighted_consensus_score")
    if score is None:
        return 0.0  # No debate → no consensus contribution
    # Normalize: |score - 0.5| * 2 maps [0.5] → 0.0 and [0.0 or 1.0] → 1.0
    return min(1.0, abs(score - 0.5) * 2.0)
```

**Note:** This is the recommended implementation of the "Claude's Discretion" Consensus proxy. The CONTEXT.md specifies "confidence resolution delta from `debate_resolution`" — the normalized distance from neutral satisfies this. It is not directional (does not penalise CASSANDRA for being contrarian) and uses an already-computed field.

### Recovery Signal Extraction

```python
def _extract_recovery_signal(state: SwarmState) -> float:
    """Extract Recovery signal: 1.0 if execution succeeded, 0.0 on self-induced error."""
    result = state.get("execution_result") or {}
    if result.get("success") is True:
        return 1.0
    # Check for self-induced error markers
    error_type = result.get("error_type", "")
    if error_type in {"INVALID_INPUT", "SCHEMA_FAILURE", "MALFORMED_OUTPUT", "TOOL_ERROR"}:
        return 0.0
    # Upstream-induced errors: check producer_agent_id provenance
    if result.get("producer_agent_id") and result.get("producer_agent_id") != state.get("active_persona"):
        return 1.0  # Not self-induced — do not penalise this agent
    return 0.0  # Default: penalise on any failure without clear upstream attribution
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Character-length proxy (`len(bullish_text)`) | KAMI merit score per soul handle | Phase 16 | DebateSynthesizer weighted consensus becomes earned rather than verbose |
| No in-graph merit tracking | `merit_scores` in SwarmState, loaded from DB | Phase 16 | Merit persists across sessions; no cold-start penalty after first cycle |
| `reliability_weight` static config | `reliability_weight` preserved for orchestration; KAMI for debate weighting | Phase 16 | Two-track system: static routing priors + dynamic earned merit |

**Note on existing soul state (important for Fidelity):** All five current soul agents (macro_analyst/AXIOM, bullish_researcher/MOMENTUM, bearish_researcher/CASSANDRA, quant_modeler/SIGMA, risk_manager/GUARDIAN) have non-empty IDENTITY.md files. All will receive `fidelity = 1.0` from Phase 16. The Fidelity gate is a future-proofing measure for genuinely empty skeleton agents.

---

## Open Questions

1. **DebateSynthesizer handle mapping for multi-agent debates**
   - What we know: In Phase 16, bullish researcher = MOMENTUM soul, bearish = CASSANDRA soul. The mapping is stable.
   - What's unclear: If future phases add multiple bullish agents simultaneously, the static mapping breaks.
   - Recommendation: Implement static mapping `{_BULLISH_SOURCE: "MOMENTUM", _BEARISH_SOURCE: "CASSANDRA"}` in Phase 16. Note the extension point with a comment for Phase 17+.

2. **merit_loader placement in graph**
   - What we know: Must run before DebateSynthesizer; must not overwrite mid-session updates.
   - What's unclear: Whether to place as graph entry point (before `classify_intent`) or as a parallel first node.
   - Recommendation: Place `merit_loader` before `classify_intent` as the new graph entry point (set `merit_loader` as entry, add edge `merit_loader → classify_intent`). Simpler than parallel placement and guarantees merit is always loaded.

3. **Accuracy deferred update path**
   - What we know: Accuracy updates async when a trade resolves; thesis records emitted at debate time.
   - What's unclear: Where does the deferred Accuracy update actually trigger in Phase 16? The CONTEXT.md says "deferred async update" but does not specify the trigger mechanism.
   - Recommendation: In Phase 16, stub the deferred path. Emit thesis records to a `data/thesis_records/` directory (JSONL) and note in a comment that a reconciliation process will consume them. The actual Accuracy EMA update path can be implemented as a CLI script or Phase 17 addition. This satisfies KAMI-01/02 without needing a full event pipeline.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (Python 3.12) |
| Config file | none — see venv note |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/test_kami.py tests/core/test_merit_loader.py tests/core/test_merit_updater.py -x -q` |
| Full suite command | `.venv/bin/python3.12 -m pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| KAMI-01 | `compute_merit()` returns float in [0.1, 1.0] using formula with weights from config | unit | `.venv/bin/python3.12 -m pytest tests/test_kami.py::test_compute_merit_formula -x` | Wave 0 |
| KAMI-01 | Default weights (α=0.30, β=0.35, γ=0.25, δ=0.10) sum to 1.0 | unit | `.venv/bin/python3.12 -m pytest tests/test_kami.py::test_default_weights_sum_to_one -x` | Wave 0 |
| KAMI-02 | EMA update: new value = λ * signal + (1-λ) * prev | unit | `.venv/bin/python3.12 -m pytest tests/test_kami.py::test_apply_ema -x` | Wave 0 |
| KAMI-02 | Cold start returns 0.5; bounded to [0.1, 1.0] floor/ceiling | unit | `.venv/bin/python3.12 -m pytest tests/test_kami.py::test_cold_start_and_bounds -x` | Wave 0 |
| KAMI-02 | INVALID_INPUT error decreases Recovery (signal=0.0, not 1.0) | unit | `.venv/bin/python3.12 -m pytest tests/test_kami.py::test_recovery_penalised_on_invalid_input -x` | Wave 0 |
| KAMI-03 | `merit_scores` field in SwarmState survives LangGraph cycle without accumulation | integration | `.venv/bin/python3.12 -m pytest tests/core/test_merit_loader.py::test_merit_scores_field_no_accumulation -x` | Wave 0 |
| KAMI-03 | `merit_loader` populates state from DB; cold-start defaults to 0.5 for unknown agents | integration | `.venv/bin/python3.12 -m pytest tests/core/test_merit_loader.py::test_merit_loader_cold_start -x` | Wave 0 |
| KAMI-03 | `merit_updater` persists updated scores to DB and returns updated `merit_scores` | integration | `.venv/bin/python3.12 -m pytest tests/core/test_merit_updater.py::test_merit_updater_persists -x` | Wave 0 |
| KAMI-04 | DebateSynthesizer uses merit scores not `len(text)` | unit | `.venv/bin/python3.12 -m pytest tests/test_adversarial_debate.py::test_debate_synthesizer_uses_merit -x` | Wave 0 |
| KAMI-04 | Skeleton agent (empty IDENTITY.md) receives weight_multiplier=0.0 via fidelity=0.0 | unit | `.venv/bin/python3.12 -m pytest tests/test_kami.py::test_fidelity_zero_for_empty_identity -x` | Wave 0 |
| KAMI-04 | Both sides zero merit → weighted_consensus_score=0.5 (neutral fallback) | unit | `.venv/bin/python3.12 -m pytest tests/test_adversarial_debate.py::test_debate_synthesizer_neutral_fallback -x` | Wave 0 |
| All | `merit_scores` in audit hash — round-trip SHA-256 deterministic with rounded floats | unit | `.venv/bin/python3.12 -m pytest tests/test_audit_chain.py::test_merit_scores_in_audit_hash -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/bin/python3.12 -m pytest tests/test_kami.py tests/core/test_merit_loader.py tests/core/test_merit_updater.py -x -q`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_kami.py` — unit tests for `compute_merit`, `apply_ema`, cold start, floor/ceil, fidelity gate; covers KAMI-01, KAMI-02, KAMI-04
- [ ] `tests/core/test_merit_loader.py` — mock DB, verify `merit_scores` populated; covers KAMI-03
- [ ] `tests/core/test_merit_updater.py` — mock state + DB, verify EMA update + persist; covers KAMI-03
- [ ] `tests/test_adversarial_debate.py` — add `test_debate_synthesizer_uses_merit` and `test_debate_synthesizer_neutral_fallback` to existing test file; covers KAMI-04
- [ ] `tests/test_audit_chain.py` — add `test_merit_scores_in_audit_hash`; covers audit requirement from CONTEXT.md

---

## Sources

### Primary (HIGH confidence)

- Direct code read: `src/graph/debate.py` — DebateSynthesizer implementation, exact replacement points for `len(text)`
- Direct code read: `src/graph/state.py` — SwarmState TypedDict structure, reducer patterns
- Direct code read: `src/core/persistence.py` — `setup_persistence()` CREATE TABLE pattern, `AsyncConnectionPool` usage
- Direct code read: `src/core/db.py` — `get_pool()`, `AsyncConnectionPool`, `get_db_connection()` patterns
- Direct code read: `src/core/audit_logger.py` — `AUDIT_EXCLUDED_FIELDS`, `_strip_excluded()`, `_calculate_hash()` with `sort_keys=True`
- Direct code read: `src/core/soul_loader.py` — `load_soul()`, `AgentSoul.identity`, `SOULS_DIR`, `_KNOWN_AGENTS`
- Direct code read: `src/graph/orchestrator.py` — node registration pattern, `with_audit_logging`, `initial_state` dict, `warmup_soul_cache()` placement
- Direct code read: `config/swarm_config.yaml` — existing config structure; `reliability_weight` fields for agents
- Direct code read: `src/graph/nodes/write_research_memory.py` — lightweight post-node pattern
- Direct code read: `.planning/phases/16-kami-merit-index/16-CONTEXT.md` — all locked decisions
- Direct code read: `.planning/REQUIREMENTS.md` — KAMI-01 through KAMI-04 exact requirement text; ARS-02 column pre-declaration requirement
- Direct code read: `tests/core/conftest.py` — `clear_soul_caches` autouse fixture pattern

### Secondary (MEDIUM confidence)

- Soul file inspection: all five soul agents have non-empty IDENTITY.md files (confirmed by `wc -c`) — Fidelity check returns 1.0 for all current agents

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all patterns directly verified in existing codebase
- Architecture: HIGH — patterns copied from Phase 15 and existing nodes; EMA math is textbook
- Pitfalls: HIGH — most pitfalls derived from direct inspection of existing code (TypedDict reducers, audit hash, DB pattern)
- Consensus signal proxy: MEDIUM — the confidence delta implementation is a design recommendation within Claude's Discretion; logic sound but not verified against live debate data

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable domain — psycopg3, LangGraph, Python EMA math are not fast-moving)
