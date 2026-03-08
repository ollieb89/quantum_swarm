import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from .db import DB_URL

logger = logging.getLogger(__name__)

@asynccontextmanager
async def get_checkpointer() -> AsyncGenerator[AsyncPostgresSaver, None]:
    """
    Initialize and return an AsyncPostgresSaver checkpointer.

    This context manager handles both the connection pool and the 
    checkpointer initialization.
    """
    async with AsyncConnectionPool(
        conninfo=DB_URL,
        min_size=1,
        max_size=5,
        kwargs={"autocommit": True}
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        yield checkpointer

async def setup_persistence():
    """
    Initializes the database schema for LangGraph checkpointing and Trade Warehouse.
    Should be run once during application startup.
    """
    logger.info("Setting up PostgreSQL schemas (LangGraph + Trade Warehouse)...")
    async with AsyncConnectionPool(conninfo=DB_URL, min_size=1, max_size=1, kwargs={"autocommit": True}) as pool:
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
        # Migration notes for existing DBs:
        # ALTER TABLE trades ADD COLUMN IF NOT EXISTS exit_time TIMESTAMPTZ;
        # ALTER TABLE trades ADD COLUMN IF NOT EXISTS atr_at_entry NUMERIC;
        # ALTER TABLE trades ADD COLUMN IF NOT EXISTS stop_loss_multiplier NUMERIC;
        # ALTER TABLE trades ADD COLUMN IF NOT EXISTS stop_loss_method VARCHAR(32);
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

    logger.info("PostgreSQL schemas initialized.")
