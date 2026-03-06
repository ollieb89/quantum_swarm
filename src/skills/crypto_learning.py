"""
Crypto Self-Learning Skills Module

Implements the self-improvement framework for continuous learning
from trade history. Includes trade logging, analysis, and rule generation.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict
from statistics import mean, stdev

logger = logging.getLogger(__name__)

# Skill registry interface
SKILL_INTENT = "weekly_review"


def handle(state: dict) -> dict:
    """Handle a weekly_review intent — returns review status without touching disk."""
    return {
        "skill_result": {"skill": "weekly_review", "status": "ok"},
        "messages": [{"role": "assistant", "content": "weekly_review skill: review triggered"}],
    }


@dataclass
class TradeRecord:
    """Single trade record"""
    trade_id: str
    timestamp: str
    symbol: str
    direction: str  # LONG/SHORT
    entry_price: float
    exit_price: float
    pnl_pct: float
    pnl_absolute: float
    indicators: Dict[str, Any]
    market_context: Dict[str, str]
    rationale: str
    outcome: str = ""  # WIN/LOSS

    def __post_init__(self):
        if self.pnl_pct > 0:
            self.outcome = "WIN"
        else:
            self.outcome = "LOSS"


@dataclass
class StrategyRule:
    """Generated trading rule"""
    rule_id: str
    type: str  # PREFER/AVOID/CAUTION
    condition: str
    description: str
    win_rate: float
    sample_size: int
    confidence: float
    created_at: str


class TradeLogger:
    """
    Trade logging module.

    Records trade details including indicators and market context
    for future analysis.
    """

    def __init__(self, log_file: str = "data/logs/trades.json"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize file if empty
        if not self.log_file.exists():
            self._write_trades([])

    def _read_trades(self) -> List[Dict]:
        """Read all trades from log"""
        try:
            with open(self.log_file) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _write_trades(self, trades: List[Dict]) -> None:
        """Write trades to log"""
        with open(self.log_file, "w") as f:
            json.dump(trades, f, indent=2)

    def log_trade(self, trade_data: Dict) -> str:
        """
        Log a new trade.

        Args:
            trade_data: Trade details including:
                - symbol, direction, entry_price, exit_price
                - indicators (RSI, MACD, etc.)
                - market_context (VIX, day_of_week, etc.)
                - rationale

        Returns:
            trade_id
        """
        import uuid
        trade_id = str(uuid.uuid4())[:8]

        # Calculate P&L
        if trade_data.get("direction") == "LONG":
            pnl_pct = ((trade_data["exit_price"] - trade_data["entry_price"])
                       / trade_data["entry_price"]) * 100
        else:
            pnl_pct = ((trade_data["entry_price"] - trade_data["exit_price"])
                       / trade_data["entry_price"]) * 100

        pnl_absolute = (pnl_pct / 100) * trade_data.get("capital", 10000)

        trade = TradeRecord(
            trade_id=trade_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            symbol=trade_data.get("symbol", "UNKNOWN"),
            direction=trade_data.get("direction", "LONG"),
            entry_price=trade_data.get("entry_price", 0),
            exit_price=trade_data.get("exit_price", 0),
            pnl_pct=pnl_pct,
            pnl_absolute=pnl_absolute,
            indicators=trade_data.get("indicators", {}),
            market_context=trade_data.get("market_context", {}),
            rationale=trade_data.get("rationale", "")
        )

        # Save to log
        trades = self._read_trades()
        trades.append(asdict(trade))
        self._write_trades(trades)

        logger.info(f"Trade logged: {trade_id} - {trade.outcome} ({pnl_pct:.2f}%)")
        return trade_id

    def get_trades(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[TradeRecord]:
        """Get trades with optional filters"""
        trades = self._read_trades()

        filtered = []
        for t in trades:
            if symbol and t.get("symbol") != symbol:
                continue

            # Date filtering would go here
            filtered.append(TradeRecord(**t))

        return filtered


class TradeAnalyzer:
    """
    Trade analysis module.

    Analyzes trade history to calculate win rates,
    identify patterns, and detect regime changes.
    """

    def __init__(self, trade_logger: TradeLogger):
        self.trade_logger = trade_logger

    def analyze_win_rates(
        self,
        group_by: str = "symbol"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate win rates grouped by specified dimension.

        Args:
            group_by: Group by 'symbol', 'day_of_week', 'indicator', etc.

        Returns:
            Dictionary of win rates by group
        """
        trades = self.trade_logger._read_trades()

        if not trades:
            return {}

        # Group trades
        groups = defaultdict(list)
        for trade in trades:
            if group_by == "symbol":
                key = trade.get("symbol", "UNKNOWN")
            elif group_by == "direction":
                key = trade.get("direction", "UNKNOWN")
            elif group_by == "day_of_week":
                ts = trade.get("timestamp", "")
                try:
                    day = datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%A")
                    key = day
                except:
                    key = "UNKNOWN"
            elif group_by == "rsi_range":
                rsi = trade.get("indicators", {}).get("rsi", 50)
                if rsi < 30:
                    key = "oversold"
                elif rsi > 70:
                    key = "overbought"
                else:
                    key = "neutral"
            else:
                key = "all"

            groups[key].append(trade)

        # Calculate statistics for each group
        results = {}
        for key, group_trades in groups.items():
            if len(group_trades) < 5:  # Minimum sample size
                continue

            wins = sum(1 for t in group_trades if t.get("pnl_pct", 0) > 0)
            total = len(group_trades)
            win_rate = wins / total

            avg_pnl = mean(t.get("pnl_pct", 0) for t in group_trades)
            avg_win = mean(t.get("pnl_pct", 0) for t in group_trades if t.get("pnl_pct", 0) > 0)
            avg_loss = mean(t.get("pnl_pct", 0) for t in group_trades if t.get("pnl_pct", 0) <= 0)

            results[key] = {
                "total_trades": total,
                "wins": wins,
                "losses": total - wins,
                "win_rate": win_rate,
                "avg_pnl": avg_pnl,
                "avg_win": avg_win if wins > 0 else 0,
                "avg_loss": avg_loss if total - wins > 0 else 0,
                "expectancy": (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss)) if total - wins > 0 else 0
            }

        return results

    def detect_regime_break(self, threshold: float = 0.2) -> List[Dict]:
        """
        Detect when a strategy's live performance diverges from backtest.

        Args:
            threshold: Minimum deviation to flag as regime break

        Returns:
            List of detected regime breaks
        """
        # This would compare live vs backtested performance
        # Simplified implementation
        return []

    def get_reliability_scores(self) -> Dict[str, float]:
        """
        Get reliability scores for each strategy/indicator combination.

        Returns:
            Dictionary of reliability scores
        """
        win_rates = self.analyze_win_rates("rsi_range")

        reliability = {}
        for condition, stats in win_rates.items():
            reliability[condition] = stats["win_rate"]

        return reliability


