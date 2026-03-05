"""
Quantum Swarm - Main Entry Point

Multi-Agent Trading System
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.cli_wrapper import OpenClawCLI, FileProtocol
from src.graph.orchestrator import LangGraphOrchestrator
from src.agents import MacroAnalyst, QuantModeler, RiskManager
from src.agents.l3_executor import DataFetcher, Backtester, OrderRouter
from src.skills.crypto_learning import SelfLearningPipeline


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class QuantumSwarm:
    """Main orchestrator for the Quantum Swarm"""

    def __init__(self, config_path: str = "config/swarm_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

        # Initialize components
        self.cli = OpenClawCLI(self.config.get("openclaw", {}))
        self.protocol = FileProtocol(
            inbox_dir=self.config.get("file_protocol", {}).get("inbox_dir", "data/inbox"),
            outbox_dir=self.config.get("file_protocol", {}).get("outbox_dir", "data/outbox"),
            comms_dir=self.config.get("file_protocol", {}).get("comms_dir", "data/inter_agent_comms")
        )

        self.orchestrator = LangGraphOrchestrator(self.config)

        # L2 Agents
        self.macro_analyst = MacroAnalyst(self.config)
        self.quant_modeler = QuantModeler(self.config)
        self.risk_manager = RiskManager(self.config)

        # L3 Executors
        self.data_fetcher = DataFetcher(self.config)
        self.backtester = Backtester(self.config)
        self.order_router = OrderRouter(self.config)

        # Self-learning
        self.self_learning = SelfLearningPipeline(
            prefer_threshold=self.config.get("self_improvement", {}).get("prefer_threshold", 0.75),
            avoid_threshold=self.config.get("self_improvement", {}).get("avoid_threshold", 0.35),
            min_trades=self.config.get("self_improvement", {}).get("min_trades_for_analysis", 10)
        )

    def _load_config(self) -> Dict:
        """Load configuration from YAML file"""
        try:
            import yaml
            with open(self.config_path) as f:
                return yaml.safe_load(f)
        except ImportError:
            # Fallback to JSON
            with open(self.config_path.replace(".yaml", ".json")) as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {self.config_path} not found, using defaults")
            return {}

    def check_gateway(self) -> bool:
        """Check if OpenClaw gateway is running"""
        try:
            result = self.cli.health_check()
            logger.info(f"Gateway health: {result}")
            return result.get("status") == "healthy"
        except Exception as e:
            logger.error(f"Gateway check failed: {e}")
            return False

    def run_task(self, user_input: str) -> Dict:
        """Process user task through the swarm"""
        logger.info(f"Processing task: {user_input}")

        # Run through orchestrator
        try:
            decision = self.orchestrator.run_task(user_input)
            return decision.to_dict()
        except Exception as e:
            logger.error(f"Task failed: {e}")
            return {
                "error": str(e),
                "task_id": None,
                "decision": "ERROR"
            }

    def run_macro_analysis(self, symbols: list = None) -> Dict:
        """Run macro analysis"""
        logger.info("Running macro analysis")
        report = self.macro_analyst.analyze(symbols)
        return self.macro_analyst.to_json(report)

    def run_quant_analysis(self, symbol: str, timeframe: str = "1H") -> Dict:
        """Run quant analysis"""
        logger.info(f"Running quant analysis for {symbol}")
        proposal = self.quant_modeler.analyze(symbol, timeframe)
        return self.quant_modeler.to_json(proposal)

    def validate_trade(self, proposal: Dict) -> Dict:
        """Validate trade with risk manager"""
        from src.agents import TradeProposal

        trade_proposal = TradeProposal(
            symbol=proposal.get("symbol", "BTC/USDT"),
            direction=proposal.get("direction", "LONG"),
            entry_price=proposal.get("entry_price", 67500),
            stop_loss=proposal.get("stop_loss", 66500),
            take_profit=proposal.get("take_profit", 69500),
            position_size=proposal.get("position_size", 0.05),
            confidence=proposal.get("confidence", 0.8),
            indicators=proposal.get("indicators", {}),
            rationale=proposal.get("rationale", "")
        )

        approval = self.risk_manager.validate(trade_proposal)
        return self.risk_manager.to_json(approval)

    def execute_trade(self, order_params: Dict) -> Dict:
        """Execute trade through order router"""
        logger.info(f"Executing trade: {order_params}")
        result = self.order_router.execute(order_params)

        return {
            "success": result.success,
            "order_id": result.order_id,
            "execution_price": result.execution_price,
            "message": result.message
        }

    def run_weekly_review(self) -> Dict:
        """Run weekly self-improvement review"""
        logger.info("Running weekly review")
        return self.self_learning.run_weekly_review()

    def log_trade(self, trade_data: Dict) -> str:
        """Log trade for self-learning"""
        return self.self_learning.log_and_analyze(trade_data)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="OpenClaw Financial Swarm")
    parser.add_argument("--config", default="config/swarm_config.yaml", help="Config file path")
    parser.add_argument("--mode", choices=["interactive", "daemon", "test"], default="interactive")
    parser.add_argument("--task", help="Single task to execute")

    args = parser.parse_args()

    # Initialize swarm
    swarm = QuantumSwarm(args.config)

    if args.mode == "test":
        # Run tests
        logger.info("Running in test mode")

        # Test gateway connection
        if swarm.check_gateway():
            logger.info("✓ Gateway connection successful")
        else:
            logger.warning("⚠ Gateway not running (this is OK for local testing)")

        # Test agents
        logger.info("Testing L2 agents...")
        macro_report = swarm.run_macro_analysis()
        logger.info(f"✓ Macro analysis: {macro_report.get('phase', 'unknown')}")

        quant_proposal = swarm.run_quant_analysis("BTC/USDT")
        logger.info(f"✓ Quant proposal: {quant_proposal.get('signal', 'unknown')}")

        # Test risk validation
        approval = swarm.validate_trade(quant_proposal)
        logger.info(f"✓ Risk approval: {approval.get('approved', False)}")

        logger.info("All tests passed!")
        return

    if args.task:
        # Execute single task
        result = swarm.run_task(args.task)
        print(json.dumps(result, indent=2))
        return

    if args.mode == "interactive":
        # Interactive mode
        print("=" * 50)
        print("OpenClaw Financial Swarm - Interactive Mode")
        print("=" * 50)
        print("\nCommands:")
        print("  analyze <symbol>  - Run analysis on symbol")
        print("  trade <symbol>   - Analyze and propose trade")
        print("  review            - Run weekly review")
        print("  status            - Show swarm status")
        print("  quit              - Exit")
        print()

        while True:
            try:
                user_input = input("> ").strip()

                if not user_input:
                    continue

                if user_input.lower() == "quit":
                    break

                if user_input.lower() == "status":
                    print(f"Gateway: {'Online' if swarm.check_gateway() else 'Offline'}")
                    print(f"Mode: {swarm.config.get('trading', {}).get('default_mode', 'paper')}")
                    continue

                if user_input.lower() == "review":
                    result = swarm.run_weekly_review()
                    print(json.dumps(result, indent=2))
                    continue

                # Parse command
                parts = user_input.split()
                command = parts[0].lower()

                if command == "analyze" and len(parts) > 1:
                    symbol = parts[1]
                    result = swarm.run_quant_analysis(symbol)
                    print(json.dumps(result, indent=2))

                elif command == "trade" and len(parts) > 1:
                    symbol = parts[1]
                    # Run full analysis
                    quant = swarm.run_quant_analysis(symbol)
                    approval = swarm.validate_trade(quant)
                    print(json.dumps(approval, indent=2))

                else:
                    # Treat as general task
                    result = swarm.run_task(user_input)
                    print(json.dumps(result, indent=2))

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error: {e}")

        print("\nGoodbye!")
        return

    if args.mode == "daemon":
        # Daemon mode - would run cron jobs, monitor inbox, etc.
        logger.info("Running in daemon mode...")
        logger.info("Press Ctrl+C to stop")

        try:
            import time
            while True:
                # Check for new tasks in inbox
                tasks = swarm.protocol.get_pending_tasks()

                for task in tasks:
                    logger.info(f"Processing task: {task.get('task_id')}")
                    result = swarm.run_task(task.get("original_input", ""))
                    logger.info(f"Result: {result.get('decision')}")

                time.sleep(10)

        except KeyboardInterrupt:
            logger.info("Daemon stopped")


if __name__ == "__main__":
    main()
