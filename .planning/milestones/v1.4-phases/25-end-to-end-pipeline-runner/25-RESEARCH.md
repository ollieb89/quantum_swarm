# Phase 25: End-to-End Pipeline Runner - Research

**Researched:** 2026-03-09
**Domain:** CLI entry point, data resilience, structured logging, state management
**Confidence:** HIGH

## Summary

Phase 25 wires the existing CycleRunner (Phase 24) into a production CLI entry point so users can run `python src/main.py analyze BTC --mode paper` and get a persisted CycleSnapshot as JSON on stdout. Five concerns are addressed: (1) CLI with argparse, (2) yfinance retry + disk cache, (3) structlog stdlib integration for structured logging, (4) message trimming in CycleRunner, and (5) soul cache hot-reload.

The existing codebase provides strong foundations. CycleRunner already builds fresh initial state per cycle, handles db_pool=None gracefully, and persists snapshots. The yfinance client has an in-memory cache and asyncio.to_thread wrapping. Soul loader uses lru_cache with cache_clear available. The old `src/main.py` is a legacy QuantumSwarm class that imports from `agents.order_router_ccxt` -- it will be replaced entirely.

**Primary recommendation:** Build five focused modules (main.py CLI, logging_config.py, yfinance retry+cache, CycleRunner message trim, soul reload function) with minimal cross-cutting changes. structlog is a new dependency that must be installed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Single-shot execution: one cycle per invocation, exit when done. No loop mode
- New `src/main.py` replaces legacy QuantumSwarm class as canonical entry point
- Invocation: `python src/main.py analyze BTC --mode paper`
- Arguments: symbol (positional) + `--mode` (paper/live, default paper) + `--reload-souls` (clear and re-warm soul cache)
- Argument parsing: argparse (stdlib, zero dependencies)
- Output: full CycleSnapshot as formatted JSON to stdout (success and failure)
- 3 retries with exponential backoff (1s -> 2s -> 4s) on yfinance rate limits
- On exhaustion: fail the cycle (status='failed' with error_context) -- no stale data fallback
- Retry logic lives inside `src/tools/data_sources/yfinance_client.py`
- JSON file disk cache at `data/cache/{symbol}.json` with TTL
- Dev mode: `QS_DEV_CACHE=1` env var controls whether disk cache is READ before hitting yfinance
- Without `QS_DEV_CACHE=1`, disk cache is written to but never read
- structlog as global stdlib integration via ProcessorFormatter
- Output format: JSON lines in production (JSONRenderer), dev (ConsoleRenderer), controlled by `LOG_FORMAT=json`
- Per-node log fields: node name, wall-clock duration, success/failure status
- Configuration module: `src/core/logging_config.py`
- Called once at CLI startup before any other imports that create loggers
- Message trimming happens inside CycleRunner as part of state reset
- Soul cache hot-reload: `reload_souls()` function that clears lru_cache + re-warms
- Exposed as `--reload-souls` CLI flag
- Subprocess integration test for CLI

### Claude's Discretion
- Exit code semantics (0/1 vs differentiated)
- Exact exponential backoff jitter implementation
- JSON cache TTL duration and eviction strategy
- Message trimming strategy details
- structlog processor chain configuration
- Dev cache directory management
- DB required vs optional with degradation
- Mock strategy for unit tests

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PIPE-01 | User can run "Analyze BTC" and full pipeline executes from intent to decision card | CLI entry point (main.py) + CycleRunner integration + graph creation |
| PIPE-02 | Data fetcher has caching/retry layer resilient to yfinance rate limits | yfinance_client.py retry with backoff + JSON disk cache + QS_DEV_CACHE |
| PIPE-03 | Messages list is bounded to prevent checkpoint state bloat | CycleRunner message trimming in _build_initial_state (already clears per cycle) |
| PIPE-04 | Structured logging captures pipeline execution for production debugging | structlog stdlib integration via ProcessorFormatter in logging_config.py |
| PIPE-05 | Soul cache can be reloaded without process restart | reload_souls() wrapping load_soul.cache_clear() + warmup_soul_cache() |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| structlog | >=24.1.0 | Structured logging with stdlib integration | De facto Python structured logging; ProcessorFormatter wraps existing getLogger calls with zero per-file changes |
| argparse | stdlib | CLI argument parsing | Zero dependencies, locked decision |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json | stdlib | Disk cache serialization, CLI output | Cache files + CycleSnapshot stdout output |
| time | stdlib | Exponential backoff sleep | Retry delays in yfinance client |
| random | stdlib | Jitter for backoff | Prevent thundering herd on retries |
| os | stdlib | Environment variable checks | QS_DEV_CACHE, LOG_FORMAT |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| structlog | python-json-logger | Less mature stdlib integration, no ConsoleRenderer for dev mode |
| argparse | click/typer | More features but adds dependency -- locked decision is argparse |
| Custom retry | tenacity | Good library but scoped retry is simpler for single function |

