from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

SOULS_DIR = Path(__file__).parent / "souls"

_KNOWN_AGENTS = (
    "macro_analyst",
    "bullish_researcher",
    "bearish_researcher",
    "quant_modeler",
    "risk_manager",
)


@dataclass(frozen=True)
class AgentSoul:
    """Immutable identity snapshot for one L2 agent. Frozen for lru_cache hashability."""
    agent_id: str
    identity: str   # Contents of IDENTITY.md
    soul: str       # Contents of SOUL.md
    agents: str     # Contents of AGENTS.md

    @property
    def system_prompt(self) -> str:
        """Full soul content concatenated for LLM system prompt injection."""
        return f"{self.identity}\n\n{self.soul}\n\n{self.agents}"

    @property
    def active_persona(self) -> str:
        """Agent handle extracted from first H1 line of IDENTITY.md, e.g. 'AXIOM'."""
        for line in self.identity.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return self.agent_id


@lru_cache(maxsize=None)
def load_soul(agent_id: str) -> AgentSoul:
    """Load and cache an agent's soul from the filesystem.

    Args:
        agent_id: Directory name under src/core/souls/ (e.g. 'macro_analyst').

    Returns:
        Immutable AgentSoul with all three soul file contents populated.

    Raises:
        ValueError: If agent_id would escape SOULS_DIR (path traversal).
        FileNotFoundError: If the agent's soul directory does not exist.
    """
    target = (SOULS_DIR / agent_id).resolve()
    if not str(target).startswith(str(SOULS_DIR.resolve())):
        raise ValueError(
            f"Invalid agent_id — path traversal detected: {agent_id!r}"
        )
    if not target.is_dir():
        raise FileNotFoundError(f"No soul directory for agent: {agent_id!r}")

    identity = (target / "IDENTITY.md").read_text(encoding="utf-8")
    soul = (target / "SOUL.md").read_text(encoding="utf-8")
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")

    return AgentSoul(
        agent_id=agent_id,
        identity=identity,
        soul=soul,
        agents=agents,
    )


def warmup_soul_cache() -> None:
    """Pre-load all known agent souls into lru_cache.

    Called once at graph creation time (after build_graph()) to fail fast
    on missing soul files rather than during a live trading run.
    """
    for agent_id in _KNOWN_AGENTS:
        load_soul(agent_id)
