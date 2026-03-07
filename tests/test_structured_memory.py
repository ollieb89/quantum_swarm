import unittest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.models.memory import MemoryRule, MemoryRegistrySchema
from src.core.memory_registry import MemoryRegistry
from src.agents.rule_generator import RuleGenerator

class TestStructuredMemory(unittest.TestCase):

    def setUp(self):
        # Use a temp file for testing
        self.test_file = Path("tests/temp_memory.json")
        if self.test_file.exists():
            self.test_file.unlink()
        self.registry = MemoryRegistry(str(self.test_file))

    def tearDown(self):
        if self.test_file.exists():
            self.test_file.unlink()
        # Clean up any leftover .tmp files
        tmp_file = Path(str(self.test_file) + ".tmp")
        if tmp_file.exists():
            tmp_file.unlink()

    def test_memory_rule_model(self):
        rule = MemoryRule(
            title="Test Rule",
            type="risk_adjustment",
            condition={"vix": ">20"},
            action={"reduce_leverage": True}
        )
        self.assertEqual(rule.status, "proposed")
        self.assertTrue(rule.id.startswith("mem_"))
        self.assertEqual(rule.version, 1)

    def test_registry_persistence(self):
        rule = MemoryRule(title="Persist Me", type="general")
        self.registry.add_rule(rule)

        # Reload
        new_registry = MemoryRegistry(str(self.test_file))
        self.assertEqual(len(new_registry.schema.rules), 1)
        self.assertEqual(new_registry.schema.rules[0].title, "Persist Me")

    def test_active_rule_filtering(self):
        r1 = MemoryRule(title="Active Rule", type="general", status="active")
        r2 = MemoryRule(title="Proposed Rule", type="general", status="proposed")
        r3 = MemoryRule(title="Rejected Rule", type="general", status="rejected")

        self.registry.add_rule(r1)
        self.registry.add_rule(r2)
        self.registry.add_rule(r3)

        active = self.registry.get_active_rules()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].title, "Active Rule")

    def test_malformed_rule_rejection(self):
        with self.assertRaises(Exception):
            MemoryRule(title="Bad Type", type="invalid_type")

    # --- Lifecycle transition tests ---

    def test_update_status_valid(self):
        """proposed -> active succeeds; version increments to 2."""
        rule = MemoryRule(title="Proposed Rule", type="general", status="proposed")
        self.registry.add_rule(rule)
        self.registry.update_status(rule.id, "active")
        updated = self.registry.get_rule(rule.id)
        self.assertEqual(updated.status, "active")
        self.assertEqual(updated.version, 2)

    def test_update_status_terminal(self):
        """active -> deprecated succeeds; deprecated -> active raises ValueError."""
        rule = MemoryRule(title="Active Rule", type="general", status="active")
        self.registry.add_rule(rule)
        self.registry.update_status(rule.id, "deprecated")
        updated = self.registry.get_rule(rule.id)
        self.assertEqual(updated.status, "deprecated")
        with self.assertRaises(ValueError):
            self.registry.update_status(rule.id, "active")

    def test_update_status_not_found(self):
        """update_status on nonexistent id raises ValueError."""
        with self.assertRaises(ValueError):
            self.registry.update_status("mem_nonexistent", "active")

    def test_update_status_invalid_reverse(self):
        """proposed -> proposed raises ValueError (not in VALID_TRANSITIONS)."""
        rule = MemoryRule(title="Proposed Rule", type="general", status="proposed")
        self.registry.add_rule(rule)
        with self.assertRaises(ValueError):
            self.registry.update_status(rule.id, "proposed")

    def test_atomic_save(self):
        """After add_rule(), no .tmp file should persist (atomic rename completed)."""
        rule = MemoryRule(title="Atomic Rule", type="general")
        self.registry.add_rule(rule)
        tmp_file = Path(str(self.test_file) + ".tmp")
        self.assertFalse(tmp_file.exists())

    def test_transition_logged(self):
        """update_status() emits an INFO log message containing the rule ID."""
        rule = MemoryRule(title="Log Test Rule", type="general", status="proposed")
        self.registry.add_rule(rule)
        with self.assertLogs("src.core.memory_registry", level="INFO") as cm:
            self.registry.update_status(rule.id, "active")
        log_output = "\n".join(cm.output)
        self.assertIn(rule.id, log_output)


