"""
src.evaluation.calibration — Confidence calibration audit for trade proposals.

Validates that analyst confidence and consensus scores correlate with actual
trade outcome quality. Addresses the design concern: "Agent confidence is
weighted lowest to avoid noisy calibration dominating the score" (v1.2 design).

Metrics:
- Calibration curve: Do high-confidence proposals actually win more often?
- False confidence rate: % of high-confidence trades that lose
- Band accuracy: Win rate within each confidence band (HIGH/MEDIUM/LOW)
- Correlation: Spearman correlation between confidence and PnL outcome
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from src.core.db import get_pool

logger = logging.getLogger(__name__)

# Confidence bands aligned with EvidenceScorer / institutional_guard usage
CONFIDENCE_HIGH = 0.75
CONFIDENCE_MEDIUM = 0.5
CONFIDENCE_LOW = 0.25


@dataclass
class CalibrationMetrics:
    """Per-band and aggregate calibration metrics."""

    total_trades: int = 0
    closed_trades: int = 0
    high_band_count: int = 0
    medium_band_count: int = 0
    low_band_count: int = 0
    insufficient_band_count: int = 0
    high_band_win_rate: Optional[float] = None
    medium_band_win_rate: Optional[float] = None
    low_band_win_rate: Optional[float] = None
    insufficient_band_win_rate: Optional[float] = None
    false_confidence_rate: Optional[float] = None  # high-confidence losses / high-confidence total
    spearman_correlation: Optional[float] = None
    mean_confidence: Optional[float] = None
    mean_pnl_pct: Optional[float] = None
    calibration_quality: str = "insufficient_data"  # good | degraded | poor | insufficient_data


@dataclass
class CalibrationReport:
    """Full calibration audit report."""

    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    lookback_days: int = 90
    metrics: CalibrationMetrics = field(default_factory=CalibrationMetrics)
    band_details: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


def _band_for_confidence(confidence: float) -> str:
    """Map confidence score to band label."""
    if confidence >= CONFIDENCE_HIGH:
        return "high"
    if confidence >= CONFIDENCE_MEDIUM:
        return "medium"
    if confidence >= CONFIDENCE_LOW:
        return "low"
    return "insufficient"


def _compute_spearman(x: list[float], y: list[float]) -> Optional[float]:
    """Compute Spearman rank correlation. Returns None if insufficient data."""
    if len(x) < 3 or len(x) != len(y):
        return None
    if len(set(x)) < 2 or len(set(y)) < 2:
        return None  # Constant input — correlation undefined
    try:
        from scipy import stats

        r, _ = stats.spearmanr(x, y, nan_policy="omit")
        return float(r) if not (r != r) else None  # NaN check
    except ImportError:
        return None


async def _fetch_closed_trades(lookback_days: int) -> list[dict[str, Any]]:
    """Fetch closed trades with strategy_context from PostgreSQL."""
    pool = get_pool()
    try:
        await pool.open()
    except Exception:
        pass  # Pool may already be open
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    trades: list[dict[str, Any]] = []

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    SELECT trade_id, symbol, side, pnl, pnl_pct, strategy_context,
                           execution_time, exit_time
                    FROM trades
                    WHERE exit_time IS NOT NULL
                      AND execution_time >= %s
                    ORDER BY execution_time DESC;
                    """,
                    (since,),
                )
                rows = await cur.fetchall()
                for row in rows:
                    trades.append({
                        "trade_id": row[0],
                        "symbol": row[1],
                        "side": row[2],
                        "pnl": float(row[3]) if row[3] is not None else 0.0,
                        "pnl_pct": float(row[4]) if row[4] is not None else 0.0,
                        "strategy_context": row[5] or {},
                        "execution_time": row[6],
                        "exit_time": row[7],
                    })
    except Exception as e:
        logger.error("Failed to fetch trades for calibration: %s", e)
        raise

    return trades


def _extract_confidence(trade: dict[str, Any]) -> Optional[float]:
    """Extract confidence from strategy_context (quant_proposal)."""
    ctx = trade.get("strategy_context") or {}
    conf = ctx.get("confidence")
    if conf is None:
        return None
    try:
        val = float(conf)
        return val if 0.0 <= val <= 1.0 else None
    except (TypeError, ValueError):
        return None


