"""Confidence calibration audit unit tests."""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.evaluation.calibration import (
    CalibrationMetrics,
    CalibrationReport,
    _band_for_confidence,
    _extract_confidence,
    run_confidence_calibration_audit,
)


def test_band_for_confidence():
    """Confidence bands map correctly."""
    assert _band_for_confidence(0.9) == "high"
    assert _band_for_confidence(0.75) == "high"
    assert _band_for_confidence(0.74) == "medium"
    assert _band_for_confidence(0.5) == "medium"
    assert _band_for_confidence(0.49) == "low"
    assert _band_for_confidence(0.25) == "low"
    assert _band_for_confidence(0.24) == "insufficient"
    assert _band_for_confidence(0.0) == "insufficient"


def test_extract_confidence():
    """Confidence extracted from strategy_context."""
    assert _extract_confidence({"strategy_context": {"confidence": 0.8}}) == 0.8
    assert _extract_confidence({"strategy_context": {"confidence": 0.0}}) == 0.0
    assert _extract_confidence({"strategy_context": {"confidence": 1.0}}) == 1.0
    assert _extract_confidence({"strategy_context": {}}) is None
    assert _extract_confidence({"strategy_context": {"confidence": "bad"}}) is None
    assert _extract_confidence({"strategy_context": {"confidence": 1.5}}) is None
    assert _extract_confidence({"strategy_context": {"confidence": -0.1}}) is None


@pytest.mark.asyncio
async def test_calibration_insufficient_data():
    """Audit returns insufficient_data when fewer than 5 closed trades."""
    mock_trades = [
        {
            "trade_id": "t1",
            "strategy_context": {"confidence": 0.8},
            "pnl": 100.0,
            "pnl_pct": 2.0,
        },
        {
            "trade_id": "t2",
            "strategy_context": {"confidence": 0.6},
            "pnl": -50.0,
            "pnl_pct": -1.0,
        },
    ]

    with patch(
        "src.evaluation.calibration._fetch_closed_trades",
        new_callable=AsyncMock,
        return_value=mock_trades,
    ):
        report = await run_confidence_calibration_audit(lookback_days=90)

    assert report.metrics.closed_trades == 2
    assert report.metrics.calibration_quality == "insufficient_data"
    assert any("Insufficient data" in r for r in report.recommendations)


@pytest.mark.asyncio
async def test_calibration_band_win_rates():
    """Audit computes win rates per confidence band."""
    # 6 high-confidence: 4 wins, 2 losses
    # 4 medium-confidence: 2 wins, 2 losses
    # 3 low-confidence: 1 win, 2 losses
    mock_trades = []
    for i, (conf, pnl) in enumerate(
        [
            (0.85, 50.0),
            (0.82, -30.0),
            (0.78, 40.0),
            (0.80, 20.0),
            (0.76, -10.0),
            (0.90, 60.0),  # high: 4 wins
            (0.65, 15.0),
            (0.55, -20.0),
            (0.60, 25.0),
            (0.52, -15.0),  # medium: 2 wins
            (0.35, -25.0),
            (0.40, 10.0),
            (0.30, -5.0),  # low: 1 win
        ]
    ):
        mock_trades.append({
            "trade_id": f"t{i}",
            "strategy_context": {"confidence": conf},
            "pnl": pnl,
            "pnl_pct": pnl / 1000.0 if pnl else 0.0,
        })

    with patch(
        "src.evaluation.calibration._fetch_closed_trades",
        new_callable=AsyncMock,
        return_value=mock_trades,
    ):
        report = await run_confidence_calibration_audit(lookback_days=90)

    assert report.metrics.closed_trades == 13
    assert report.metrics.high_band_count == 6
    assert report.metrics.medium_band_count == 4
    assert report.metrics.low_band_count == 3
    assert report.metrics.high_band_win_rate == pytest.approx(4 / 6, rel=0.01)
    assert report.metrics.medium_band_win_rate == pytest.approx(2 / 4, rel=0.01)
    assert report.metrics.low_band_win_rate == pytest.approx(1 / 3, rel=0.01)
    assert report.metrics.false_confidence_rate == pytest.approx(2 / 6, rel=0.01)
    assert report.metrics.calibration_quality in ("good", "degraded", "poor")


@pytest.mark.asyncio
async def test_calibration_poor_quality():
    """High-confidence trades that mostly lose yield poor calibration."""
    mock_trades = [
        {"trade_id": f"t{i}", "strategy_context": {"confidence": 0.85}, "pnl": -50.0, "pnl_pct": -2.0}
        for i in range(6)
    ]
    mock_trades[0]["pnl"] = 10.0
    mock_trades[0]["pnl_pct"] = 0.5  # 1 win, 5 losses in high band

    with patch(
        "src.evaluation.calibration._fetch_closed_trades",
        new_callable=AsyncMock,
        return_value=mock_trades,
    ):
        report = await run_confidence_calibration_audit(lookback_days=90)

    assert report.metrics.high_band_win_rate == pytest.approx(1 / 6, rel=0.01)
    assert report.metrics.calibration_quality == "poor"
    assert any("underperform" in r.lower() or "overconfidence" in r.lower() for r in report.recommendations)


@pytest.mark.asyncio
async def test_calibration_skips_trades_without_confidence():
    """Trades without confidence in strategy_context are excluded from metrics."""
    mock_trades = [
        {"trade_id": "t1", "strategy_context": {"confidence": 0.8}, "pnl": 100.0, "pnl_pct": 2.0},
        {"trade_id": "t2", "strategy_context": {}, "pnl": -50.0, "pnl_pct": -1.0},
        {"trade_id": "t3", "strategy_context": {"confidence": 0.7}, "pnl": 30.0, "pnl_pct": 1.0},
        {"trade_id": "t4", "strategy_context": {"confidence": 0.6}, "pnl": -20.0, "pnl_pct": -0.5},
        {"trade_id": "t5", "strategy_context": {"confidence": 0.9}, "pnl": 80.0, "pnl_pct": 1.5},
        {"trade_id": "t6", "strategy_context": {"confidence": 0.65}, "pnl": 15.0, "pnl_pct": 0.5},
    ]

    with patch(
        "src.evaluation.calibration._fetch_closed_trades",
        new_callable=AsyncMock,
        return_value=mock_trades,
    ):
        report = await run_confidence_calibration_audit(lookback_days=90)

    assert report.metrics.total_trades == 6
    assert report.metrics.closed_trades == 5  # t2 excluded (no confidence)
    assert len(report.band_details) >= 1
