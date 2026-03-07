import unittest
from src.skills.quant_alpha_intelligence import TechnicalIndicators, handle
from src.skills.registry import SkillRegistry

class TestQuantAlphaIntelligence(unittest.TestCase):

    def setUp(self):
        self.calculator = TechnicalIndicators()
        # Sample price data (20 points)
        self.prices = [
            100.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0, 108.0, 107.0, 109.0,
            111.0, 110.0, 112.0, 114.0, 113.0, 115.0, 117.0, 116.0, 118.0, 120.0
        ]
        self.highs = [p + 1.0 for p in self.prices]
        self.lows = [p - 1.0 for p in self.prices]
        self.closes = self.prices

    def test_rsi_calculation(self):
        # RSI(14)
        rsi = self.calculator.rsi(self.prices, period=14)
        self.assertIsInstance(rsi, float)
        self.assertTrue(0 <= rsi <= 100)
        
        # Test full series
        rsi_full = self.calculator.rsi(self.prices, period=14, full=True)
        self.assertIsInstance(rsi_full, list)
        self.assertEqual(len(rsi_full), len(self.prices) - 14)

    def test_rsi_constant_series(self):
        # Constant prices should yield neutral RSI (50.0)
        constant_prices = [100.0] * 20
        rsi = self.calculator.rsi(constant_prices, period=14)
        self.assertEqual(rsi, 50.0)

    def test_macd_calculation(self):
        macd = self.calculator.macd(self.prices, fast=5, slow=10, signal=3)
        self.assertIsInstance(macd, dict)
        self.assertIn("macd", macd)
        self.assertIn("signal", macd)
        self.assertIn("histogram", macd)

    def test_bollinger_bands_with_bandwidth(self):
        bb = self.calculator.bollinger_bands(self.prices, period=10)
        self.assertIsInstance(bb, dict)
        self.assertIn("upper", bb)
        self.assertIn("middle", bb)
        self.assertIn("lower", bb)
        self.assertIn("bandwidth", bb)
        self.assertTrue(bb["upper"] > bb["middle"] > bb["lower"])
        self.assertTrue(bb["bandwidth"] > 0)

    def test_atr_dependency_validation(self):
        # ATR requires high, low, close
        with self.assertRaises(ValueError) as cm:
            self.calculator.atr(highs=[], lows=[], closes=[], period=10)
        self.assertIn("requires 'high', 'low', and 'close'", str(cm.exception))

    def test_atr_calculation(self):
        atr = self.calculator.atr(self.highs, self.lows, self.closes, period=10)
        self.assertIsInstance(atr, float)
        self.assertTrue(atr > 0)

    def test_safe_range_validation(self):
        state = {
            "series": {"close": self.prices},
            "indicators": [{"name": "rsi", "params": {"period": 300}}]
        }
        result = handle(state)
        self.assertEqual(result["results"]["rsi"]["error"]["code"], "INVALID_PARAMETER")
        self.assertIn("safe range", result["results"]["rsi"]["error"]["message"])

    def test_insufficient_data(self):
        state = {
            "series": {"close": [100.0, 101.0]},
            "indicators": [{"name": "rsi", "params": {"period": 14}}]
        }
        result = handle(state)
        self.assertEqual(result["results"]["rsi"]["error"]["code"], "INVALID_PARAMETER")
        self.assertIn("requires at least", result["results"]["rsi"]["error"]["message"])

    def test_skill_registry_discovery(self):
        registry = SkillRegistry()
        registry.discover()
        self.assertIn("quant-alpha-intelligence", registry.intents)

    # --- TDD RED: Task 1 new behavior tests ---

    def test_rsi_state_annotation(self):
        """handle() RSI result is a dict with 'value' and 'state' keys at key 'rsi_14'."""
        state = {
            "series": {"close": self.prices},
            "indicators": [{"name": "rsi", "params": {"period": 14}}]
        }
        result = handle(state)
        rsi_result = result["results"]["rsi_14"]
        self.assertIn("value", rsi_result)
        self.assertIn("state", rsi_result)
        self.assertIsInstance(rsi_result["value"], float)
        self.assertIn(rsi_result["state"], {"overbought", "oversold", "neutral"})

    def test_insufficient_data_error_code(self):
        """Too-short series returns INSUFFICIENT_DATA, not INVALID_PARAMETER."""
        state = {
            "series": {"close": [100.0, 101.0]},
            "indicators": [{"name": "rsi", "params": {"period": 14}}]
        }
        result = handle(state)
        self.assertEqual(result["results"]["rsi_14"]["error"]["code"], "INSUFFICIENT_DATA")

    def test_multi_instance_rsi(self):
        """Two RSI requests with different periods produce separate keys rsi_14 and rsi_28."""
        prices_30 = [float(100 + i) for i in range(30)]
        state = {
            "series": {"close": prices_30},
            "indicators": [
                {"name": "rsi", "params": {"period": 14}},
                {"name": "rsi", "params": {"period": 28}},
            ]
        }
        result = handle(state)
        self.assertIn("rsi_14", result["results"])
        self.assertIn("rsi_28", result["results"])
        self.assertIn("value", result["results"]["rsi_14"])
        self.assertIn("value", result["results"]["rsi_28"])

if __name__ == "__main__":
    unittest.main()
