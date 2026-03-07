"""
tests/test_rule_validator.py — Unit and integration tests for RuleValidator.
"""

import asyncio
import json
import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.memory_registry import MemoryRegistry
from src.models.memory import MemoryRule

from src.agents.rule_validator import RuleValidator


# ---------------------------------------------------------------------------
# Shared mock backtest result helpers
# ---------------------------------------------------------------------------

_BASELINE_RESULT = {
    "sharpe_ratio": 1.0,
    "total_return": 0.05,
    "max_drawdown": -0.10,
    "total_trades": 15,
    "win_rate": 0.50,
    "period_days": 90,
}

_TREATMENT_IMPROVED = {
    "sharpe_ratio": 1.5,
    "total_return": 0.12,
    "max_drawdown": -0.05,
    "total_trades": 15,
    "win_rate": 0.60,
    "period_days": 90,
}

_TREATMENT_WORSE = {
    "sharpe_ratio": 0.8,
    "total_return": 0.03,
    "max_drawdown": -0.15,
    "total_trades": 15,
    "win_rate": 0.42,
    "period_days": 90,
}


def _make_proposed_rule(rule_id: str = "mem_test0001") -> MemoryRule:
    return MemoryRule(
        id=rule_id,
        title="Avoid trading in high-VIX regimes",
        type="risk_adjustment",
        condition={"vix": ">30"},
        action={"reduce_position_size": 0.5},
        evidence={},
        status="proposed",
    )


class TestRuleValidator(unittest.TestCase):
    """
    Unit tests for RuleValidator behaviour.

    setUp creates isolated temp registry + audit files and wires the
    validator to them (same isolation pattern as TestRuleGeneratorIntegration).
    """

    def setUp(self):
        # Temp registry file with one proposed rule
        self.tmp_dir = tempfile.mkdtemp()
        self.test_registry_file = Path(self.tmp_dir) / "registry.json"
        self.test_audit_file = Path(self.tmp_dir) / "audit.jsonl"

        # Seed registry with one proposed rule
        self.registry = MemoryRegistry(str(self.test_registry_file))
        self.rule = _make_proposed_rule()
        self.registry.add_rule(self.rule)

        # Create validator with redirected file paths
        self.validator = RuleValidator()
        self.validator.registry = MemoryRegistry(str(self.test_registry_file))
        self.validator.audit_path = Path(str(self.test_audit_file))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # 1. Fetching proposed rules
    # ------------------------------------------------------------------

    def test_fetches_proposed_rules(self):
        """validate_proposed_rules() returns a count matching proposed rules."""
        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=[_BASELINE_RESULT, _TREATMENT_IMPROVED],
        ):
            count = self.validator.validate_proposed_rules()
        self.assertEqual(count, 1)

    # ------------------------------------------------------------------
    # 2. Backtest call count
    # ------------------------------------------------------------------

    def test_two_backtest_calls_per_rule(self):
        """_run_nautilus_backtest is called exactly twice per proposed rule."""
        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=[_BASELINE_RESULT, _TREATMENT_IMPROVED],
        ) as mock_bt:
            self.validator.validate_proposed_rules()
        self.assertEqual(mock_bt.call_count, 2)

    # ------------------------------------------------------------------
    # 3. Promotion to active
    # ------------------------------------------------------------------

    def test_pass_promotes_to_active(self):
        """When 2+ metrics improve, rule status in registry becomes 'active'."""
        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=[_BASELINE_RESULT, _TREATMENT_IMPROVED],
        ):
            self.validator.validate_proposed_rules()

        updated = self.validator.registry.get_rule(self.rule.id)
        self.assertEqual(updated.status, "active")

    # ------------------------------------------------------------------
    # 4. Rejection when metrics regress
    # ------------------------------------------------------------------

    def test_fail_rejects_rule(self):
        """When fewer than 2 metrics improve, rule status becomes 'rejected'."""
        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=[_BASELINE_RESULT, _TREATMENT_WORSE],
        ):
            self.validator.validate_proposed_rules()

        updated = self.validator.registry.get_rule(self.rule.id)
        self.assertEqual(updated.status, "rejected")

    # ------------------------------------------------------------------
    # 5. Insufficient trade count guard
    # ------------------------------------------------------------------

    def test_insufficient_trades_skipped(self):
        """When baseline total_trades < validation_min_trades, rule stays 'proposed'."""
        low_trade_baseline = dict(_BASELINE_RESULT, total_trades=2)
        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=[low_trade_baseline, _TREATMENT_IMPROVED],
        ):
            count = self.validator.validate_proposed_rules()

        # Rule should stay proposed, processed count = 0 (skipped)
        self.assertEqual(count, 0)
        rule = self.validator.registry.get_rule(self.rule.id)
        self.assertEqual(rule.status, "proposed")

    # ------------------------------------------------------------------
    # 6. Backtest error leaves rule in proposed
    # ------------------------------------------------------------------

    def test_backtest_error_leaves_proposed(self):
        """When _run_nautilus_backtest raises, rule stays 'proposed' and no exception propagates."""
        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=RuntimeError("yfinance unavailable"),
        ):
            # Should not raise
            count = self.validator.validate_proposed_rules()

        self.assertEqual(count, 0)
        rule = self.validator.registry.get_rule(self.rule.id)
        self.assertEqual(rule.status, "proposed")

    # ------------------------------------------------------------------
    # 7. Audit event on promotion
    # ------------------------------------------------------------------

    def test_audit_event_on_promotion(self):
        """audit.jsonl contains a line with rule_id, before_status='proposed', after_status='active'."""
        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=[_BASELINE_RESULT, _TREATMENT_IMPROVED],
        ):
            self.validator.validate_proposed_rules()

        self.assertTrue(self.test_audit_file.exists())
        lines = self.test_audit_file.read_text().strip().splitlines()
        self.assertEqual(len(lines), 1)
        event = json.loads(lines[0])
        self.assertEqual(event["rule_id"], self.rule.id)
        self.assertEqual(event["before_status"], "proposed")
        self.assertEqual(event["after_status"], "active")

    # ------------------------------------------------------------------
    # 8. Audit event on rejection
    # ------------------------------------------------------------------

    def test_audit_event_on_rejection(self):
        """audit.jsonl contains a line with rule_id, before_status='proposed', after_status='rejected'."""
        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=[_BASELINE_RESULT, _TREATMENT_WORSE],
        ):
            self.validator.validate_proposed_rules()

        self.assertTrue(self.test_audit_file.exists())
        lines = self.test_audit_file.read_text().strip().splitlines()
        self.assertEqual(len(lines), 1)
        event = json.loads(lines[0])
        self.assertEqual(event["rule_id"], self.rule.id)
        self.assertEqual(event["before_status"], "proposed")
        self.assertEqual(event["after_status"], "rejected")

    # ------------------------------------------------------------------
    # 9. Evidence written to rule
    # ------------------------------------------------------------------

    def test_evidence_written_to_rule(self):
        """After validation, rule.evidence contains all six required keys."""
        # Expected keys: baseline_sharpe, treatment_sharpe, baseline_drawdown,
        # treatment_drawdown, baseline_win_rate, treatment_win_rate
        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=[_BASELINE_RESULT, _TREATMENT_IMPROVED],
        ):
            self.validator.validate_proposed_rules()

        rule = self.validator.registry.get_rule(self.rule.id)
        required_keys = {
            "baseline_sharpe", "treatment_sharpe",
            "baseline_drawdown", "treatment_drawdown",
            "baseline_win_rate", "treatment_win_rate",
        }
        self.assertTrue(required_keys.issubset(set(rule.evidence.keys())))


