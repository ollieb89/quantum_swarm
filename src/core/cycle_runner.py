"""
src.core.cycle_runner -- Async wrapper that executes a LangGraph pipeline,
extracts SwarmState fields into a CycleSnapshot, and persists to both
filesystem and PostgreSQL.

IMPORT BOUNDARY: This module must NOT import from src.graph.
The graph is received via dependency injection (constructor parameter).
"""

import json
import logging
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .cycle_snapshot import CycleSnapshot

logger = logging.getLogger(__name__)

# Default base directory for cycle snapshot files
_DEFAULT_BASE_DIR = "data/cycles"


class CycleRunner:
    """
    Executes a LangGraph pipeline and persists results as CycleSnapshot.

    Sits outside the graph per architecture decision -- no graph node changes.
    Each run_cycle() builds a fresh initial_state to prevent accumulation.
    """

    def __init__(
        self,
        graph: Any,
        db_pool: Any = None,
        execution_mode: str = "paper",
        base_dir: str = _DEFAULT_BASE_DIR,
    ) -> None:
        self._graph = graph
        self._db_pool = db_pool
        self._execution_mode = execution_mode
        self._base_dir = base_dir

    # ------------------------------------------------------------------
    # Database operations
    # ------------------------------------------------------------------

    async def _allocate_cycle_id(self, symbol: str) -> int:
        """
        INSERT placeholder row into cycle_snapshots with status='running'.
        Returns SERIAL cycle_id via RETURNING.
        Falls back to timestamp-based ID if db_pool is None.
        """
        if self._db_pool is None:
            return int(datetime.now(timezone.utc).timestamp() * 1000) % 10**9

        async with self._db_pool.connection() as conn:
            cursor = await conn.execute(
                "INSERT INTO cycle_snapshots (task_id, symbol, status) "
                "VALUES (%s, %s, 'running') RETURNING cycle_id",
                ("pending", symbol),
            )
            row = await cursor.fetchone()
            return row[0]

    async def _update_cycle_row(self, snapshot: CycleSnapshot) -> None:
        """
        UPDATE cycle_snapshots with final metadata.
        No-op if db_pool is None.
        """
        if self._db_pool is None:
            return

        snapshot_path = str(Path(self._base_dir) / snapshot.padded_id() / "snapshot.json")
        error_summary = None
        if snapshot.error_context:
            error_summary = snapshot.error_context.get("message", "")[:500]

        async with self._db_pool.connection() as conn:
            await conn.execute(
                "UPDATE cycle_snapshots SET "
                "status = %s, task_id = %s, consensus_score = %s, "
                "snapshot_path = %s, error_summary = %s "
                "WHERE cycle_id = %s",
                (
                    snapshot.status,
                    snapshot.task_id,
                    snapshot.weighted_consensus_score,
                    snapshot_path,
                    error_summary,
                    snapshot.cycle_id,
                ),
            )

    # ------------------------------------------------------------------
    # State building
    # ------------------------------------------------------------------

    def _build_initial_state(self, user_input: str) -> dict:
        """
        Build a fresh SwarmState dict with a new uuid task_id.

        Duplicates the initial_state pattern from orchestrator.py.
        Each call produces an independent state -- NO reuse.
        """
        task_id = str(uuid.uuid4())
        return {
            "task_id": task_id,
            "user_input": user_input,
            "intent": "unknown",
            "messages": [],
            "macro_report": None,
            "quant_proposal": None,
            "bullish_thesis": None,
            "bearish_thesis": None,
            "debate_resolution": None,
            "weighted_consensus_score": None,
            "debate_history": [],
            "risk_approval": None,
            "consensus_score": 0.0,
            "compliance_flags": [],
            "risk_approved": None,
            "risk_notes": None,
            "final_decision": None,
            "metadata": {"created_at": datetime.now(timezone.utc).isoformat()},
            "blackboard_session": task_id,
            "total_tokens": 0,
            "trade_history": [],
            "execution_mode": self._execution_mode,
            "data_fetcher_result": None,
            "knowledge_base_result": None,
            "backtest_result": None,
            "execution_result": None,
            "decision_card_status": None,
            "decision_card_error": None,
            "decision_card_audit_ref": None,
            "system_prompt": None,
            "active_persona": None,
            "merit_scores": None,
            "soul_sync_context": None,
            "soft_failed_nodes": [],
        }

    # ------------------------------------------------------------------
    # Snapshot extraction
    # ------------------------------------------------------------------

    def _extract_snapshot(
        self,
        cycle_id: int,
        task_id: str,
        symbol: str,
        final_state: dict,
        status: str,
        error_ctx: Optional[dict] = None,
    ) -> CycleSnapshot:
        """
        Map SwarmState fields to CycleSnapshot.

        For completed: reads all fields.
        For rejected: agent memos + debate present, execution_result/decision_card None.
        For failed: populates error_context, agent fields may be None.
        """
        # Build decision_card dict from state if available
        decision_card = None
        if status == "completed" and final_state.get("decision_card_audit_ref"):
            decision_card = {
                "card_id": final_state.get("decision_card_audit_ref"),
                "status": final_state.get("decision_card_status"),
            }

        return CycleSnapshot(
            cycle_id=cycle_id,
            task_id=task_id,
            symbol=symbol,
            status=status,
            macro_report=final_state.get("macro_report"),
            quant_proposal=final_state.get("quant_proposal"),
            bullish_thesis=final_state.get("bullish_thesis"),
            bearish_thesis=final_state.get("bearish_thesis"),
            debate_history=final_state.get("debate_history"),
            debate_resolution=final_state.get("debate_resolution"),
            weighted_consensus_score=final_state.get("weighted_consensus_score"),
            merit_scores=final_state.get("merit_scores"),
            soul_sync_context=final_state.get("soul_sync_context"),
            risk_approved=final_state.get("risk_approved"),
            risk_notes=final_state.get("risk_notes"),
            execution_result=final_state.get("execution_result"),
            decision_card=decision_card,
            error_context=error_ctx,
            soft_failed_nodes=final_state.get("soft_failed_nodes", []),
            degraded=bool(final_state.get("soft_failed_nodes")),
        )

    # ------------------------------------------------------------------
    # Filesystem persistence
    # ------------------------------------------------------------------

    def _write_snapshot_file(self, snapshot: CycleSnapshot) -> Path:
        """
        Create data/cycles/{padded_id}/ and write snapshot.json.
        Returns the Path to the written file.
        """
        snap_dir = Path(snapshot.snapshot_dir(base=self._base_dir))
        snap_dir.mkdir(parents=True, exist_ok=True)

        file_path = snap_dir / "snapshot.json"
        file_path.write_text(
            json.dumps(snapshot.model_dump(mode="json"), indent=2, default=str),
            encoding="utf-8",
        )
        return file_path

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def run_cycle(self, user_input: str, symbol: str) -> CycleSnapshot:
        """
        Execute a full pipeline cycle and persist the result.

        1. Allocate cycle_id from PostgreSQL (or fallback)
        2. Build fresh initial_state
        3. Invoke graph
        4. Determine status (failed/rejected/completed)
        5. Extract snapshot, validate, write file, update DB
        6. Return CycleSnapshot
        """
        cycle_id = await self._allocate_cycle_id(symbol)
        initial_state = self._build_initial_state(user_input)
        task_id = initial_state["task_id"]

        config = {"configurable": {"thread_id": task_id}}

        # Reset per-session budget counters so each cycle starts fresh
        budget = getattr(self._graph, "budget_manager", None)
        if budget is not None:
            budget.reset_session()

        try:
            final_state = await self._graph.ainvoke(initial_state, config=config)

            # Determine status from final state
            if final_state.get("risk_approved") is False:
                status = "rejected"
            else:
                status = "completed"

            snapshot = self._extract_snapshot(
                cycle_id=cycle_id,
                task_id=task_id,
                symbol=symbol,
                final_state=final_state,
                status=status,
            )

        except Exception as exc:
            snapshot = self._extract_snapshot(
                cycle_id=cycle_id,
                task_id=task_id,
                symbol=symbol,
                final_state={},
                status="failed",
                error_ctx={
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                    "traceback_summary": traceback.format_exc()[-500:],
                },
            )

        # Validate completed cycles (skip for degraded — partial runs are valid)
        if snapshot.status == "completed" and not snapshot.degraded:
            snapshot.validate_completed()

        # Persist
        self._write_snapshot_file(snapshot)
        await self._update_cycle_row(snapshot)

        logger.info(
            "Cycle %s (%s) finished: status=%s",
            snapshot.padded_id(), symbol, snapshot.status,
        )
        return snapshot