class RuleGenerator:
    """
    Rule generation module.

    Generates PREFER, AVOID, and CAUTION rules based on
    statistical analysis of trade history.
    """

    def __init__(
        self,
        prefer_threshold: float = 0.75,
        avoid_threshold: float = 0.35,
        min_sample_size: int = 5
    ):
        self.prefer_threshold = prefer_threshold
        self.avoid_threshold = avoid_threshold
        self.min_sample_size = min_sample_size

    def generate_rules(self, analyzer: TradeAnalyzer) -> List[StrategyRule]:
        """Generate trading rules based on analysis"""
        rules = []

        # Analyze by RSI ranges
        rsi_analysis = analyzer.analyze_win_rates("rsi_range")

        for condition, stats in rsi_analysis.items():
            if stats["total_trades"] < self.min_sample_size:
                continue

            win_rate = stats["win_rate"]

            if win_rate >= self.prefer_threshold:
                rule_type = "PREFER"
                confidence = win_rate
            elif win_rate <= self.avoid_threshold:
                rule_type = "AVOID"
                confidence = 1 - win_rate
            else:
                rule_type = "CAUTION"
                confidence = 0.5

            rule = StrategyRule(
                rule_id=f"rsi_{condition}_{datetime.utcnow().strftime('%Y%m%d')}",
                type=rule_type,
                condition=f"RSI in {condition} range",
                description=f"When RSI is {condition}, {rule_type.lower()} {stats['total_trades']} trades with {win_rate:.1%} win rate",
                win_rate=win_rate,
                sample_size=stats["total_trades"],
                confidence=confidence,
                created_at=datetime.utcnow().isoformat() + "Z"
            )
            rules.append(rule)

        # Analyze by day of week
        dow_analysis = analyzer.analyze_win_rates("day_of_week")

        for condition, stats in dow_analysis.items():
            if stats["total_trades"] < self.min_sample_size:
                continue

            win_rate = stats["win_rate"]

            if win_rate >= self.prefer_threshold:
                rule_type = "PREFER"
                confidence = win_rate
            elif win_rate <= self.avoid_threshold:
                rule_type = "AVOID"
                confidence = 1 - win_rate
            else:
                continue  # Skip caution for day of week

            rule = StrategyRule(
                rule_id=f"dow_{condition}_{datetime.utcnow().strftime('%Y%m%d')}",
                type=rule_type,
                condition=f"Day of week is {condition}",
                description=f"On {condition}s, {rule_type.lower()} trades with {win_rate:.1%} win rate over {stats['total_trades']} trades",
                win_rate=win_rate,
                sample_size=stats["total_trades"],
                confidence=confidence,
                created_at=datetime.utcnow().isoformat() + "Z"
            )
            rules.append(rule)

        return rules


