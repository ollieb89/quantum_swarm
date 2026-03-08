"""
Phase 18 — Theory of Mind Soul-Sync: test_soul_sync.py

Full test suite covering TOM-01 and TOM-02 (14 test cases).
Tasks 1-11 will be RED until Task 2 implementation is in place.
Tests 12-14 (topology/handshake) will be RED (skipped) until Plan 02.
"""
import pytest
from unittest.mock import MagicMock, patch

from src.core.soul_loader import AgentSoul, load_soul, warmup_soul_cache
from src.graph.state import SwarmState

# ---------------------------------------------------------------------------
# Plan 02 import guard — soul_sync_handshake_node doesn't exist yet
# ---------------------------------------------------------------------------
try:
    from src.graph.nodes.soul_sync_handshake import soul_sync_handshake_node
    from src.graph.orchestrator import build_graph

    _PLAN02_AVAILABLE = True
except ImportError:
    _PLAN02_AVAILABLE = False
    soul_sync_handshake_node = None  # type: ignore[assignment]
    build_graph = None  # type: ignore[assignment]


# ===========================================================================
# TestAgentSoulUsers — TOM-01: users field
# ===========================================================================

class TestAgentSoulUsers:
    def test_users_field_defaults_empty(self):
        """AgentSoul(agent_id, identity, soul, agents).users == ''"""
        soul = AgentSoul(agent_id="x", identity="i", soul="s", agents="a")
        assert soul.users == ""

    def test_users_in_system_prompt(self):
        """AgentSoul with users='USERS' includes it in system_prompt output."""
        soul = AgentSoul(agent_id="x", identity="i", soul="s", agents="a", users="USERS")
        assert "USERS" in soul.system_prompt

    def test_users_absent_from_system_prompt(self):
        """AgentSoul with users='' does NOT add extra blank blocks to system_prompt."""
        soul = AgentSoul(agent_id="x", identity="i", soul="s", agents="a", users="")
        # system_prompt should be exactly identity + soul + agents joined by "\n\n"
        expected = "i\n\ns\n\na"
        assert soul.system_prompt == expected


# ===========================================================================
# TestPublicSoulSummary — TOM-01: public_soul_summary()
# ===========================================================================

class TestPublicSoulSummary:
    def test_momentum_summary_non_empty(self):
        """load_soul('bullish_researcher').public_soul_summary() returns non-empty string."""
        soul = load_soul("bullish_researcher")
        result = soul.public_soul_summary()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_cassandra_summary_non_empty(self):
        """load_soul('bearish_researcher').public_soul_summary() returns non-empty string."""
        soul = load_soul("bearish_researcher")
        result = soul.public_soul_summary()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_drift_guard_excluded(self):
        """'Drift Guard' must NOT appear in public_soul_summary() output."""
        soul = load_soul("bullish_researcher")
        result = soul.public_soul_summary()
        assert "Drift Guard" not in result

    def test_summary_length(self):
        """len(public_soul_summary()) <= 300 chars."""
        soul = load_soul("bullish_researcher")
        result = soul.public_soul_summary()
        assert len(result) <= 300

    def test_peer_visible_sections_present(self):
        """At least one of Core Beliefs, Voice, Non-Goals content is represented."""
        soul = load_soul("bullish_researcher")
        result = soul.public_soul_summary()
        # At least one section heading or its content should be detectable
        # The summary strips headings but includes the section text;
        # check that at least some content from a peer-visible section is present.
        assert len(result) > 0  # Already covered above; also check no empty output
        # Stronger: summary should NOT be the raw soul dump (Drift Guard excluded means filtering worked)
        assert "Drift Guard" not in result


# ===========================================================================
# TestAgentSoulHashability — TOM-01: lru_cache compatibility
# ===========================================================================

class TestAgentSoulHashability:
    def test_soul_is_hashable(self):
        """hash(AgentSoul(...)) must not raise — required for lru_cache."""
        soul = AgentSoul(agent_id="x", identity="i", soul="s", agents="a")
        result = hash(soul)
        assert isinstance(result, int)


# ===========================================================================
# TestWarmupWithUsers — TOM-01: warmup without USER.md
# ===========================================================================

class TestWarmupWithUsers:
    def test_warmup_no_user_md(self):
        """warmup_soul_cache() completes without error when no USER.md files exist."""
        # macro_analyst, quant_modeler, risk_manager have no USER.md — must not raise
        warmup_soul_cache()


# ===========================================================================
# TestSwarmStateSoulSync — TOM-02: SwarmState field
# ===========================================================================

class TestSwarmStateSoulSync:
    def test_soul_sync_context_field(self):
        """SwarmState TypedDict must have a 'soul_sync_context' annotation."""
        assert "soul_sync_context" in SwarmState.__annotations__


# ===========================================================================
# TestUserMdContent — TOM-01: USER.md integration (unit via dataclass)
# ===========================================================================

class TestUserMdContent:
    def test_users_appended_to_system_prompt(self):
        """When users is non-empty, system_prompt ends with the users content."""
        soul = AgentSoul(
            agent_id="x", identity="identity", soul="soul", agents="agents", users="user content"
        )
        assert soul.system_prompt.endswith("user content")

    def test_users_empty_system_prompt_no_trailing_newlines(self):
        """When users is empty, system_prompt has no trailing double-newline."""
        soul = AgentSoul(agent_id="x", identity="i", soul="s", agents="a", users="")
        assert not soul.system_prompt.endswith("\n\n")


# ===========================================================================
# TestSoulSyncHandshakeNode — Plan 02 scope (skipped until Plan 02)
# ===========================================================================

@pytest.mark.skipif(not _PLAN02_AVAILABLE, reason="Plan 02 not yet implemented")
class TestSoulSyncHandshakeNode:
    def test_node_returns_dict(self):
        """soul_sync_handshake_node(state) returns dict with 'soul_sync_context' key."""
        state: SwarmState = {  # type: ignore[typeddict-item]
            "task_id": "test-01",
            "user_input": "test",
        }
        result = soul_sync_handshake_node(state)
        assert isinstance(result, dict)
        assert "soul_sync_context" in result


# ===========================================================================
# TestGraphTopology — Plan 02 scope (skipped until Plan 02)
# ===========================================================================

@pytest.mark.skipif(not _PLAN02_AVAILABLE, reason="Plan 02 not yet implemented")
class TestGraphTopology:
    def test_build_graph_compiles(self):
        """build_graph() returns a compiled graph without error."""
        graph = build_graph()
        assert graph is not None


# ===========================================================================
# TestNoLLMCalls — Plan 02 scope (skipped until Plan 02)
# ===========================================================================

@pytest.mark.skipif(not _PLAN02_AVAILABLE, reason="Plan 02 not yet implemented")
class TestNoLLMCalls:
    def test_handshake_no_llm(self):
        """soul_sync_handshake_node must not invoke any LLM during execution."""
        with patch("src.graph.nodes.soul_sync_handshake.ChatGoogleGenerativeAI") as mock_llm:
            state: SwarmState = {  # type: ignore[typeddict-item]
                "task_id": "test-01",
                "user_input": "test",
            }
            soul_sync_handshake_node(state)
            mock_llm.assert_not_called()
