"""Unit tests for CircuitBreaker state machine and error classification."""

import logging
import time
from unittest.mock import patch

import httpx
from google.genai.errors import ClientError, ServerError
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

from src.core.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    DEFAULT_COOLDOWN_S,
    DEFAULT_THRESHOLD,
    is_transient_llm_error,
)


# ---------------------------------------------------------------------------
# CircuitBreaker state-machine tests
# ---------------------------------------------------------------------------

class TestCircuitBreakerStateMachine:

    def test_initial_state(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0

    def test_closed_allows_calls(self):
        cb = CircuitBreaker()
        assert cb.check() is True

    def test_single_failure_stays_closed(self):
        cb = CircuitBreaker()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_threshold_failures_opens(self):
        cb = CircuitBreaker(threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_open_blocks_calls(self):
        cb = CircuitBreaker(threshold=3, cooldown_s=60)
        for _ in range(3):
            cb.record_failure()
        assert cb.check() is False

    def test_success_resets_counter(self):
        cb = CircuitBreaker(threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_mixed_success_failure_no_open(self):
        cb = CircuitBreaker(threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()  # resets counter
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_cooldown_transitions_to_half_open(self):
        cb = CircuitBreaker(threshold=3, cooldown_s=10)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Simulate time passing beyond cooldown
        with patch("src.core.circuit_breaker.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 11
            result = cb.check()
        assert result is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_success_closes(self):
        cb = CircuitBreaker(threshold=3, cooldown_s=10)
        for _ in range(3):
            cb.record_failure()

        # Transition to HALF_OPEN
        with patch("src.core.circuit_breaker.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 11
            cb.check()

        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(threshold=3, cooldown_s=10)
        for _ in range(3):
            cb.record_failure()

        # Transition to HALF_OPEN
        with patch("src.core.circuit_breaker.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 11
            cb.check()

        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        # Fresh cooldown — opened_at was reset
        assert cb._opened_at is not None


# ---------------------------------------------------------------------------
# is_transient_llm_error tests
# ---------------------------------------------------------------------------

class TestIsTransientLlmError:

    def test_is_transient_server_error_503(self):
        exc = ServerError(503, {})
        assert is_transient_llm_error(exc) is True

    def test_is_transient_server_error_500(self):
        exc = ServerError(500, {})
        assert is_transient_llm_error(exc) is False

    def test_is_transient_wrapped_429(self):
        cause = ClientError(429, {})
        exc = ChatGoogleGenerativeAIError("rate limited")
        exc.__cause__ = cause
        assert is_transient_llm_error(exc) is True

    def test_is_transient_wrapped_400(self):
        cause = ClientError(400, {})
        exc = ChatGoogleGenerativeAIError("bad request")
        exc.__cause__ = cause
        assert is_transient_llm_error(exc) is False

    def test_is_transient_timeout(self):
        exc = httpx.TimeoutException("connection timed out")
        assert is_transient_llm_error(exc) is True

    def test_is_transient_other_exception(self):
        exc = ValueError("something else")
        assert is_transient_llm_error(exc) is False


# ---------------------------------------------------------------------------
# Logging tests
# ---------------------------------------------------------------------------

class TestCircuitBreakerLogging:

    def test_transition_logging(self, caplog):
        cb = CircuitBreaker(threshold=2)
        with caplog.at_level(logging.INFO, logger="src.core.circuit_breaker"):
            cb.record_failure()
            cb.record_failure()  # triggers CLOSED -> OPEN

        assert any(
            "circuit_breaker_transition" in r.message
            and "closed" in str(getattr(r, "from_state", "")) or "closed" in r.message
            for r in caplog.records
        ), f"Expected transition log, got: {[r.message for r in caplog.records]}"


# ---------------------------------------------------------------------------
# Kill switch tests
# ---------------------------------------------------------------------------

class TestCircuitBreakerKillSwitch:

    def test_kill_switch(self, monkeypatch):
        monkeypatch.setenv("CIRCUIT_BREAKER_ENABLED", "false")
        cb = CircuitBreaker(threshold=1)
        # Even after a failure that would normally open the circuit:
        cb.record_failure()
        # check() should still return True (breaker disabled)
        assert cb.check() is True
        # record_failure should be a no-op, state stays CLOSED
        assert cb.state == CircuitState.CLOSED


# ---------------------------------------------------------------------------
# Constants tests
# ---------------------------------------------------------------------------

class TestConstants:

    def test_default_threshold(self):
        assert DEFAULT_THRESHOLD == 3

    def test_default_cooldown(self):
        assert DEFAULT_COOLDOWN_S == 30
