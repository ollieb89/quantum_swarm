"""Content fidelity tests for macro_analyst soul files (SOUL-02).

Extended with all-agent structural, drift_guard, HEXACO-6, and pairwise
distance tests for Phase 23 persona population validation.
"""
import itertools
import math
import re

import pytest
import yaml

from src.core.drift_eval import SUPPORTED_TYPES
from src.core.soul_loader import _KNOWN_AGENTS, load_soul


def _parse_hexaco(soul_text: str) -> dict[str, float]:
    """Extract hexaco_6 values from SOUL.md text."""
    match = re.search(
        r"```yaml\s*\n(.*?)```",
        soul_text.split("## Personality Profile")[1],
        re.DOTALL,
    )
    parsed = yaml.safe_load(match.group(1))
    return parsed["hexaco_6"]


# ---------------------------------------------------------------------------
# Existing AXIOM-specific tests (unchanged)
# ---------------------------------------------------------------------------


class TestAxiomIdentity:
    def test_identity_contains_identity_section(self):
        soul = load_soul("macro_analyst")
        assert "## Identity" in soul.identity

    def test_identity_contains_archetype_section(self):
        soul = load_soul("macro_analyst")
        assert "## Archetype" in soul.identity

    def test_identity_contains_role_in_swarm_section(self):
        soul = load_soul("macro_analyst")
        assert "## Role in Swarm" in soul.identity

    def test_identity_h1_is_axiom(self):
        soul = load_soul("macro_analyst")
        assert soul.active_persona == "AXIOM"


class TestAxiomSoul:
    def test_soul_contains_core_beliefs_section(self):
        soul = load_soul("macro_analyst")
        assert "## Core Beliefs" in soul.soul

    def test_soul_contains_drift_guard_section(self):
        soul = load_soul("macro_analyst")
        assert "## Drift Guard" in soul.soul

    def test_soul_contains_voice_section(self):
        soul = load_soul("macro_analyst")
        assert "## Voice" in soul.soul

    def test_soul_contains_non_goals_section(self):
        soul = load_soul("macro_analyst")
        assert "## Non-Goals" in soul.soul

    def test_drift_guard_mentions_recency_bias(self):
        soul = load_soul("macro_analyst")
        assert "recency" in soul.soul.lower() or "momentum" in soul.soul.lower()


class TestAxiomAgents:
    def test_agents_contains_output_contract_section(self):
        soul = load_soul("macro_analyst")
        assert "## Output Contract" in soul.agents

    def test_agents_contains_decision_rules_section(self):
        soul = load_soul("macro_analyst")
        assert "## Decision Rules" in soul.agents

    def test_agents_contains_workflow_section(self):
        soul = load_soul("macro_analyst")
        assert "## Workflow" in soul.agents


# ---------------------------------------------------------------------------
# All-agent structural validation (Phase 23)
# ---------------------------------------------------------------------------


class TestAllAgentStructure:
    """Verify every agent has required sections in IDENTITY.md, SOUL.md, AGENTS.md."""

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_identity_has_identity_section(self, agent_id: str):
        soul = load_soul(agent_id)
        assert "## Identity" in soul.identity

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_identity_has_archetype_section(self, agent_id: str):
        soul = load_soul(agent_id)
        assert "## Archetype" in soul.identity

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_identity_has_role_in_swarm_section(self, agent_id: str):
        soul = load_soul(agent_id)
        assert "## Role in Swarm" in soul.identity

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_soul_has_core_beliefs_section(self, agent_id: str):
        soul = load_soul(agent_id)
        assert "## Core Beliefs" in soul.soul

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_soul_has_drift_guard_section(self, agent_id: str):
        soul = load_soul(agent_id)
        assert "## Drift Guard" in soul.soul

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_soul_has_voice_section(self, agent_id: str):
        soul = load_soul(agent_id)
        assert "## Voice" in soul.soul

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_soul_has_non_goals_section(self, agent_id: str):
        soul = load_soul(agent_id)
        assert "## Non-Goals" in soul.soul

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_agents_has_output_contract_section(self, agent_id: str):
        soul = load_soul(agent_id)
        assert "## Output Contract" in soul.agents

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_agents_has_decision_rules_section(self, agent_id: str):
        soul = load_soul(agent_id)
        assert "## Decision Rules" in soul.agents

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_agents_has_workflow_section(self, agent_id: str):
        soul = load_soul(agent_id)
        assert "## Workflow" in soul.agents

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_active_persona_is_meaningful(self, agent_id: str):
        soul = load_soul(agent_id)
        assert soul.active_persona, "active_persona must not be empty"
        assert soul.active_persona != agent_id, (
            f"active_persona should be a persona name, not the agent_id '{agent_id}'"
        )


