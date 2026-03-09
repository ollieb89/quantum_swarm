# Phase 24: Cycle Persistence - Research

**Researched:** 2026-03-09
**Domain:** Pydantic data modeling, PostgreSQL persistence, filesystem snapshot storage
**Confidence:** HIGH

## Summary

Phase 24 introduces a CycleSnapshot Pydantic model and CycleRunner wrapper that captures the full cognitive trace of each pipeline run into both filesystem (JSON) and PostgreSQL (metadata). The domain is well-understood because all building blocks already exist in the codebase: DecisionCard provides the Pydantic model template, persistence.py provides the idempotent CREATE TABLE pattern, db.py provides the async connection pool, and LangGraphOrchestrator.run_task_async() provides the exact SwarmState initialization and invocation pattern that CycleRunner will wrap.

The core challenge is not technical novelty but correctness of extraction: ensuring CycleRunner reads every relevant field from the final SwarmState, handles the three status paths (completed/rejected/failed), and resets state between runs. The filesystem and PostgreSQL layers follow established project patterns verbatim.

**Primary recommendation:** Build CycleSnapshot as a Pydantic BaseModel in `src/core/cycle_snapshot.py`, CycleRunner as an async wrapper in `src/core/cycle_runner.py`, add the cycle_snapshots table to `setup_persistence()`, and register both modules in import boundary tests.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Agent memos captured verbatim from SwarmState fields: macro_report, quant_proposal, bullish_thesis, bearish_thesis (dict-typed, no transformation)
- Full debate_history list (all rounds with provenance) plus debate_resolution dict
- Merit scores and soul_sync_context both included in snapshot
- Weighted consensus score included
- Hybrid storage: PostgreSQL cycle_snapshots table for metadata + filesystem for full snapshot
- Cycle numbering: monotonic integer (PostgreSQL SERIAL), zero-padded for filesystem (data/cycles/0042/)
- Single file per cycle: data/cycles/{zero_padded_id}/snapshot.json
- PostgreSQL table stores queryable metadata (cycle_id, symbol, timestamp, status, consensus_score, task_id)
- External wrapper pattern: CycleRunner sits outside the graph, calls graph.ainvoke(), then extracts SwarmState fields
- No changes to existing graph nodes
- CycleRunner resets SwarmState between runs
- Module: src/core/cycle_runner.py
- CycleSnapshot Pydantic model: src/core/cycle_snapshot.py
- Failed runs persist with status='failed'
- Risk-rejected cycles persist with status='rejected'
- Status taxonomy: 'completed' | 'rejected' | 'failed'
- Optional fields strategy: agent memos and debate are required; post-risk-gate fields Optional; CYCL-02 "no Optional None" applies only to status='completed'
- Structured error_context field (Optional dict) on failed cycles: error_type, message, failed_node, traceback_summary

### Claude's Discretion
- Exact PostgreSQL table column set beyond the core fields
- Whether decision card is inlined or referenced
- CycleSnapshot field naming and nesting structure
- How zero-padding width is determined
- Filesystem directory creation strategy (eager vs lazy)

### Deferred Ideas (OUT OF SCOPE)
None

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CYCL-01 | Each pipeline run persists agent memos, debate, consensus, merit scores, and decision card to a numbered cycle folder | CycleRunner wrapper extracts from SwarmState after ainvoke(), writes snapshot.json to data/cycles/{padded_id}/ |
| CYCL-02 | CycleSnapshot Pydantic model defines the canonical artifact schema | Pydantic v2 BaseModel in src/core/cycle_snapshot.py, follows DecisionCard pattern |
| CYCL-03 | PostgreSQL cycle_snapshots table indexes cycles with monotonic numbering and queryable metadata | SERIAL primary key in setup_persistence(), async psycopg3 INSERT via db.py pool |
| CYCL-04 | Cycle manifest includes timestamp, symbol, status, and cycle_id | Top-level CycleSnapshot fields, mirrored as PostgreSQL columns with indexes |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 | CycleSnapshot model with validation | Already used for DecisionCard, AgentContributions, RiskSnapshot |
| psycopg | 3.3.3 | Async PostgreSQL access | Already used throughout via db.py pool |
| psycopg_pool | (bundled) | Connection pooling | Already used in db.py and persistence.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | - | Serializing snapshot to filesystem | snapshot.json write |
| pathlib (stdlib) | - | Filesystem path handling | data/cycles/ directory creation |
| traceback (stdlib) | - | Extracting traceback_summary for failed cycles | error_context construction |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSON file per cycle | SQLite blob | Adds dependency; JSON is human-readable and grep-friendly |
| SERIAL for cycle_id | Application-level counter | SERIAL is atomic, concurrent-safe, and already the project pattern |

