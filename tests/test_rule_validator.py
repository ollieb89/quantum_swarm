"""
tests/test_rule_validator.py — TDD RED stubs for RuleValidator.

Wave 0: All tests fail (ImportError or NotImplementedError) until Plan 02
creates src/agents/rule_validator.py. This is intentional RED state.
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

# This import will fail (RED) until Plan 02 creates the module:
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
        raise NotImplementedError("RED: implement RuleValidator first")

    # ------------------------------------------------------------------
    # 2. Backtest call count
    # ------------------------------------------------------------------

    def test_two_backtest_calls_per_rule(self):
        """_run_nautilus_backtest is called exactly twice per proposed rule."""
        raise NotImplementedError("RED: implement RuleValidator first")

    # ------------------------------------------------------------------
    # 3. Promotion to active
    # ------------------------------------------------------------------

    def test_pass_promotes_to_active(self):
        """When 2+ metrics improve, rule status in registry becomes 'active'."""
        raise NotImplementedError("RED: implement RuleValidator first")

    # ------------------------------------------------------------------
    # 4. Rejection when metrics regress
    # ------------------------------------------------------------------

    def test_fail_rejects_rule(self):
        """When fewer than 2 metrics improve, rule status becomes 'rejected'."""
        raise NotImplementedError("RED: implement RuleValidator first")

    # ------------------------------------------------------------------
    # 5. Insufficient trade count guard
    # ------------------------------------------------------------------

    def test_insufficient_trades_skipped(self):
        """When baseline total_trades < validation_min_trades, rule stays 'proposed'."""
        raise NotImplementedError("RED: implement RuleValidator first")

    # ------------------------------------------------------------------
    # 6. Backtest error leaves rule in proposed
    # ------------------------------------------------------------------

    def test_backtest_error_leaves_proposed(self):
        """When _run_nautilus_backtest raises, rule stays 'proposed' and no exception propagates."""
        raise NotImplementedError("RED: implement RuleValidator first")

    # ------------------------------------------------------------------
    # 7. Audit event on promotion
    # ------------------------------------------------------------------

    def test_audit_event_on_promotion(self):
        """audit.jsonl contains a line with rule_id, before_status='proposed', after_status='active'."""
        raise NotImplementedError("RED: implement RuleValidator first")

    # ------------------------------------------------------------------
    # 8. Audit event on rejection
    # ------------------------------------------------------------------

    def test_audit_event_on_rejection(self):
        """audit.jsonl contains a line with rule_id, before_status='proposed', after_status='rejected'."""
        raise NotImplementedError("RED: implement RuleValidator first")

    # ------------------------------------------------------------------
    # 9. Evidence written to rule
    # ------------------------------------------------------------------

    def test_evidence_written_to_rule(self):
        """After validation, rule.evidence contains all six required keys."""
        # Expected keys: baseline_sharpe, treatment_sharpe, baseline_drawdown,
        # treatment_drawdown, baseline_win_rate, treatment_win_rate
        raise NotImplementedError("RED: implement RuleValidator first")


class TestRuleValidatorIntegration(unittest.TestCase):
    """
    Integration tests for RuleValidator.

    setUp creates isolated temp registry + audit files and a proposed rule,
    then wires the validator to them.
    """

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.test_registry_file = Path(self.tmp_dir) / "registry.json"
        self.test_audit_file = Path(self.tmp_dir) / "audit.jsonl"

        # Seed registry with one proposed rule
        self.registry = MemoryRegistry(str(self.test_registry_file))
        self.rule = _make_proposed_rule(rule_id="mem_integ0001")
        self.registry.add_rule(self.rule)

        # Create validator with redirected file paths
        self.validator = RuleValidator()
        self.validator.registry = MemoryRegistry(str(self.test_registry_file))
        self.validator.audit_path = Path(str(self.test_audit_file))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # 10. Persist then validate
    # ------------------------------------------------------------------

    def test_persist_then_validate(self):
        """
        After RuleGenerator.persist_rules([rule]) and validator.validate_proposed_rules(),
        the rule is active or rejected in registry (not proposed).
        """
        raise NotImplementedError("RED: implement RuleValidator first")

    # ------------------------------------------------------------------
    # 11. Full audit trail
    # ------------------------------------------------------------------

    def test_full_audit_trail(self):
        """
        After validate_proposed_rules(), audit.jsonl contains one event line
        with all required fields: rule_id, before_status, after_status,
        baseline_sharpe, treatment_sharpe, sharpe_delta.
        """
        raise NotImplementedError("RED: implement RuleValidator first")


if __name__ == "__main__":
    unittest.main()
