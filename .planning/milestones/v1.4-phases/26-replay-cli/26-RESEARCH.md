# Phase 26: Replay CLI - Research

**Researched:** 2026-03-09
**Domain:** CLI design, terminal rendering, read-only data access
**Confidence:** HIGH

## Summary

Phase 26 builds a read-only CLI for reviewing persisted cycle data. The implementation adds three subcommands (`replay list`, `replay show`, `replay compare`) to the existing argparse structure in `src/main.py`, backed by a new `src/core/cycle_store.py` module that reads CycleSnapshot data from filesystem JSON files and PostgreSQL metadata.

The technical domain is well-understood: argparse sub-parsers for command routing, rich library for terminal rendering (already installed v14.3.3), Pydantic `model_validate()` for JSON deserialization, and psycopg3 for DB queries. The CycleSnapshot model is fully defined and the persistence layer (Phase 24) writes both filesystem snapshots and DB metadata rows with indexed columns.

**Primary recommendation:** Build cycle_store.py as a pure read module (no async needed for filesystem reads, async only for DB list queries), then wire three thin subcommand handlers that delegate to cycle_store for data and rich for rendering.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Extend existing `src/main.py` with `replay` subcommand group alongside `analyze`
- Three replay subcommands: `replay list`, `replay show <id>`, `replay compare <id1> <id2>`
- `replay show` presents full cycle in one dump, sectioned in execution order: agent memos -> debate -> consensus/merit -> decision card
- Navigation is explicit IDs only -- no prev/next aliases, no interactive stepping, no state between invocations
- `replay list` supports `--symbol`, `--status`, and `--limit N` filters. Newest first by default
- Use `rich` library for colored tables, panels, and horizontal bar charts
- Degrades gracefully when piped (rich auto-detects non-TTY)
- `--json` flag available on all replay subcommands for machine-parseable output
- Merit weights visualized as horizontal bar charts with numeric values
- Drift flags and ARS suspension status displayed inline with merit weights as annotations
- Sequential layout with deltas (not side-by-side columns) for comparison
- Compare scope: consensus score diff, merit weight shifts with directional arrows, agent reasoning shift summaries
- Same-symbol enforcement on compare
- Delta indicators: triangle-up for increase, triangle-down for decrease, arrow-less for unchanged
- Filesystem-first strategy: `replay show` and `replay compare` load from `data/cycles/{zero_padded_id}/snapshot.json`
- `replay list` queries PostgreSQL `cycle_snapshots` table for fast indexed metadata retrieval
- DB fallback for list: if PostgreSQL unavailable, fall back to scanning `data/cycles/` directories
- Read-only cycle loading logic lives in new `src/core/cycle_store.py`
- `cycle_store.py` follows core leaf import pattern (no upward imports to graph/agents)

### Claude's Discretion
- rich panel/table styling details (colors, borders, padding)
- How agent memo summaries are extracted for comparison view
- Exact error messages for missing cycles, DB connection failures
- Whether `replay list` defaults to --limit 20 or shows all
- How debate rounds are formatted in the show output
- Argument parsing structure for the replay subcommand group (argparse sub-parsers)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REPL-01 | User can list all available cycles with summary metadata | cycle_store.py list_cycles() queries DB or scans filesystem; rich Table for display |
| REPL-02 | User can step through a cycle (memos -> debate -> consensus -> decision card) | cycle_store.py load_cycle() reads snapshot.json; show command renders sections in order |
| REPL-03 | User can navigate between cycles (previous/next) | CONTEXT decision: explicit IDs only, no prev/next. Requirement satisfied by `replay show <id>` with `replay list` for discovery |
| REPL-04 | Merit weights are visualized per cycle showing agent influence | merit_scores dict from CycleSnapshot rendered as rich horizontal bar charts |
| REPL-05 | Drift flags and ARS signals are displayed when viewing a cycle | soul_sync_context + DB evolution_suspended status; inline annotations on merit display |
| REPL-06 | User can compare two cycles side-by-side | replay compare renders sequential deltas with directional arrows |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rich | 14.3.3 | Terminal tables, panels, bar charts, color | Already installed; auto-detects TTY for pipe-safe output |
| argparse | stdlib | CLI argument parsing | Already used in main.py; sub-parsers for nested commands |
| pydantic | (existing) | CycleSnapshot deserialization via model_validate() | Already the canonical schema layer |
| psycopg | 3.3.3+ | PostgreSQL queries for cycle list | Already used throughout project |
| pathlib | stdlib | Filesystem directory scanning for fallback | Standard Python |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json | stdlib | JSON serialization for --json flag | All subcommands with --json |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| rich | click + tabulate | rich already installed, superior auto-TTY detection |
| argparse sub-parsers | typer/click | Unnecessary dependency; argparse already established |

