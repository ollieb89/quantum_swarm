"""Unit tests for SoulLoader (SOUL-01, SOUL-03, SOUL-04, SOUL-06, EVOL-02)."""
import pytest
from src.core.drift_eval import DriftRule
from src.core.soul_loader import AgentSoul, load_soul, warmup_soul_cache
from src.core.soul_errors import SoulNotFoundError, SoulSecurityError


# --- SOUL-01: load_soul returns populated AgentSoul ---

class TestLoadSoul:
    def test_load_soul_returns_agent_soul(self):
        soul = load_soul("macro_analyst")
        assert isinstance(soul, AgentSoul)

    def test_load_soul_fields_are_non_empty(self):
        soul = load_soul("macro_analyst")
        assert soul.identity.strip()
        assert soul.soul.strip()
        assert soul.agents.strip()

    def test_load_soul_agent_id_preserved(self):
        soul = load_soul("macro_analyst")
        assert soul.agent_id == "macro_analyst"

    def test_system_prompt_combines_all_files(self):
        soul = load_soul("macro_analyst")
        assert soul.identity in soul.system_prompt
        assert soul.soul in soul.system_prompt
        assert soul.agents in soul.system_prompt

    def test_active_persona_is_non_empty_string(self):
        soul = load_soul("macro_analyst")
        assert isinstance(soul.active_persona, str)
        assert soul.active_persona.strip()

    def test_agent_soul_is_hashable(self):
        soul = load_soul("macro_analyst")
        assert hash(soul) is not None  # frozen=True guarantees hashability

    def test_path_traversal_raises_soul_security_error(self):
        with pytest.raises(SoulSecurityError, match="path traversal"):
            load_soul("../etc/passwd")

    def test_path_traversal_does_not_raise_file_not_found(self):
        with pytest.raises(SoulSecurityError):
            load_soul("../../sensitive")

    def test_missing_agent_raises_soul_not_found_error(self):
        with pytest.raises(SoulNotFoundError):
            load_soul("nonexistent_agent_xyz")

    def test_lru_cache_returns_same_object(self):
        soul1 = load_soul("macro_analyst")
        soul2 = load_soul("macro_analyst")
        assert soul1 is soul2  # lru_cache: same object reference


# --- SOUL-06: cache_clear is callable (fixture exercises this automatically) ---

class TestCacheClear:
    def test_load_soul_has_cache_clear(self):
        assert callable(load_soul.cache_clear)

    def test_cache_clear_does_not_raise(self):
        load_soul.cache_clear()  # must not raise


# --- SOUL-03: warmup_soul_cache ---

class TestWarmupSoulCache:
    def test_warmup_completes_without_error(self):
        # Requires all five soul directories to exist (macro_analyst + 4 skeletons)
        warmup_soul_cache()  # must not raise


# --- SOUL-04: SwarmState carries system_prompt and active_persona fields ---

class TestSwarmStateFields:
    def test_swarmstate_has_system_prompt_field(self):
        from src.graph.state import SwarmState
        import typing
        hints = typing.get_type_hints(SwarmState)
        assert "system_prompt" in hints, "SwarmState missing 'system_prompt' field"

    def test_swarmstate_has_active_persona_field(self):
        from src.graph.state import SwarmState
        import typing
        hints = typing.get_type_hints(SwarmState)
        assert "active_persona" in hints, "SwarmState missing 'active_persona' field"


# --- EVOL-02: AgentSoul.drift_rules populated from SOUL.md YAML ---

class TestDriftRulesIntegration:
    def test_macro_analyst_has_drift_rules(self):
        soul = load_soul("macro_analyst")
        assert isinstance(soul.drift_rules, tuple)
        assert len(soul.drift_rules) > 0
        assert all(isinstance(r, DriftRule) for r in soul.drift_rules)

    def test_macro_analyst_has_expected_flag_ids(self):
        soul = load_soul("macro_analyst")
        flag_ids = {r.flag_id for r in soul.drift_rules}
        assert flag_ids == {"recency_bias", "narrative_capture", "certainty_overreach"}

    def test_skeleton_agent_has_empty_drift_rules(self):
        soul = load_soul("bullish_researcher")
        assert soul.drift_rules == ()

    def test_drift_rules_field_is_tuple(self):
        soul = load_soul("macro_analyst")
        assert isinstance(soul.drift_rules, tuple)