**Installation:**
No new dependencies required. All libraries are already in the project.

## Architecture Patterns

### Recommended Project Structure
```
src/core/
    cycle_snapshot.py      # CycleSnapshot Pydantic model
    cycle_runner.py        # CycleRunner async wrapper
    persistence.py         # += cycle_snapshots CREATE TABLE
data/
    cycles/
        0001/snapshot.json
        0002/snapshot.json
tests/core/
    test_cycle_snapshot.py  # Model validation tests
    test_cycle_runner.py    # Runner logic tests
```

### Pattern 1: CycleSnapshot Pydantic Model
**What:** A Pydantic BaseModel defining the canonical schema for a complete cycle artifact, following the DecisionCard structural pattern.
**When to use:** Every time a pipeline run completes (any status).

**Recommended field structure:**
```python
from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, Field

class CycleSnapshot(BaseModel):
    """Complete cognitive trace of a single pipeline cycle."""

    # Manifest fields (CYCL-04)
    cycle_id: int
    task_id: str
    symbol: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Literal["completed", "rejected", "failed"]

    # Agent memos (always present for completed/rejected)
    macro_report: dict
    quant_proposal: dict
    bullish_thesis: dict
    bearish_thesis: dict

    # Debate trace
    debate_history: list[dict]
    debate_resolution: dict

    # Consensus
    weighted_consensus_score: float

    # Merit & soul context
    merit_scores: dict
    soul_sync_context: dict

    # Post-risk-gate fields (Optional for rejected/failed)
    risk_approved: Optional[bool] = None
    risk_notes: Optional[str] = None
    execution_result: Optional[dict] = None
    decision_card: Optional[dict] = None  # Inlined — avoids cross-reference complexity

    # Failure context (Optional, only for status='failed')
    error_context: Optional[dict] = None
```

**Design decision -- inline decision card:** Inline the full DecisionCard dict rather than reference by card_id. Rationale: (1) the replay CLI (Phase 26) needs the full card for display without a separate lookup, (2) the snapshot is already a complete trace by design, (3) the snapshot.json file is written once and never mutated so duplication cost is zero.

**Design decision -- zero-padding width:** Use 6 digits (e.g., `000042`). This supports up to 999,999 cycles before needing width change. Hardcode as a module constant `CYCLE_ID_PAD_WIDTH = 6`.

### Pattern 2: CycleRunner Wrapper
**What:** An async class that wraps `graph.ainvoke()`, extracts SwarmState fields into a CycleSnapshot, persists to both filesystem and PostgreSQL, and resets state between runs.
**When to use:** Replaces direct `graph.ainvoke()` calls for production pipeline execution.

```python
class CycleRunner:
    """Orchestrates a single pipeline cycle with full persistence."""

    def __init__(self, graph, config: dict, db_pool=None):
        self.graph = graph
        self.config = config
        self.db_pool = db_pool

    async def run_cycle(self, user_input: str, symbol: str) -> CycleSnapshot:
        """Execute one pipeline cycle and persist the snapshot."""
        # 1. Build fresh initial_state (same pattern as LangGraphOrchestrator.run_task_async)
        # 2. try: final_state = await self.graph.ainvoke(initial_state, config)
        #    except Exception: build failed snapshot with error_context
        # 3. Allocate cycle_id from PostgreSQL (INSERT RETURNING id)
        # 4. Extract fields from final_state into CycleSnapshot
        # 5. Determine status from final_state (completed/rejected/failed)
        # 6. Write snapshot.json to data/cycles/{padded_id}/
        # 7. UPDATE PostgreSQL row with metadata
        # 8. Return CycleSnapshot
```