**Installation:**
```bash
# rich already installed but NOT in pyproject.toml -- must add
uv add rich
```

## Architecture Patterns

### Recommended Project Structure
```
src/
  core/
    cycle_store.py        # NEW: read-only cycle data access (core leaf)
  cli/
    replay.py             # NEW: replay subcommand handlers + rich rendering
  main.py                 # MODIFIED: add replay subparser group
tests/
  core/
    test_cycle_store.py   # NEW: unit tests for data loading
  cli/
    test_replay.py        # NEW: CLI integration tests
```

### Pattern 1: Core Leaf Module (cycle_store.py)
**What:** Read-only data access module in `src/core/` that loads CycleSnapshot from filesystem and queries DB for metadata.
**When to use:** All cycle data retrieval for replay commands.
**Key constraints:**
- Must NOT import from `src/graph/` (enforced by test_import_boundaries.py)
- May import from `src/core/cycle_snapshot` and `src/core/db`
- Mirrors CycleRunner's graceful db_pool=None pattern
- Synchronous for filesystem reads, async only for DB queries

```python
# Source: project pattern from cycle_runner.py
import json
from pathlib import Path
from typing import Optional
from src.core.cycle_snapshot import CycleSnapshot, CYCLE_ID_PAD_WIDTH

_DEFAULT_BASE_DIR = "data/cycles"

def load_cycle(cycle_id: int, base_dir: str = _DEFAULT_BASE_DIR) -> CycleSnapshot:
    """Load a CycleSnapshot from filesystem JSON."""
    padded = str(cycle_id).zfill(CYCLE_ID_PAD_WIDTH)
    path = Path(base_dir) / padded / "snapshot.json"
    if not path.exists():
        raise FileNotFoundError(f"Cycle {cycle_id} not found at {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return CycleSnapshot.model_validate(data)
```

### Pattern 2: CLI Rendering Module (cli/replay.py)
**What:** Separate module for replay command logic and rich rendering, keeping main.py thin.
**When to use:** All replay subcommand handling.
**Design:** Functions like `handle_list(args)`, `handle_show(args)`, `handle_compare(args)` that are called from main.py's dispatch.

```python
# Source: project pattern from main.py
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def handle_list(args) -> int:
    """Handle 'replay list' subcommand. Returns exit code."""
    if args.json:
        # Machine-parseable output
        print(json.dumps(cycles_metadata, indent=2, default=str))
    else:
        # Rich table output
        table = Table(title="Cycle History")
        table.add_column("ID", style="cyan")
        # ...
        console.print(table)
    return 0
```

### Pattern 3: Argparse Sub-Parser Group
**What:** Nested sub-parsers under a `replay` parent command.
**Structure:**

```python
# In main.py
replay_parser = sub.add_parser("replay", help="Review past swarm cycles")
replay_sub = replay_parser.add_subparsers(dest="replay_command")

list_parser = replay_sub.add_parser("list", help="List available cycles")
list_parser.add_argument("--symbol", help="Filter by symbol")
list_parser.add_argument("--status", help="Filter by status")
list_parser.add_argument("--limit", type=int, help="Max results")
list_parser.add_argument("--json", action="store_true", help="JSON output")

show_parser = replay_sub.add_parser("show", help="Show cycle details")
show_parser.add_argument("cycle_id", type=int, help="Cycle ID")
show_parser.add_argument("--json", action="store_true", help="JSON output")

compare_parser = replay_sub.add_parser("compare", help="Compare two cycles")
compare_parser.add_argument("cycle_id_1", type=int)
compare_parser.add_argument("cycle_id_2", type=int)
compare_parser.add_argument("--json", action="store_true", help="JSON output")
```

