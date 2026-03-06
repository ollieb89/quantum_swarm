"""
src.core.budget_manager — Token spend tracking and safety budget enforcement.

Tracks cumulative input/output token usage and estimated USD cost across a swarm
session.  Raises SafetyShutdown when configurable session or daily ceilings are
breached.

Config keys (under ``budget:`` in swarm_config.yaml)::

    budget:
      session_token_limit: 100000       # max tokens per graph invocation
      daily_token_limit:   1000000      # max tokens per calendar day (rough)
      daily_usd_limit:     5.00         # max USD spend per day
      model_pricing:
        gemini-2.0-flash:
          input_per_million:  0.075     # USD per 1 M input tokens
          output_per_million: 0.30      # USD per 1 M output tokens

Usage::

    manager = BudgetManager(config)
    manager.record_usage(input_tokens=500, output_tokens=200)
    manager.check_budget()    # raises SafetyShutdown if over limit
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional

from src.tools.verification_wrapper import SafetyShutdown

logger = logging.getLogger(__name__)

# Default pricing for Gemini 2.0 Flash (USD per 1 M tokens, as of 2026-03)
_DEFAULT_PRICING: Dict[str, Dict[str, float]] = {
    "gemini-2.0-flash": {
        "input_per_million": 0.075,
        "output_per_million": 0.30,
    },
}

# Conservative defaults if no config supplied
_DEFAULT_SESSION_TOKEN_LIMIT = 100_000
_DEFAULT_DAILY_TOKEN_LIMIT = 1_000_000
_DEFAULT_DAILY_USD_LIMIT = 5.00


class BudgetManager:
    """Thread-safe token spend tracker with configurable safety ceilings.

    Instantiate once per swarm session and share across nodes.  Call
    :meth:`record_usage` after each LLM invocation and :meth:`check_budget`
    at entry points (e.g. ``classify_intent``) to halt before over-spending.

    Args:
        config: The swarm config dict (or sub-dict).  Reads ``budget.*`` keys.
        model:  Default model name for pricing lookups.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        model: str = "gemini-2.0-flash",
    ) -> None:
        cfg = (config or {}).get("budget", {})
        self._session_token_limit: int = int(
            cfg.get("session_token_limit", _DEFAULT_SESSION_TOKEN_LIMIT)
        )
        self._daily_token_limit: int = int(
            cfg.get("daily_token_limit", _DEFAULT_DAILY_TOKEN_LIMIT)
        )
        self._daily_usd_limit: float = float(
            cfg.get("daily_usd_limit", _DEFAULT_DAILY_USD_LIMIT)
        )
        pricing_cfg = cfg.get("model_pricing", {})
        self._pricing: Dict[str, Dict[str, float]] = {
            **_DEFAULT_PRICING,
            **pricing_cfg,
        }
        self._default_model = model

        # Runtime counters (thread-safe via lock)
        self._lock = threading.Lock()
        self._session_input_tokens: int = 0
        self._session_output_tokens: int = 0
        self._session_usd: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        model: Optional[str] = None,
    ) -> None:
        """Add token counts to the session total and update USD estimate.

        Args:
            input_tokens:  Number of prompt/input tokens consumed.
            output_tokens: Number of completion/output tokens generated.
            model:         Model name for pricing lookup (falls back to default).
        """
        model = model or self._default_model
        pricing = self._pricing.get(model, self._pricing.get(self._default_model, {}))
        input_rate = pricing.get("input_per_million", 0.0)
        output_rate = pricing.get("output_per_million", 0.0)
        cost = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000

        with self._lock:
            self._session_input_tokens += input_tokens
            self._session_output_tokens += output_tokens
            self._session_usd += cost

        logger.debug(
            "BudgetManager: +%d in / +%d out / +$%.6f → total %d tokens / $%.4f",
            input_tokens, output_tokens, cost,
            self.total_tokens, self._session_usd,
        )

    def check_budget(self) -> None:
        """Assert that all session ceilings are within limits.

        Raises:
            SafetyShutdown: if any ceiling is breached.
        """
        with self._lock:
            total = self._session_input_tokens + self._session_output_tokens
            usd = self._session_usd

        if total >= self._session_token_limit:
            raise SafetyShutdown(
                f"BudgetManager: session token limit reached "
                f"({total:,} ≥ {self._session_token_limit:,}). Swarm halted."
            )
        if usd >= self._daily_usd_limit:
            raise SafetyShutdown(
                f"BudgetManager: daily USD limit reached "
                f"(${usd:.4f} ≥ ${self._daily_usd_limit:.2f}). Swarm halted."
            )
        logger.debug(
            "BudgetManager: budget OK — %d tokens / $%.4f used",
            total, usd,
        )

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def total_tokens(self) -> int:
        with self._lock:
            return self._session_input_tokens + self._session_output_tokens

    @property
    def session_usd(self) -> float:
        with self._lock:
            return self._session_usd

    def summary(self) -> Dict[str, Any]:
        """Return a snapshot dict suitable for logging or state storage."""
        with self._lock:
            return {
                "session_input_tokens": self._session_input_tokens,
                "session_output_tokens": self._session_output_tokens,
                "total_tokens": self._session_input_tokens + self._session_output_tokens,
                "session_usd": round(self._session_usd, 6),
                "session_token_limit": self._session_token_limit,
                "daily_usd_limit": self._daily_usd_limit,
            }