**Key detail -- state reset:** CycleRunner creates a fresh `initial_state` dict for every call. This is inherent to the wrapper pattern -- each `run_cycle()` builds its own state dict. No explicit "reset" logic is needed because SwarmState is not reused across calls.

**Key detail -- cycle_id allocation:** INSERT a placeholder row into cycle_snapshots first (with status='running'), get the SERIAL id back via RETURNING, then UPDATE after the run completes. This ensures monotonic numbering even under concurrent runs.

### Pattern 3: PostgreSQL Table Addition
**What:** Add cycle_snapshots CREATE TABLE to setup_persistence() following the existing idempotent pattern.
**When to use:** Application startup.

```python
# In setup_persistence(), after section 5 (ARS):
# 6. Cycle Snapshots (Phase 24: Cycle Persistence)
async with pool.connection() as conn:
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS cycle_snapshots (
        cycle_id    SERIAL PRIMARY KEY,
        task_id     VARCHAR(64) NOT NULL,
        symbol      VARCHAR(32) NOT NULL,
        status      VARCHAR(16) NOT NULL DEFAULT 'running',
        timestamp   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        consensus_score NUMERIC(6, 4),
        snapshot_path   TEXT,
        error_summary   TEXT,
        CONSTRAINT valid_status CHECK (status IN ('running', 'completed', 'rejected', 'failed'))
    );
    CREATE INDEX IF NOT EXISTS idx_cycle_task_id ON cycle_snapshots(task_id);
    CREATE INDEX IF NOT EXISTS idx_cycle_symbol ON cycle_snapshots(symbol);
    CREATE INDEX IF NOT EXISTS idx_cycle_status ON cycle_snapshots(status);
    CREATE INDEX IF NOT EXISTS idx_cycle_timestamp ON cycle_snapshots(timestamp);
    """)
```

**Column rationale:**
- `cycle_id SERIAL`: Monotonic, auto-incrementing, PostgreSQL-native
- `task_id`: Links to LangGraph thread_id and audit_logs
- `symbol`: Queryable for "show me all BTC cycles"
- `status`: Queryable with CHECK constraint for valid values
- `timestamp`: When cycle started
- `consensus_score`: Quick filtering without loading full snapshot
- `snapshot_path`: Filesystem path to snapshot.json (e.g., `data/cycles/000042/snapshot.json`)
- `error_summary`: Brief error message for failed cycles (avoids loading snapshot for triage)

### Anti-Patterns to Avoid
- **Storing full snapshot in PostgreSQL JSONB:** The snapshot can be large (debate_history with multiple rounds). Keep full data on filesystem, metadata in PostgreSQL.
- **Modifying graph nodes to emit cycle data:** The CONTEXT.md locks "no changes to existing graph nodes." Persistence is post-graph.
- **Using SwarmState to carry cycle_id:** Cycle numbering is a persistence concern, not a graph concern. cycle_id is allocated after the graph run.
- **Reusing SwarmState across runs:** Each run_cycle() must build a fresh initial_state. The `messages` and `debate_history` fields use `operator.add` reducers and would accumulate across calls.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cycle numbering | Application-level counter with file lock | PostgreSQL SERIAL | Atomic, concurrent-safe, survives crashes |
| Data validation | Manual dict key checking | Pydantic BaseModel | Already the project pattern, gives free serialization |
| JSON serialization | Custom encoder | `model.model_dump(mode="json")` | Pydantic v2 handles datetime, nested models |
| Connection pooling | Manual connection management | Existing db.py get_pool() / get_db_connection() | Already battle-tested in the project |

**Key insight:** Every infrastructure piece needed for this phase already exists in the codebase. The phase is purely about composition, not new infrastructure.

## Common Pitfalls

### Pitfall 1: operator.add Reducer Accumulation
**What goes wrong:** If SwarmState is reused across cycles, `messages` and `debate_history` (both using `operator.add` reducer) grow unboundedly, causing checkpoint bloat.
**Why it happens:** LangGraph's reducer pattern appends on every state update. Reusing state means old messages persist.
**How to avoid:** CycleRunner creates a fresh `initial_state` dict for every `run_cycle()` call. Never pass a previous cycle's final_state as input.
**Warning signs:** `messages` list length growing across cycles; snapshot.json files growing in size.