### Anti-Patterns to Avoid
- **Importing graph modules from cycle_store:** Core leaf import law. cycle_store reads raw JSON and uses CycleSnapshot.model_validate() only.
- **Async for filesystem reads:** Unnecessary complexity. Only DB queries need async; filesystem reads are synchronous via pathlib.
- **Mutating cycle data:** This is read-only. No writes, no updates, no deletes.
- **Storing state between invocations:** Each CLI call is independent. No session state, no cursor position.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Terminal color/formatting | ANSI escape codes | rich.Console | Auto TTY detection, pipe safety, cross-platform |
| Horizontal bar charts | Manual string padding | rich.Bar or string multiplication with rich colors | Alignment, truncation handled |
| Table formatting | Manual column alignment | rich.Table | Auto-sizing, wrapping, borders |
| JSON serialization | Custom dict builders | CycleSnapshot.model_dump(mode="json") | Already canonical, handles datetime/Decimal |

**Key insight:** rich handles TTY detection automatically via `Console(force_terminal=...)`. When stdout is piped, rich strips formatting. This satisfies the "degrades gracefully" requirement with zero custom code.

## Common Pitfalls

### Pitfall 1: Async Entrypoint for DB Queries
**What goes wrong:** `replay list` needs async DB access but CLI is synchronous.
**Why it happens:** psycopg3 pool uses async connections.
**How to avoid:** Use `asyncio.run()` for the DB query path only, matching main.py's existing pattern. For the filesystem fallback, stay fully synchronous.
**Warning signs:** ImportError or RuntimeError about event loops.

### Pitfall 2: Missing rich in pyproject.toml
**What goes wrong:** rich is installed in the current venv but not declared as a dependency.
**Why it happens:** It was pulled in as a transitive dependency of another package.
**How to avoid:** Add `"rich>=13.0"` to pyproject.toml dependencies before implementation.
**Warning signs:** CI/fresh install fails on `import rich`.

### Pitfall 3: Structured Logging Interference with Rich Output
**What goes wrong:** structlog's ProcessorFormatter writes to stderr, but if misconfigured could interfere with stdout JSON output.
**Why it happens:** main.py calls configure_logging() at module level before imports.
**How to avoid:** Replay commands should write rich output to stdout via Console() and let structlog continue writing to stderr. For --json mode, use plain `print()` to stdout (same pattern as existing main.py line 129).
**Warning signs:** Interleaved log lines in JSON output.

### Pitfall 4: CycleSnapshot Field Access for Failed/Rejected Cycles
**What goes wrong:** Accessing `.merit_scores` or `.debate_history` on a failed cycle returns None, causing AttributeError in rendering.
**Why it happens:** Failed cycles have partial data by design (see CycleSnapshot._COMPLETED_REQUIRED_FIELDS).
**How to avoid:** All rendering functions must handle None gracefully for every Optional field. Use `snapshot.merit_scores or {}` pattern consistently.
**Warning signs:** Crashes when showing failed or rejected cycles.

### Pitfall 5: DB Pool Initialization Side Effect
**What goes wrong:** Importing `get_pool()` opens a real DB connection at call time.
**Why it happens:** `get_pool()` creates the pool with `open=True`.
**How to avoid:** For `replay list`, attempt DB connection in a try/except and fall back to filesystem scan. Mirror `_try_get_pool()` pattern from main.py.
**Warning signs:** ConnectionRefused error when PostgreSQL is not running.

## Code Examples

### Loading CycleSnapshot from Filesystem
```python
# Source: CycleRunner._write_snapshot_file() shows write format
# Read counterpart:
import json
from pathlib import Path
from src.core.cycle_snapshot import CycleSnapshot, CYCLE_ID_PAD_WIDTH

def load_cycle(cycle_id: int, base_dir: str = "data/cycles") -> CycleSnapshot:
    padded = str(cycle_id).zfill(CYCLE_ID_PAD_WIDTH)
    path = Path(base_dir) / padded / "snapshot.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return CycleSnapshot.model_validate(data)
```

