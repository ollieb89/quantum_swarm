import pytest
import asyncio
from datetime import datetime, timezone
from src.core.audit_logger import AuditLogger
from src.core.db import close_db_pool

@pytest.fixture
async def audit_logger():
    """Fixture to provide a clean AuditLogger and ensure DB pool is closed."""
    from src.core.db import get_pool
    pool = get_pool()
    await pool.open()
    # Truncate before each test to ensure isolated chain verification
    async with pool.connection() as conn:
        await conn.execute("TRUNCATE audit_logs RESTART IDENTITY CASCADE")
    logger = AuditLogger()
    yield logger
    await close_db_pool()

@pytest.mark.asyncio
async def test_audit_chain_integrity(audit_logger):
    """Tests that the hash chain is correctly linked and verifiable."""
    # Use a dummy task ID
    task_id = "test-task-001"
    
    # Log a few transitions
    await audit_logger.log_transition(
        task_id=task_id,
        node_id="node_1",
        input_data={"msg": "start"},
        output_data={"status": "running"}
    )
    
    await audit_logger.log_transition(
        task_id=task_id,
        node_id="node_2",
        input_data={"status": "running"},
        output_data={"status": "processing"}
    )
    
    await audit_logger.log_transition(
        task_id=task_id,
        node_id="node_3",
        input_data={"status": "processing"},
        output_data={"status": "complete"}
    )
    
    # Verify the chain
    is_valid = await audit_logger.verify_chain()
    assert is_valid is True, "Audit chain should be valid after normal logging"

@pytest.mark.asyncio
async def test_audit_chain_tamper_detection(audit_logger):
    """Tests that tampering with an entry breaks the chain verification."""
    from src.core.db import get_pool
    
    task_id = "tamper-task"
    
    # Log two entries
    await audit_logger.log_transition(task_id, "n1", {"in": 1}, {"out": 1})
    await audit_logger.log_transition(task_id, "n2", {"in": 2}, {"out": 2})
    
    # Verify it's valid initially
    assert await audit_logger.verify_chain() is True
    
    # Manually tamper with the database
    pool = get_pool()
    # Ensure pool is open if not already
    await pool.open()
    
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            # Change the output_data of the first entry
            await cur.execute(
                "UPDATE audit_logs SET output_data = '{\"out\": \"TAMPERED\"}' WHERE node_id = 'n1' AND task_id = %s",
                (task_id,)
            )
    
    # Verify the chain again - should fail now
    is_valid = await audit_logger.verify_chain()
    assert is_valid is False, "Audit chain verification should fail after tampering"
