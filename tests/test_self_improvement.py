import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
from src.agents.l3_executor import OrderRouter
from src.agents.review_agent import PerformanceReviewAgent
from src.agents.rule_generator import RuleGenerator
from src.graph.orchestrator import LangGraphOrchestrator

class TestSelfImprovement(unittest.TestCase):

    def setUp(self):
        self.router = OrderRouter(config={"trading": {"default_mode": "paper"}})

    def test_order_router_directional_validation(self):
        # LONG with stop > entry (Invalid)
        order_params_long = {
            "symbol": "BTC-USD",
            "side": "buy",
            "entry_price": 60000.0,
            "stop_loss": 61000.0
        }
        with self.assertRaises(ValueError) as cm:
            self.router.execute(order_params_long)
        self.assertIn("LONG stop_loss must be strictly below entry price", str(cm.exception))

        # SHORT with stop < entry (Invalid)
        order_params_short = {
            "symbol": "BTC-USD",
            "side": "sell",
            "entry_price": 60000.0,
            "stop_loss": 59000.0
        }
        with self.assertRaises(ValueError) as cm:
            self.router.execute(order_params_short)
        self.assertIn("SHORT stop_loss must be strictly above entry price", str(cm.exception))

    async def _async_test_review_agent_data_fetch(self):
        # We patch the DB call internally or the whole method
        with patch("src.agents.review_agent.PerformanceReviewAgent.get_recent_trade_data", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [
                {"trade_id": "t1", "symbol": "BTC-USD", "side": "buy", "quantity": 1.0, "execution_price": 60000.0, "stop_loss": 58000.0, "pnl": 100.0, "pnl_pct": 1.6, "strategy_context": {"backtest_result": {}}, "macro_report": {"phase": "bullish"}, "rationale": "long rationale"}
            ]
            agent = PerformanceReviewAgent()
            trades = await agent.get_recent_trade_data(days=7)
            self.assertEqual(len(trades), 1)
            self.assertEqual(trades[0]["symbol"], "BTC-USD")

    def test_review_agent_data_fetch(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._async_test_review_agent_data_fetch())

    def test_rule_generator_logic(self):
        # Mock LLM response with valid JSON list of MemoryRule-compatible objects
        import json
        mock_rules_json = json.dumps([
            {
                "title": "Prefer Longs in Bullish Regime",
                "type": "strategy_preference",
                "condition": {"regime": "bullish"},
                "action": {"bias": "long"},
                "evidence": {"win_rate": 0.72}
            },
            {
                "title": "Avoid Shorts in Bullish Regime",
                "type": "strategy_preference",
                "condition": {"regime": "bullish"},
                "action": {"bias": "avoid_short"},
                "evidence": {"loss_rate": 0.65}
            }
        ])
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content=mock_rules_json))

        generator = RuleGenerator()
        generator.llm = mock_llm

        loop = asyncio.new_event_loop()
        rules = loop.run_until_complete(generator.generate_rules({"status": "ok"}))

        self.assertEqual(len(rules), 2)
        # Rules are MemoryRule instances with structured fields
        self.assertEqual(rules[0].title, "Prefer Longs in Bullish Regime")
        self.assertEqual(rules[0].type, "strategy_preference")
        self.assertEqual(rules[1].title, "Avoid Shorts in Bullish Regime")

    def test_orchestrator_memory_loading(self):
        # Create a temp memory file
        memory_path = Path("data/MEMORY.md")
        original_content = ""
        if memory_path.exists():
            original_content = memory_path.read_text()
        
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        memory_path.write_text("# Memory\n\n## Generated Rules\n- PREFER: Logic A\n- AVOID: Logic B")
        
        orchestrator = LangGraphOrchestrator({})
        memory = orchestrator._load_institutional_memory()
        
        self.assertIn("PREFER: Logic A", memory)
        self.assertIn("AVOID: Logic B", memory)
        
        # Cleanup
        if original_content:
            memory_path.write_text(original_content)
        else:
            memory_path.unlink()

if __name__ == "__main__":
    unittest.main()
