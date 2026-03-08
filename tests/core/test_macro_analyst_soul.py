"""Integration tests: macro_analyst_node soul injection and audit exclusion (SOUL-05, SOUL-07)."""
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage

import src.graph.agents.analysts as analysts_mod
from src.graph.agents.analysts import MacroAnalyst
from src.graph.state import SwarmState


def _make_state(**overrides) -> dict:
    base: dict = {
        "task_id": "test-soul-001",
        "user_input": "test soul injection",
        "intent": "macro",
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
        "metadata": {},
        "blackboard_session": None,
        "total_tokens": 0,
        "trade_history": [],
        "execution_mode": "paper",
        "data_fetcher_result": None,
        "knowledge_base_result": None,
        "backtest_result": None,
        "execution_result": None,
        "decision_card_status": None,
        "decision_card_error": None,
        "decision_card_audit_ref": None,
        "system_prompt": None,
        "active_persona": None,
    }
    base.update(overrides)
    return base


class TestMacroAnalystSoulInjection:
    """SOUL-05: macro_analyst_node writes system_prompt and active_persona to state."""

    def test_macro_analyst_writes_system_prompt_to_state(self):
        analysts_mod._macro_agent = None
        fake_response = AIMessage(content='{"phase": "test", "risk_on": true, "confidence": 0.5, "sentiment": "neutral", "outlook": "short", "indicators": {}}', name="MacroAnalyst")
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": [fake_response]}
        analysts_mod._macro_agent = mock_agent

        state = _make_state()
        result = MacroAnalyst(state)

        assert "system_prompt" in result, "MacroAnalyst must write system_prompt to state"
        assert result["system_prompt"] is not None
        assert len(result["system_prompt"]) > 0

    def test_macro_analyst_writes_active_persona_to_state(self):
        analysts_mod._macro_agent = None
        fake_response = AIMessage(content='{"phase": "test"}', name="MacroAnalyst")
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": [fake_response]}
        analysts_mod._macro_agent = mock_agent

        state = _make_state()
        result = MacroAnalyst(state)

        assert "active_persona" in result, "MacroAnalyst must write active_persona to state"
        assert result["active_persona"] == "AXIOM"

    def test_macro_analyst_uses_no_live_llm_calls(self):
        """SOUL-07: test runs zero real LLM calls — mock verifies invocation count."""
        analysts_mod._macro_agent = None
        fake_response = AIMessage(content="test", name="MacroAnalyst")
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": [fake_response]}
        analysts_mod._macro_agent = mock_agent

        state = _make_state()
        MacroAnalyst(state)

        mock_agent.invoke.assert_called_once()


class TestAuditFieldExclusion:
    """SOUL-05: system_prompt and active_persona must not appear in AuditLogger hash input."""

    def test_audit_excluded_fields_constant_exists(self):
        from src.core.audit_logger import AUDIT_EXCLUDED_FIELDS
        assert "system_prompt" in AUDIT_EXCLUDED_FIELDS
        assert "active_persona" in AUDIT_EXCLUDED_FIELDS

    def test_audit_excluded_fields_includes_soul_sync_context(self):
        """Phase 18 pre-declared exclusion must also be present."""
        from src.core.audit_logger import AUDIT_EXCLUDED_FIELDS
        assert "soul_sync_context" in AUDIT_EXCLUDED_FIELDS

    def test_strip_excluded_removes_soul_fields(self):
        from src.core.audit_logger import AUDIT_EXCLUDED_FIELDS
        from src.core.audit_logger import AuditLogger
        logger_instance = AuditLogger()
        data = {
            "some_field": "value",
            "system_prompt": "AXIOM soul content",
            "active_persona": "AXIOM",
        }
        stripped = {k: v for k, v in data.items() if k not in AUDIT_EXCLUDED_FIELDS}
        assert "system_prompt" not in stripped
        assert "active_persona" not in stripped
        assert "some_field" in stripped
