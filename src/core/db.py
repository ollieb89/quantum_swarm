import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

# Connection string (using defaults from docker-compose.yml)
# In production, these should be loaded from environment variables
DB_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://quantum_user:quantum_password@localhost:5433/quantum_swarm"
)

# Global pool instance
_pool: AsyncConnectionPool = None

_db_unavailable = False  # Sticky flag: once DB is known-unreachable, skip retries

def get_pool() -> AsyncConnectionPool | None:
    """Initialize and return the global connection pool.

    Returns ``None`` if the database is unreachable (avoids background
    retry threads that produce noisy RuntimeWarnings).
    """
    global _pool, _db_unavailable
    if _db_unavailable:
        return None
    if _pool is None:
        # Attempt a real psycopg connection to verify the DB is usable
        # before creating the pool (which spawns background threads).
        from psycopg import connect as pg_connect

        try:
            conn = pg_connect(conninfo=DB_URL, connect_timeout=3)
            conn.close()
        except Exception as exc:
            logger.info("PostgreSQL not available — skipping pool init: %s", exc)
            _db_unavailable = True
            return None

        logger.info("Initializing PostgreSQL connection pool...")
        _pool = AsyncConnectionPool(
            conninfo=DB_URL,
            open=False,
            min_size=2,
            max_size=10,
        )
    return _pool

_pool_opened = False


async def ensure_pool_open() -> AsyncConnectionPool | None:
    """Return the pool after ensuring it is open. Returns None if DB unavailable."""
    global _pool_opened
    pool = get_pool()
    if pool is None:
        return None
    if not _pool_opened:
        await pool.open()
        _pool_opened = True
    return pool


@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[AsyncConnection, None]:
    """Async context manager for getting a connection from the pool."""
    pool = await ensure_pool_open()
    if pool is None:
        raise RuntimeError("PostgreSQL is not available")
    async with pool.connection() as conn:
        yield conn

async def close_db_pool():
    """Close the global connection pool."""
    global _pool, _db_unavailable, _pool_opened
    if _pool is not None:
        logger.info("Closing PostgreSQL connection pool...")
        await _pool.close()
        _pool = None
    _db_unavailable = False
    _pool_opened = False
