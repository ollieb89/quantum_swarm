import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.models.audit import AuditLogEntry
from .db import get_pool

logger = logging.getLogger(__name__)

# Phase 15: Fields excluded from AuditLogger hash input.
# Soul fields must not enter the hash chain — they are runtime-injected persona
# context, not trade-decision data, and would corrupt MiFID II audit immutability
# if included (content changes across agent restarts without any decision change).
# soul_sync_context is pre-declared here for Phase 18 (Theory of Mind Soul-Sync).
AUDIT_EXCLUDED_FIELDS: frozenset[str] = frozenset({
    "system_prompt",
    "active_persona",
    "soul_sync_context",
})


def _strip_excluded(data: dict) -> dict:
    """Return a shallow copy of data with AUDIT_EXCLUDED_FIELDS removed."""
    return {k: v for k, v in data.items() if k not in AUDIT_EXCLUDED_FIELDS}


class AuditLogger:
    """
    Asynchronous audit logger with hash-chaining for immutable provenance logs.
    Ensures every node transition in the graph is recorded and auditable.
    """

    def __init__(self):
        self._last_hash: Optional[str] = None
        self._table_initialized: bool = False

    async def initialize(self):
        """Creates the audit_logs table if it doesn't exist."""
        if self._table_initialized:
            return

        query = """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            task_id VARCHAR(64) NOT NULL,
            timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            node_id VARCHAR(128) NOT NULL,
            input_data JSONB NOT NULL,
            output_data JSONB NOT NULL,
            entry_hash CHAR(64) NOT NULL,
            prev_hash CHAR(64),
            -- Prevent modifications after insertion
            CONSTRAINT audit_log_immutability CHECK (id IS NOT NULL)
        );
        -- Prevent UPDATE/DELETE via triggers in production
        -- CREATE INDEX IF NOT EXISTS idx_audit_task_id ON audit_logs(task_id);
        """
        pool = get_pool()
        try:
            await pool.open()
        except Exception:
            pass  # Pool may already be open
        async with pool.connection() as conn:
            await conn.execute(query)
            # Retrieve the last hash in the chain for session continuity
            self._last_hash = await self._get_last_hash(conn)
            
        self._table_initialized = True
        logger.info("AuditLogger initialized with last_hash: %s", self._last_hash)

    async def _get_last_hash(self, conn) -> Optional[str]:
        """Retrieves the hash of the most recent audit log entry."""
        async with conn.cursor() as cur:
            await cur.execute("SELECT entry_hash FROM audit_logs ORDER BY id DESC LIMIT 1")
            row = await cur.fetchone()
            return row[0] if row else None

    def _calculate_hash(self, entry: Dict[str, Any], prev_hash: Optional[str]) -> str:
        """Calculates a SHA-256 hash for the given entry data and previous hash."""
        # Strip soul fields before hashing — must happen here so verify_chain is consistent
        clean_input = _strip_excluded(entry.get("input_data", {}))
        clean_output = _strip_excluded(entry.get("output_data", {}))

        data_string = json.dumps({
            "task_id": entry["task_id"],
            "timestamp": entry["timestamp"].isoformat(),
            "node_id": entry["node_id"],
            "input_data": clean_input,
            "output_data": clean_output,
        }, sort_keys=True, default=str)
        
        hasher = hashlib.sha256()
        hasher.update(data_string.encode('utf-8'))
        if prev_hash:
            hasher.update(prev_hash.encode('utf-8'))
            
        return hasher.hexdigest()

    async def log_transition(self, task_id: str, node_id: str, input_data: Dict[str, Any], output_data: Dict[str, Any]):
        """Records a single node transition to the persistent audit log."""
        if not self._table_initialized:
            await self.initialize()

        timestamp = datetime.now(timezone.utc)
        
        # Prepare the log entry payload
        entry_payload = {
            "task_id": task_id,
            "timestamp": timestamp,
            "node_id": node_id,
            "input_data": input_data,
            "output_data": output_data
        }
        
        # Calculate the next hash in the chain
        current_hash = self._calculate_hash(entry_payload, self._last_hash)
        
        # Save to database
        pool = get_pool()
        try:
            await pool.open()
        except Exception:
            pass  # Pool may already be open
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO audit_logs (task_id, timestamp, node_id, input_data, output_data, entry_hash, prev_hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        task_id, 
                        timestamp, 
                        node_id, 
                        json.dumps(input_data, default=str), 
                        json.dumps(output_data, default=str), 
                        current_hash, 
                        self._last_hash
                    )
                )
        
        # Update session state for next chain element
        self._last_hash = current_hash
        logger.debug("Logged audit transition for node %s in task %s", node_id, task_id)

    async def verify_chain(self) -> bool:
        """Verifies the integrity of the entire hash chain in the database."""
        pool = get_pool()
        try:
            await pool.open()
        except Exception:
            pass  # Pool may already be open
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT task_id, timestamp, node_id, input_data, output_data, entry_hash, prev_hash FROM audit_logs ORDER BY id ASC")
                prev_h = None
                async for row in cur:
                    task_id, ts, node_id, input_data, output_data, entry_hash, prev_hash = row
                    
                    # Verify link consistency
                    if prev_hash != prev_h:
                        logger.error("Audit chain break detected at hash %s! Expected prev_hash %s but found %s", entry_hash, prev_h, prev_hash)
                        return False
                        
                    # Recalculate hash and verify integrity
                    calc_payload = {
                        "task_id": task_id,
                        "timestamp": ts,
                        "node_id": node_id,
                        "input_data": input_data,
                        "output_data": output_data
                    }
                    if self._calculate_hash(calc_payload, prev_h) != entry_hash:
                        logger.error("Audit integrity breach detected! Re-calculated hash for %s does not match stored hash.", entry_hash)
                        return False
                    
                    prev_h = entry_hash
                    
        return True
