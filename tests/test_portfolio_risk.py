import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from src.security.institutional_guard import InstitutionalGuard

class TestPortfolioRisk(unittest.TestCase):

    def setUp(self):
        self.config = {
            "risk_limits": {
                "starting_capital": 1000000.0,
                "max_notional_exposure": 500000.0,
                "max_asset_concentration_pct": 0.20,
                "max_concurrent_trades": 3,
                "max_daily_loss": 0.05,
                "max_drawdown": 0.15,
            }
        }
        self.guard = InstitutionalGuard(self.config)

    async def _async_test_exposure_rejection(self):
        # Mock 2 open positions totaling 400k
        open_positions = [
            {"symbol": "BTC-USD", "quantity": 2.0, "price": 100000.0},
            {"symbol": "ETH-USD", "quantity": 10.0, "price": 20000.0}
        ]
        
        with patch.object(InstitutionalGuard, "_get_open_positions", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = open_positions
            
            # New order for 200k (Total 600k > 500k limit)
            state = {
                "quant_proposal": {
                    "symbol": "SOL-USD",
                    "entry_price": 100.0,
                    "quantity": 2000.0
                }
            }
            result = await self.guard.check_compliance(state)
            self.assertFalse(result["approved"])
            self.assertIn("exceeds max notional exposure", result["violation"])

    def test_exposure_rejection(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._async_test_exposure_rejection())

    async def _async_test_concentration_rejection(self):
        # Mock 1 open position 150k in BTC
        open_positions = [
            {"symbol": "BTC-USD", "quantity": 1.5, "price": 100000.0}
        ]
        
        with patch.object(InstitutionalGuard, "_get_open_positions", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = open_positions
            
            # New order for 100k in BTC (Total 250k > 200k limit for 1M capital)
            state = {
                "quant_proposal": {
                    "symbol": "BTC-USD",
                    "entry_price": 100000.0,
                    "quantity": 1.0
                }
            }
            result = await self.guard.check_compliance(state)
            self.assertFalse(result["approved"])
            self.assertIn("Concentration limit for BTC-USD exceeded", result["violation"])

    def test_concentration_rejection(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._async_test_concentration_rejection())

    def test_risk_scoring_logic(self):
        proposal = {
            "entry_price": 100.0,
            "stop_loss": 95.0, # 5% move
            "confidence": 0.8
        }
        # Heat = 0.5
        score = self.guard.calculate_risk_score(proposal, 0.5)

        # dist_score = 0.05 / 0.1 = 0.5
        # conf_score = 1.0 - 0.8 = 0.2
        # heat_score = 0.5
        # Weighted: (0.5 * 0.4) + (0.2 * 0.3) + (0.5 * 0.3) = 0.2 + 0.06 + 0.15 = 0.41
        self.assertEqual(score, 0.41)

    async def _async_test_drawdown_rejection(self):
        state = {
            "quant_proposal": {
                "symbol": "BTC/USDT",
                "entry_price": 50000.0,
                "quantity": 1.0,
                "stop_loss": 47500.0,
                "confidence": 0.8,
            }
        }
        with patch.object(InstitutionalGuard, "_get_open_positions",
                          new_callable=AsyncMock, return_value=[]):
            result = await self.guard.check_compliance(state)
        # RED: drawdown check not implemented; currently returns approved=True
        self.assertFalse(result["approved"], "drawdown circuit breaker not implemented")
        self.assertIn("drawdown", result.get("violation", "").lower())

    def test_drawdown_rejection(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._async_test_drawdown_rejection())

if __name__ == "__main__":
    unittest.main()