**Installation:**
```bash
pip install structlog>=24.1.0
```

## Architecture Patterns

### New/Modified Files
```
src/
  main.py                          # REPLACE: new CLI entry point (argparse + CycleRunner)
  core/
    logging_config.py              # NEW: structlog stdlib configuration
    cycle_runner.py                # MODIFY: message trimming (already resets per cycle)
    soul_loader.py                 # MODIFY: add reload_souls() function
  tools/
    data_sources/
      yfinance_client.py           # MODIFY: add retry + disk cache
tests/
  core/
    test_import_boundaries.py      # MODIFY: add logging_config.py leaf import test
  test_cli_integration.py          # NEW: subprocess CLI test (or extend existing test_cli_wrapper.py)
```

### Pattern 1: structlog stdlib Integration (logging_config.py)

**What:** Configure structlog once at startup so all existing `logging.getLogger(__name__)` calls emit structured output.
**When to use:** Called once in main.py before any module imports that create loggers.

```python
# src/core/logging_config.py
import logging
import os
import sys

import structlog

def configure_logging() -> None:
    """Configure structlog as stdlib formatter. Call once at startup."""
    log_format = os.environ.get("LOG_FORMAT", "console")

    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ExtraAdder(),
    ]

    if log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
```

**Key insight:** Logs go to stderr, CycleSnapshot JSON goes to stdout. This separation is critical for machine-parseable output.

### Pattern 2: CLI Entry Point (main.py)

**What:** argparse-based single-shot CLI that creates graph, runs cycle, outputs JSON.
**When to use:** Canonical way to run the swarm.

```python
# src/main.py (replacement)
import argparse
import asyncio
import json
import sys

# Configure logging FIRST, before other project imports
from src.core.logging_config import configure_logging
configure_logging()

from src.core.cycle_runner import CycleRunner
from src.core.soul_loader import reload_souls
from src.graph.orchestrator import create_orchestrator_graph

def main():
    parser = argparse.ArgumentParser(description="Quantum Swarm Pipeline")
    sub = parser.add_subparsers(dest="command")
    analyze = sub.add_parser("analyze")
    analyze.add_argument("symbol")
    analyze.add_argument("--mode", default="paper", choices=["paper", "live"])
    analyze.add_argument("--reload-souls", action="store_true")

    args = parser.parse_args()

    if args.command != "analyze":
        parser.print_help()
        sys.exit(1)

    if args.reload_souls:
        reload_souls()

    snapshot = asyncio.run(_run(args.symbol, args.mode))
    print(json.dumps(snapshot.model_dump(mode="json"), indent=2, default=str))
    sys.exit(0 if snapshot.status != "failed" else 1)

async def _run(symbol, mode):
    # Optional DB pool
    db_pool = _try_get_pool()
    graph = create_orchestrator_graph({})
    runner = CycleRunner(graph, db_pool=db_pool, execution_mode=mode)
    return await runner.run_cycle(f"Analyze {symbol}", symbol)
```

### Pattern 3: Retry with Exponential Backoff

**What:** Wrap yfinance download with 3 retries, 1s/2s/4s delays plus jitter.

```python
import random
import time

MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds

async def _fetch_with_retry(symbol, period):
    for attempt in range(MAX_RETRIES):
        try:
            return await asyncio.to_thread(
                yf.download, tickers=symbol, period=period,
                interval="1d", progress=False
            )
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise
            delay = BASE_DELAY * (2 ** attempt) + random.uniform(0, 0.5)
            logger.warning("yfinance retry %d/%d for %s: %s (wait %.1fs)",
                          attempt + 1, MAX_RETRIES, symbol, e, delay)
            await asyncio.sleep(delay)
```

### Pattern 4: Disk Cache with TTL

**What:** JSON file cache at `data/cache/{symbol}.json` with TTL check.
**Key:** Written on every successful fetch. Only READ when `QS_DEV_CACHE=1`.

```python
CACHE_DIR = Path("data/cache")
CACHE_TTL_SECONDS = 3600  # 1 hour

def _read_disk_cache(symbol: str) -> Optional[MarketData]:
    if os.environ.get("QS_DEV_CACHE") != "1":
        return None
    cache_file = CACHE_DIR / f"{symbol.replace('/', '_')}.json"
    if not cache_file.exists():
        return None
    data = json.loads(cache_file.read_text())
    if time.time() - data.get("_cached_at", 0) > CACHE_TTL_SECONDS:
        return None
    return MarketData(**data["market_data"])

def _write_disk_cache(symbol: str, market_data: MarketData) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{symbol.replace('/', '_')}.json"
    cache_file.write_text(json.dumps({
        "_cached_at": time.time(),
        "market_data": market_data.model_dump(mode="json"),
    }, default=str))
```

