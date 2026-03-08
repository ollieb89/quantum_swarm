"""Post-execution node: in-cycle KAMI EMA update for Recovery, Consensus, Fidelity dimensions."""
import json
import logging
from pathlib import Path
from typing import Any, Dict

import yaml

from src.core.db import get_pool
from src.core.kami import (
    KAMIDimensions,
    apply_ema,
    compute_merit,
    DEFAULT_MERIT,
    _extract_recovery_signal,
    _extract_consensus_signal,
    _extract_fidelity_signal,
)
from src.graph.state import SwarmState

logger = logging.getLogger(__name__)

_KAMI_CONFIG: Dict = {}


def _load_kami_config() -> Dict:
    global _KAMI_CONFIG
    if not _KAMI_CONFIG:
        config_path = Path(__file__).parents[3] / "config" / "swarm_config.yaml"
        try:
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
            _KAMI_CONFIG = cfg.get("kami", {})
        except Exception as e:
            logger.warning("merit_updater: could not load swarm_config.yaml: %s", e)
            _KAMI_CONFIG = {}
    return _KAMI_CONFIG


def _get_weights() -> Dict[str, float]:
    cfg = _load_kami_config()
    return {
        "alpha": cfg.get("alpha", 0.30),
        "beta": cfg.get("beta", 0.35),
        "gamma": cfg.get("gamma", 0.25),
        "delta": cfg.get("delta", 0.10),
    }


def _get_lambda() -> float:
    return _load_kami_config().get("lambda", 0.9)


async def _persist_merit(soul_handle: str, entry: Dict[str, Any]) -> None:
    composite = entry["composite"]
    dimensions = {k: v for k, v in entry.items() if k != "composite"}
    pool = get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            """
            INSERT INTO agent_merit_scores (soul_handle, composite, dimensions, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (soul_handle) DO UPDATE SET
                composite   = EXCLUDED.composite,
                dimensions  = EXCLUDED.dimensions,
                updated_at  = EXCLUDED.updated_at
            """,
            (soul_handle, composite, json.dumps(dimensions)),
        )


async def merit_updater_node(state: SwarmState) -> dict:
    """In-cycle KAMI EMA update for Recovery, Consensus, Fidelity.

    Accuracy is NOT updated in-cycle (deferred async path for post-trade resolution).
    Aborted cycles (no execution_result) are skipped entirely.
    DB write must succeed before state update is returned — if DB fails, return {} to keep sync.
    """
    if not state.get("execution_result"):
        return {}  # Aborted cycle — no KAMI update

    active_handle = state.get("active_persona", "")
    if not active_handle:
        logger.warning("merit_updater: active_persona not set — skipping update")
        return {}

    current_scores = state.get("merit_scores") or {}
    agent_entry = current_scores.get(active_handle, {})

    lam = _get_lambda()
    weights = _get_weights()

    # Extract in-cycle signals
    recovery_signal = _extract_recovery_signal(state)
    consensus_signal = _extract_consensus_signal(state)
    fidelity_signal = _extract_fidelity_signal(active_handle)

    # Apply EMA to each dimension (Accuracy is preserved unchanged)
    new_rec = apply_ema(agent_entry.get("recovery", DEFAULT_MERIT), recovery_signal, lam)
    new_con = apply_ema(agent_entry.get("consensus", DEFAULT_MERIT), consensus_signal, lam)
    new_fid = apply_ema(agent_entry.get("fidelity", DEFAULT_MERIT), fidelity_signal, lam)
    new_acc = agent_entry.get("accuracy", DEFAULT_MERIT)  # Accuracy: unchanged in-cycle

    dims = KAMIDimensions(accuracy=new_acc, recovery=new_rec, consensus=new_con, fidelity=new_fid)
    composite = compute_merit(dims, weights)

    updated_entry = {
        "accuracy": round(new_acc, 4),
        "recovery": round(new_rec, 4),
        "consensus": round(new_con, 4),
        "fidelity": round(new_fid, 4),
        "composite": round(composite, 4),
    }

    # Persist first — if DB write fails, do NOT update state (keeps DB and state in sync)
    try:
        await _persist_merit(active_handle, updated_entry)
    except Exception as e:
        logger.error(
            "merit_updater: DB persist failed for %s: %s — skipping state update",
            active_handle,
            e,
        )
        return {}

    new_scores = {**current_scores, active_handle: updated_entry}
    return {"merit_scores": new_scores}