### Querying DB for Cycle List Metadata
```python
# Source: persistence.py cycle_snapshots table schema
async def list_cycles_db(pool, symbol=None, status=None, limit=None):
    query = "SELECT cycle_id, symbol, status, timestamp, consensus_score FROM cycle_snapshots"
    conditions, params = [], []
    if symbol:
        conditions.append("symbol = %s"); params.append(symbol)
    if status:
        conditions.append("status = %s"); params.append(status)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY timestamp DESC"
    if limit:
        query += " LIMIT %s"; params.append(limit)
    async with pool.connection() as conn:
        cursor = await conn.execute(query, params)
        return await cursor.fetchall()
```

### Merit Weight Bar Chart with Rich
```python
from rich.console import Console
from rich.text import Text

def render_merit_weights(merit_scores: dict, console: Console):
    """Render horizontal bar chart for each agent's merit composite."""
    for handle in ["AXIOM", "MOMENTUM", "CASSANDRA", "SIGMA", "GUARDIAN"]:
        agent = merit_scores.get(handle, {})
        composite = agent.get("composite", 0.5)
        bar_width = int(composite * 30)  # scale to ~30 chars
        bar = Text()
        bar.append(f"{handle:12s} ", style="bold")
        bar.append("█" * bar_width, style="green")
        bar.append(f" {composite:.2f}")
        console.print(bar)
```

### Filesystem Fallback for List
```python
def list_cycles_filesystem(base_dir: str = "data/cycles") -> list[dict]:
    """Scan data/cycles/ directories when DB unavailable."""
    base = Path(base_dir)
    if not base.exists():
        return []
    cycles = []
    for cycle_dir in sorted(base.iterdir(), reverse=True):
        snap_file = cycle_dir / "snapshot.json"
        if snap_file.exists():
            data = json.loads(snap_file.read_text(encoding="utf-8"))
            cycles.append({
                "cycle_id": data.get("cycle_id"),
                "symbol": data.get("symbol"),
                "status": data.get("status"),
                "timestamp": data.get("timestamp"),
                "consensus_score": data.get("weighted_consensus_score"),
            })
    return cycles
```

### Comparison Delta Calculation
```python
def compute_deltas(snap_a: CycleSnapshot, snap_b: CycleSnapshot) -> dict:
    """Compute structured delta between two snapshots."""
    delta = {
        "consensus_score": {
            "from": snap_a.weighted_consensus_score,
            "to": snap_b.weighted_consensus_score,
            "delta": (snap_b.weighted_consensus_score or 0) - (snap_a.weighted_consensus_score or 0),
        },
        "merit_shifts": {},
    }
    merits_a = snap_a.merit_scores or {}
    merits_b = snap_b.merit_scores or {}
    for handle in ["AXIOM", "MOMENTUM", "CASSANDRA", "SIGMA", "GUARDIAN"]:
        ca = merits_a.get(handle, {}).get("composite", 0.5)
        cb = merits_b.get(handle, {}).get("composite", 0.5)
        delta["merit_shifts"][handle] = {"from": ca, "to": cb, "delta": round(cb - ca, 4)}
    return delta
```

## Data Structure Reference

### merit_scores Dict (from merit_loader_node)
```json
{
  "AXIOM": {"accuracy": 0.5, "recovery": 0.5, "consensus": 0.5, "fidelity": 0.5, "composite": 0.5},
  "MOMENTUM": {"accuracy": 0.5, "recovery": 0.62, "consensus": 0.48, "fidelity": 0.5, "composite": 0.52},
  ...
}
```

### soul_sync_context Dict (from soul_sync_handshake_node)
```json
{
  "MOMENTUM": "<public soul summary text>",
  "CASSANDRA": "<public soul summary text>"
}
```

### ARS Suspension Status
Stored in DB `agent_merit_scores.evolution_suspended` (boolean). NOT in CycleSnapshot directly. For REPL-05, the show command can either:
1. Query DB for current suspension status (adds async requirement)
2. Check MEMORY.md evolution logs for drift flags (available in snapshot indirectly)
3. Parse drift flags from soul_sync_context or debate annotations

**Recommendation:** For drift flags, parse from the cycle's memory writer entries if available in the snapshot, or display a note that drift data requires DB access. Keep it simple -- the snapshot already contains merit_scores which reflect drift impact.

