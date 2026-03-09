#!/usr/bin/env python3
"""
Quantum Swarm Pipeline Runner -- CLI entry point.

Runs the full LangGraph swarm pipeline for a given symbol and outputs
a CycleSnapshot as JSON to stdout.

Usage:
    python src/main.py analyze BTC --mode paper
    python src/main.py analyze BTC --mode paper --reload-souls

PIPE-03: Messages bounded by single-shot execution -- CycleRunner resets
messages:[] per cycle.  Each invocation runs exactly one cycle and exits.
Within a single cycle, message growth is bounded by graph topology (fixed
number of nodes).  No trimming needed beyond the fresh-state reset.
"""

import argparse
import asyncio
import json
import logging
import sys

# CRITICAL: configure structured logging BEFORE any other project imports.
# This ensures every module-level getLogger(__name__) call picks up the
# structlog ProcessorFormatter on the root logger.  See 25-RESEARCH.md Pitfall 1.
from src.core.logging_config import configure_logging

configure_logging()

from src.core.cycle_runner import CycleRunner  # noqa: E402
from src.core.cycle_snapshot import CycleSnapshot  # noqa: E402
from src.core.persistence import setup_persistence  # noqa: E402
from src.cli.replay import handle_replay, register_replay_parser  # noqa: E402
from src.core.soul_loader import reload_souls  # noqa: E402
from src.graph.orchestrator import create_orchestrator_graph  # noqa: E402

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------


def _try_get_pool():
    """Attempt to acquire a PostgreSQL connection pool.

    Returns the pool on success, or None if PostgreSQL is unavailable.
    CycleRunner already handles db_pool=None gracefully (timestamp-based
    IDs, no-op DB updates).
    """
    try:
        from src.core.db import get_pool

        return get_pool()
    except Exception:
        logger.warning("PostgreSQL unavailable, running without DB persistence")
        return None


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------


async def _run(symbol: str, mode: str) -> CycleSnapshot:
    """Execute a single pipeline cycle and return the snapshot."""
    pool = _try_get_pool()
    if pool:
        await setup_persistence(pool)

    graph = create_orchestrator_graph({})
    runner = CycleRunner(graph, db_pool=pool, execution_mode=mode)
    return await runner.run_cycle(f"Analyze {symbol}", symbol)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and run the swarm pipeline."""
    parser = argparse.ArgumentParser(
        description="Quantum Swarm Pipeline Runner",
    )
    sub = parser.add_subparsers(dest="command")

    analyze_parser = sub.add_parser(
        "analyze", help="Run analysis pipeline for a symbol"
    )
    analyze_parser.add_argument("symbol", help="Ticker symbol (e.g. BTC, AAPL)")
    analyze_parser.add_argument(
        "--mode",
        default="paper",
        choices=["paper", "live"],
        help="Execution mode (default: paper)",
    )
    analyze_parser.add_argument(
        "--reload-souls",
        action="store_true",
        help="Clear and re-warm soul cache before running",
    )

    register_replay_parser(sub)

    args = parser.parse_args()

    if args.command == "replay":
        sys.exit(handle_replay(args))

    if args.command != "analyze":
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.reload_souls:
        reload_souls()

    try:
        snapshot = asyncio.run(_run(args.symbol, args.mode))
    except Exception as exc:
        # Build a minimal failed CycleSnapshot so output format is consistent
        snapshot = CycleSnapshot(
            cycle_id=0,
            task_id="cli-error",
            symbol=args.symbol,
            status="failed",
            error_context={
                "error_type": type(exc).__name__,
                "message": str(exc),
            },
        )

    print(json.dumps(snapshot.model_dump(mode="json"), indent=2, default=str))
    sys.exit(0 if snapshot.status != "failed" else 1)


if __name__ == "__main__":
    main()
