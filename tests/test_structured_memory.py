import unittest
import json
from pathlib import Path
from src.models.memory import MemoryRule, MemoryRegistrySchema
from src.core.memory_registry import MemoryRegistry

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


if __name__ == "__main__":
    unittest.main()
