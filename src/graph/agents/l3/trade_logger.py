"""
src.graph.agents.l3.trade_logger — TradeLogger LangGraph node.

Exports:
    trade_logger_node(state: SwarmState) -> dict    synchronous LangGraph node
    get_recent_trades(state) -> list                sliding-window helper for L2 researchers
    TRADE_HISTORY_WINDOW                            N=15 (within discretion range 10-20)

This node closes the self-improvement loop by appending a serializable TradeRecord
to SwarmState.trade_history after each execution cycle.  L2 researchers (BullishResearcher,
BearishResearcher) call get_recent_trades(state) to inject the last N trades as context.

State reads:
    state["quant_proposal"]    dict — symbol, side, quantity
    state["execution_result"]  dict — execution_price, success, order_id
    state["execution_mode"]    str  — "paper" | "live"

State writes:
    "trade_history"  list with one new TradeRecord dict (operator.add reducer appends it)
    "messages"       list — one assistant message entry

IMPORTANT: Returns [record_dict] (list-wrapped) because the operator.add reducer
in SwarmState concatenates lists — returning a plain dict would raise a TypeError.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from src.graph.state import SwarmState
from src.core.parsing import parse_quant_proposal
from src.models.data_models import TradeRecord
from src.core.db import get_pool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRADE_HISTORY_WINDOW: int = 15  # N=15 within Claude's discretion range 10-20


# ---------------------------------------------------------------------------
# Helper: sliding-window read for L2 researchers
# ---------------------------------------------------------------------------


def get_recent_trades(state: Any) -> list:
    """Return at most TRADE_HISTORY_WINDOW most recent trade records from state."""
    history = state.get("trade_history", [])
    return list(history[-TRADE_HISTORY_WINDOW:])


# ---------------------------------------------------------------------------
# TradeLogger LangGraph node
# ---------------------------------------------------------------------------


async def trade_logger_node(state: SwarmState) -> dict[str, Any]:
    """L3 TradeLogger — append a TradeRecord to SwarmState.trade_history AND persist to PostgreSQL Warehouse.

    Args:
        state: Current SwarmState shared across the LangGraph graph.

    Returns:
        Partial state update dict with ``trade_history`` and ``messages`` keys.
    """
    task_id = state.get("task_id", "unknown")
    logger.info("TradeLogger node invoked (task_id=%s)", task_id)

    quant_parsed: dict = parse_quant_proposal(state)
    execution_result: dict = state.get("execution_result") or {}

    symbol: str = quant_parsed.get("symbol", "UNKNOWN")
    side: str = quant_parsed.get("side", "buy")
    quantity: float = float(quant_parsed.get("quantity", 1.0))
    execution_price: float = float(execution_result.get("execution_price", 0.0) or 0.0)
    stop_loss: float | None = quant_parsed.get("stop_loss")
    if stop_loss is not None:
        stop_loss = float(stop_loss)
    
    atr_at_entry: float | None = quant_parsed.get("atr_at_entry")
    if atr_at_entry is not None:
        atr_at_entry = float(atr_at_entry)
    
    stop_loss_multiplier: float | None = quant_parsed.get("stop_loss_multiplier", 2.0)
    if stop_loss_multiplier is not None:
        stop_loss_multiplier = float(stop_loss_multiplier)

    # Phase 8: Risk metrics from metadata
    meta = state.get("metadata", {})
    trade_risk_score = meta.get("trade_risk_score")
    portfolio_heat = meta.get("portfolio_heat")

    execution_mode: str = state.get("execution_mode", "paper")
    # Bug Fix: Ensure trade_id is never None even if order_id is explicitly None
    trade_id: str = (execution_result.get("order_id") or 
                   f"trade_{task_id}_{datetime.now(timezone.utc).timestamp()}")

    record = TradeRecord(
        trade_id=trade_id,
        symbol=symbol,
        side=side,
        entry_price=execution_price,
        stop_loss_level=stop_loss,
        atr_at_entry=atr_at_entry,
        stop_loss_multiplier=stop_loss_multiplier,
        stop_loss_method="atr",
        trade_risk_score=trade_risk_score,
        portfolio_heat=portfolio_heat,
        exit_price=None,
        position_size=quantity,
        pnl=None,
        pnl_pct=None,
        entry_time=datetime.now(timezone.utc),
        exit_time=None,
        execution_mode=execution_mode,
        strategy_context=dict(quant_parsed),  # snapshot
    )

    # Persist to Trade Warehouse (PostgreSQL)
    pool = get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # Resolve the last audit log ID for this task to provide full trace
                await cur.execute(
                    "SELECT id FROM audit_logs WHERE task_id = %s ORDER BY id DESC LIMIT 1",
                    (task_id,)
                )
                audit_row = await cur.fetchone()
                audit_log_id = audit_row[0] if audit_row else None

                await cur.execute(
                    """
                    INSERT INTO trades (
                        trade_id, task_id, audit_log_id, symbol, side, position_size, 
                        entry_price, stop_loss_level, atr_at_entry, 
                        stop_loss_multiplier, stop_loss_method, trade_risk_score, 
                        portfolio_heat, execution_mode, strategy_context
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (trade_id) DO NOTHING;
                    """,
                    (
                        trade_id,
                        task_id,
                        audit_log_id,
                        symbol,
                        side,
                        quantity,
                        execution_price,
                        stop_loss,
                        atr_at_entry,
                        stop_loss_multiplier,
                        "atr",
                        trade_risk_score,
                        portfolio_heat,
                        execution_mode,
                        json.dumps(dict(quant_parsed))
                    )
                )
    except Exception as e:
        logger.error("Failed to persist trade %s to PostgreSQL warehouse: %s", trade_id, e)

    # Pydantic v2 — mode="json" ensures datetime is serialized to ISO string
    record_dict = record.model_dump(mode="json")

    logger.info(
        "TradeLogger: recorded trade_id=%s symbol=%s side=%s @ %.4f mode=%s",
        record.trade_id,
        symbol,
        side,
        execution_price,
        execution_mode,
    )

    return {
        # List-wrapped so operator.add reducer appends (not replaces) trade_history
        "trade_history": [record_dict],
        "messages": [
            {
                "role": "assistant",
                "content": f"TradeLogger: recorded {symbol} {side} trade_id={record.trade_id} in PostgreSQL warehouse",
            }
        ],
    }
