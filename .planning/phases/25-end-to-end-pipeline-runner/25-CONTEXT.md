# Phase 25: End-to-End Pipeline Runner - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

User can run the full swarm against real market data and get a persisted, observable cycle. Covers: production CLI entry point, data fetcher resilience, structured logging, message trimming, and soul cache hot-reload. The replay CLI for browsing persisted cycles is Phase 26.

</domain>

<decisions>
## Implementation Decisions

### Data fetcher resilience
- 3 retries with exponential backoff (1s -> 2s -> 4s) on yfinance rate limits
- On exhaustion: fail the cycle (status='failed' with error_context) — no stale data fallback
- Retry logic lives inside `src/tools/data_sources/yfinance_client.py` — scoped to yfinance only, not a generic decorator
- JSON file cache for development: cache fetched data to `data/cache/{symbol}.json` with TTL, dev mode reads from disk first to avoid hitting yfinance during iteration

### Structured logging
- Migrate pipeline-path modules only (~8-10 modules: CycleRunner, data_fetcher_node, graph nodes on critical path). Other modules keep stdlib logging
- Output format: JSON lines in production (JSONRenderer), human-readable in dev (ConsoleRenderer), controlled by env var (e.g. LOG_FORMAT=json)
- Per-node log fields: node name, wall-clock duration, success/failure status — covers PIPE-04's "each node entry/exit with timing"
- Configuration module: `src/core/logging_config.py` (new module, follows core infrastructure pattern like db.py, persistence.py)

### CLI invocation & entry point
- New `src/main.py` replaces the legacy QuantumSwarm class as canonical entry point
- Invocation: `python src/main.py analyze BTC --mode paper`
- Arguments: symbol (positional) + `--mode` (paper/live, default paper)
- Output on success: full decision card dump to stdout
- Remove old `main.py` (legacy QuantumSwarm class) — CycleRunner is the real runner now, clean break

### Soul cache hot-reload
- Add `reload_souls()` function that clears `lru_cache` and re-warms via `warmup_soul_cache()`
- Exposed as `--reload-souls` CLI flag: `python src/main.py analyze BTC --reload-souls`
- No file watcher — explicit invalidation only

### Message trimming
- Trimming happens inside CycleRunner as part of its state reset between runs (Phase 24 established this boundary)
- Claude's Discretion: exact trimming strategy (clear all vs rolling window) — choose based on SwarmState architecture and checkpoint behavior

### Claude's Discretion
- Exact exponential backoff jitter implementation
- JSON cache TTL duration and eviction strategy
- Which specific modules beyond CycleRunner get structlog migration
- Message trimming strategy details
- structlog processor chain configuration
- How the dev cache directory is managed (cleanup, size limits)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/core/cycle_runner.py`: CycleRunner class with `run_cycle()`, already builds fresh initial_state per run — message trimming extends this
- `src/tools/data_sources/yfinance_client.py`: Has in-memory `_data_cache` dict and `clear_cache()` — add retry + disk cache alongside
- `src/core/soul_loader.py`: `load_soul()` with `@lru_cache(maxsize=None)`, `warmup_soul_cache()` — add cache_clear() wrapper
- `src/core/cycle_snapshot.py`: CycleSnapshot Pydantic model — CLI reads this for decision card output
- `src/core/persistence.py`: `setup_persistence()` — called at startup, already idempotent

### Established Patterns
- Core modules are leaf imports — no upward imports from core to graph (enforced by test_import_boundaries.py)
- Lazy LLM init pattern (getter functions for module-level instances)
- Module-level `logging.getLogger(__name__)` across all files
- `asyncio.to_thread()` for wrapping sync calls (yfinance)
- Pydantic models for validated artifacts

### Integration Points
- `src/graph/orchestrator.py` — `create_orchestrator_graph()` returns the compiled graph that CycleRunner wraps
- `src/core/db.py` — `get_pool()` for PostgreSQL connection pool (CycleRunner needs this)
- `src/graph/state.py` — SwarmState with `messages: Annotated[List[dict], operator.add]` reducer
- `tests/core/test_import_boundaries.py` — add `logging_config.py` to core leaf import tests
- Old `main.py` at repo root — to be removed and replaced by `src/main.py`

</code_context>

<specifics>
## Specific Ideas

- Full decision card dump to stdout on success — user wants to see the complete output, not just a summary line
- Dev cache avoids yfinance entirely during development iteration — important for fast feedback loops

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 25-end-to-end-pipeline-runner*
*Context gathered: 2026-03-09*
