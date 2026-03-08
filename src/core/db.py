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

def get_pool() -> AsyncConnectionPool:
    """Initialize and return the global connection pool."""
    global _pool
    if _pool is None:
        logger.info("Initializing PostgreSQL connection pool...")
        _pool = AsyncConnectionPool(
            conninfo=DB_URL,
            open=True, # Open immediately
            min_size=2,
            max_size=10,
        )
    return _pool

@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[AsyncConnection, None]:
    """Async context manager for getting a connection from the pool."""
    pool = get_pool()
    async with pool.connection() as conn:
        yield conn

async def close_db_pool():
    """Close the global connection pool."""
    global _pool
    if _pool is not None:
        logger.info("Closing PostgreSQL connection pool...")
        await _pool.close()
        _pool = None
