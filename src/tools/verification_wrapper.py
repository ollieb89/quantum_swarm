"""
Verification Wrapper — BudgetedTool and deduplication cache for researcher agents.

Provides:
  - BudgetedTool: wraps any @tool function, enforces a per-invocation call budget,
    and requires a hypothesis kwarg on every call.
  - ToolCache: module-level dict that deduplicates identical tool calls so analyst-
    fetched data is reused by researchers without hitting the underlying tool again.
  - budgeted(tool_fn, max_calls=5): factory that returns a ready-to-use BudgetedTool.

Design:
  - Per-invocation state (call count) lives in the BudgetedTool *instance*.
    Create a fresh instance per graph invocation to reset the counter.
  - The ToolCache is intentionally module-level so that data fetched by analyst
    agents earlier in the same Python process is available to researcher agents.

Exceptions:
  - ToolBudgetExceeded: raised when the call count exceeds max_calls.
  - ValueError:         raised when hypothesis kwarg is missing.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ToolBudgetExceeded(Exception):
    """Raised when a BudgetedTool has exhausted its call budget."""


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