class TestRuleGeneratorIntegration(unittest.TestCase):
    """Integration tests: RuleGenerator.persist_rules() stores proposed rules in registry."""

    def setUp(self):
        self.test_registry_file = Path("tests/temp_integration_registry.json")
        self.test_memory_md = Path("tests/temp_MEMORY.md")
        if self.test_registry_file.exists():
            self.test_registry_file.unlink()
        if self.test_memory_md.exists():
            self.test_memory_md.unlink()

    def tearDown(self):
        if self.test_registry_file.exists():
            self.test_registry_file.unlink()
        if self.test_memory_md.exists():
            self.test_memory_md.unlink()

    def test_persist_rules_stores_proposed(self):
        """persist_rules() writes rule as proposed; not returned by get_active_rules()."""
        rg = RuleGenerator()
        rg.registry = MemoryRegistry(str(self.test_registry_file))
        rg.memory_md_path = self.test_memory_md
        rule = MemoryRule(title="Integration Rule", type="risk_adjustment")
        rg.persist_rules([rule])
        # Assert rule in registry
        reloaded = MemoryRegistry(str(self.test_registry_file))
        self.assertEqual(len(reloaded.schema.rules), 1)
        self.assertEqual(reloaded.schema.rules[0].status, "proposed")
        # Assert NOT in active rules
        self.assertEqual(len(reloaded.get_active_rules()), 0)
        # Assert MEMORY.md was written
        self.assertTrue(self.test_memory_md.exists())

    def test_promote_rule_appears_in_active(self):
        """After update_status(active), rule is returned by get_active_rules()."""
        rg = RuleGenerator()
        rg.registry = MemoryRegistry(str(self.test_registry_file))
        rg.memory_md_path = self.test_memory_md
        rule = MemoryRule(title="Promotable Rule", type="strategy_preference")
        rg.persist_rules([rule])
        # Now promote
        reloaded = MemoryRegistry(str(self.test_registry_file))
        stored_rule = reloaded.schema.rules[0]
        reloaded.update_status(stored_rule.id, "active")
        # Assert now active
        active = reloaded.get_active_rules()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].title, "Promotable Rule")


class TestOrchestratorMemoryInjection(unittest.TestCase):
    """Integration tests: _load_institutional_memory() injects only active rules."""

    def setUp(self):
        self.test_registry_file = Path("tests/temp_orch_registry.json")
        if self.test_registry_file.exists():
            self.test_registry_file.unlink()

    def tearDown(self):
        if self.test_registry_file.exists():
            self.test_registry_file.unlink()

    def test_empty_registry_returns_fallback_message(self):
        """Empty registry with no MEMORY.md returns fallback string."""
        from src.graph.orchestrator import LangGraphOrchestrator
        orch = LangGraphOrchestrator.__new__(LangGraphOrchestrator)
        orch._yaml_config = {}
        with patch("src.graph.orchestrator.MemoryRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_active_rules.return_value = []
            mock_reg_cls.return_value = mock_reg
            with patch("src.graph.orchestrator.Path") as mock_path_cls:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = False
                mock_path_cls.return_value = mock_path_instance
                result = orch._load_institutional_memory()
        self.assertEqual(result, "No active institutional rules.")

    def test_active_rule_appears_in_injection(self):
        """Active rule title and id appear in the injection string."""
        from src.graph.orchestrator import LangGraphOrchestrator
        active_rule = MemoryRule(title="Buy on breakout", type="strategy_preference", status="active")
        with patch("src.graph.orchestrator.MemoryRegistry") as mock_reg_cls:
            mock_reg = MagicMock()
            mock_reg.get_active_rules.return_value = [active_rule]
            mock_reg_cls.return_value = mock_reg
            with patch("src.graph.orchestrator.Path") as mock_path_cls:
                mock_path_instance = MagicMock()
                mock_path_instance.exists.return_value = False
                mock_path_cls.return_value = mock_path_instance
                orch = LangGraphOrchestrator.__new__(LangGraphOrchestrator)
                orch._yaml_config = {}
                result = orch._load_institutional_memory()
        self.assertIn("Buy on breakout", result)
        self.assertIn(active_rule.id, result)


if __name__ == "__main__":
    unittest.main()
