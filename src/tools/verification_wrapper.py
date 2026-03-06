"""
Verification Wrapper — BudgetedTool, ShellGuard, and deduplication cache.

Provides:
  - BudgetedTool: wraps any @tool function, enforces a per-invocation call budget,
    and requires a hypothesis kwarg on every call.
  - ToolCache: module-level dict that deduplicates identical tool calls so analyst-
    fetched data is reused by researchers without hitting the underlying tool again.
  - ShellGuard: sandboxed shell executor — restricts commands to a whitelist and
    confines execution to authorized project directories.
  - budgeted(tool_fn, max_calls=5): factory that returns a ready-to-use BudgetedTool.

Design:
  - Per-invocation state (call count) lives in the BudgetedTool *instance*.
    Create a fresh instance per graph invocation to reset the counter.
  - The ToolCache is intentionally module-level so that data fetched by analyst
    agents earlier in the same Python process is available to researcher agents.

Exceptions:
  - ToolBudgetExceeded: raised when the call count exceeds max_calls.
  - SafetyShutdown:     raised by ShellGuard when a blocked command is attempted.
  - ValueError:         raised when hypothesis kwarg is missing.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ToolBudgetExceeded(Exception):
    """Raised when a BudgetedTool has exhausted its call budget."""


class SafetyShutdown(Exception):
    """Raised when a security or budget violation requires the swarm to halt immediately."""


# ---------------------------------------------------------------------------
# Module-level deduplication cache
# ---------------------------------------------------------------------------

# Keyed by (tool_name: str, frozen_args: frozenset) → result dict
ToolCache: dict[tuple[str, frozenset], Any] = {}


# ---------------------------------------------------------------------------
# BudgetedTool
# ---------------------------------------------------------------------------


class BudgetedTool:
    """Wraps a LangChain @tool function with budget enforcement and caching.

    Args:
        tool_fn:   A LangChain @tool-decorated callable.
        max_calls: Maximum number of underlying tool invocations allowed
                   before ToolBudgetExceeded is raised. Default: 5.

    Usage::

        from src.tools.analyst_tools import fetch_market_data
        from src.tools.verification_wrapper import budgeted

        tool = budgeted(fetch_market_data, max_calls=5)
        result = tool(symbol="BTC-USD", timeframe="1h", hypothesis="BTC is bullish")

    The hypothesis kwarg is required on every call and is logged but NOT passed
    on to the underlying tool function (analyst tools do not accept it).
    """

    def __init__(self, tool_fn: Callable[..., Any], max_calls: int = 5) -> None:
        self._tool_fn = tool_fn
        self.max_calls = max_calls
        self._call_count: int = 0

        # Derive a stable name for cache keying
        # LangChain tools expose .name; plain callables fall back to __name__.
        self.tool_name: str = getattr(tool_fn, "name", None) or getattr(
            tool_fn, "__name__", repr(tool_fn)
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def call_count(self) -> int:
        """Number of underlying tool invocations made so far."""
        return self._call_count

    # ------------------------------------------------------------------
    # Core logic
    # ------------------------------------------------------------------

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Invoke the wrapped tool with budget and hypothesis enforcement.

        Args:
            *args:      Positional arguments forwarded to the underlying tool.
            **kwargs:   Keyword arguments forwarded to the underlying tool.
                        MUST include ``hypothesis`` (str) — raises ValueError
                        if absent or empty.

        Returns:
            The result from the underlying tool (or cached result).

        Raises:
            ToolBudgetExceeded: If the call budget has been exhausted.
            ValueError:         If hypothesis kwarg is missing or blank.
        """
        # --- 1. Hypothesis gate ---
        hypothesis = kwargs.pop("hypothesis", None)
        if not hypothesis:
            raise ValueError(
                f"BudgetedTool '{self.tool_name}' requires a non-empty "
                "'hypothesis' keyword argument."
            )

        # --- 2. Budget check ---
        if self._call_count >= self.max_calls:
            raise ToolBudgetExceeded(
                f"Tool '{self.tool_name}' budget exhausted: "
                f"{self._call_count}/{self.max_calls} calls used. "
                "Hypothesis was: " + hypothesis
            )

        # --- 3. Cache lookup ---
        cache_key = (self.tool_name, frozenset(list(args) + sorted(kwargs.items())))
        if cache_key in ToolCache:
            logger.debug(
                "Cache HIT for tool '%s' (hypothesis=%s)",
                self.tool_name,
                hypothesis,
            )
            return ToolCache[cache_key]

        # --- 4. Invoke underlying tool ---
        logger.info(
            "Calling tool '%s' (call %d/%d, hypothesis='%s')",
            self.tool_name,
            self._call_count + 1,
            self.max_calls,
            hypothesis,
        )
        result = self._tool_fn(*args, **kwargs)
        self._call_count += 1

        # --- 5. Populate cache ---
        ToolCache[cache_key] = result

        return result


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def budgeted(tool_fn: Callable[..., Any], max_calls: int = 5) -> BudgetedTool:
    """Create a BudgetedTool wrapping *tool_fn* with a per-invocation call limit.

    Create a **fresh** instance per graph invocation to reset the call counter.

    Args:
        tool_fn:   A LangChain @tool-decorated callable (or any callable).
        max_calls: Maximum allowed invocations before ToolBudgetExceeded.

    Returns:
        A new :class:`BudgetedTool` instance ready for use.

    Example::

        from src.tools.analyst_tools import fetch_market_data
        from src.tools.verification_wrapper import budgeted

        bounded_fetch = budgeted(fetch_market_data, max_calls=5)
    """
    return BudgetedTool(tool_fn=tool_fn, max_calls=max_calls)


