import pytest
import asyncio
import uuid
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from src.graph.orchestrator import create_orchestrator_graph
from src.core.db import DB_URL, get_pool, close_db_pool

@pytest.mark.asyncio
async def test_langgraph_persistence_postgres():
    """
    Verifies that LangGraph can persist and resume state using PostgreSQL.
    """
    async with AsyncConnectionPool(conninfo=DB_URL, max_size=5, kwargs={"autocommit": True}) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        # Ensure tables exist
        await checkpointer.setup()
        
        # Compile graph with postgres checkpointer
        config = {"configurable": {"thread_id": "persistence-test-thread"}}
        graph = create_orchestrator_graph({}, checkpointer=checkpointer)
        
        # 1. Run the first step (classify_intent)
        initial_state = {
            "task_id": "persist-123",
            "user_input": "What is the macro outlook?",
            "intent": "unknown",
            "messages": [],
            "total_tokens": 0,
            "trade_history": [],
            "metadata": {}
        }
        
        await graph.ainvoke(initial_state, config=config)
        
        # 2. Verify state was saved in DB
        state = await graph.aget_state(config)
        assert state.values["user_input"] == "What is the macro outlook?"
        
        # 3. Resume / Load from another instance
        graph2 = create_orchestrator_graph({}, checkpointer=checkpointer)
        state2 = await graph2.aget_state(config)
        assert state2.values["user_input"] == "What is the macro outlook?"
        assert state2.next is not None

@pytest.mark.asyncio
async def test_trade_warehouse_persistence():
    """
    Verifies that trade_logger_node successfully writes to the trades table.
    """
    from src.graph.agents.l3.trade_logger import trade_logger_node
    
    # Initialize the global pool for the test
    pool = get_pool()
    await pool.open()
    
    try:
        task_id = f"warehouse-test-{uuid.uuid4().hex[:4]}"
        state = {
            "task_id": task_id,
            "quant_proposal": {"symbol": "ETH/USDT", "side": "buy", "quantity": 0.5},
            "execution_result": {"execution_price": 2500.0, "order_id": f"order-{task_id}"},
            "execution_mode": "paper",
            "trade_history": []
        }
        
        # Run the node
        await trade_logger_node(state)
        
        # Check database
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT symbol, quantity FROM trades WHERE task_id = %s", (task_id,))
                row = await cur.fetchone()
                assert row is not None
                assert row[0] == "ETH/USDT"
                assert float(row[1]) == 0.5
    finally:
        await close_db_pool()
