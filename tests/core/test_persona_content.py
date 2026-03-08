"""Content fidelity tests for macro_analyst soul files (SOUL-02)."""
import pytest
from src.core.soul_loader import load_soul


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
