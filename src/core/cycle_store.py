"""
src.core.cycle_store — Read-only cycle data access layer.

Provides functions to load CycleSnapshot from filesystem JSON and query
PostgreSQL for cycle metadata listing. Core leaf module: NO imports from
src.graph.*.

Exported functions:
    load_cycle           — Load a single CycleSnapshot from disk
    list_cycles          — Unified listing (DB with filesystem fallback)
    list_cycles_db       — List cycle metadata from PostgreSQL
    list_cycles_filesystem — List cycle metadata by scanning filesystem
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.core.cycle_snapshot import CYCLE_ID_PAD_WIDTH, CycleSnapshot

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metadata keys returned by all list_cycles* functions
# ---------------------------------------------------------------------------

_META_KEYS = ("cycle_id", "symbol", "status", "timestamp", "consensus_score")


# ---------------------------------------------------------------------------
# load_cycle
# ---------------------------------------------------------------------------


def load_cycle(cycle_id: int, base_dir: str = "data/cycles") -> CycleSnapshot:
    """Load a CycleSnapshot from its filesystem snapshot.json.

    Args:
        cycle_id: Numeric cycle identifier.
        base_dir: Root directory containing padded cycle subdirectories.

    Returns:
        Validated CycleSnapshot instance.

    Raises:
        FileNotFoundError: If the snapshot.json does not exist.
    """
    padded = str(cycle_id).zfill(CYCLE_ID_PAD_WIDTH)
    path = Path(base_dir) / padded / "snapshot.json"

    if not path.exists():
        raise FileNotFoundError(
            f"No snapshot found for cycle {cycle_id} "
            f"(expected {path})"
        )

    data = json.loads(path.read_text(encoding="utf-8"))
    return CycleSnapshot.model_validate(data)


# ---------------------------------------------------------------------------
# list_cycles_filesystem
# ---------------------------------------------------------------------------


def list_cycles_filesystem(
    base_dir: str = "data/cycles",
    symbol: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Scan filesystem for cycle metadata, sorted newest-first.

    Args:
        base_dir: Root directory containing padded cycle subdirectories.
        symbol: Optional symbol filter (exact match).
        status: Optional status filter (exact match).
        limit: Maximum number of results to return.

    Returns:
        List of metadata dicts with keys: cycle_id, symbol, status,
        timestamp, consensus_score.
    """
    base = Path(base_dir)
    if not base.exists():
        return []

    results: list[dict[str, Any]] = []

    for child in base.iterdir():
        if not child.is_dir():
            continue
        snapshot_path = child / "snapshot.json"
        if not snapshot_path.exists():
            continue

        try:
            raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skipping %s: %s", snapshot_path, exc)
            continue

        entry = {
            "cycle_id": raw.get("cycle_id"),
            "symbol": raw.get("symbol"),
            "status": raw.get("status"),
            "timestamp": raw.get("timestamp"),
            "consensus_score": raw.get("weighted_consensus_score"),
        }

        # Apply filters
        if symbol is not None and entry["symbol"] != symbol:
            continue
        if status is not None and entry["status"] != status:
            continue

        results.append(entry)

    # Sort newest-first by timestamp string (ISO 8601 sorts lexicographically)
    results.sort(key=lambda r: r.get("timestamp") or "", reverse=True)

    if limit is not None:
        results = results[:limit]

    return results


# ---------------------------------------------------------------------------
# list_cycles_db
# ---------------------------------------------------------------------------


async def list_cycles_db(
    pool: Any,
    symbol: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Query PostgreSQL cycle_snapshots table for cycle metadata.

    Args:
        pool: psycopg AsyncConnectionPool instance.
        symbol: Optional symbol filter.
        status: Optional status filter.
        limit: Maximum number of results.

    Returns:
        List of metadata dicts matching the filesystem interface.
    """
    clauses: list[str] = []
    params: list[Any] = []

    if symbol is not None:
        clauses.append("symbol = %s")
        params.append(symbol)
    if status is not None:
        clauses.append("status = %s")
        params.append(status)

    where = ""
    if clauses:
        where = " WHERE " + " AND ".join(clauses)

    sql = (
        "SELECT cycle_id, symbol, status, timestamp, consensus_score"
        f" FROM cycle_snapshots{where}"
        " ORDER BY timestamp DESC"
    )

    if limit is not None:
        sql += " LIMIT %s"
        params.append(limit)

    async with pool.connection() as conn:
        cursor = await conn.execute(sql, params or None)
        rows = await cursor.fetchall()

    return [
        {
            "cycle_id": row[0],
            "symbol": row[1],
            "status": row[2],
            "timestamp": row[3],
            "consensus_score": row[4],
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# list_cycles (unified)
# ---------------------------------------------------------------------------


async def list_cycles(
    pool: Any = None,
    base_dir: str = "data/cycles",
    symbol: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Unified cycle listing: tries DB first, falls back to filesystem.

    Args:
        pool: Optional psycopg AsyncConnectionPool. If None, uses filesystem.
        base_dir: Filesystem base directory (used as fallback or primary).
        symbol: Optional symbol filter.
        status: Optional status filter.
        limit: Maximum number of results.

    Returns:
        List of metadata dicts.
    """
    if pool is not None:
        try:
            return await list_cycles_db(
                pool, symbol=symbol, status=status, limit=limit
            )
        except Exception:
            logger.warning(
                "PostgreSQL query failed, falling back to filesystem",
                exc_info=True,
            )

    return list_cycles_filesystem(
        base_dir=base_dir, symbol=symbol, status=status, limit=limit
    )