### Pitfall 2: Symbol Extraction from User Input
**What goes wrong:** CycleRunner needs a `symbol` field but SwarmState doesn't have an explicit symbol field. The symbol is embedded in `user_input` (e.g., "Analyze BTC").
**Why it happens:** The current graph was designed for single-shot analysis, not structured cycle metadata.
**How to avoid:** CycleRunner accepts `symbol` as an explicit parameter in `run_cycle(user_input, symbol)`. The caller provides it. Alternatively, extract from `data_fetcher_result` if present, but the explicit parameter is safer and simpler.
**Warning signs:** symbol=None or symbol="" in cycle_snapshots table.

### Pitfall 3: Partial State on Failed Cycles
**What goes wrong:** If the graph fails mid-execution (e.g., at debate_synthesizer), some SwarmState fields are None. Constructing a CycleSnapshot with required fields fails Pydantic validation.
**Why it happens:** The CycleSnapshot model requires agent memos as non-Optional for completed/rejected cycles, but a failure might occur before agents run.
**How to avoid:** For status='failed' cycles, use a separate constructor path (or factory method) that allows all agent fields to be Optional or uses empty defaults. Alternatively, have two model variants or use a `model_validator` that relaxes requirements when status='failed'.
**Warning signs:** Pydantic ValidationError on failed cycle persistence.

**Recommended approach:** Use a `@model_validator(mode='after')` that only enforces non-None requirements when status is 'completed' or 'rejected'. For 'failed' status, allow any field to be None by making the base fields Optional and validating post-construction.

Actually, simpler: make agent memo fields Optional on the model itself, but add a `validate_completed()` method that raises if any required field is None. Call this method only for completed/rejected cycles. This keeps the model flexible for all statuses while providing a strict validation gate.

### Pitfall 4: Filesystem Race on Directory Creation
**What goes wrong:** Two concurrent CycleRunner instances could try to create the same cycle directory.
**Why it happens:** If cycle_id is allocated but directory creation races.
**How to avoid:** Use `Path.mkdir(parents=True, exist_ok=True)`. Since cycle_ids are unique (SERIAL), directories will never truly collide. The `exist_ok=True` handles the theoretical race gracefully.
**Warning signs:** FileExistsError on mkdir.

### Pitfall 5: Import Boundary Violation
**What goes wrong:** New core modules (cycle_snapshot.py, cycle_runner.py) accidentally import from src.graph.
**Why it happens:** CycleRunner needs to interact with the graph, making it tempting to import orchestrator types.
**How to avoid:** CycleRunner receives the compiled graph as a constructor parameter (dependency injection). It never imports from src.graph directly. cycle_snapshot.py is a pure data model with zero graph imports.
**Warning signs:** test_import_boundaries.py failures.

