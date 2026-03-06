"""
src.skills.registry — Skill discovery and deterministic routing.

At startup, SkillRegistry scans src/skills/ for modules that expose:
  - SKILL_INTENT: str   — the intent name this skill handles
  - handle(state: dict) -> dict  — the handler function

route(intent, state) returns the handler result or None if no skill matches.
"""

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

_SKILLS_PACKAGE = "src.skills"
_SKILLS_DIR = Path(__file__).parent


class SkillRegistry:
    """Discovers and routes to skill handlers by intent."""

    def __init__(self):
        self._handlers: Dict[str, Callable] = {}

    @property
    def intents(self) -> list:
        return list(self._handlers.keys())

    def discover(self) -> None:
        """Scan src/skills/ for modules with SKILL_INTENT + handle()."""
        self._handlers.clear()
        for finder, name, _ in pkgutil.iter_modules([str(_SKILLS_DIR)]):
            if name in ("registry",):
                continue
            try:
                module = importlib.import_module(f"{_SKILLS_PACKAGE}.{name}")
                intent = getattr(module, "SKILL_INTENT", None)
                handler = getattr(module, "handle", None)
                if intent and callable(handler):
                    self._handlers[intent] = handler
                    logger.debug("Registered skill: %s → %s.handle", intent, name)
            except Exception as exc:
                logger.warning("Failed to load skill module %s: %s", name, exc)

        logger.info("SkillRegistry: discovered %d skill(s): %s", len(self._handlers), self.intents)

    def route(self, intent: str, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call the handler for intent, or return None if no skill matches."""
        handler = self._handlers.get(intent)
        if handler is None:
            return None
        logger.info("SkillRegistry: routing intent=%r to skill handler", intent)
        return handler(state)
