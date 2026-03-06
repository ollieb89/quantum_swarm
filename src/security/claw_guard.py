"""
src.security.claw_guard — ClawGuard security rule engine.

Intercepts agent outputs before execution to enforce hard safety rules.
Rules are config-driven and can be audited without code changes.
"""

import re
import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# Credential detection patterns (regex)
_CREDENTIAL_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),           # OpenAI / Anthropic API keys
    re.compile(r"AIza[A-Za-z0-9_\-]{35}"),          # Google API keys
    re.compile(r"(?i)password\s*[=:]\s*\S+"),        # password=... or password: ...
    re.compile(r"(?i)api[_\-]?key\s*[=:]\s*\S+"),   # api_key=... variants
    re.compile(r"(?i)secret\s*[=:]\s*\S+"),          # secret=...
    re.compile(r"(?i)token\s*[=:]\s*[A-Za-z0-9_\-\.]{16,}"),  # token=<long value>
]


class ClawGuard:
    """Rule engine that validates SwarmState before order execution.

    Rules applied (in order):
      1. require_risk_approval
      2. require_consensus_threshold
      3. no_credential_in_messages
      4. paper_trade_only
    """

    def __init__(self, config: Dict[str, Any]):
        sec = config.get("security", {})
        self._min_consensus: float = sec.get("min_consensus", 0.75)
        self._paper_only: bool = sec.get("paper_trade_only", True)

    def check(self, state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Run all rules against state.

        Returns:
            (approved, violations) — approved is False if any rule fires.
        """
        violations: List[str] = []

        self._require_risk_approval(state, violations)
        self._require_consensus_threshold(state, violations)
        self._no_credential_in_messages(state, violations)
        self._paper_trade_only(state, violations)

        approved = len(violations) == 0
        if not approved:
            logger.warning("ClawGuard blocked execution: %s", violations)
        return approved, violations

    # --- Rules ---

    def _require_risk_approval(self, state: dict, violations: list) -> None:
        if state.get("risk_approved") is not True:
            violations.append(
                f"require_risk_approval: risk_approved={state.get('risk_approved')!r} — must be True"
            )

    def _require_consensus_threshold(self, state: dict, violations: list) -> None:
        score = state.get("weighted_consensus_score")
        if score is None:
            violations.append(
                "require_consensus_threshold: weighted_consensus_score is None"
            )
        elif score < self._min_consensus:
            violations.append(
                f"require_consensus_threshold: score={score:.4f} < min={self._min_consensus}"
            )

    def _no_credential_in_messages(self, state: dict, violations: list) -> None:
        messages = state.get("messages", [])
        for msg in messages:
            content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
            for pattern in _CREDENTIAL_PATTERNS:
                if pattern.search(content):
                    violations.append(
                        "no_credential_in_messages: potential credential detected in message history"
                    )
                    return  # one violation per message scan is enough

    def _paper_trade_only(self, state: dict, violations: list) -> None:
        if self._paper_only and state.get("execution_mode") == "live":
            violations.append(
                "paper_trade_only: execution_mode='live' is blocked — "
                "set security.paper_trade_only=false in config to allow live trading"
            )


def claw_guard_node(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node wrapper for ClawGuard.

    Writes compliance_flags to state. If any rule fires, sets risk_approved=False
    to propagate the block signal downstream (order_router checks this).
    """
    guard = ClawGuard(config)
    approved, violations = guard.check(state)

    return {
        "risk_approved": approved,
        "compliance_flags": violations,
        "messages": [
            {
                "role": "assistant",
                "content": (
                    "ClawGuard: PASS" if approved
                    else f"ClawGuard: BLOCKED — {'; '.join(violations)}"
                ),
            }
        ],
    }
