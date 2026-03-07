"""
src.agents.rule_validator — RuleValidator: backtests proposed memory rules and
promotes or rejects them based on 2-of-3 metric improvement (Sharpe, drawdown, win rate).

Writes MiFID II-style audit events to data/audit.jsonl.
"""

import asyncio
import json
import logging
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import List

# Top-level import required so tests can patch at
# "src.agents.rule_validator._run_nautilus_backtest"
from src.graph.agents.l3.backtester import _run_nautilus_backtest  # noqa: F401
from src.core.memory_registry import MemoryRegistry
from src.models.memory import MemoryRule

logger = logging.getLogger(__name__)


class RuleValidator:
    """
    Validates proposed memory rules by running two NautilusTrader backtests per rule
    (baseline with empty strategy, treatment with rule metadata) and comparing three
    performance metrics using a 2-of-3 majority vote.

    Promotion and rejection events are written to audit.jsonl for MiFID II compliance.
    """

    def __init__(
        self,
        config_path: str = "config/swarm_config.yaml",
        registry_path: str = "data/memory_registry.json",
        audit_path: str = "data/audit.jsonl",
    ):
        self.audit_path = Path(audit_path)
        self.registry = MemoryRegistry(registry_path)

        # Load validation config from swarm_config.yaml
        cfg_file = Path(config_path)
        cfg: dict = yaml.safe_load(cfg_file.read_text()) if cfg_file.exists() else {}
        si = cfg.get("self_improvement", {})
        self.lookback_days: int = si.get("validation_lookback_days", 90)
        self.min_trades: int = si.get("validation_min_trades", 10)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_proposed_rules(self) -> int:
        """
        Run validation for all proposed rules in the registry.

        For each proposed rule:
        - Run a baseline backtest (empty strategy).
        - Run a treatment backtest (rule metadata injected into strategy).
        - If baseline total_trades < min_trades: skip (leave proposed).
        - If 2+ of 3 metrics improve: promote to active.
        - Otherwise: reject.
        - Populate rule.evidence with six metric keys.
        - Write an audit event.

        Returns the number of rules processed (skipped rules are NOT counted).
        """
        # Re-load registry to pick up rules written by persist_rules()
        self.registry.schema = self.registry._load()

        rules: List[MemoryRule] = self.registry.get_proposed_rules()
        processed = 0

        for rule in rules:
            instrument: str = rule.condition.get("instrument", "AAPL")

            # --- Run both backtests ---
            try:
                baseline = asyncio.run(
                    asyncio.to_thread(_run_nautilus_backtest, instrument, {})
                )
                treatment = asyncio.run(
                    asyncio.to_thread(
                        _run_nautilus_backtest,
                        instrument,
                        {"rule_id": rule.id, "rule_title": rule.title},
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Backtest error for rule %s — leaving proposed: %s", rule.id, exc
                )
                continue

            # --- Guard: insufficient baseline data ---
            if baseline.get("total_trades", 0) < self.min_trades:
                logger.warning(
                    "Rule %s skipped: baseline total_trades=%d < min_trades=%d",
                    rule.id,
                    baseline.get("total_trades", 0),
                    self.min_trades,
                )
                continue

            # --- Determine outcome ---
            passed = self._passes_validation(baseline, treatment)
            outcome = "active" if passed else "rejected"

            # --- Update registry status ---
            self.registry.update_status(rule.id, outcome)

            # --- Populate evidence on the live rule object ---
            live_rule = self.registry.get_rule(rule.id)
            if live_rule is not None:
                live_rule.evidence = {
                    "baseline_sharpe": baseline["sharpe_ratio"],
                    "treatment_sharpe": treatment["sharpe_ratio"],
                    "baseline_drawdown": baseline["max_drawdown"],
                    "treatment_drawdown": treatment["max_drawdown"],
                    "baseline_win_rate": baseline["win_rate"],
                    "treatment_win_rate": treatment["win_rate"],
                }
                self.registry.save()

            # --- Write audit event ---
            self._write_audit(rule.id, outcome, baseline, treatment)

            processed += 1

        return processed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _passes_validation(self, baseline: dict, treatment: dict) -> bool:
        """Return True when treatment improves >= 2 of 3 metrics vs baseline."""
        improvements = 0
        if treatment["sharpe_ratio"] > baseline["sharpe_ratio"]:
            improvements += 1
        # max_drawdown is non-positive; less negative = better improvement
        if treatment["max_drawdown"] > baseline["max_drawdown"]:
            improvements += 1
        if treatment["win_rate"] > baseline["win_rate"]:
            improvements += 1
        return improvements >= 2

    def _write_audit(
        self, rule_id: str, outcome: str, baseline: dict, treatment: dict
    ) -> None:
        """Append a MiFID II audit event JSON line to self.audit_path."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "rule_validation",
            "rule_id": rule_id,
            "before_status": "proposed",
            "after_status": outcome,
            "baseline_sharpe": baseline["sharpe_ratio"],
            "treatment_sharpe": treatment["sharpe_ratio"],
            "sharpe_delta": treatment["sharpe_ratio"] - baseline["sharpe_ratio"],
            "baseline_drawdown": baseline["max_drawdown"],
            "treatment_drawdown": treatment["max_drawdown"],
            "drawdown_delta": treatment["max_drawdown"] - baseline["max_drawdown"],
            "baseline_win_rate": baseline["win_rate"],
            "treatment_win_rate": treatment["win_rate"],
            "win_rate_delta": treatment["win_rate"] - baseline["win_rate"],
        }
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.audit_path, "a") as f:
            f.write(json.dumps(event) + "\n")