class MemoryManager:
    """
    Memory management module.

    Updates MEMORY.md with learned rules and manages
    the persistent knowledge base.
    """

    def __init__(self, memory_file: str = "data/MEMORY.md"):
        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

        if not self.memory_file.exists():
            self._initialize_memory()

    def _initialize_memory(self) -> None:
        """Initialize MEMORY.md with header"""
        header = """# Financial Swarm Memory

This file contains learned trading rules and patterns from the self-improvement framework.

## Rules Format

- **PREFER**: High-confidence setups that historically perform well
- **AVOID**: Low-confidence setups that historically underperform
- **CAUTION**: Settings requiring reduced position sizes

## Generated Rules

No rules generated yet.

"""
        with open(self.memory_file, "w") as f:
            f.write(header)

    def read_memory(self) -> str:
        """Read current memory contents"""
        try:
            with open(self.memory_file) as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def update_memory(self, rules: List[StrategyRule]) -> None:
        """
        Update MEMORY.md with new rules.

        Args:
            rules: List of StrategyRule to add
        """
        if not rules:
            logger.info("No rules to update")
            return

        # Read existing memory
        content = self.read_memory()

        # Find the Rules section
        lines = content.split("\n")
        rules_start = -1

        for i, line in enumerate(lines):
            if line.startswith("## Generated Rules"):
                rules_start = i
                break

        # Build new rules section
        new_rules = []

        for rule in rules:
            emoji = "✅" if rule.type == "PREFER" else "❌" if rule.type == "AVOID" else "⚠️"
            new_rules.append(f"- **{emoji} {rule.type}**: {rule.description}")
            new_rules.append(f"  - Win Rate: {rule.win_rate:.1%}, Samples: {rule.sample_size}, Confidence: {rule.confidence:.2f}")

        # Update content
        if rules_start >= 0:
            # Find end of rules section (next ## or end)
            rules_end = len(lines)
            for i in range(rules_start + 1, len(lines)):
                if lines[i].startswith("## "):
                    rules_end = i
                    break

            # Replace rules section
            lines = lines[:rules_start + 1] + new_rules + ["", ""] + lines[rules_end:]

        content = "\n".join(lines)

        # Write updated memory
        with open(self.memory_file, "w") as f:
            f.write(content)

        logger.info(f"Memory updated with {len(rules)} rules")

    def get_rules_for_context(self) -> str:
        """
        Get relevant rules for current trading context.

        This would be called by L1 to inject into prompts.
        """
        content = self.read_memory()

        # Extract rules section
        lines = content.split("\n")
        in_rules = False
        rules = []

        for line in lines:
            if line.startswith("## Generated Rules"):
                in_rules = True
                continue
            if in_rules and line.startswith("## "):
                break
            if in_rules and line.strip():
                rules.append(line)

        return "\n".join(rules) if rules else "No learned rules."


class SelfLearningPipeline:
    """
    Complete self-learning pipeline.

    Orchestrates logging, analysis, rule generation, and memory updates.
    """

    def __init__(
        self,
        prefer_threshold: float = 0.75,
        avoid_threshold: float = 0.35,
        min_trades: int = 10
    ):
        self.trade_logger = TradeLogger()
        self.trade_analyzer = TradeAnalyzer(self.trade_logger)
        self.rule_generator = RuleGenerator(
            prefer_threshold=prefer_threshold,
            avoid_threshold=avoid_threshold
        )
        self.memory_manager = MemoryManager()
        self.min_trades = min_trades

    def log_and_analyze(self, trade_data: Dict) -> str:
        """Log a trade and return trade_id"""
        return self.trade_logger.log_trade(trade_data)

    def run_weekly_review(self) -> Dict[str, Any]:
        """
        Run weekly review and update memory.

        Returns:
            Review summary
        """
        logger.info("Running weekly review...")

        # Check if enough trades
        trades = self.trade_logger._read_trades()
        if len(trades) < self.min_trades:
            logger.info(f"Not enough trades for review: {len(trades)}/{self.min_trades}")
            return {
                "status": "skipped",
                "reason": f"Only {len(trades)} trades, need {self.min_trades}",
                "trades_analyzed": len(trades)
            }

        # Analyze
        win_rates = self.trade_analyzer.analyze_win_rates("rsi_range")
        dow_rates = self.trade_analyzer.analyze_win_rates("day_of_week")

        # Generate rules
        rules = self.rule_generator.generate_rules(self.trade_analyzer)

        # Update memory
        self.memory_manager.update_memory(rules)

        summary = {
            "status": "completed",
            "trades_analyzed": len(trades),
            "rules_generated": len(rules),
            "win_rates": win_rates,
            "dow_rates": dow_rates,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        logger.info(f"Weekly review complete: {len(rules)} rules generated")
        return summary

    def get_memory_context(self) -> str:
        """Get memory context for L1 prompts"""
        return self.memory_manager.get_rules_for_context()
