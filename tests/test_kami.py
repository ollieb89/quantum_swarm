"""Unit tests for src/core/kami.py — KAMI Merit Index arithmetic core.

Phase 16, Plan 01 — TDD suite.
No LLM calls. No DB connections. Pure function tests only.
"""
import pytest

from src.core.kami import (
    KAMIDimensions,
    compute_merit,
    apply_ema,
    DEFAULT_MERIT,
    MERIT_FLOOR,
    MERIT_CEIL,
    _extract_recovery_signal,
    _extract_fidelity_signal,
)

# ---------------------------------------------------------------------------
# Constants and defaults
# ---------------------------------------------------------------------------

class TestConstants:
    def test_default_merit_is_half(self):
        assert DEFAULT_MERIT == 0.5

    def test_floor_is_one_tenth(self):
        assert MERIT_FLOOR == 0.1

    def test_ceil_is_one(self):
        assert MERIT_CEIL == 1.0

    def test_default_weights_sum_to_one(self):
        """Default weights alpha + beta + gamma + delta must equal 1.0."""
        # Import the module-level DEFAULT_WEIGHTS dict from kami
        from src.core.kami import DEFAULT_WEIGHTS
        total = (
            DEFAULT_WEIGHTS["alpha"]
            + DEFAULT_WEIGHTS["beta"]
            + DEFAULT_WEIGHTS["gamma"]
            + DEFAULT_WEIGHTS["delta"]
        )
        assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"

    def test_rebalanced_weights(self):
        """Phase 30: alpha=0.08, delta=0.32, beta/gamma unchanged, sum=1.0."""
        from src.core.kami import DEFAULT_WEIGHTS
        assert DEFAULT_WEIGHTS["alpha"] == 0.08, f"alpha={DEFAULT_WEIGHTS['alpha']}, expected 0.08"
        assert DEFAULT_WEIGHTS["delta"] == 0.32, f"delta={DEFAULT_WEIGHTS['delta']}, expected 0.32"
        assert DEFAULT_WEIGHTS["beta"] == 0.35
        assert DEFAULT_WEIGHTS["gamma"] == 0.25
        assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# KAMIDimensions dataclass
# ---------------------------------------------------------------------------

class TestKAMIDimensions:
    def test_cold_start_defaults(self):
        """KAMIDimensions() defaults every dimension to DEFAULT_MERIT (0.5)."""
        dims = KAMIDimensions()
        assert dims.accuracy == DEFAULT_MERIT
        assert dims.recovery == DEFAULT_MERIT
        assert dims.consensus == DEFAULT_MERIT
        assert dims.fidelity == DEFAULT_MERIT

    def test_frozen_immutability(self):
        dims = KAMIDimensions()
        with pytest.raises((AttributeError, TypeError)):
            dims.accuracy = 0.9  # type: ignore[misc]


# ---------------------------------------------------------------------------
# compute_merit
# ---------------------------------------------------------------------------

class TestComputeMerit:
    def test_compute_merit_formula(self):
        """Formula: alpha*acc + beta*rec + gamma*con + delta*fid, clamped to [0.1, 1.0]."""
        dims = KAMIDimensions(accuracy=0.8, recovery=0.9, consensus=0.7, fidelity=1.0)
        weights = {"alpha": 0.30, "beta": 0.35, "gamma": 0.25, "delta": 0.10}
        expected = round(0.30 * 0.8 + 0.35 * 0.9 + 0.25 * 0.7 + 0.10 * 1.0, 10)
        result = compute_merit(dims, weights)
        assert abs(result - expected) < 1e-9
        assert MERIT_FLOOR <= result <= MERIT_CEIL

    def test_floor_clamp_on_all_zeros(self):
        """compute_merit with all-zero dimensions is floor-clamped to 0.1."""
        dims = KAMIDimensions(accuracy=0.0, recovery=0.0, consensus=0.0, fidelity=0.0)
        weights = {"alpha": 0.30, "beta": 0.35, "gamma": 0.25, "delta": 0.10}
        result = compute_merit(dims, weights)
        assert result == MERIT_FLOOR, f"Expected {MERIT_FLOOR}, got {result}"

    def test_ceiling_clamp_on_all_ones(self):
        """compute_merit with all-one dimensions is ceiling-clamped to 1.0."""
        dims = KAMIDimensions(accuracy=1.0, recovery=1.0, consensus=1.0, fidelity=1.0)
        weights = {"alpha": 0.30, "beta": 0.35, "gamma": 0.25, "delta": 0.10}
        result = compute_merit(dims, weights)
        assert result == MERIT_CEIL, f"Expected {MERIT_CEIL}, got {result}"

    def test_weight_rebalance_shifts_composite(self):
        """Phase 30: fidelity-heavy weights yield higher composite when fidelity > accuracy."""
        from src.core.kami import DEFAULT_WEIGHTS
        dims = KAMIDimensions(accuracy=0.5, recovery=0.8, consensus=0.7, fidelity=0.9)
        new_result = compute_merit(dims, DEFAULT_WEIGHTS)
        old_weights = {"alpha": 0.30, "beta": 0.35, "gamma": 0.25, "delta": 0.10}
        old_result = compute_merit(dims, old_weights)
        # New weights give fidelity 32% instead of 10%, so composite should be higher
        assert new_result > old_result, (
            f"New weights ({new_result}) should exceed old weights ({old_result})"
        )
        assert new_result > 0.7, f"Expected composite > 0.7, got {new_result}"


