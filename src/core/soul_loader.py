from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from src.core.drift_eval import DriftRule, parse_drift_guard_yaml
from src.core.soul_errors import SoulNotFoundError, SoulSecurityError

logger = logging.getLogger(__name__)

SOULS_DIR = Path(__file__).parent / "souls"

_KNOWN_AGENTS = (
    "macro_analyst",
    "bullish_researcher",
    "bearish_researcher",
    "quant_modeler",
    "risk_manager",
)

# Sections of SOUL.md that are visible to peer agents during soul-sync handshake.
# Drift Guard and Core Wounds are internal — excluded from public summaries.
_PEER_VISIBLE_SECTIONS: frozenset[str] = frozenset({"Core Beliefs", "Voice", "Non-Goals"})


@dataclass(frozen=True)
class AgentSoul:
    """Immutable identity snapshot for one L2 agent. Frozen for lru_cache hashability."""
    agent_id: str
    identity: str   # Contents of IDENTITY.md
    soul: str       # Contents of SOUL.md
    agents: str     # Contents of AGENTS.md
    users: str = ""  # Contents of USER.md (optional peer-user context); empty when absent
    drift_rules: tuple[DriftRule, ...] = ()  # Parsed drift guard rules from SOUL.md YAML

    @property
    def system_prompt(self) -> str:
        """Full soul content concatenated for LLM system prompt injection.

        Appends USER.md content only when non-empty to avoid trailing blank blocks.
        """
        parts = [self.identity, self.soul, self.agents]
        if self.users:
            parts.append(self.users)
        return "\n\n".join(parts)

    @property
    def active_persona(self) -> str:
        """Agent handle extracted from first H1 line of IDENTITY.md, e.g. 'AXIOM'."""
        for line in self.identity.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return self.agent_id

    def public_soul_summary(self) -> str:
        """Return a peer-visible summary of this agent's soul, capped at 300 chars.

        Includes: Core Beliefs, Voice, Non-Goals sections from SOUL.md.
        Excludes: Drift Guard, Core Wounds (internal self-regulatory content).

        Returns:
            Non-empty string of up to 300 chars representing peer-visible soul content.
            Falls back to first 300 chars of raw soul content if no matching sections found.
        """
        # Normalize line endings before splitting
        text = self.soul.replace("\r\n", "\n")

        # Split on H2 boundaries (each part starts at the ## heading or before first ##)
        parts = re.split(r"\n(?=## )", text)

        allowed_parts: list[str] = []
        for part in parts:
            # Extract heading from the first line of the part
            heading_match = re.match(r"^## (.+)", part.strip())
            if heading_match:
                heading = heading_match.group(1).strip()
                if heading in _PEER_VISIBLE_SECTIONS:
                    allowed_parts.append(part.strip())

        if not allowed_parts:
            # Fallback: return condensed raw soul (log a warning)
            logger.warning(
                "public_soul_summary: no peer-visible sections found for agent %r — using raw soul fallback",
                self.agent_id,
            )
            condensed = re.sub(r"\s+", " ", self.soul).strip()
            return condensed[:300]

        # Join allowed sections and normalize internal whitespace
        joined = " ".join(allowed_parts)
        normalized = re.sub(r"\s+", " ", joined).strip()

        if len(normalized) <= 300:
            return normalized

        # Truncate at word boundary
        truncated = normalized[:300].rsplit(" ", 1)[0]
        return truncated


@lru_cache(maxsize=None)
def load_soul(agent_id: str) -> AgentSoul:
    """Load and cache an agent's soul from the filesystem.

    Args:
        agent_id: Directory name under src/core/souls/ (e.g. 'macro_analyst').

    Returns:
        Immutable AgentSoul with all soul file contents populated.

    Raises:
        SoulSecurityError: If agent_id would escape SOULS_DIR (path traversal).
        SoulNotFoundError: If the agent's soul directory does not exist.
    """
    target = (SOULS_DIR / agent_id).resolve()
    if not str(target).startswith(str(SOULS_DIR.resolve())):
        raise SoulSecurityError(
            f"Invalid agent_id — path traversal detected: {agent_id!r}"
        )
    if not target.is_dir():
        raise SoulNotFoundError(f"No soul directory for agent: {agent_id!r}")

    identity = (target / "IDENTITY.md").read_text(encoding="utf-8")
    soul = (target / "SOUL.md").read_text(encoding="utf-8")
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")
    try:
        users = (target / "USER.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        users = ""

    # Parse drift guard rules from SOUL.md YAML block (fail-soft: log and continue)
    try:
        drift_rules = parse_drift_guard_yaml(soul)
    except ValueError as e:
        logger.warning(
            "Malformed drift_guard YAML for agent %r — drift evaluation disabled: %s",
            agent_id,
            e,
        )
        drift_rules = ()

    return AgentSoul(
        agent_id=agent_id,
        identity=identity,
        soul=soul,
        agents=agents,
        users=users,
        drift_rules=drift_rules,
    )


def warmup_soul_cache() -> None:
    """Pre-load all known agent souls into lru_cache.

    Called once at graph creation time (after build_graph()) to fail fast
    on missing soul files rather than during a live trading run.
    """
    for agent_id in _KNOWN_AGENTS:
        load_soul(agent_id)
