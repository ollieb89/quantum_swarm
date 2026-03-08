"""
src.evaluation — Confidence calibration and evaluation harness.

Phase 10: Evaluation & Calibration — validates that analyst/consensus
confidence scores correlate with actual trade outcome quality.
"""

from src.evaluation.calibration import (
    CalibrationReport,
    CalibrationMetrics,
    run_confidence_calibration_audit,
)

__all__ = [
    "CalibrationReport",
    "CalibrationMetrics",
    "run_confidence_calibration_audit",
]