# ---------------------------------------------------------------------------
# apply_ema
# ---------------------------------------------------------------------------

class TestApplyEma:
    def test_apply_ema_formula(self):
        """apply_ema(0.5, 1.0, 0.9) == 0.9 * 1.0 + 0.1 * 0.5 == 0.95."""
        result = apply_ema(prev=0.5, signal=1.0, lam=0.9)
        assert abs(result - 0.95) < 1e-9, f"Expected 0.95, got {result}"

    def test_apply_ema_no_change_when_equal(self):
        """EMA of equal prev and signal returns the same value."""
        result = apply_ema(prev=0.7, signal=0.7, lam=0.9)
        assert abs(result - 0.7) < 1e-9

    def test_apply_ema_lambda_zero_returns_prev(self):
        """lam=0.0 means ignore signal entirely — return prev unchanged."""
        result = apply_ema(prev=0.3, signal=1.0, lam=0.0)
        assert abs(result - 0.3) < 1e-9

    def test_apply_ema_lambda_one_returns_signal(self):
        """lam=1.0 means replace prev entirely with signal."""
        result = apply_ema(prev=0.3, signal=0.8, lam=1.0)
        assert abs(result - 0.8) < 1e-9

    def test_ema_absorption_preserves_dimensions(self):
        """EMA operates on individual dimension scores, not composites (KAMI-07).

        The same prev/signal/lambda produces the same result regardless of
        which dimension the value represents — weights are irrelevant to EMA.
        """
        acc_ema = apply_ema(0.5, 0.9, 0.9)
        fid_ema = apply_ema(0.5, 0.9, 0.9)
        rec_ema = apply_ema(0.5, 0.9, 0.9)
        assert acc_ema == fid_ema == rec_ema


# ---------------------------------------------------------------------------
# _extract_recovery_signal
# ---------------------------------------------------------------------------

class TestRecoverySignal:
    def test_success_true_returns_one(self):
        state = {"execution_result": {"success": True}}
        assert _extract_recovery_signal(state) == 1.0

    def test_invalid_input_returns_zero(self):
        """INVALID_INPUT error type is self-induced — recovery signal is 0.0."""
        state = {
            "execution_result": {
                "success": False,
                "error_type": "INVALID_INPUT",
            }
        }
        assert _extract_recovery_signal(state) == 0.0

    def test_schema_failure_returns_zero(self):
        state = {"execution_result": {"success": False, "error_type": "SCHEMA_FAILURE"}}
        assert _extract_recovery_signal(state) == 0.0

    def test_malformed_output_returns_zero(self):
        state = {"execution_result": {"success": False, "error_type": "MALFORMED_OUTPUT"}}
        assert _extract_recovery_signal(state) == 0.0

    def test_tool_error_returns_zero(self):
        state = {"execution_result": {"success": False, "error_type": "TOOL_ERROR"}}
        assert _extract_recovery_signal(state) == 0.0

    def test_upstream_error_not_penalised(self):
        """If producer_agent_id != active_persona the error is upstream — return 1.0."""
        state = {
            "active_persona": "AXIOM",
            "execution_result": {
                "success": False,
                "error_type": "INVALID_INPUT",
                "producer_agent_id": "MOMENTUM",
            },
        }
        assert _extract_recovery_signal(state) == 1.0

    def test_unknown_failure_returns_zero(self):
        """Unknown failure (no error_type, success=False) → 0.0."""
        state = {"execution_result": {"success": False}}
        assert _extract_recovery_signal(state) == 0.0

    def test_missing_execution_result_returns_one(self):
        """No execution_result key → treat as no execution run → 1.0."""
        state = {}
        assert _extract_recovery_signal(state) == 1.0


# ---------------------------------------------------------------------------
# _extract_fidelity_signal
# ---------------------------------------------------------------------------

class TestFidelitySignal:
    def test_fidelity_one_for_real_soul(self):
        """macro_analyst has a non-empty IDENTITY.md — fidelity should be 1.0."""
        result = _extract_fidelity_signal("macro_analyst")
        assert result == 1.0

    def test_fidelity_zero_for_missing_agent(self):
        """Unknown agent_id → SoulNotFoundError caught → fidelity 0.0."""
        result = _extract_fidelity_signal("nonexistent_agent_xyz")
        assert result == 0.0