### cycle_snapshots DB Table Columns
```
cycle_id (SERIAL PK), task_id, symbol, status, timestamp, consensus_score, snapshot_path, error_summary
```
Indexes on: task_id, symbol, status, timestamp.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual JSON inspection | Structured CLI replay | Phase 26 | Users can review cycles without jq |
| No comparison capability | Delta comparison with arrows | Phase 26 | Enables tracking institutional drift |

## Open Questions

1. **ARS Suspension Display**
   - What we know: evolution_suspended is a DB-only boolean on agent_merit_scores table. It is NOT persisted in CycleSnapshot.
   - What's unclear: Whether to query DB live for suspension status or simply note it's unavailable in filesystem-only mode.
   - Recommendation: Query DB if available (same try/except pattern as list), show "DB unavailable" annotation if not. Since replay show already loads from filesystem, this is a lightweight DB check.

2. **Drift Flags in Snapshot**
   - What we know: Drift flags are computed by memory_writer and written to MEMORY.md evolution entries. They are NOT stored as a first-class field in CycleSnapshot.
   - What's unclear: How to surface drift flags in the show view without a CycleSnapshot field.
   - Recommendation: Check if debate_history or soul_sync_context contains drift annotations. If not, the REPL-05 requirement may need drift_flags added to CycleSnapshot in a future phase, or query the DB ars_state table for the closest audit timestamp.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_store.py -x` |
| Full suite command | `.venv/bin/python3.12 -m pytest tests/ -x --ignore=tests/integration` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REPL-01 | List cycles with metadata | unit | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_store.py::test_list_cycles -x` | No - Wave 0 |
| REPL-02 | Load and display single cycle | unit | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_store.py::test_load_cycle -x` | No - Wave 0 |
| REPL-03 | Navigate by explicit ID | unit | `.venv/bin/python3.12 -m pytest tests/cli/test_replay.py::test_show_by_id -x` | No - Wave 0 |
| REPL-04 | Merit weight visualization | unit | `.venv/bin/python3.12 -m pytest tests/cli/test_replay.py::test_merit_display -x` | No - Wave 0 |
| REPL-05 | Drift flags and ARS display | unit | `.venv/bin/python3.12 -m pytest tests/cli/test_replay.py::test_drift_display -x` | No - Wave 0 |
| REPL-06 | Compare two cycles | unit | `.venv/bin/python3.12 -m pytest tests/cli/test_replay.py::test_compare -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python3.12 -m pytest tests/core/test_cycle_store.py tests/cli/test_replay.py -x`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/core/test_cycle_store.py` -- covers REPL-01, REPL-02
- [ ] `tests/cli/__init__.py` -- new test package
- [ ] `tests/cli/test_replay.py` -- covers REPL-03, REPL-04, REPL-05, REPL-06
- [ ] `src/cli/__init__.py` -- new source package
- [ ] Add `cycle_store` to `test_import_boundaries.py` TestCoreLeafImports
- [ ] Add `rich>=13.0` to pyproject.toml dependencies

## Sources

### Primary (HIGH confidence)
- `src/core/cycle_snapshot.py` -- CycleSnapshot model, padded_id(), snapshot_dir()
- `src/core/cycle_runner.py` -- Write path: _write_snapshot_file(), _update_cycle_row()
- `src/core/persistence.py` -- cycle_snapshots table DDL with indexes
- `src/main.py` -- Existing argparse structure, asyncio.run() pattern
- `src/core/db.py` -- get_pool() with open=True semantics
- `src/graph/nodes/merit_loader.py` -- merit_scores dict structure
- `src/graph/nodes/soul_sync_handshake.py` -- soul_sync_context dict structure
- `tests/core/test_import_boundaries.py` -- Import law enforcement pattern
- rich 14.3.3 installed locally -- Console, Table, Panel, Text confirmed available

### Secondary (MEDIUM confidence)
- rich TTY auto-detection: documented behavior in rich docs, verified by library presence

### Tertiary (LOW confidence)
- Drift flag availability in CycleSnapshot: drift flags are computed per-cycle but not stored as a CycleSnapshot field. REPL-05 implementation may need creative data sourcing.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already installed and used in project
- Architecture: HIGH -- follows established core leaf + CLI patterns
- Pitfalls: HIGH -- derived from direct code reading of existing modules
- Drift/ARS display: MEDIUM -- data availability for REPL-05 needs runtime verification

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable domain, no fast-moving dependencies)
