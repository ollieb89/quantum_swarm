"""
Unit tests for src.core.decision_card — DecisionCard model, builder, canonical JSON, verifier.
Drive implementation via TDD: RED → GREEN → REFACTOR.
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


class TestDecisionCardBuilder(unittest.TestCase):
    """Tests for build_decision_card() — field population from SwarmState."""

    def _make_state(self, **overrides) -> dict:
        """Return a minimal synthetic SwarmState dict."""
        base = {
            "task_id": "task-abc-123",
            "user_input": "Buy BTC",
            "intent": "trade",
            "messages": [],
            "macro_report": {"summary": "Bullish macro"},
            "quant_proposal": {"signal": "BUY", "confidence": 0.8},
            "bullish_thesis": {"argument": "Strong momentum"},
            "bearish_thesis": {"argument": "Overbought"},
            "debate_resolution": {"winner": "bullish", "margin": 0.6},
            "weighted_consensus_score": 0.75,
            "debate_history": [],
            "risk_approval": {"approved": True, "reasoning": "Within limits", "stop_loss": 42000.0},
            "consensus_score": 0.75,
            "compliance_flags": ["FLAG_A"],
            "risk_approved": True,
            "risk_notes": None,
            "final_decision": {"action": "BUY"},
            "metadata": {"trade_risk_score": 0.42},
            "blackboard_session": None,
            "total_tokens": 0,
            "trade_history": [],
            "execution_mode": "paper",
            "data_fetcher_result": None,
            "knowledge_base_result": None,
            "backtest_result": None,
            "execution_result": {
                "order_id": "ord-001",
                "execution_price": 43000.0,
                "success": True,
                "message": "Filled",
                "metadata": {},
            },
        }
        base.update(overrides)
        return base

    def test_all_required_fields_present(self):
        from src.core.decision_card import build_decision_card, DecisionCard

        state = self._make_state()
        card = build_decision_card(state)

        self.assertIsInstance(card, DecisionCard)
        self.assertTrue(card.card_id)
        self.assertEqual(card.schema_version, "1.0")
        self.assertEqual(card.event_type, "decision_card_created")
        self.assertEqual(card.task_id, "task-abc-123")
        self.assertIsInstance(card.generated_at, datetime)
        self.assertIsNotNone(card.execution_result)
        self.assertIsNotNone(card.agent_contributions)
        self.assertIsInstance(card.applied_rule_ids, list)
        self.assertIsNotNone(card.risk_snapshot)
        self.assertEqual(card.hash_algorithm, "sha256")
        self.assertTrue(card.content_hash)  # must be non-empty string after build

    def test_applied_rule_ids(self):
        from src.core.decision_card import build_decision_card

        mock_registry = MagicMock()
        rule_a = MagicMock()
        rule_a.id = "mem_0001"
        rule_b = MagicMock()
        rule_b.id = "mem_0003"
        mock_registry.get_active_rules.return_value = [rule_a, rule_b]

        state = self._make_state()
        card = build_decision_card(state, registry=mock_registry)

        self.assertEqual(card.applied_rule_ids, ["mem_0001", "mem_0003"])

    def test_risk_field_mapping(self):
        from src.core.decision_card import build_decision_card

        state = self._make_state(
            consensus_score=0.75,
            risk_approval={"approved": True},
            compliance_flags=["FLAG_A"],
            metadata={"trade_risk_score": 0.42},
        )
        card = build_decision_card(state)

        self.assertEqual(card.risk_snapshot.consensus_score, 0.75)
        self.assertEqual(card.risk_snapshot.risk_approval, {"approved": True})
        self.assertEqual(card.risk_snapshot.compliance_flags, ["FLAG_A"])
        self.assertEqual(card.risk_snapshot.portfolio_risk_score, 0.42)

    def test_portfolio_risk_score_absent(self):
        """state['metadata'] has no 'trade_risk_score' -> portfolio_risk_score is None."""
        from src.core.decision_card import build_decision_card

        state = self._make_state(metadata={})
        card = build_decision_card(state)

        self.assertIsNone(card.risk_snapshot.portfolio_risk_score)

    def test_portfolio_risk_score_not_top_level(self):
        """state has no 'metadata' key -> portfolio_risk_score is None, must not KeyError."""
        from src.core.decision_card import build_decision_card

        state = self._make_state()
        del state["metadata"]
        card = build_decision_card(state)

        self.assertIsNone(card.risk_snapshot.portfolio_risk_score)

    def test_agent_contributions_all_fields(self):
        from src.core.decision_card import build_decision_card

        state = self._make_state(
            macro_report={"summary": "Bearish macro"},
            quant_proposal={"signal": "SELL"},
            bullish_thesis={"arg": "Strong trend"},
            bearish_thesis={"arg": "Recession risk"},
            debate_resolution={"winner": "bearish"},
        )
        card = build_decision_card(state)

        ac = card.agent_contributions
        self.assertEqual(ac.macro_report, {"summary": "Bearish macro"})
        self.assertEqual(ac.quant_proposal, {"signal": "SELL"})
        self.assertEqual(ac.bullish_thesis, {"arg": "Strong trend"})
        self.assertEqual(ac.bearish_thesis, {"arg": "Recession risk"})
        self.assertEqual(ac.debate_resolution, {"winner": "bearish"})

    def test_agent_contributions_optional(self):
        """All agent fields None -> agent_contributions all None, no error."""
        from src.core.decision_card import build_decision_card

        state = self._make_state(
            macro_report=None,
            quant_proposal=None,
            bullish_thesis=None,
            bearish_thesis=None,
            debate_resolution=None,
        )
        card = build_decision_card(state)

        ac = card.agent_contributions
        self.assertIsNone(ac.macro_report)
        self.assertIsNone(ac.quant_proposal)
        self.assertIsNone(ac.bullish_thesis)
        self.assertIsNone(ac.bearish_thesis)
        self.assertIsNone(ac.debate_resolution)


class TestHashing(unittest.TestCase):
    """Tests for canonical_json(), verify_decision_card(), and hash integrity."""

    def _make_state(self, **overrides) -> dict:
        base = {
            "task_id": "task-hash-test",
            "user_input": "Buy ETH",
            "intent": "trade",
            "messages": [],
            "macro_report": None,
            "quant_proposal": None,
            "bullish_thesis": None,
            "bearish_thesis": None,
            "debate_resolution": None,
            "weighted_consensus_score": 0.6,
            "debate_history": [],
            "risk_approval": {"approved": True},
            "consensus_score": 0.6,
            "compliance_flags": [],
            "risk_approved": True,
            "risk_notes": None,
            "final_decision": None,
            "metadata": {"trade_risk_score": 0.3},
            "blackboard_session": None,
            "total_tokens": 0,
            "trade_history": [],
            "execution_mode": "paper",
            "data_fetcher_result": None,
            "knowledge_base_result": None,
            "backtest_result": None,
            "execution_result": {
                "order_id": "ord-002",
                "execution_price": 2800.0,
                "success": True,
                "message": "Filled",
                "metadata": {},
            },
        }
        base.update(overrides)
        return base

    def test_canonical_json_deterministic(self):
        from src.core.decision_card import canonical_json

        payload = {"b": 2, "a": 1, "c": [3, 1, 2]}
        result_1 = canonical_json(payload)
        result_2 = canonical_json(payload)

        self.assertEqual(result_1, result_2)

    def test_canonical_json_key_order_irrelevant(self):
        from src.core.decision_card import canonical_json

        dict_a = {"b": 2, "a": 1}
        dict_b = {"a": 1, "b": 2}

        self.assertEqual(canonical_json(dict_a), canonical_json(dict_b))

    def test_verify_freshly_built_card(self):
        from src.core.decision_card import build_decision_card, verify_decision_card

        state = self._make_state()
        card = build_decision_card(state)
        card_dict = card.model_dump(mode="json")

        self.assertTrue(verify_decision_card(card_dict))

    def test_verify_null_prev_hash(self):
        """Card with prev_audit_hash=None must pass verification."""
        from src.core.decision_card import build_decision_card, verify_decision_card

        state = self._make_state()
        card = build_decision_card(state, prev_audit_hash=None)

        self.assertIsNone(card.prev_audit_hash)
        card_dict = card.model_dump(mode="json")
        self.assertTrue(verify_decision_card(card_dict))

    def test_verify_tampered_card(self):
        """Mutating content_hash field -> verify returns False."""
        from src.core.decision_card import build_decision_card, verify_decision_card

        state = self._make_state()
        card = build_decision_card(state)
        card_dict = card.model_dump(mode="json")
        card_dict["content_hash"] = "deadbeef" * 8  # 64-char fake hash

        self.assertFalse(verify_decision_card(card_dict))

    def test_verify_tampered_field(self):
        """Changing task_id after hash computed -> verify returns False."""
        from src.core.decision_card import build_decision_card, verify_decision_card

        state = self._make_state()
        card = build_decision_card(state)
        card_dict = card.model_dump(mode="json")
        card_dict["task_id"] = "tampered-task-id"

        self.assertFalse(verify_decision_card(card_dict))

    def test_hash_excludes_content_hash_field(self):
        """The SHA-256 payload must NOT contain the 'content_hash' key."""
        from src.core.decision_card import build_decision_card, canonical_json, _compute_hash

        state = self._make_state()
        card = build_decision_card(state)
        card_dict = card.model_dump(mode="json")

        # Reconstruct payload the same way _compute_hash does
        payload = {k: v for k, v in card_dict.items() if k != "content_hash"}
        raw = canonical_json(payload)

        # The raw string must not contain the literal key "content_hash"
        self.assertNotIn('"content_hash"', raw)

        # And the recomputed hash must match
        import hashlib
        recomputed = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        self.assertEqual(recomputed, card_dict["content_hash"])


if __name__ == "__main__":
    unittest.main()