### Anti-Patterns to Avoid
- **Logging to stdout:** Logs MUST go to stderr. stdout is reserved for the CycleSnapshot JSON output. Mixing them corrupts machine-parseable output.
- **Importing graph modules before configure_logging():** If modules create loggers at import time, those loggers get default handlers. Call configure_logging() first in main.py.
- **Generic retry decorator:** Retry logic is scoped to yfinance only (locked decision). Don't build a generic retry wrapper.
- **Reading disk cache in production:** Disk cache is write-always, read-only-in-dev. Production always gets fresh data from yfinance.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured logging | Custom JSON formatter | structlog ProcessorFormatter | Handles stdlib integration, thread safety, processor chains |
| Log timestamp formatting | Manual datetime formatting | structlog.processors.TimeStamper | ISO 8601 format, consistent across all log entries |
| CLI argument parsing | Manual sys.argv parsing | argparse | Handles help text, validation, subcommands |

## Common Pitfalls

### Pitfall 1: Logger Creation Before Configuration
**What goes wrong:** Modules imported before `configure_logging()` create loggers with default (null) handlers. Those loggers miss structlog formatting.
**Why it happens:** Python's `logging.getLogger(__name__)` at module level runs at import time.
**How to avoid:** In main.py, import and call `configure_logging()` BEFORE importing any project modules. The root logger handler replacement in configure_logging() covers all child loggers retroactively because they inherit from root.
**Warning signs:** Some log lines appear unformatted while others are structured.

### Pitfall 2: SwarmState messages Reducer Accumulation
**What goes wrong:** `messages: Annotated[List[dict], operator.add]` uses an append reducer. LangGraph's state management means messages accumulate across checkpoint updates within a single graph invocation.
**Why it happens:** The operator.add reducer concatenates lists on every state update from every node.
**How to avoid:** CycleRunner._build_initial_state() already starts with `messages: []`. This is sufficient for single-shot execution. The "trimming" concern from PIPE-03 is about ensuring checkpoint storage doesn't bloat -- since we do single-shot (no multi-cycle loops), messages are naturally bounded to one cycle's worth. Document this explicitly.
**Warning signs:** Checkpoint files growing linearly with node count (expected) vs growing across cycles (bug).

### Pitfall 3: yfinance Multi-Index Columns
**What goes wrong:** yfinance sometimes returns DataFrame with MultiIndex columns, breaking `df["close"]` access.
**Why it happens:** yfinance behavior varies by ticker type and version.
**How to avoid:** Already handled in existing yfinance_client.py (line 60-61). Ensure retry logic preserves this normalization.

### Pitfall 4: asyncio.run() in Tests vs Production
**What goes wrong:** Tests use `asyncio.run()` directly; production uses it in main(). Nesting asyncio.run() causes "This event loop is already running".
**Why it happens:** pytest-asyncio or other async test runners may create their own event loop.
**How to avoid:** Use `asyncio.run()` in test functions directly (project pattern from MEMORY.md). Do not use `asyncio.get_event_loop().run_until_complete()`.

### Pitfall 5: DB Pool Initialization Failure
**What goes wrong:** `get_pool()` raises if PostgreSQL is not running, killing the CLI before any useful work.
**Why it happens:** psycopg_pool opens connections eagerly by default (`open=True`).
**How to avoid:** Wrap pool initialization in try/except, fall back to `db_pool=None`. CycleRunner already handles this gracefully with timestamp-based IDs and no-op DB updates.

## Code Examples

### Existing CycleRunner Integration Point
```python
# CycleRunner._build_initial_state() already resets messages: []
# This satisfies PIPE-03 for single-shot mode.
# No additional trimming needed -- each invocation starts clean.

# Source: src/core/cycle_runner.py lines 101-143
```

### Soul Cache Reload
```python
# src/core/soul_loader.py -- add this function
def reload_souls() -> None:
    """Clear soul lru_cache and re-warm all known agents.

    Use for development iteration when SOUL.md files are edited.
    """
    load_soul.cache_clear()
    warmup_soul_cache()
```

