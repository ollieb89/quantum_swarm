#!/usr/bin/env python3
"""
Run confidence calibration audit against closed trades in the trade warehouse.

Usage:
    uv run python scripts/run_calibration_audit.py [--days 90] [--json]

Exits 0 on success; exits 1 if calibration quality is 'poor' (for CI gates).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on path when run as script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import asyncio
import json
import sys

from src.evaluation.calibration import run_confidence_calibration_audit


def _format_report(report) -> str:
    """Format CalibrationReport as human-readable text."""
    m = report.metrics
    lines = [
        "=" * 60,
        "Confidence Calibration Audit",
        f"Generated: {report.generated_at.isoformat()}",
        f"Lookback: {report.lookback_days} days",
        "=" * 60,
        "",
        f"Total closed trades: {m.closed_trades} (of {m.total_trades} in window)",
        f"Calibration quality: {m.calibration_quality}",
        "",
    ]

    if m.high_band_count > 0:
        lines.append("Band breakdown:")
        for bd in report.band_details:
            wr = bd.get("win_rate")
            wr_str = f"{wr:.1%}" if wr is not None else "N/A"
            lines.append(f"  {bd['band']:12} n={bd['count']:3}  wins={bd['wins']:3}  win_rate={wr_str}")
        lines.append("")

    if m.false_confidence_rate is not None:
        lines.append(f"False confidence rate (high-band losses): {m.false_confidence_rate:.1%}")
    if m.spearman_correlation is not None:
        lines.append(f"Spearman(confidence, pnl_pct): {m.spearman_correlation:.3f}")
    if m.mean_confidence is not None:
        lines.append(f"Mean confidence: {m.mean_confidence:.3f}")
    if m.mean_pnl_pct is not None:
        lines.append(f"Mean PnL %: {m.mean_pnl_pct:.2%}")
    lines.append("")

    if report.recommendations:
        lines.append("Recommendations:")
        for r in report.recommendations:
            lines.append(f"  - {r}")
        lines.append("")

    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run confidence calibration audit")
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="Lookback days for closed trades (default: 90)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output report as JSON",
    )
    parser.add_argument(
        "--fail-on-poor",
        action="store_true",
        help="Exit 1 if calibration quality is 'poor'",
    )
    args = parser.parse_args()

    report = await run_confidence_calibration_audit(lookback_days=args.days)

    if args.json:
        # Serialize for JSON (dataclasses with datetime)
        out = {
            "generated_at": report.generated_at.isoformat(),
            "lookback_days": report.lookback_days,
            "metrics": {
                "total_trades": report.metrics.total_trades,
                "closed_trades": report.metrics.closed_trades,
                "high_band_count": report.metrics.high_band_count,
                "medium_band_count": report.metrics.medium_band_count,
                "low_band_count": report.metrics.low_band_count,
                "insufficient_band_count": report.metrics.insufficient_band_count,
                "high_band_win_rate": report.metrics.high_band_win_rate,
                "medium_band_win_rate": report.metrics.medium_band_win_rate,
                "low_band_win_rate": report.metrics.low_band_win_rate,
                "insufficient_band_win_rate": report.metrics.insufficient_band_win_rate,
                "false_confidence_rate": report.metrics.false_confidence_rate,
                "spearman_correlation": report.metrics.spearman_correlation,
                "mean_confidence": report.metrics.mean_confidence,
                "mean_pnl_pct": report.metrics.mean_pnl_pct,
                "calibration_quality": report.metrics.calibration_quality,
            },
            "band_details": report.band_details,
            "recommendations": report.recommendations,
        }
        print(json.dumps(out, indent=2))
    else:
        print(_format_report(report))

    if args.fail_on_poor and report.metrics.calibration_quality == "poor":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
