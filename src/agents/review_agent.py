"""
src.agents.review_agent — Analyzes trade outcomes and performance drift.

This agent queries the PostgreSQL trade warehouse, correlates results with
audit rationales and market regimes, and produces a drift report.
"""

import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from src.core.db import get_pool

logger = logging.getLogger(__name__)

_MODEL_ID = "gemini-2.5-flash"

# Lazy LLM singleton — instantiation requires GOOGLE_API_KEY at runtime, not import
_llm = None

def _get_llm() -> ChatGoogleGenerativeAI:
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(model=_MODEL_ID)
    return _llm


class PerformanceReviewAgent:
    """Agent responsible for weekly performance review and drift analysis."""

    def __init__(self):
        # LLM is resolved lazily — not at import time — so modules can be imported
        # in test environments without a live GOOGLE_API_KEY.
        self._llm: Optional[ChatGoogleGenerativeAI] = None

    @property
    def llm(self) -> ChatGoogleGenerativeAI:
        if self._llm is None:
            self._llm = _get_llm()
        return self._llm

    @llm.setter
    def llm(self, value: ChatGoogleGenerativeAI):
        self._llm = value

    async def get_recent_trade_data(self, days: int = 7) -> List[Dict[str, Any]]:
        """Fetch joined trade and audit data for the last N days."""
        pool = get_pool()
        trades = []
        
        query = """
            SELECT
                t.trade_id, t.symbol, t.side, t.position_size, t.entry_price,
                t.stop_loss_level, t.pnl, t.pnl_pct, t.strategy_context,
                a.input_data->'macro_report' as macro_report,
                a.output_data->'rationale' as rationale
            FROM trades t
            LEFT JOIN audit_logs a ON t.audit_log_id = a.id
            WHERE t.execution_time > %s
            ORDER BY t.execution_time DESC;
        """
        
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, (since,))
                    rows = await cur.fetchall()
                    for row in rows:
                        trades.append({
                            "trade_id": row[0],
                            "symbol": row[1],
                            "side": row[2],
                            "position_size": float(row[3]) if row[3] else 0,
                            "entry_price": float(row[4]) if row[4] else 0,
                            "stop_loss": float(row[5]) if row[5] else 0,
                            "pnl": float(row[6]) if row[6] else 0,
                            "pnl_pct": float(row[7]) if row[7] else 0,
                            "strategy_context": row[8],
                            "macro_report": row[9],
                            "rationale": row[10]
                        })
        except Exception as e:
            logger.error("Failed to fetch trade data for review: %s", e)
            
        return trades

    async def generate_drift_report(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trades using LLM to identify performance drift and patterns."""
        if not trades:
            return {"status": "no_data", "message": "No trades found in the specified period."}

        # Prepare a condensed summary for the LLM
        trade_summary = []
        for t in trades:
            trade_summary.append({
                "id": t["trade_id"],
                "sym": t["symbol"],
                "side": t["side"],
                "pnl_pct": t["pnl_pct"],
                "backtest_pnl": t["strategy_context"].get("backtest_result", {}).get("pnl", {}).get("percentage"),
                "regime": t["macro_report"].get("phase") if t["macro_report"] else "unknown",
                "rationale": t["rationale"]
            })

        prompt = (
            "You are the PerformanceReviewAgent for Quantum Swarm. "
            "Analyze the following recent trade outcomes and compare them against their backtest projections. "
            "Identify strategies that are over-performing or under-performing. "
            "Correlate performance with market regimes (bullish, bearish, volatile). "
            "Return a structured JSON report with keys: 'summary', 'drift_detected' (bool), "
            "'overperforming_strategies' (list), 'underperforming_strategies' (list), 'recommendations' (list). "
            f"\n\nTrade Data:\n{json.dumps(trade_summary, indent=2)}"
        )

        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        
        try:
            # Clean LLM output if it includes markdown blocks
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            return json.loads(content)
        except Exception as e:
            logger.error("Failed to parse drift report from LLM: %s", e)
            return {"status": "error", "message": "Failed to parse LLM response"}