### Per-Node Timing in Audit Wrapper
```python
# The with_audit_logging wrapper in orchestrator.py already wraps every node.
# Structured logging captures node entry/exit naturally through logger calls.
# Adding wall-clock timing:
import time
async def wrapped_node(state, **kwargs):
    t0 = time.monotonic()
    logger.info("node_enter", node=node_id)
    result = await node_fn(state, **kwargs)
    elapsed = time.monotonic() - t0
    logger.info("node_exit", node=node_id, duration_ms=round(elapsed * 1000, 1), status="ok")
    return result
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LangGraphOrchestrator.run_task() | CycleRunner.run_cycle() | Phase 24 (v1.4) | CycleRunner is the canonical runner now |
| Legacy src/main.py (QuantumSwarm class) | New argparse CLI | Phase 25 | Clean break, old code removed |
| logging.basicConfig | structlog ProcessorFormatter | Phase 25 | All existing getLogger calls emit structured output |

**Deprecated/outdated:**
- `src/main.py` (current): Legacy QuantumSwarm class with infinite loop. Will be entirely replaced.
- `LangGraphOrchestrator`: Still exists in orchestrator.py but CycleRunner is the preferred wrapper. LangGraphOrchestrator may remain for backward compatibility but is not the CLI path.

## Open Questions

1. **Node timing: modify with_audit_logging or add separate middleware?**
   - What we know: with_audit_logging in orchestrator.py already wraps every node. Adding timing there is natural.
   - What's unclear: Whether modifying orchestrator.py is in scope for Phase 25 or if timing should be logging-only.
   - Recommendation: Add timing to with_audit_logging since it already wraps all nodes. Structured logging will capture it via structlog.

2. **Message trimming scope for single-shot**
   - What we know: CycleRunner._build_initial_state() already starts with empty messages. Single-shot means no accumulation across cycles.
   - What's unclear: Whether PIPE-03 requires explicit trimming within a single cycle (node messages accumulate via reducer) or just across cycles.
   - Recommendation: For PIPE-03, document that single-shot mode satisfies the requirement. Within a cycle, messages grow proportionally to nodes (bounded by graph topology, not unbounded). No explicit truncation needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via `.venv/bin/python3.12 -m pytest`) |
| Config file | None -- pytest runs from project root |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_runner.py tests/test_cli_integration.py -x` |
| Full suite command | `.venv/bin/python3.12 -m pytest tests/ -x --ignore=tests/test_persistence.py` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-01 | CLI runs analyze command, outputs JSON | integration (subprocess) | `.venv/bin/python3.12 -m pytest tests/test_cli_integration.py -x` | No -- Wave 0 |
| PIPE-02 | yfinance retry on failure, disk cache write/read | unit | `.venv/bin/python3.12 -m pytest tests/test_yfinance_resilience.py -x` | No -- Wave 0 |
| PIPE-03 | Messages list bounded across cycles | unit | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_runner.py::TestBuildInitialState -x` | Yes (existing covers fresh state) |
| PIPE-04 | structlog captures node entry/exit with timing | unit | `.venv/bin/python3.12 -m pytest tests/test_logging_config.py -x` | No -- Wave 0 |
| PIPE-05 | reload_souls clears cache and re-warms | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_loader.py -x` | Partial -- needs reload_souls test |

### Sampling Rate
- **Per task commit:** `.venv/bin/python3.12 -m pytest tests/core/test_cycle_runner.py tests/core/test_soul_loader.py -x`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest tests/ -x --ignore=tests/test_persistence.py`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_cli_integration.py` -- covers PIPE-01 (subprocess test)
- [ ] `tests/test_yfinance_resilience.py` -- covers PIPE-02 (retry + disk cache)
- [ ] `tests/test_logging_config.py` -- covers PIPE-04 (structlog configuration)
- [ ] `tests/core/test_soul_loader.py` -- extend with `test_reload_souls` for PIPE-05
- [ ] `tests/core/test_import_boundaries.py` -- extend with `test_logging_config_imports_cleanly`
- [ ] Framework install: `pip install structlog>=24.1.0`

## Sources

### Primary (HIGH confidence)
- structlog official docs (v25.5.0) - stdlib integration, ProcessorFormatter pattern: https://www.structlog.org/en/stable/standard-library.html
- Existing codebase: `src/core/cycle_runner.py`, `src/tools/data_sources/yfinance_client.py`, `src/core/soul_loader.py`, `src/graph/orchestrator.py`, `src/graph/state.py`
- Phase 25 CONTEXT.md - locked decisions and discretion areas

### Secondary (MEDIUM confidence)
- structlog API patterns verified via official documentation fetch

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - structlog is well-documented, argparse is stdlib, all other components exist in codebase
- Architecture: HIGH - follows established project patterns (core leaf modules, CycleRunner, with_audit_logging)
- Pitfalls: HIGH - derived from direct codebase analysis and known project patterns from MEMORY.md

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable domain, no fast-moving dependencies)
