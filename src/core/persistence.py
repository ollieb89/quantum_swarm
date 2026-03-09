import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from .db import DB_URL

logger = logging.getLogger(__name__)

@asynccontextmanager
async def get_checkpointer(
    pool: AsyncConnectionPool | None = None,
) -> AsyncGenerator[AsyncPostgresSaver, None]:
    """
    Initialize and return an AsyncPostgresSaver checkpointer.

    If *pool* is provided it is reused (caller owns its lifecycle).
    Otherwise a dedicated pool is created with explicit open to avoid
    background supervisor errors ("pool-1").
    """
    if pool is not None:
        checkpointer = AsyncPostgresSaver(pool)
        yield checkpointer
    else:
        async with AsyncConnectionPool(
            conninfo=DB_URL,
            min_size=1,
            max_size=5,
            open=False,
            kwargs={"autocommit": True},
        ) as owned_pool:
            await owned_pool.open()
            checkpointer = AsyncPostgresSaver(owned_pool)
            yield checkpointer

async def setup_persistence(pool: AsyncConnectionPool | None = None):
    """
    Initializes the database schema for LangGraph checkpointing and Trade Warehouse.
    Should be run once during application startup.

    If *pool* is provided it is reused; otherwise a dedicated pool is created.
    """
    logger.info("Setting up PostgreSQL schemas (LangGraph + Trade Warehouse)...")
    if pool is not None:
        await _run_schema_setup(pool)
    else:
        async with AsyncConnectionPool(
            conninfo=DB_URL, min_size=1, max_size=1, open=False, kwargs={"autocommit": True}
        ) as owned_pool:
            await owned_pool.open()
            await _run_schema_setup(owned_pool)
    logger.info("PostgreSQL schemas initialized.")


async def _run_schema_setup(pool: AsyncConnectionPool) -> None:
    """Execute all CREATE TABLE / migration statements against *pool*."""
    # 1. LangGraph Checkpoints
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()

    # 2. Audit Logs (Phase 4, Step 2)
    async with pool.connection() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            task_id VARCHAR(64) NOT NULL,
            timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            node_id VARCHAR(128) NOT NULL,
            input_data JSONB NOT NULL,
            output_data JSONB NOT NULL,
            entry_hash CHAR(64) NOT NULL,
            prev_hash CHAR(64),
            CONSTRAINT audit_log_immutability CHECK (id IS NOT NULL)
        );
        CREATE INDEX IF NOT EXISTS idx_audit_task_id ON audit_logs(task_id);
        """)

    # 3. Trade Warehouse
    async with pool.connection() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id SERIAL PRIMARY KEY,
            trade_id VARCHAR(64) UNIQUE NOT NULL,
            task_id VARCHAR(64) NOT NULL,
            audit_log_id INTEGER REFERENCES audit_logs(id),
            symbol VARCHAR(32) NOT NULL,
            side VARCHAR(16) NOT NULL,
            position_size NUMERIC NOT NULL,
            entry_price NUMERIC NOT NULL,
            stop_loss_level NUMERIC,
            atr_at_entry NUMERIC,
            stop_loss_multiplier NUMERIC,
            stop_loss_method VARCHAR(32),
            trade_risk_score NUMERIC,
            portfolio_heat NUMERIC,
            execution_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            exit_time TIMESTAMPTZ,
            execution_mode VARCHAR(16) NOT NULL,
            strategy_context JSONB,
            pnl NUMERIC,
            pnl_pct NUMERIC
        );
        CREATE INDEX IF NOT EXISTS idx_trades_task_id ON trades(task_id);
        CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
        CREATE INDEX IF NOT EXISTS idx_trades_exit_time ON trades(exit_time);
        """)
        # Idempotent column migrations for existing tables
        await conn.execute("""
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS position_size NUMERIC;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS stop_loss_level NUMERIC;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS atr_at_entry NUMERIC;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS stop_loss_multiplier NUMERIC;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS stop_loss_method VARCHAR(32);
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS trade_risk_score NUMERIC;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS portfolio_heat NUMERIC;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS strategy_context JSONB;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS pnl NUMERIC;
        ALTER TABLE trades ADD COLUMN IF NOT EXISTS pnl_pct NUMERIC;
        """)

    # 4. Agent Merit Scores (Phase 16: KAMI Merit Index)
    async with pool.connection() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_merit_scores (
            soul_handle    VARCHAR(64) PRIMARY KEY,
            composite      NUMERIC(6, 4) NOT NULL DEFAULT 0.5,
            dimensions     JSONB,
            updated_at     TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            evolution_suspended BOOLEAN DEFAULT FALSE
        );
        CREATE INDEX IF NOT EXISTS idx_merit_soul_handle ON agent_merit_scores(soul_handle);
        """)

    # 5. ARS Drift Auditor State (Phase 19: ARS-01)
    async with pool.connection() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS ars_state (
            soul_handle    VARCHAR(64) NOT NULL,
            metric_name    VARCHAR(64) NOT NULL,
            breach_count   INTEGER DEFAULT 0,
            last_audit_ts  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (soul_handle, metric_name)
        );
        """)

    # 6. Cycle Snapshots (Phase 24: Cycle Persistence)
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
            error_summary   TEXT,
            CONSTRAINT valid_status CHECK (status IN ('running', 'completed', 'rejected', 'failed'))
        );
        CREATE INDEX IF NOT EXISTS idx_cycle_task_id ON cycle_snapshots(task_id);
        CREATE INDEX IF NOT EXISTS idx_cycle_symbol ON cycle_snapshots(symbol);
        CREATE INDEX IF NOT EXISTS idx_cycle_status ON cycle_snapshots(status);
        CREATE INDEX IF NOT EXISTS idx_cycle_timestamp ON cycle_snapshots(timestamp);
        """)

    # 7. Persona Scores (Phase 29: PersonaScore 5D)
    async with pool.connection() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS persona_scores (
            id            SERIAL PRIMARY KEY,
            cycle_id      INTEGER NOT NULL,
            soul_handle   VARCHAR(64) NOT NULL,
            consistency   NUMERIC(5, 4) NOT NULL,
            tone          NUMERIC(5, 4) NOT NULL,
            logic         NUMERIC(5, 4) NOT NULL,
            depth         NUMERIC(5, 4) NOT NULL,
            bias          NUMERIC(5, 4) NOT NULL,
            composite     NUMERIC(5, 4) NOT NULL,
            rationale     TEXT,
            scored_at     TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_persona_scores_soul_handle ON persona_scores(soul_handle);
        CREATE INDEX IF NOT EXISTS idx_persona_scores_cycle_id ON persona_scores(cycle_id);
        """)
