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

if __name__ == "__main__":
    unittest.main()