# ---------------------------------------------------------------------------
# All-agent drift_guard validation (Phase 23)
# ---------------------------------------------------------------------------


class TestAllAgentDriftGuard:
    """Verify every agent has at least 2 valid, unique drift rules."""

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_has_at_least_two_drift_rules(self, agent_id: str):
        soul = load_soul(agent_id)
        assert len(soul.drift_rules) >= 2, (
            f"{agent_id} has {len(soul.drift_rules)} drift rules, need >= 2"
        )

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_drift_rules_have_unique_flag_ids(self, agent_id: str):
        soul = load_soul(agent_id)
        flag_ids = [r.flag_id for r in soul.drift_rules]
        assert len(flag_ids) == len(set(flag_ids)), (
            f"{agent_id} has duplicate flag_ids: {flag_ids}"
        )

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_drift_rules_have_supported_types(self, agent_id: str):
        soul = load_soul(agent_id)
        for rule in soul.drift_rules:
            assert rule.type in SUPPORTED_TYPES, (
                f"{agent_id} rule '{rule.flag_id}' has unsupported type '{rule.type}'"
            )


# ---------------------------------------------------------------------------
# HEXACO-6 profile validation (Phase 23)
# ---------------------------------------------------------------------------


class TestHexacoProfiles:
    """Verify every agent has a HEXACO-6 personality profile with valid values."""

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_soul_has_personality_profile_section(self, agent_id: str):
        soul = load_soul(agent_id)
        assert "## Personality Profile" in soul.soul

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_soul_has_hexaco_6_yaml_key(self, agent_id: str):
        soul = load_soul(agent_id)
        assert "hexaco_6:" in soul.soul

    @pytest.mark.parametrize("agent_id", sorted(_KNOWN_AGENTS))
    def test_hexaco_6_values_in_valid_range(self, agent_id: str):
        soul = load_soul(agent_id)
        hexaco = _parse_hexaco(soul.soul)
        assert len(hexaco) == 6, f"Expected 6 HEXACO dimensions, got {len(hexaco)}"
        for dim, val in hexaco.items():
            assert isinstance(val, (int, float)), (
                f"{agent_id} HEXACO dimension '{dim}' is not numeric: {val}"
            )
            assert 0.0 <= val <= 1.0, (
                f"{agent_id} HEXACO dimension '{dim}' = {val} is outside [0.0, 1.0]"
            )


# ---------------------------------------------------------------------------
# HEXACO-6 pairwise distance validation (Phase 23)
# ---------------------------------------------------------------------------


class TestHexacoDistances:
    """All 10 pairwise Euclidean distances between 5 agents must exceed 1.0."""

    def test_all_pairwise_distances_exceed_threshold(self):
        agents = sorted(_KNOWN_AGENTS)
        profiles: dict[str, list[float]] = {}
        for agent_id in agents:
            soul = load_soul(agent_id)
            hexaco = _parse_hexaco(soul.soul)
            profiles[agent_id] = list(hexaco.values())

        threshold = 1.0
        for a, b in itertools.combinations(agents, 2):
            dist = math.sqrt(
                sum((x - y) ** 2 for x, y in zip(profiles[a], profiles[b]))
            )
            assert dist > threshold, (
                f"HEXACO distance between {a} and {b} is {dist:.3f}, "
                f"must exceed {threshold}"
            )