async def run_confidence_calibration_audit(
    lookback_days: int = 90,
) -> CalibrationReport:
    """
    Run confidence calibration audit against closed trades.

    Args:
        lookback_days: Number of days to look back for closed trades.

    Returns:
        CalibrationReport with metrics and recommendations.
    """
    trades = await _fetch_closed_trades(lookback_days)
    report = CalibrationReport(lookback_days=lookback_days)

    # Filter to trades with valid confidence
    with_confidence: list[dict[str, Any]] = []
    for t in trades:
        conf = _extract_confidence(t)
        if conf is not None:
            t["_confidence"] = conf
            t["_band"] = _band_for_confidence(conf)
            t["_win"] = (t.get("pnl") or 0.0) > 0.0
            with_confidence.append(t)

    report.metrics.total_trades = len(trades)
    report.metrics.closed_trades = len(with_confidence)

    if len(with_confidence) < 5:
        report.recommendations.append(
            f"Insufficient data: {len(with_confidence)} closed trades with confidence. "
            "Need at least 5 for meaningful calibration. Run more paper/live trades."
        )
        return report

    # Aggregate by band
    bands: dict[str, list[dict]] = {"high": [], "medium": [], "low": [], "insufficient": []}
    for t in with_confidence:
        bands[t["_band"]].append(t)

    report.metrics.high_band_count = len(bands["high"])
    report.metrics.medium_band_count = len(bands["medium"])
    report.metrics.low_band_count = len(bands["low"])
    report.metrics.insufficient_band_count = len(bands["insufficient"])

    # Win rates per band
    for band_name, band_trades in bands.items():
        if band_trades:
            wins = sum(1 for t in band_trades if t["_win"])
            wr = wins / len(band_trades)
            setattr(report.metrics, f"{band_name}_band_win_rate", wr)
            report.band_details.append({
                "band": band_name,
                "count": len(band_trades),
                "wins": wins,
                "win_rate": wr,
            })

    # False confidence rate: high-confidence trades that lost
    if report.metrics.high_band_count > 0:
        high_trades = bands["high"]
        high_losses = sum(1 for t in high_trades if not t["_win"])
        report.metrics.false_confidence_rate = high_losses / len(high_trades)

    # Spearman correlation: confidence vs PnL%
    confs = [t["_confidence"] for t in with_confidence]
    pnls = [t.get("pnl_pct") or 0.0 for t in with_confidence]
    report.metrics.spearman_correlation = _compute_spearman(confs, pnls)
    report.metrics.mean_confidence = sum(confs) / len(confs)
    report.metrics.mean_pnl_pct = sum(pnls) / len(pnls)

    # Calibration quality heuristic
    if report.metrics.high_band_win_rate is not None:
        if report.metrics.high_band_win_rate >= 0.55 and (
            report.metrics.false_confidence_rate or 1.0
        ) < 0.45:
            report.metrics.calibration_quality = "good"
        elif report.metrics.high_band_win_rate >= 0.45:
            report.metrics.calibration_quality = "degraded"
        else:
            report.metrics.calibration_quality = "poor"
    else:
        report.metrics.calibration_quality = "insufficient_data"

    # Recommendations
    if report.metrics.calibration_quality == "poor":
        report.recommendations.append(
            "High-confidence trades underperform: consider lowering confidence weight "
            "in risk scoring or tightening analyst prompt to reduce overconfidence."
        )
    if report.metrics.false_confidence_rate and report.metrics.false_confidence_rate > 0.5:
        report.recommendations.append(
            f"False confidence rate {report.metrics.false_confidence_rate:.1%} is high. "
            "Review QuantModeler output format and confidence calibration."
        )
    if report.metrics.spearman_correlation is not None and report.metrics.spearman_correlation < 0:
        report.recommendations.append(
            "Negative correlation between confidence and PnL: confidence may be "
            "inversely related to outcome quality. Audit analyst prompts."
        )

    return report
