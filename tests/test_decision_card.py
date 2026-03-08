"""
Unit tests for src.core.decision_card — DecisionCard model, builder, canonical JSON, verifier.
Also: Integration tests for decision_card_writer node in src.graph.orchestrator.
Drive implementation via TDD: RED → GREEN → REFACTOR.
"""

import asyncio
import json
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch
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


def _make_ccxt_stub():
    """Stub the broken ccxt package so orchestrator imports succeed."""
    if "ccxt" not in sys.modules:
        ccxt_stub = MagicMock()
        sys.modules["ccxt"] = ccxt_stub
        sys.modules["ccxt.async_support"] = ccxt_stub


class TestDecisionCardWriter(unittest.TestCase):
    """Integration tests for the decision_card_writer_node in src.graph.orchestrator."""

    @classmethod
    def setUpClass(cls):
        _make_ccxt_stub()

    def _make_state(self, **overrides) -> dict:
        """Return a minimal synthetic SwarmState dict for writer tests."""
        base = {
            "task_id": "test-task-001",
            "user_input": "Buy BTC",
            "intent": "trade",
            "messages": [],
            "macro_report": None,
            "quant_proposal": None,
            "bullish_thesis": None,
            "bearish_thesis": None,
            "debate_resolution": None,
            "weighted_consensus_score": 0.8,
            "debate_history": [],
            "risk_approval": {"approved": True, "reasoning": "ok", "stop_loss_level": 95.0},
            "consensus_score": 0.8,
            "compliance_flags": [],
            "risk_approved": True,
            "risk_notes": None,
            "final_decision": None,
            "metadata": {"trade_risk_score": 0.35},
            "blackboard_session": None,
            "total_tokens": 0,
            "trade_history": [],
            "execution_mode": "paper",
            "data_fetcher_result": None,
            "knowledge_base_result": None,
            "backtest_result": None,
            "execution_result": {
                "order_id": "ORD-1",
                "execution_price": 100.0,
                "success": True,
                "message": "filled",
                "metadata": {},
            },
            "decision_card_status": None,
            "decision_card_error": None,
            "decision_card_audit_ref": None,
        }
        base.update(overrides)
        return base

    def _make_pool_mock(self):
        """Return an AsyncMock pool that simulates no prior DB rows."""
        mock_cur = AsyncMock()
        mock_cur.fetchone = AsyncMock(return_value=None)
        mock_cur.__aenter__ = AsyncMock(return_value=mock_cur)
        mock_cur.__aexit__ = AsyncMock(return_value=False)

        mock_conn = AsyncMock()
        mock_conn.cursor = MagicMock(return_value=mock_cur)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)

        mock_pool = MagicMock()
        mock_pool.connection = MagicMock(return_value=mock_conn)

        return mock_pool

    def _make_registry_mock(self):
        """Return a MagicMock MemoryRegistry with no active rules."""
        mock_registry = MagicMock()
        mock_registry.get_active_rules.return_value = []
        return mock_registry

    # ------------------------------------------------------------------
    # Routing tests (synchronous — no async needed)
    # ------------------------------------------------------------------

    def test_route_after_order_router_success(self):
        """State with execution_result.success=True -> route to 'decision_card_writer'."""
        from src.graph.orchestrator import route_after_order_router

        state = self._make_state(execution_result={"success": True})
        self.assertEqual(route_after_order_router(state), "decision_card_writer")

    def test_route_after_order_router_failure(self):
        """State with execution_result.success=False -> route to 'trade_logger'."""
        from src.graph.orchestrator import route_after_order_router

        state = self._make_state(execution_result={"success": False})
        self.assertEqual(route_after_order_router(state), "trade_logger")

    def test_route_after_order_router_none(self):
        """State with execution_result=None -> route to 'trade_logger'."""
        from src.graph.orchestrator import route_after_order_router

        state = self._make_state(execution_result=None)
        self.assertEqual(route_after_order_router(state), "trade_logger")

    # ------------------------------------------------------------------
    # Node tests (async via asyncio.run)
    # ------------------------------------------------------------------

    def test_card_appended_to_audit_jsonl(self):
        """Successful trade -> audit.jsonl contains one valid decision card line."""
        from src.graph.orchestrator import decision_card_writer_node
        from src.core.decision_card import verify_decision_card

        state = self._make_state()
        captured_lines = []

        # Capture writes via mock_open; then read back what was "written"
        m = mock_open()

        def patched_open(path, mode="r", *args, **kwargs):
            if mode == "a":
                return m(path, mode, *args, **kwargs)
            return open(path, mode, *args, **kwargs)

        with patch("src.graph.orchestrator.get_pool", return_value=self._make_pool_mock()), \
             patch("src.graph.orchestrator.MemoryRegistry", return_value=self._make_registry_mock()), \
             patch("builtins.open", side_effect=patched_open):

            result = asyncio.run(decision_card_writer_node(state))

        self.assertEqual(result["decision_card_status"], "written")
        self.assertIsNotNone(result["decision_card_audit_ref"])
        self.assertIsNone(result["decision_card_error"])

        # Check that write() was called with valid JSON + newline
        write_calls = m().write.call_args_list
        self.assertTrue(len(write_calls) >= 1, "Expected at least one write() call")
        written_data = "".join(call.args[0] for call in write_calls)
        line = written_data.strip()
        card_dict = json.loads(line)
        self.assertEqual(card_dict["event_type"], "decision_card_created")
        self.assertTrue(verify_decision_card(card_dict))

    def test_card_not_written_for_failed_trade(self):
        """Route function directs failed trades away from writer -> no card created."""
        from src.graph.orchestrator import route_after_order_router

        state = self._make_state(execution_result={"success": False, "order_id": "ORD-2"})
        route = route_after_order_router(state)
        self.assertEqual(route, "trade_logger")
        # The node is never called for failed trades (verified by routing alone)

    def test_retry_behavior(self):
        """First open() raises OSError; second succeeds -> status='written'."""
        from src.graph.orchestrator import decision_card_writer_node

        state = self._make_state()
        call_count = {"n": 0}
        m = mock_open()

        def side_effect_open(path, mode="r", *args, **kwargs):
            if mode == "a":
                call_count["n"] += 1
                if call_count["n"] == 1:
                    raise OSError("disk full")
                return m(path, mode, *args, **kwargs)
            return open(path, mode, *args, **kwargs)

        with patch("src.graph.orchestrator.get_pool", return_value=self._make_pool_mock()), \
             patch("src.graph.orchestrator.MemoryRegistry", return_value=self._make_registry_mock()), \
             patch("builtins.open", side_effect=side_effect_open):

            result = asyncio.run(decision_card_writer_node(state))

        self.assertEqual(result["decision_card_status"], "written")
        self.assertIsNotNone(result["decision_card_audit_ref"])
        self.assertEqual(call_count["n"], 2, "Expected exactly 2 open() attempts for append")

    def test_double_failure_sets_failed_status(self):
        """Both open() attempts raise OSError -> status='failed', audit_ref is None."""
        from src.graph.orchestrator import decision_card_writer_node

        state = self._make_state()

        def always_fail(path, mode="r", *args, **kwargs):
            if mode == "a":
                raise OSError("disk full every time")
            return open(path, mode, *args, **kwargs)

        with patch("src.graph.orchestrator.get_pool", return_value=self._make_pool_mock()), \
             patch("src.graph.orchestrator.MemoryRegistry", return_value=self._make_registry_mock()), \
             patch("builtins.open", side_effect=always_fail):

            result = asyncio.run(decision_card_writer_node(state))

        self.assertEqual(result["decision_card_status"], "failed")
        self.assertIsNone(result["decision_card_audit_ref"])
        self.assertIn("disk full", result["decision_card_error"])


if __name__ == "__main__":
    unittest.main()
