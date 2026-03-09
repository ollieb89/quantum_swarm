# Phase 25: End-to-End Pipeline Runner - Context

**Gathered:** 2026-03-09
**Updated:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

User can run the full swarm against real market data and get a persisted, observable cycle. Covers: production CLI entry point, data fetcher resilience, structured logging, message trimming, and soul cache hot-reload. The replay CLI for browsing persisted cycles is Phase 26.

</domain>

<decisions>
## Implementation Decisions

### CLI invocation & entry point
- Single-shot execution: one cycle per invocation, exit when done. No loop mode — compose with cron/systemd for recurring runs
- New `src/main.py` replaces the legacy QuantumSwarm class as canonical entry point
- Invocation: `python src/main.py analyze BTC --mode paper`
- Arguments: symbol (positional) + `--mode` (paper/live, default paper) + `--reload-souls` (clear and re-warm soul cache)
- Argument parsing: argparse (stdlib, zero dependencies)
- Output on success: full CycleSnapshot as formatted JSON to stdout. Same format on failure (status='failed' with error_context populated). Consistent machine-parseable output regardless of outcome
- Remove old `src/main.py` (legacy QuantumSwarm class) — CycleRunner is the real runner now, clean break
- Subprocess integration test: verify `python src/main.py analyze BTC --mode paper` exits cleanly and outputs valid JSON (with mocked APIs)

### Data fetcher resilience
- 3 retries with exponential backoff (1s -> 2s -> 4s) on yfinance rate limits
- On exhaustion: fail the cycle (status='failed' with error_context) — no stale data fallback, no disk cache fallback
- Retry logic lives inside `src/tools/data_sources/yfinance_client.py` — scoped to yfinance only, not a generic decorator
- JSON file disk cache at `data/cache/{symbol}.json` with TTL
- Disk cache writes happen on every successful yfinance fetch (cache builds naturally)
- Dev mode activated by `QS_DEV_CACHE=1` environment variable — controls whether disk cache is READ before hitting yfinance. Matches LOG_FORMAT env var pattern
- Without `QS_DEV_CACHE=1`, disk cache is written to but never read (production always hits yfinance fresh)

### Structured logging
- Use structlog as a global stdlib integration: `structlog.stdlib.ProcessorFormatter` wraps existing `logging.getLogger(__name__)` calls. No per-file rewrites needed — all modules get structured output via the formatter
- Output format: JSON lines in production (JSONRenderer), human-readable in dev (ConsoleRenderer), controlled by env var (e.g. `LOG_FORMAT=json`)
- Per-node log fields: node name, wall-clock duration, success/failure status — covers PIPE-04's "each node entry/exit with timing"
- Configuration module: `src/core/logging_config.py` (new module, follows core infrastructure pattern like db.py, persistence.py)
- Called once at CLI startup before any other imports that create loggers

### Database connection
- Use existing `src/core/db.py` pattern: `get_pool()` for connection pool, `setup_persistence()` at startup
- DB connection configured via existing environment variable (no CLI flag override)
- Claude's Discretion: whether DB is required or optional with filesystem-only degradation (CycleRunner already has fallback for no db_pool)

### Error handling
- Uniform handling: all exceptions → failed CycleSnapshot with error_context. The error_type field captures the exception class
- CLI outputs the same JSON format for both success and failure — CycleSnapshot with status field distinguishing outcomes
- No differentiated handling for specific error types (rate limit vs API error vs timeout). error_context is informative enough

### Soul cache hot-reload
- Add `reload_souls()` function that clears `lru_cache` and re-warms via `warmup_soul_cache()`
- Exposed as `--reload-souls` CLI flag: `python src/main.py analyze BTC --reload-souls`
- No file watcher — explicit invalidation only

### Message trimming
- Trimming happens inside CycleRunner as part of its state reset between runs (Phase 24 established this boundary)
- Claude's Discretion: exact trimming strategy (clear all vs rolling window) — choose based on SwarmState architecture and checkpoint behavior

### Testing approach
- Subprocess CLI integration test: `python src/main.py analyze BTC --mode paper` exits cleanly, outputs valid JSON (APIs mocked via env vars or module-level patches)
- Claude's Discretion: mock strategy for unit tests (mock at boundaries vs snapshot replay). Follow existing project patterns

### Claude's Discretion
- Exit code semantics (0/1 vs differentiated exit codes for completed/rejected/failed)
- Exact exponential backoff jitter implementation
- JSON cache TTL duration and eviction strategy
- Message trimming strategy details
- structlog processor chain configuration
- How the dev cache directory is managed (cleanup, size limits)
- DB required vs optional with degradation (CycleRunner already supports both)
- Mock strategy for unit tests

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/core/cycle_runner.py`: CycleRunner class with `run_cycle()`, already builds fresh initial_state per run — message trimming extends this. Has db_pool=None fallback for filesystem-only mode
- `src/tools/data_sources/yfinance_client.py`: Has in-memory `_data_cache` dict and `clear_cache()` — add retry + disk cache alongside
- `src/core/soul_loader.py`: `load_soul()` with `@lru_cache(maxsize=None)`, `warmup_soul_cache()` — add cache_clear() wrapper
- `src/core/cycle_snapshot.py`: CycleSnapshot Pydantic model — CLI outputs this as JSON
- `src/core/persistence.py`: `setup_persistence()` — called at startup, already idempotent
- `src/core/db.py`: `DB_URL`, `get_pool()`, `get_db_connection()` — connection infrastructure ready

### Established Patterns
- Core modules are leaf imports — no upward imports from core to graph (enforced by test_import_boundaries.py)
- Lazy LLM init pattern (getter functions for module-level instances)
- Module-level `logging.getLogger(__name__)` across all files — structlog wraps these via ProcessorFormatter
- `asyncio.to_thread()` for wrapping sync calls (yfinance)
- Pydantic models for validated artifacts
- Env var configuration: `GOOGLE_API_KEY`, `LOG_FORMAT`, now `QS_DEV_CACHE`

### Integration Points
- `src/graph/orchestrator.py` — `create_orchestrator_graph()` returns the compiled graph that CycleRunner wraps
- `src/core/db.py` — `get_pool()` for PostgreSQL connection pool
- `src/graph/state.py` — SwarmState with `messages: Annotated[List[dict], operator.add]` reducer
- `tests/core/test_import_boundaries.py` — add `logging_config.py` to core leaf import tests
- Old `src/main.py` at project root — legacy QuantumSwarm class to be replaced entirely

</code_context>

<specifics>
## Specific Ideas

- Full CycleSnapshot JSON dump to stdout on both success and failure — consistent machine-parseable format, user sees complete output
- Dev cache (`QS_DEV_CACHE=1`) avoids yfinance entirely during development iteration — important for fast feedback loops
- structlog stdlib integration means zero per-file changes: configure once in logging_config.py, all existing getLogger calls emit structured output

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 25-end-to-end-pipeline-runner*
*Context gathered: 2026-03-09*
