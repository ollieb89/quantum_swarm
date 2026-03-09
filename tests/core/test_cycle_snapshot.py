"""Tests for CycleSnapshot Pydantic model."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.core.cycle_snapshot import CycleSnapshot, CYCLE_ID_PAD_WIDTH


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _full_snapshot(**overrides) -> dict:
    """Return a dict with all fields populated for a completed cycle."""
    base = dict(
        cycle_id=42,
        task_id="task-abc-123",
        symbol="BTC/USDT",
        timestamp=datetime(2026, 3, 9, tzinfo=timezone.utc),
        status="completed",
        macro_report={"trend": "bullish"},
        quant_proposal={"signal": 0.85},
        bullish_thesis={"catalyst": "ETF approval"},
        bearish_thesis={"risk": "regulatory"},
        debate_history=[{"round": 1}],
        debate_resolution={"winner": "bull"},
        weighted_consensus_score=0.72,
        merit_scores={"axiom": 0.6},
        soul_sync_context={"active_persona": "axiom"},
        risk_approved=True,
        risk_notes="Within limits",
        execution_result={"order_id": "X123"},
        decision_card={"card_id": "dc-001"},
        error_context=None,
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCycleSnapshotValidation:
    """CycleSnapshot model validation tests."""

    def test_full_snapshot_validates(self):
        """CycleSnapshot with all fields populated validates successfully."""
        snap = CycleSnapshot(**_full_snapshot())
        assert snap.cycle_id == 42
        assert snap.symbol == "BTC/USDT"
        assert snap.status == "completed"

    def test_failed_with_none_agent_fields(self):
        """CycleSnapshot with status='failed' and None agent fields validates."""
        snap = CycleSnapshot(
            cycle_id=1,
            task_id="t1",
            symbol="ETH/USDT",
            status="failed",
            error_context={"error_type": "timeout", "message": "LLM timeout"},
        )
        assert snap.status == "failed"
        assert snap.macro_report is None
        assert snap.execution_result is None

    def test_rejected_with_none_post_risk(self):
        """CycleSnapshot with status='rejected' and None post-risk fields validates."""
        snap = CycleSnapshot(
            cycle_id=2,
            task_id="t2",
            symbol="SOL/USDT",
            status="rejected",
            macro_report={"trend": "flat"},
            quant_proposal={"signal": 0.3},
            bullish_thesis={"catalyst": "none"},
            bearish_thesis={"risk": "high"},
            debate_history=[{"round": 1}],
            debate_resolution={"winner": "bear"},
            weighted_consensus_score=0.25,
            merit_scores={"axiom": 0.4},
            soul_sync_context={"active_persona": "axiom"},
            risk_approved=False,
            risk_notes="Below threshold",
        )
        assert snap.status == "rejected"
        assert snap.execution_result is None
        assert snap.decision_card is None

    def test_invalid_status_rejected(self):
        """Status field rejects invalid values."""
        with pytest.raises(ValidationError):
            CycleSnapshot(
                cycle_id=3,
                task_id="t3",
                symbol="BTC/USDT",
                status="running",
            )


class TestValidateCompleted:
    """Tests for validate_completed() method."""

    def test_raises_for_completed_missing_execution_result(self):
        """validate_completed() raises ValueError when completed but execution_result is None."""
        snap = CycleSnapshot(**_full_snapshot(execution_result=None))
        with pytest.raises(ValueError, match="execution_result"):
            snap.validate_completed()

    def test_no_raise_for_failed_with_none(self):
        """validate_completed() does NOT raise for status='failed' with None fields."""
        snap = CycleSnapshot(
            cycle_id=10,
            task_id="t10",
            symbol="BTC/USDT",
            status="failed",
            error_context={"error_type": "crash"},
        )
        snap.validate_completed()  # Should not raise

    def test_no_raise_for_rejected_with_none_post_risk(self):
        """validate_completed() does NOT raise for status='rejected' with None post-risk."""
        snap = CycleSnapshot(
            cycle_id=11,
            task_id="t11",
            symbol="ETH/USDT",
            status="rejected",
            risk_approved=False,
        )
        snap.validate_completed()  # Should not raise


class TestHelperMethods:
    """Tests for padded_id() and snapshot_dir()."""

    def test_padded_id(self):
        """padded_id() returns zero-padded string of CYCLE_ID_PAD_WIDTH digits."""
        snap = CycleSnapshot(**_full_snapshot(cycle_id=42))
        assert snap.padded_id() == "000042"
        assert len(snap.padded_id()) == CYCLE_ID_PAD_WIDTH

    def test_snapshot_dir(self):
        """snapshot_dir() returns correct path."""
        snap = CycleSnapshot(**_full_snapshot(cycle_id=42))
        assert snap.snapshot_dir() == "data/cycles/000042"

    def test_snapshot_dir_custom_base(self):
        """snapshot_dir() with custom base path."""
        snap = CycleSnapshot(**_full_snapshot(cycle_id=7))
        assert snap.snapshot_dir(base="/tmp/cycles") == "/tmp/cycles/000007"


class TestSerialization:
    """Tests for JSON serialization."""

    def test_model_dump_json_serializable(self):
        """model_dump(mode='json') produces JSON-serializable dict."""
        snap = CycleSnapshot(**_full_snapshot())
        d = snap.model_dump(mode="json")
        assert isinstance(d, dict)
        # datetime should be serialized as string
        assert isinstance(d["timestamp"], str)


class TestTokenUsage:
    """Tests for token_usage field (Phase 30)."""

    def test_token_usage_field(self):
        """token_usage round-trips through model_dump/model_validate."""
        token_data = {
            "macro_analyst": {
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
                "usd_cost": 0.0225,
            }
        }
        snap = CycleSnapshot(**_full_snapshot(token_usage=token_data))
        assert snap.token_usage == token_data

        dumped = snap.model_dump(mode="json")
        restored = CycleSnapshot.model_validate(dumped)
        assert restored.token_usage == token_data

    def test_token_usage_defaults_none(self):
        """token_usage defaults to None when not provided."""
        snap = CycleSnapshot(**_full_snapshot())
        assert snap.token_usage is None


class TestManifestFields:
    """Manifest fields are always present on any valid snapshot."""

    @pytest.mark.parametrize("status", ["completed", "rejected", "failed"])
    def test_manifest_fields_present(self, status):
        """cycle_id, symbol, timestamp, status always present."""
        kwargs = dict(cycle_id=99, task_id="tx", symbol="XRP/USDT", status=status)
        if status == "completed":
            kwargs.update(_full_snapshot(cycle_id=99, task_id="tx", symbol="XRP/USDT"))
        snap = CycleSnapshot(**kwargs)
        assert snap.cycle_id == 99
        assert snap.symbol == "XRP/USDT"
        assert snap.timestamp is not None
        assert snap.status == status
