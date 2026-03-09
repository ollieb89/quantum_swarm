# Phase 26: Replay CLI - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Read-only CLI for listing, stepping through, and comparing persisted cycles. User can review past swarm decisions through a terminal interface. No mutation of cycle data — purely observational. The pipeline runner (Phase 25) and cycle persistence (Phase 24) are already complete.

</domain>

<decisions>
## Implementation Decisions

### CLI structure & navigation
- Extend existing `src/main.py` with `replay` subcommand group alongside `analyze`
- Three replay subcommands: `replay list`, `replay show <id>`, `replay compare <id1> <id2>`
- `replay show` presents full cycle in one dump, sectioned in execution order: agent memos -> debate -> consensus/merit -> decision card
- Navigation is explicit IDs only — no prev/next aliases, no interactive stepping, no state between invocations
- `replay list` supports `--symbol`, `--status`, and `--limit N` filters. Newest first by default
- Invocations: `python src/main.py replay list`, `python src/main.py replay show 42`, `python src/main.py replay compare 41 42`

### Output formatting & display
- Use `rich` library for colored tables, panels, and horizontal bar charts
- Degrades gracefully when piped (rich auto-detects non-TTY)
- `--json` flag available on all replay subcommands (list, show, compare) for machine-parseable output
- Merit weights visualized as horizontal bar charts with numeric values: `AXIOM ██████████████████ 0.35`
- Drift flags and ARS suspension status displayed inline with merit weights as annotations (e.g., `⚠ DRIFT: voice_tone`, `⛔ SUSPENDED`)
- JSON output on `show` dumps the full CycleSnapshot; on `list` dumps array of metadata objects

### Comparison mode
- Sequential layout with deltas (not side-by-side columns) — works in narrow terminals
- Compare scope: consensus score diff, merit weight shifts with directional arrows, and a summary line from each agent's reasoning showing shifts
- `--json` on compare outputs structured delta object with from/to/delta for numeric fields
- Same-symbol enforcement: compare errors if the two cycles have different symbols
- Delta indicators: ▲ for increase, ▼ for decrease, arrow-less for unchanged

### Data source & loading
- Filesystem-first strategy: `replay show` and `replay compare` load from `data/cycles/{zero_padded_id}/snapshot.json`
- `replay list` queries PostgreSQL `cycle_snapshots` table for fast indexed metadata retrieval
- DB fallback for list: if PostgreSQL unavailable, fall back to scanning `data/cycles/` directories and parsing snapshot.json files
- Read-only cycle loading logic lives in new `src/core/cycle_store.py` — read counterpart to CycleRunner's write path
- `cycle_store.py` follows core leaf import pattern (no upward imports to graph/agents)

### Claude's Discretion
- rich panel/table styling details (colors, borders, padding)
- How agent memo summaries are extracted for comparison view (first line, key field, etc.)
- Exact error messages for missing cycles, DB connection failures
- Whether `replay list` defaults to --limit 20 or shows all
- How debate rounds are formatted in the show output
- Argument parsing structure for the replay subcommand group (argparse sub-parsers)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/core/cycle_snapshot.py`: CycleSnapshot Pydantic model with `padded_id()`, `snapshot_dir()`, `validate_completed()` — replay reads these directly
- `src/main.py`: argparse with subcommands (`analyze`) — extend with `replay` subcommand group
- `src/core/db.py`: `get_pool()`, `get_db_connection()` — reuse for list queries
- `src/core/persistence.py`: `cycle_snapshots` table already has indexes on symbol, status, timestamp, task_id

### Established Patterns
- Core modules are leaf imports — no upward imports (enforced by test_import_boundaries.py)
- CycleRunner already handles db_pool=None gracefully — cycle_store should mirror this pattern
- Pydantic `model_dump(mode="json")` for JSON serialization (used in main.py line 129)
- structlog stdlib integration configured at startup in logging_config.py

### Integration Points
- `src/main.py` — add replay subcommand parsers alongside analyze
- `src/core/cycle_snapshot.py` — CycleSnapshot.model_validate() for loading from JSON files
- `src/core/db.py` — get_pool() for PostgreSQL metadata queries
- `data/cycles/{zero_padded_id}/snapshot.json` — filesystem read path
- `tests/core/test_import_boundaries.py` — add cycle_store.py to core leaf import tests

</code_context>

<specifics>
## Specific Ideas

- Merit bar chart with inline drift annotations creates a single "agent health dashboard" view per cycle
- Sequential delta comparison with ▲/▼ arrows is designed to answer "what changed and why" at a glance
- --json on all subcommands enables scripting workflows (e.g., compare all BTC cycles over time with jq)
- Filesystem-first loading means replay works without a running database — important for reviewing cycles on a different machine or after DB migration

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 26-replay-cli*
*Context gathered: 2026-03-09*
