"""
src.agents.self_learning — Orchestrates the automated self-improvement pipeline.

Integrates PerformanceReviewAgent and RuleGenerator to analyze trades
from PostgreSQL and maintain MEMORY.md.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from src.agents.review_agent import PerformanceReviewAgent
from src.agents.rule_generator import RuleGenerator

logger = logging.getLogger(__name__)

class SelfLearningPipeline:
    """High-level pipeline for reviewing performance and updating institutional memory."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.review_agent = PerformanceReviewAgent()
        self.rule_generator = RuleGenerator()
        self.min_trades = config.get("self_improvement", {}).get("min_trades_for_analysis", 5)

    async def run_review_async(self) -> Dict[str, Any]:
        """Execute the full review and rule generation pipeline."""
        logger.info("Starting Self-Learning Review Pipeline...")

        # 1. Fetch trade data
        trades = await self.review_agent.get_recent_trade_data(days=7)
        
        if len(trades) < self.min_trades:
            logger.info("Insufficient trades for review: %d/%d", len(trades), self.min_trades)
            return {
                "status": "skipped",
                "reason": f"Only {len(trades)} trades found, need {self.min_trades}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # 2. Generate Drift Report
        drift_report = await self.review_agent.generate_drift_report(trades)
        
        # 3. Generate and persist rules
        rules = await self.rule_generator.generate_rules(drift_report)
        self.rule_generator.persist_rules(rules)

        summary = {
            "status": "completed",
            "trades_analyzed": len(trades),
            "rules_generated": len(rules),
            "drift_detected": drift_report.get("drift_detected", False),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Self-Learning Review complete: %d rules generated", len(rules))
        return summary

    def run_review(self) -> Dict[str, Any]:
        """Synchronous wrapper for main.py integration."""
        return asyncio.run(self.run_review_async())