class TestRuleValidatorIntegration(unittest.TestCase):
    """
    Integration tests verifying the full persist_rules() -> validate_proposed_rules() chain.

    RuleGenerator.persist_rules() is called with a proposed rule; we assert that
    validation fires automatically (no manual call needed) and that the rule
    transitions out of 'proposed' state.
    """

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.test_registry_file = Path(self.tmp_dir) / "registry.json"
        self.test_audit_file = Path(self.tmp_dir) / "audit.jsonl"
        self.test_memory_md = Path(self.tmp_dir) / "MEMORY.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # 10. Persist then validate (auto-wiring)
    # ------------------------------------------------------------------

    def test_persist_then_validate(self):
        """
        After rg.persist_rules([rule]), validation fires automatically.
        No rule should remain in 'proposed' state.
        """
        from src.agents.rule_generator import RuleGenerator
        from src.agents.rule_validator import RuleValidator

        rule = MemoryRule(title="Integration Test Rule", type="general")

        rg = RuleGenerator()
        rg.registry = MemoryRegistry(str(self.test_registry_file))
        rg.memory_md_path = self.test_memory_md

        original_init = RuleValidator.__init__

        def patched_init(self_v, **kwargs):
            original_init(self_v)
            self_v.audit_path = self.test_audit_file

        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=[_BASELINE_RESULT, _TREATMENT_IMPROVED],
        ):
            with patch.object(RuleValidator, "__init__", patched_init):
                rg.persist_rules([rule])

        # Rule must no longer be proposed after persist_rules() fires validator
        fresh_reg = MemoryRegistry(str(self.test_registry_file))
        proposed = fresh_reg.get_proposed_rules()
        self.assertEqual(len(proposed), 0, "No rule should remain proposed after persist_rules()")

    # ------------------------------------------------------------------
    # 11. Full audit trail (auto-wiring)
    # ------------------------------------------------------------------

    def test_full_audit_trail(self):
        """
        After persist_rules(), audit.jsonl contains one event line with all
        required fields: rule_id, before_status, after_status, baseline_sharpe,
        treatment_sharpe, sharpe_delta.
        """
        from src.agents.rule_generator import RuleGenerator
        from src.agents.rule_validator import RuleValidator

        rule = MemoryRule(title="Audit Trail Test Rule", type="general")

        rg = RuleGenerator()
        rg.registry = MemoryRegistry(str(self.test_registry_file))
        rg.memory_md_path = self.test_memory_md

        original_init = RuleValidator.__init__

        def patched_init(self_v, **kwargs):
            original_init(self_v)
            self_v.audit_path = self.test_audit_file

        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=[_BASELINE_RESULT, _TREATMENT_IMPROVED],
        ):
            with patch.object(RuleValidator, "__init__", patched_init):
                rg.persist_rules([rule])

        self.assertTrue(self.test_audit_file.exists(), "audit.jsonl must be created")
        lines = self.test_audit_file.read_text().strip().splitlines()
        self.assertEqual(len(lines), 1)
        event = json.loads(lines[0])

        required_fields = {
            "rule_id", "before_status", "after_status",
            "baseline_sharpe", "treatment_sharpe", "sharpe_delta",
        }
        for field in required_fields:
            self.assertIn(field, event, f"Missing field: {field}")
        self.assertEqual(event["before_status"], "proposed")
        self.assertIn(event["after_status"], ("active", "rejected"))


if __name__ == "__main__":
    unittest.main()