# ---------------------------------------------------------------------------
# ShellGuard — sandboxed shell executor
# ---------------------------------------------------------------------------

# Commands whose base name is permitted to run
_ALLOWED_BASE_COMMANDS: frozenset[str] = frozenset([
    "ls", "cat", "head", "tail", "grep", "find", "wc",
    "echo", "python3", "python", "pytest", "pip", "git",
    "curl",  # read-only fetches; blocked patterns below catch pipe-to-shell abuse
])

# Patterns that are always rejected regardless of command whitelist
_BLOCKED_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?\b"),   # rm -rf and variants
    re.compile(r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r?\b"),   # rm -fr and variants
    re.compile(r"\brmdir\b"),
    re.compile(r"\bdd\b"),
    re.compile(r"\bmkfs\b"),
    re.compile(r">[>&]?\s*/dev/"),                      # redirect to /dev/*
    re.compile(r"\bcurl\b.*\|\s*(?:ba)?sh\b"),          # curl | sh
    re.compile(r"\bwget\b.*\|\s*(?:ba)?sh\b"),          # wget | sh
    re.compile(r"\bchmod\s+[0-9]*7[0-9]*\b"),          # chmod 777 variants
    re.compile(r"\bsudo\b"),
    re.compile(r"\bsu\s+"),
    re.compile(r";\s*rm\b"),                            # chained rm
    re.compile(r"&&\s*rm\b"),
]

# Restricted environment — strip credentials and sensitive vars
_SAFE_ENV_KEYS: frozenset[str] = frozenset([
    "PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TERM",
    "VIRTUAL_ENV", "PYTHONPATH",
])


class ShellGuard:
    """Sandboxed shell executor for L1/L3 agent tool calls.

    Restricts execution to:
      - A whitelist of allowed base commands (``_ALLOWED_BASE_COMMANDS``).
      - A set of authorized working directories (defaults to project root and
        its ``data/`` and ``src/`` subdirectories).
      - A stripped environment that omits credentials and sensitive vars.

    Raises:
        SafetyShutdown: immediately if a blocked command or pattern is detected.

    Usage::

        guard = ShellGuard()
        result = guard.safe_exec("ls data/inter_agent_comms/")
        print(result["stdout"])
    """

    def __init__(
        self,
        allowed_dirs: Optional[List[Path]] = None,
        timeout: int = 30,
    ) -> None:
        project_root = Path(__file__).resolve().parents[2]
        if allowed_dirs is None:
            self._allowed_dirs: List[Path] = [
                project_root,
                project_root / "data",
                project_root / "src",
                project_root / "tests",
                project_root / "config",
            ]
        else:
            self._allowed_dirs = [Path(d).resolve() for d in allowed_dirs]
        self._timeout = timeout
        self._env = {k: v for k, v in os.environ.items() if k in _SAFE_ENV_KEYS}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def safe_exec(self, command: str, cwd: Optional[Path] = None) -> Dict[str, Any]:
        """Validate and execute *command* in a restricted environment.

        Args:
            command: Shell command string to execute.
            cwd:     Working directory.  Must be within an authorized dir.
                     Defaults to the project root.

        Returns:
            Dict with keys: ``stdout``, ``stderr``, ``returncode``.

        Raises:
            SafetyShutdown: If the command fails validation.
        """
        self._validate_command(command)
        resolved_cwd = self._validate_cwd(cwd)

        logger.info("ShellGuard executing: %r (cwd=%s)", command, resolved_cwd)
        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                cwd=resolved_cwd,
                env=self._env,
            )
        except subprocess.TimeoutExpired:
            raise SafetyShutdown(
                f"ShellGuard: command timed out after {self._timeout}s: {command!r}"
            )

        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
        }

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_command(self, command: str) -> None:
        """Raise SafetyShutdown if command is not allowed."""
        # Check blocked patterns first (catches chained/piped abuse)
        for pattern in _BLOCKED_PATTERNS:
            if pattern.search(command):
                raise SafetyShutdown(
                    f"ShellGuard: blocked pattern matched in command: {command!r}"
                )

        # Check base command is in whitelist
        base = command.strip().split()[0] if command.strip() else ""
        base_name = Path(base).name  # strip any path prefix (e.g. /usr/bin/ls → ls)
        if base_name not in _ALLOWED_BASE_COMMANDS:
            raise SafetyShutdown(
                f"ShellGuard: command '{base_name}' is not in the allowed list. "
                f"Allowed: {sorted(_ALLOWED_BASE_COMMANDS)}"
            )

    def _validate_cwd(self, cwd: Optional[Path]) -> Path:
        """Resolve cwd and confirm it is within an authorized directory."""
        project_root = Path(__file__).resolve().parents[2]
        resolved = (Path(cwd).resolve() if cwd else project_root)
        for allowed in self._allowed_dirs:
            try:
                resolved.relative_to(allowed)
                return resolved
            except ValueError:
                continue
        raise SafetyShutdown(
            f"ShellGuard: working directory '{resolved}' is outside authorized paths. "
            f"Allowed: {self._allowed_dirs}"
        )
