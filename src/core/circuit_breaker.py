"""Three-state circuit breaker for Gemini API resilience.

States: CLOSED (healthy) -> OPEN (tripped) -> HALF_OPEN (probing) -> CLOSED
Only transient errors (429, 503, timeout) trip the breaker.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from enum import Enum

import httpx
from google.genai.errors import ClientError, ServerError
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLD: int = 3
DEFAULT_COOLDOWN_S: int = 30

_TRANSIENT_CODES = {429, 503}


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------

def is_transient_llm_error(exc: Exception) -> bool:
    """Return True if *exc* represents a transient Gemini API failure.

    Transient errors are those caused by temporary overload or unavailability:
    - HTTP 429 (rate-limited) or 503 (service unavailable) from the API
    - Any timeout from the HTTP transport layer (httpx)

    Non-transient errors (400 bad-request, 401 auth, 403 forbidden, 500 internal)
    indicate bugs or configuration problems and must NOT trip the breaker.
    """
    # Direct google.genai ServerError (5xx) — only 429/503 are transient
    if isinstance(exc, ServerError):
        return getattr(exc, "code", 0) in _TRANSIENT_CODES

    # LangChain wraps google.genai ClientError (4xx, including 429)
    if isinstance(exc, ChatGoogleGenerativeAIError):
        cause = exc.__cause__
        if isinstance(cause, (ClientError, ServerError)):
            return getattr(cause, "code", 0) in _TRANSIENT_CODES
        return False

    # httpx transport-level timeout
    if isinstance(exc, httpx.TimeoutException):
        return True

    return False


# ---------------------------------------------------------------------------
# Circuit state enum
# ---------------------------------------------------------------------------

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """Thread-safe three-state circuit breaker.

    Parameters
    ----------
    threshold : int
        Consecutive transient failures required to trip the breaker.
    cooldown_s : int | float
        Seconds to wait in OPEN state before allowing a probe (HALF_OPEN).
    """

    def __init__(
        self,
        threshold: int = DEFAULT_THRESHOLD,
        cooldown_s: int | float = DEFAULT_COOLDOWN_S,
    ) -> None:
        self._lock = threading.Lock()
        self._state = CircuitState.CLOSED
        self._failure_count: int = 0
        self._opened_at: float | None = None
        self._threshold = threshold
        self._cooldown_s = cooldown_s

        # Kill switch — read once at init
        self._enabled = os.environ.get(
            "CIRCUIT_BREAKER_ENABLED", "true"
        ).lower() != "false"

    # -- observable state ---------------------------------------------------

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state

    # -- public API ---------------------------------------------------------

    def check(self) -> bool:
        """Return True if the call should proceed, False if blocked.

        Side-effect: transitions OPEN -> HALF_OPEN when cooldown expires.
        """
        if not self._enabled:
            return True

        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                elapsed = time.monotonic() - self._opened_at  # type: ignore[operator]
                if elapsed >= self._cooldown_s:
                    self._transition(CircuitState.HALF_OPEN)
                    return True
                return False

            # HALF_OPEN — allow exactly one probe
            return True

    def record_success(self) -> None:
        """Record a successful call."""
        if not self._enabled:
            return

        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._transition(CircuitState.CLOSED)
            self._failure_count = 0
            self._opened_at = None

    def record_failure(self) -> None:
        """Record a failed call (must be transient to count)."""
        if not self._enabled:
            return

        with self._lock:
            self._failure_count += 1

            if self._state == CircuitState.HALF_OPEN:
                # Probe failed — reopen with fresh cooldown
                self._opened_at = time.monotonic()
                self._transition(CircuitState.OPEN)
            elif self._failure_count >= self._threshold:
                self._opened_at = time.monotonic()
                self._transition(CircuitState.OPEN)

    # -- internals ----------------------------------------------------------

    def _transition(self, new_state: CircuitState) -> None:
        """Log and apply state transition.  Must be called under lock."""
        old = self._state
        self._state = new_state
        logger.info(
            "circuit_breaker_transition",
            extra={
                "from_state": old.value,
                "to_state": new_state.value,
                "failure_count": self._failure_count,
            },
        )