**Important nuance:** cycle_runner.py will need to construct the same initial_state dict that LangGraphOrchestrator.run_task_async() builds. This is currently inline in orchestrator.py. The cleanest approach is to duplicate the state initialization in cycle_runner.py (it's just a dict literal) rather than importing from orchestrator. Alternatively, extract a `build_initial_state()` helper into a shared location, but that's Phase 25 territory.

## Code Examples

### CycleSnapshot Model (verified pattern from DecisionCard)
```python
# src/core/cycle_snapshot.py
import json
from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, Field

CYCLE_ID_PAD_WIDTH = 6

class CycleSnapshot(BaseModel):
    """Complete cognitive trace of a single pipeline cycle."""

    cycle_id: int
    task_id: str
    symbol: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Literal["completed", "rejected", "failed"]

    # Agent memos
    macro_report: Optional[dict] = None
    quant_proposal: Optional[dict] = None
    bullish_thesis: Optional[dict] = None
    bearish_thesis: Optional[dict] = None

    # Debate
    debate_history: Optional[list[dict]] = None
    debate_resolution: Optional[dict] = None

    # Consensus
    weighted_consensus_score: Optional[float] = None

    # Merit & persona
    merit_scores: Optional[dict] = None
    soul_sync_context: Optional[dict] = None

    # Risk gate
    risk_approved: Optional[bool] = None
    risk_notes: Optional[str] = None

    # Post-risk (completed only)
    execution_result: Optional[dict] = None
    decision_card: Optional[dict] = None

    # Failure (failed only)
    error_context: Optional[dict] = None

    def padded_id(self) -> str:
        return str(self.cycle_id).zfill(CYCLE_ID_PAD_WIDTH)

    def snapshot_dir(self, base: str = "data/cycles") -> str:
        from pathlib import Path
        return str(Path(base) / self.padded_id())

    def validate_completed(self) -> None:
        """Raise ValueError if required fields are None for a completed cycle."""
        if self.status != "completed":
            return
        required = [
            "macro_report", "quant_proposal", "bullish_thesis", "bearish_thesis",
            "debate_history", "debate_resolution", "weighted_consensus_score",
            "merit_scores", "soul_sync_context", "execution_result", "decision_card",
        ]
        missing = [f for f in required if getattr(self, f) is None]
        if missing:
            raise ValueError(f"Completed cycle missing required fields: {missing}")
```

### CycleRunner Skeleton
```python
# src/core/cycle_runner.py
import json
import logging
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .cycle_snapshot import CycleSnapshot, CYCLE_ID_PAD_WIDTH

logger = logging.getLogger(__name__)

class CycleRunner:
    def __init__(self, graph, config: dict, db_pool=None):
        self.graph = graph
        self.config = config
        self.db_pool = db_pool

    async def _allocate_cycle_id(self) -> int:
        """INSERT placeholder row, return SERIAL cycle_id."""
        # Uses self.db_pool
        ...

    async def _update_cycle_row(self, snapshot: CycleSnapshot) -> None:
        """UPDATE the placeholder row with final metadata."""
        ...

    def _build_initial_state(self, user_input: str) -> dict:
        """Build a fresh SwarmState dict (mirrors LangGraphOrchestrator)."""
        ...

    def _extract_snapshot(self, cycle_id: int, symbol: str, final_state: dict,
                          status: str, error_ctx: Optional[dict] = None) -> CycleSnapshot:
        """Extract CycleSnapshot from final SwarmState."""
        ...

    def _write_snapshot_file(self, snapshot: CycleSnapshot) -> Path:
        """Write snapshot.json to data/cycles/{padded_id}/."""
        dir_path = Path(snapshot.snapshot_dir())
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / "snapshot.json"
        file_path.write_text(
            json.dumps(snapshot.model_dump(mode="json"), indent=2, default=str)
        )
        return file_path

    async def run_cycle(self, user_input: str, symbol: str) -> CycleSnapshot:
        """Execute one full pipeline cycle with persistence."""
        cycle_id = await self._allocate_cycle_id()
        initial_state = self._build_initial_state(user_input)
        config = {"configurable": {"thread_id": initial_state["task_id"]}}

        try:
            final_state = await self.graph.ainvoke(initial_state, config=config)
            # Determine status
            if final_state.get("risk_approved") is False:
                status = "rejected"
            else:
                status = "completed"
            snapshot = self._extract_snapshot(cycle_id, symbol, final_state, status)
        except Exception as exc:
            error_ctx = {
                "error_type": type(exc).__name__,
                "message": str(exc),
                "failed_node": "unknown",
                "traceback_summary": traceback.format_exc()[-500:],
            }
            snapshot = self._extract_snapshot(
                cycle_id, symbol, initial_state, "failed", error_ctx
            )

        # Persist
        if snapshot.status == "completed":
            snapshot.validate_completed()
        self._write_snapshot_file(snapshot)
        await self._update_cycle_row(snapshot)

        return snapshot
```

### PostgreSQL Table (follows persistence.py pattern)
```python
# Addition to setup_persistence() in src/core/persistence.py
async with pool.connection() as conn:
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS cycle_snapshots (
        cycle_id        SERIAL PRIMARY KEY,
        task_id         VARCHAR(64) NOT NULL,
        symbol          VARCHAR(32) NOT NULL,
        status          VARCHAR(16) NOT NULL DEFAULT 'running',
        timestamp       TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        consensus_score NUMERIC(6, 4),
        snapshot_path   TEXT,
        error_summary   TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_cycle_task_id ON cycle_snapshots(task_id);
    CREATE INDEX IF NOT EXISTS idx_cycle_symbol ON cycle_snapshots(symbol);
    CREATE INDEX IF NOT EXISTS idx_cycle_status ON cycle_snapshots(status);
    CREATE INDEX IF NOT EXISTS idx_cycle_timestamp ON cycle_snapshots(timestamp);
    """)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Store everything in SwarmState | External CycleSnapshot + filesystem | Phase 24 | Prevents checkpoint bloat, enables replay |
| No cycle numbering | PostgreSQL SERIAL monotonic IDs | Phase 24 | Enables ordered cycle browsing |
| Pydantic v1 .dict() | Pydantic v2 .model_dump(mode="json") | Already migrated | Must use v2 API |

**Deprecated/outdated:**
- Pydantic v1 `.dict()` and `.json()` methods: use `.model_dump()` and `.model_dump_json()` instead

## Open Questions

1. **How to determine status='rejected' reliably**
   - What we know: `risk_approved is False` indicates rejection. Also, `route_after_debate` sends to END when `weighted_consensus_score <= 0.6` (hold path).
   - What's unclear: The "hold" path (consensus too low) could be considered "rejected" or a separate status. Currently CONTEXT.md only defines three statuses.
   - Recommendation: Treat both risk-gate rejection (`risk_approved is False`) and consensus-below-threshold (weighted_consensus_score <= 0.6 or None) as "rejected". The error_context is only for exception-based failures.

2. **How CycleRunner gets the compiled graph**
   - What we know: `create_orchestrator_graph()` returns the compiled graph. CycleRunner needs this plus a config dict.
   - What's unclear: Whether CycleRunner should use LangGraphOrchestrator or compose alongside it.
   - Recommendation: CycleRunner accepts the compiled graph directly. Phase 25 (end-to-end pipeline) will handle the orchestration of creating and passing the graph. For Phase 24, CycleRunner's constructor takes `graph` as a parameter.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via `.venv/bin/python3.12 -m pytest`) |
| Config file | None (uses defaults) |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_snapshot.py tests/core/test_cycle_runner.py -x` |
| Full suite command | `.venv/bin/python3.12 -m pytest tests/core/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CYCL-01 | Pipeline run persists memos, debate, consensus, merit, decision card to numbered folder | unit | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_runner.py::test_completed_cycle_writes_snapshot -x` | No -- Wave 0 |
| CYCL-02 | CycleSnapshot Pydantic model validates all artifacts | unit | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_snapshot.py -x` | No -- Wave 0 |
| CYCL-03 | PostgreSQL cycle_snapshots table with monotonic numbering | unit | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_runner.py::test_cycle_id_allocation -x` | No -- Wave 0 |
| CYCL-04 | Manifest includes timestamp, symbol, status, cycle_id | unit | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_snapshot.py::test_manifest_fields -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python3.12 -m pytest tests/core/test_cycle_snapshot.py tests/core/test_cycle_runner.py -x`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest tests/core/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/core/test_cycle_snapshot.py` -- CycleSnapshot model validation (CYCL-02, CYCL-04)
- [ ] `tests/core/test_cycle_runner.py` -- CycleRunner logic, filesystem writes, status determination (CYCL-01, CYCL-03)
- [ ] Add `cycle_snapshot` and `cycle_runner` to `tests/core/test_import_boundaries.py`

## Sources

### Primary (HIGH confidence)
- `src/core/decision_card.py` -- Pydantic model pattern, canonical_json, SHA-256 hashing
- `src/core/persistence.py` -- Idempotent CREATE TABLE pattern, async pool usage
- `src/core/db.py` -- DB_URL, get_pool(), get_db_connection() patterns
- `src/graph/state.py` -- SwarmState TypedDict with all field names and types
- `src/graph/orchestrator.py` -- LangGraphOrchestrator.run_task_async() initial_state construction
- `tests/core/test_import_boundaries.py` -- Import boundary enforcement pattern
- Pydantic v2.12.5 installed, psycopg 3.3.3 installed (verified via pip)

### Secondary (MEDIUM confidence)
- Pydantic v2 documentation for `model_dump(mode="json")` behavior with datetime, Literal types

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in use, versions verified
- Architecture: HIGH -- all patterns directly mirror existing codebase (DecisionCard, persistence.py, orchestrator.py)
- Pitfalls: HIGH -- identified from direct code inspection of operator.add reducers, SwarmState field optionality, and import boundary tests

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable domain, no external dependencies)
