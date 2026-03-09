"""Tests for src.core.persona_scorer — PersonaScore 5D LLM-as-Judge evaluation."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# PersonaScoreResult validation tests
# ---------------------------------------------------------------------------


class TestPersonaScoreResult:
    """Pydantic model validation for 5-dimension persona scores."""

    def test_valid_scores_produce_correct_composite(self):
        from src.core.persona_scorer import PersonaScoreResult

        result = PersonaScoreResult(
            consistency=0.8,
            tone=0.6,
            logic=0.9,
            depth=0.7,
            bias=1.0,
            rationale="Good alignment overall.",
        )
        expected = round((0.8 + 0.6 + 0.9 + 0.7 + 1.0) / 5, 4)
        assert result.composite == expected

    def test_rejects_floats_outside_range(self):
        from src.core.persona_scorer import PersonaScoreResult

        with pytest.raises(ValidationError):
            PersonaScoreResult(
                consistency=1.5,  # out of range
                tone=0.5,
                logic=0.5,
                depth=0.5,
                bias=0.5,
                rationale="Bad",
            )

        with pytest.raises(ValidationError):
            PersonaScoreResult(
                consistency=0.5,
                tone=-0.1,  # out of range
                logic=0.5,
                depth=0.5,
                bias=0.5,
                rationale="Bad",
            )

    def test_entry_has_fallback_false_default(self):
        from src.core.persona_scorer import PersonaScoreEntry

        entry = PersonaScoreEntry(
            soul_handle="AXIOM",
            consistency=0.5,
            tone=0.5,
            logic=0.5,
            depth=0.5,
            bias=0.5,
            composite=0.5,
            rationale="test",
        )
        assert entry.fallback is False


# ---------------------------------------------------------------------------
# Mapping tests
# ---------------------------------------------------------------------------


class TestMappings:
    """Verify handle-to-agent and handle-to-output mappings."""

    def test_handle_to_agent_id_has_4_entries(self):
        from src.core.persona_scorer import HANDLE_TO_AGENT_ID

        assert len(HANDLE_TO_AGENT_ID) == 4
        assert set(HANDLE_TO_AGENT_ID.keys()) == {"AXIOM", "MOMENTUM", "CASSANDRA", "SIGMA"}

    def test_handle_to_output_field_has_4_entries(self):
        from src.core.persona_scorer import HANDLE_TO_OUTPUT_FIELD

        assert len(HANDLE_TO_OUTPUT_FIELD) == 4
        assert set(HANDLE_TO_OUTPUT_FIELD.keys()) == {"AXIOM", "MOMENTUM", "CASSANDRA", "SIGMA"}


# ---------------------------------------------------------------------------
# Judge prompt tests
# ---------------------------------------------------------------------------


class TestBuildJudgePrompt:
    """Verify judge prompt includes soul files and agent output."""

    def test_prompt_includes_soul_content_and_output(self):
        from src.core.persona_scorer import _build_judge_prompt

        soul = MagicMock()
        soul.identity = "# AXIOM\nIdentity content"
        soul.soul = "Soul content with beliefs"
        soul.agents = "Agents context"

        agent_output = {"recommendation": "BUY BTC"}
        prompt = _build_judge_prompt(soul, agent_output, "AXIOM")

        assert "Identity content" in prompt
        assert "Soul content with beliefs" in prompt
        assert "Agents context" in prompt
        assert "BUY BTC" in prompt


# ---------------------------------------------------------------------------
# evaluate_agent() tests
# ---------------------------------------------------------------------------


class TestEvaluateAgent:
    """Unit tests for single-agent evaluation."""

    def test_returns_result_from_mocked_llm(self):
        from src.core.persona_scorer import PersonaScoreResult

        mock_result = PersonaScoreResult(
            consistency=0.8,
            tone=0.7,
            logic=0.9,
            depth=0.6,
            bias=0.8,
            rationale="Well aligned.",
        )
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_result)

        with patch("src.core.persona_scorer._get_judge_llm", return_value=mock_llm), \
             patch("src.core.persona_scorer.load_soul") as mock_soul:
            soul = MagicMock()
            soul.identity = "# AXIOM"
            soul.soul = "Soul"
            soul.agents = "Agents"
            mock_soul.return_value = soul

            from src.core.persona_scorer import evaluate_agent, _scorer_breaker
            # Ensure breaker is closed
            _scorer_breaker._state = __import__(
                "src.core.circuit_breaker", fromlist=["CircuitState"]
            ).CircuitState.CLOSED
            _scorer_breaker._failure_count = 0

            result = asyncio.run(
                evaluate_agent("AXIOM", {"recommendation": "BUY"}, cycle_id=1)
            )
            assert result is not None
            assert result.consistency == 0.8

    def test_returns_none_on_llm_failure(self):
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("LLM down"))

        with patch("src.core.persona_scorer._get_judge_llm", return_value=mock_llm), \
             patch("src.core.persona_scorer.load_soul") as mock_soul:
            soul = MagicMock()
            soul.identity = "# AXIOM"
            soul.soul = "Soul"
            soul.agents = "Agents"
            mock_soul.return_value = soul

            from src.core.persona_scorer import evaluate_agent, _scorer_breaker
            from src.core.circuit_breaker import CircuitState
            _scorer_breaker._state = CircuitState.CLOSED
            _scorer_breaker._failure_count = 0

            result = asyncio.run(
                evaluate_agent("AXIOM", {"recommendation": "BUY"}, cycle_id=1)
            )
            assert result is None

    def test_skips_when_circuit_breaker_open(self):
        with patch("src.core.persona_scorer.load_soul"):
            from src.core.persona_scorer import evaluate_agent, _scorer_breaker
            from src.core.circuit_breaker import CircuitState

            # Force breaker open
            _scorer_breaker._state = CircuitState.OPEN
            _scorer_breaker._opened_at = __import__("time").monotonic()

            result = asyncio.run(
                evaluate_agent("AXIOM", {"recommendation": "BUY"}, cycle_id=1)
            )
            assert result is None

            # Reset
            _scorer_breaker._state = CircuitState.CLOSED
            _scorer_breaker._failure_count = 0

    def test_skips_when_agent_output_is_none(self):
        from src.core.persona_scorer import evaluate_agent

        result = asyncio.run(evaluate_agent("AXIOM", None, cycle_id=1))
        assert result is None


# ---------------------------------------------------------------------------
# evaluate_all_agents() tests
# ---------------------------------------------------------------------------


class TestEvaluateAllAgents:
    """Tests for parallel evaluation with fallback handling."""

    def test_collects_results_and_uses_fallback_for_failures(self):
        from src.core.persona_scorer import PersonaScoreResult

        mock_result = PersonaScoreResult(
            consistency=0.8, tone=0.7, logic=0.9, depth=0.6, bias=0.8,
            rationale="Good.",
        )

        call_count = 0

        async def mock_evaluate(handle, output, cycle_id):
            nonlocal call_count
            call_count += 1
            if handle == "CASSANDRA":
                return None  # simulate failure
            return mock_result

        agent_outputs = {
            "AXIOM": {"report": "x"},
            "MOMENTUM": {"thesis": "y"},
            "CASSANDRA": {"thesis": "z"},
            "SIGMA": {"proposal": "w"},
        }

        with patch("src.core.persona_scorer.evaluate_agent", side_effect=mock_evaluate), \
             patch("src.core.persona_scorer.get_latest_persona_composite", new_callable=AsyncMock, return_value=0.65):
            from src.core.persona_scorer import evaluate_all_agents
            results = asyncio.run(evaluate_all_agents(agent_outputs, cycle_id=1))

        assert len(results) == 4
        assert results["AXIOM"].fallback is False
        assert results["CASSANDRA"].fallback is True
        # Fallback should use previous composite spread across dims
        assert results["CASSANDRA"].composite == 0.65

    def test_handles_partial_failures_with_return_exceptions(self):
        from src.core.persona_scorer import PersonaScoreResult

        mock_result = PersonaScoreResult(
            consistency=0.9, tone=0.9, logic=0.9, depth=0.9, bias=0.9,
            rationale="Great.",
        )

        async def mock_evaluate(handle, output, cycle_id):
            if handle == "SIGMA":
                raise RuntimeError("Unexpected error")
            return mock_result

        agent_outputs = {
            "AXIOM": {"report": "x"},
            "MOMENTUM": {"thesis": "y"},
            "CASSANDRA": {"thesis": "z"},
            "SIGMA": {"proposal": "w"},
        }

        with patch("src.core.persona_scorer.evaluate_agent", side_effect=mock_evaluate), \
             patch("src.core.persona_scorer.get_latest_persona_composite", new_callable=AsyncMock, return_value=None):
            from src.core.persona_scorer import evaluate_all_agents
            results = asyncio.run(evaluate_all_agents(agent_outputs, cycle_id=1))

        assert len(results) == 4
        assert results["SIGMA"].fallback is True
        # No previous composite -> default 0.5
        assert results["SIGMA"].composite == 0.5


# ---------------------------------------------------------------------------
# DB persistence tests
# ---------------------------------------------------------------------------


class TestPersistence:
    """Tests for persona score DB operations."""

    def test_persist_persona_scores_writes_rows(self):
        from src.core.persona_scorer import PersonaScoreEntry, persist_persona_scores

        scores = {
            "AXIOM": PersonaScoreEntry(
                soul_handle="AXIOM", consistency=0.8, tone=0.7, logic=0.9,
                depth=0.6, bias=0.8, composite=0.76, rationale="Good.",
            ),
        }

        mock_conn = AsyncMock()
        mock_cur = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cur)
        mock_cur.__aenter__ = AsyncMock(return_value=mock_cur)
        mock_cur.__aexit__ = AsyncMock(return_value=False)

        mock_pool = AsyncMock()
        mock_pool.connection = MagicMock(return_value=mock_conn)

        with patch("src.core.persona_scorer.ensure_pool_open", new_callable=AsyncMock, return_value=mock_pool):
            asyncio.run(persist_persona_scores(cycle_id=1, scores=scores))

        mock_cur.execute.assert_called_once()

    def test_get_latest_persona_composite_returns_value(self):
        mock_conn = AsyncMock()
        mock_cur = AsyncMock()
        mock_cur.fetchone = AsyncMock(return_value=(0.82,))
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cur)
        mock_cur.__aenter__ = AsyncMock(return_value=mock_cur)
        mock_cur.__aexit__ = AsyncMock(return_value=False)

        mock_pool = AsyncMock()
        mock_pool.connection = MagicMock(return_value=mock_conn)

        with patch("src.core.persona_scorer.ensure_pool_open", new_callable=AsyncMock, return_value=mock_pool):
            from src.core.persona_scorer import get_latest_persona_composite
            result = asyncio.run(get_latest_persona_composite("AXIOM"))

        assert result == 0.82

    def test_get_latest_persona_composite_returns_none_when_empty(self):
        mock_conn = AsyncMock()
        mock_cur = AsyncMock()
        mock_cur.fetchone = AsyncMock(return_value=None)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cur)
        mock_cur.__aenter__ = AsyncMock(return_value=mock_cur)
        mock_cur.__aexit__ = AsyncMock(return_value=False)

        mock_pool = AsyncMock()
        mock_pool.connection = MagicMock(return_value=mock_conn)

        with patch("src.core.persona_scorer.ensure_pool_open", new_callable=AsyncMock, return_value=mock_pool):
            from src.core.persona_scorer import get_latest_persona_composite
            result = asyncio.run(get_latest_persona_composite("NONEXISTENT"))

        assert result is None
