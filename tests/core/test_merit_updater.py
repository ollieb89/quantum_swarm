"""Merit updater node tests — Plan 02 implementation + Phase 29 PersonaScore wiring."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.kami import DEFAULT_MERIT, _extract_fidelity_signal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_scores(handle: str = "AXIOM") -> dict:
    """Return a merit_scores dict with one agent at default values."""
    return {
        handle: {
            "accuracy": DEFAULT_MERIT,
            "recovery": DEFAULT_MERIT,
            "consensus": DEFAULT_MERIT,
            "fidelity": DEFAULT_MERIT,
            "composite": DEFAULT_MERIT,
        }
    }


def _make_state(execution_result=None, active_persona="AXIOM", merit_scores=None,
                weighted_consensus_score=None) -> dict:
    """Build a minimal SwarmState-like dict for tests."""
    return {
        "execution_result": execution_result,
        "active_persona": active_persona,
        "merit_scores": merit_scores or _default_scores(active_persona),
        "weighted_consensus_score": weighted_consensus_score,
    }


def _make_conn_mock():
    """Return a mock async connection with conn.execute() as AsyncMock."""
    conn_mock = AsyncMock()
    conn_mock.execute = AsyncMock()

    conn_ctx = AsyncMock()
    conn_ctx.__aenter__ = AsyncMock(return_value=conn_mock)
    conn_ctx.__aexit__ = AsyncMock(return_value=False)

    pool_mock = MagicMock()
    pool_mock.connection = MagicMock(return_value=conn_ctx)
    return pool_mock, conn_mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_merit_updater_persists():
    """merit_updater calls DB upsert exactly once and returns updated merit_scores for
    the active agent when execution_result has success=True."""
    from src.graph.nodes.merit_updater import merit_updater_node

    pool_mock, conn_mock = _make_conn_mock()
    state = _make_state(
        execution_result={"success": True},
        active_persona="AXIOM",
        merit_scores=_default_scores("AXIOM"),
        weighted_consensus_score=0.8,
    )

    async def run():
        with patch("src.graph.nodes.merit_updater.ensure_pool_open", new_callable=AsyncMock, return_value=pool_mock):
            result = await merit_updater_node(state)
        return result

    result = asyncio.run(run())

    assert "merit_scores" in result
    assert "AXIOM" in result["merit_scores"]
    # DB upsert must have been called once
    conn_mock.execute.assert_called_once()


def test_merit_updater_skips_aborted_cycle():
    """merit_updater returns {} immediately (no DB call) when execution_result is None."""
    from src.graph.nodes.merit_updater import merit_updater_node

    pool_mock, conn_mock = _make_conn_mock()
    state = _make_state(execution_result=None, active_persona="AXIOM")

    async def run():
        with patch("src.graph.nodes.merit_updater.ensure_pool_open", new_callable=AsyncMock, return_value=pool_mock):
            result = await merit_updater_node(state)
        return result

    result = asyncio.run(run())

    assert result == {}
    conn_mock.execute.assert_not_called()


def test_merit_updater_db_fail_no_state_update():
    """If DB upsert raises, merit_updater returns {} so state is not updated without
    persistence (DB and state stay in sync)."""
    from src.graph.nodes.merit_updater import merit_updater_node

    pool_mock, conn_mock = _make_conn_mock()
    conn_mock.execute.side_effect = RuntimeError("DB connection lost")

    state = _make_state(
        execution_result={"success": True},
        active_persona="AXIOM",
        merit_scores=_default_scores("AXIOM"),
    )

    async def run():
        with patch("src.graph.nodes.merit_updater.ensure_pool_open", new_callable=AsyncMock, return_value=pool_mock):
            result = await merit_updater_node(state)
        return result

    result = asyncio.run(run())

    assert result == {}


def test_merit_updater_accuracy_unchanged():
    """After merit_updater runs, the agent's accuracy dimension equals the prior value
    (accuracy is never updated in-cycle)."""
    from src.graph.nodes.merit_updater import merit_updater_node

    prior_accuracy = 0.73
    pool_mock, conn_mock = _make_conn_mock()
    scores = {
        "AXIOM": {
            "accuracy": prior_accuracy,
            "recovery": DEFAULT_MERIT,
            "consensus": DEFAULT_MERIT,
            "fidelity": DEFAULT_MERIT,
            "composite": DEFAULT_MERIT,
        }
    }
    state = _make_state(
        execution_result={"success": True},
        active_persona="AXIOM",
        merit_scores=scores,
        weighted_consensus_score=0.9,
    )

    async def run():
        with patch("src.graph.nodes.merit_updater.ensure_pool_open", new_callable=AsyncMock, return_value=pool_mock):
            result = await merit_updater_node(state)
        return result

    result = asyncio.run(run())

    assert "merit_scores" in result
    axiom = result["merit_scores"]["AXIOM"]
    assert axiom["accuracy"] == round(prior_accuracy, 4), (
        f"Accuracy must remain {prior_accuracy}, got {axiom['accuracy']}"
    )


def test_merit_updater_rounds_to_4dp():
    """Composite value returned by merit_updater has at most 4 decimal places."""
    from src.graph.nodes.merit_updater import merit_updater_node

    pool_mock, conn_mock = _make_conn_mock()
    state = _make_state(
        execution_result={"success": True},
        active_persona="AXIOM",
        merit_scores=_default_scores("AXIOM"),
        weighted_consensus_score=0.75,
    )

    async def run():
        with patch("src.graph.nodes.merit_updater.ensure_pool_open", new_callable=AsyncMock, return_value=pool_mock):
            result = await merit_updater_node(state)
        return result

    result = asyncio.run(run())

    assert "merit_scores" in result
    composite = result["merit_scores"]["AXIOM"]["composite"]
    # Verify at most 4 decimal places
    composite_str = str(composite)
    if "." in composite_str:
        decimals = len(composite_str.split(".")[1])
        assert decimals <= 4, f"Composite has {decimals} decimal places: {composite}"


# ---------------------------------------------------------------------------
# Phase 29: _extract_fidelity_signal rewiring tests
# ---------------------------------------------------------------------------

class TestExtractFidelitySignalRewired:
    """Test _extract_fidelity_signal with persona_composite parameter (Phase 29)."""

    def test_persona_composite_provided(self):
        """When persona_composite=0.72, returns 0.72 directly."""
        result = _extract_fidelity_signal("macro_analyst", persona_composite=0.72)
        assert result == 0.72

    def test_persona_composite_none_falls_back(self):
        """When persona_composite=None, falls back to legacy binary soul check."""
        with patch("src.core.kami.load_soul") as mock_soul:
            mock_soul.return_value = MagicMock(identity="AXIOM identity content")
            result = _extract_fidelity_signal("macro_analyst", persona_composite=None)
        assert result == 1.0  # non-empty identity -> 1.0

    def test_persona_composite_zero_does_not_fallback(self):
        """When persona_composite=0.0, returns 0.0 (does NOT fall back)."""
        result = _extract_fidelity_signal("macro_analyst", persona_composite=0.0)
        assert result == 0.0


# ---------------------------------------------------------------------------
# Phase 29: merit_updater_node PersonaScore integration tests
# ---------------------------------------------------------------------------

class TestMeritUpdaterPersonaScoreIntegration:
    """Test merit_updater_node queries and passes PersonaScore composite."""

    def test_queries_persona_composite(self):
        """merit_updater_node calls get_latest_persona_composite before fidelity."""
        from src.graph.nodes.merit_updater import merit_updater_node

        pool_mock, conn_mock = _make_conn_mock()
        state = _make_state(
            execution_result={"success": True},
            active_persona="AXIOM",
            merit_scores=_default_scores("AXIOM"),
            weighted_consensus_score=0.8,
        )

        mock_get_composite = AsyncMock(return_value=0.85)

        async def run():
            with patch("src.graph.nodes.merit_updater.ensure_pool_open", new_callable=AsyncMock, return_value=pool_mock), \
                 patch("src.graph.nodes.merit_updater.get_latest_persona_composite", mock_get_composite):
                result = await merit_updater_node(state)
            return result

        result = asyncio.run(run())

        mock_get_composite.assert_called_once_with("AXIOM")
        assert "merit_scores" in result
        # Fidelity should be EMA'd toward 0.85
        fidelity = result["merit_scores"]["AXIOM"]["fidelity"]
        assert fidelity != DEFAULT_MERIT  # Should have changed

    def test_persona_composite_085_used_for_fidelity(self):
        """When get_latest_persona_composite returns 0.85, fidelity EMA uses 0.85."""
        from src.graph.nodes.merit_updater import merit_updater_node

        pool_mock, conn_mock = _make_conn_mock()
        state = _make_state(
            execution_result={"success": True},
            active_persona="AXIOM",
            merit_scores=_default_scores("AXIOM"),
            weighted_consensus_score=0.8,
        )

        mock_get_composite = AsyncMock(return_value=0.85)

        async def run():
            with patch("src.graph.nodes.merit_updater.ensure_pool_open", new_callable=AsyncMock, return_value=pool_mock), \
                 patch("src.graph.nodes.merit_updater.get_latest_persona_composite", mock_get_composite):
                result = await merit_updater_node(state)
            return result

        result = asyncio.run(run())

        fidelity = result["merit_scores"]["AXIOM"]["fidelity"]
        # EMA: 0.9 * 0.85 + 0.1 * 0.5 = 0.765 + 0.05 = 0.815
        assert abs(fidelity - 0.815) < 0.001

    def test_persona_composite_none_uses_legacy(self):
        """When get_latest_persona_composite returns None, falls back to legacy binary."""
        from src.graph.nodes.merit_updater import merit_updater_node

        pool_mock, conn_mock = _make_conn_mock()
        state = _make_state(
            execution_result={"success": True},
            active_persona="AXIOM",
            merit_scores=_default_scores("AXIOM"),
            weighted_consensus_score=0.8,
        )

        mock_get_composite = AsyncMock(return_value=None)

        async def run():
            with patch("src.graph.nodes.merit_updater.ensure_pool_open", new_callable=AsyncMock, return_value=pool_mock), \
                 patch("src.graph.nodes.merit_updater.get_latest_persona_composite", mock_get_composite):
                result = await merit_updater_node(state)
            return result

        result = asyncio.run(run())

        # Should still work -- uses legacy binary path
        assert "merit_scores" in result

    def test_persona_composite_db_error_uses_legacy(self):
        """When get_latest_persona_composite raises, falls back to legacy (None)."""
        from src.graph.nodes.merit_updater import merit_updater_node

        pool_mock, conn_mock = _make_conn_mock()
        state = _make_state(
            execution_result={"success": True},
            active_persona="AXIOM",
            merit_scores=_default_scores("AXIOM"),
            weighted_consensus_score=0.8,
        )

        mock_get_composite = AsyncMock(side_effect=RuntimeError("DB down"))

        async def run():
            with patch("src.graph.nodes.merit_updater.ensure_pool_open", new_callable=AsyncMock, return_value=pool_mock), \
                 patch("src.graph.nodes.merit_updater.get_latest_persona_composite", mock_get_composite):
                result = await merit_updater_node(state)
            return result

        result = asyncio.run(run())

        # Should still produce results -- legacy fallback
        assert "merit_scores" in result
