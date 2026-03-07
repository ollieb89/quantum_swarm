"""
src.core.memory_registry — Persistence and logic for structured memory rules.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from src.models.memory import MemoryRule, MemoryRegistrySchema

logger = logging.getLogger(__name__)

class MemoryRegistry:
    """
    Manages the lifecycle and persistence of institutional memory rules.
    """

    def __init__(self, file_path: str = "data/memory_registry.json"):
        self.file_path = Path(file_path)
        self.schema = self._load()

    def _load(self) -> MemoryRegistrySchema:
        """Load registry from JSON or initialize empty."""
        if not self.file_path.exists():
            return MemoryRegistrySchema(rules=[])
        
        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)
            return MemoryRegistrySchema(**data)
        except Exception as e:
            logger.error("Failed to load memory registry from %s: %s", self.file_path, e)
            return MemoryRegistrySchema(rules=[])

    def save(self):
        """Persist registry to JSON."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w") as f:
                f.write(self.schema.model_dump_json(indent=2))
        except Exception as e:
            logger.error("Failed to save memory registry to %s: %s", self.file_path, e)

    def add_rule(self, rule: MemoryRule):
        """Add a new rule (defaulting to proposed)."""
        self.schema.rules.append(rule)
        self.save()
        logger.info("Added new memory rule: %s (%s)", rule.title, rule.status)

    def get_active_rules(self) -> List[MemoryRule]:
        """Return only active rules for agent injection."""
        return [r for r in self.schema.rules if r.status == "active"]

    def get_rule(self, rule_id: str) -> Optional[MemoryRule]:
        """Find a rule by ID."""
        for r in self.schema.rules:
            if r.id == rule_id:
                return r
        return None
