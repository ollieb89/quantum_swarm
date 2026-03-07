"""
src.agents.rule_generator — Generates institutional rules from performance reviews.

Processes drift reports and appends PREFER/AVOID/CAUTION rules to MEMORY.md.
"""

import logging
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from src.core.memory_registry import MemoryRegistry
from src.models.memory import MemoryRule

logger = logging.getLogger(__name__)

_MODEL_ID = "gemini-2.0-flash"

# Lazy LLM singleton — instantiation requires GOOGLE_API_KEY at runtime, not import
_llm = None

def _get_llm() -> ChatGoogleGenerativeAI:
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(model=_MODEL_ID)
    return _llm


class RuleGenerator:
    """Agent responsible for translating performance findings into actionable rules."""

    def __init__(self):
        # LLM is resolved lazily — not at import time — so modules can be imported
        # in test environments without a live GOOGLE_API_KEY.
        self._llm: Optional[ChatGoogleGenerativeAI] = None
        self.registry = MemoryRegistry()
        self.memory_md_path = Path("data/MEMORY.md")

    @property
    def llm(self) -> ChatGoogleGenerativeAI:
        if self._llm is None:
            self._llm = _get_llm()
        return self._llm

    @llm.setter
    def llm(self, value: ChatGoogleGenerativeAI):
        self._llm = value

    async def generate_rules(self, drift_report: Dict[str, Any]) -> List[MemoryRule]:
        """Convert a drift report into a list of structured MemoryRules."""
        if not drift_report or drift_report.get("status") == "no_data":
            return []

        prompt = (
            "You are the RuleGenerator for Quantum Swarm. "
            "Based on the following Performance Drift Report, generate institutional knowledge rules. "
            "Output strictly a JSON list of rule objects. "
            "Each object must match this schema: "
            "{'title': str, 'type': 'risk_adjustment'|'strategy_preference'|'market_regime', "
            "'condition': dict, 'action': dict, 'evidence': dict}. "
            "Do NOT include 'id', 'status', or timestamps (system handles those). "
            f"\n\nDrift Report:\n{json.dumps(drift_report, indent=2)}"
        )

        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        
        rules = []
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            
            data = json.loads(content)
            if isinstance(data, list):
                for item in data:
                    try:
                        rule = MemoryRule(**item)
                        rules.append(rule)
                    except Exception as e:
                        logger.warning("Skipping malformed rule: %s", e)
        except Exception as e:
            logger.error("Failed to parse rule generation output: %s", e)
                
        return rules

    def _rule_to_prefix(self, rule: MemoryRule) -> str:
        """Map a MemoryRule to a PREFER/AVOID/CAUTION prefix for MEMORY.md."""
        action_vals = " ".join(str(v) for v in rule.action.values()).lower()
        if any(kw in action_vals for kw in ("avoid", "reduce", "short_only")):
            return "AVOID"
        if rule.type == "strategy_preference":
            return "PREFER"
        if rule.type == "risk_adjustment":
            return "AVOID"
        return "CAUTION"

    def persist_rules(self, rules: List[MemoryRule]):
        """Append new rules to the JSON registry and to data/MEMORY.md."""
        if not rules:
            return
        for rule in rules:
            self.registry.add_rule(rule)
        # Append human-readable entries to MEMORY.md for orchestrator injection
        self.memory_md_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        lines = [f"\n<!-- pipeline:{timestamp} -->"]
        for rule in rules:
            prefix = self._rule_to_prefix(rule)
            lines.append(f"- {prefix}: {rule.title}")
        with open(self.memory_md_path, "a") as f:
            f.write("\n".join(lines) + "\n")
        logger.info("Appended %d rules to %s", len(rules), self.memory_md_path)
