import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agents.l3_executor import OrderRouter


class TestStopLossEnforcement(unittest.TestCase):

    def setUp(self):
        self.router = OrderRouter(config={"trading": {"default_mode": "paper"}})

    def test_order_router_rejects_missing_stop_loss(self):
        # Order without stop_loss should be rejected
        order_params = {
            "symbol": "BTC-USD",
            "side": "buy",
            "quantity": 1.0,
            "entry_price": 67000.0
        }
        with self.assertRaises(ValueError) as cm:
            self.router.execute(order_params)
        self.assertIn("Compliance Error: Every order must include a calculated stop_loss", str(cm.exception))

    def test_order_router_accepts_valid_stop_loss(self):
        # Order with stop_loss should be accepted in paper mode
        order_params = {
            "symbol": "BTC-USD",
            "side": "buy",
            "quantity": 1.0,
            "entry_price": 67000.0,
            "stop_loss": 65000.0
        }
        result = self.router.execute(order_params)
        self.assertTrue(result.success)
        self.assertEqual(result.execution_price, 67000.0)
        self.assertIn("PAPER-", result.order_id)

    def test_order_router_rejects_null_stop_loss(self):
        # Order with null stop_loss should be rejected
        order_params = {
            "symbol": "BTC-USD",
            "side": "buy",
            "quantity": 1.0,
            "entry_price": 67000.0,
            "stop_loss": None
        }
        with self.assertRaises(ValueError) as cm:
            self.router.execute(order_params)
        self.assertIn("Compliance Error: Every order must include a calculated stop_loss", str(cm.exception))

    def test_order_router_rejects_long_stop_loss_above_entry(self):
        # LONG order where stop_loss >= entry_price must be rejected
        order_params = {
            "symbol": "BTC-USD",
            "side": "buy",
            "quantity": 1.0,
            "entry_price": 67000.0,
            "stop_loss": 68000.0  # above entry — invalid for LONG
        }
        with self.assertRaises(ValueError) as cm:
            self.router.execute(order_params)
        self.assertIn("LONG stop_loss must be strictly below entry price", str(cm.exception))

    def test_order_router_rejects_short_stop_loss_below_entry(self):
        # SHORT order where stop_loss <= entry_price must be rejected
        order_params = {
            "symbol": "BTC-USD",
            "side": "sell",
            "quantity": 1.0,
            "entry_price": 67000.0,
            "stop_loss": 65000.0  # below entry — invalid for SHORT
        }
        with self.assertRaises(ValueError) as cm:
            self.router.execute(order_params)
        self.assertIn("SHORT stop_loss must be strictly above entry price", str(cm.exception))


class TestTradeLoggerPersistence(unittest.TestCase):
    """Tests that trade_logger_node writes stop_loss_level to the PostgreSQL trades table."""

    def _make_mock_pool(self, captured_rows: list):
        """Build a nested AsyncMock pool that captures execute() call args."""
        mock_cur = AsyncMock()
        mock_cur.__aenter__ = AsyncMock(return_value=mock_cur)
        mock_cur.__aexit__ = AsyncMock(return_value=False)
        mock_cur.fetchone = AsyncMock(return_value=None)  # no audit row

        def capture_execute(sql, params=None):
            if params:
                captured_rows.append(params)
            return AsyncMock()()

        mock_cur.execute = AsyncMock(side_effect=capture_execute)

        mock_conn = MagicMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cur)

        mock_pool = MagicMock()
        mock_pool.connection = MagicMock(return_value=mock_conn)

        return mock_pool

    def test_stop_loss_written_to_trades_table(self):
        """trade_logger_node must pass stop_loss_level to the trades INSERT."""
        from src.graph.agents.l3 import trade_logger as tl_mod

        captured: list = []
        mock_pool = self._make_mock_pool(captured)

        state = {
            "task_id": "test-task-001",
            "quant_proposal": {
                "symbol": "BTC-USD",
                "side": "buy",
                "quantity": 0.01,
                "stop_loss": 65000.0,
                "atr_at_entry": 1000.0,
                "stop_loss_multiplier": 2.0,
            },
            "execution_result": {
                "execution_price": 67000.0,
                "success": True,
                "order_id": "PAPER-TEST-001",
            },
            "execution_mode": "paper",
            "metadata": {},
        }

        with patch.object(tl_mod, "get_pool", return_value=mock_pool):
            asyncio.run(tl_mod.trade_logger_node(state))

        # Find the INSERT params tuple (the one with trade_id as first element)
        insert_params = next(
            (row for row in captured if isinstance(row, tuple) and len(row) > 5),
            None,
        )
        self.assertIsNotNone(insert_params, "No INSERT params captured — DB was not called")

        # stop_loss_level is positional index 7 in the INSERT VALUES tuple:
        # (trade_id, task_id, audit_log_id, symbol, side, quantity,
        #  execution_price, stop_loss_level, ...)
        stop_loss_level_index = 7
        self.assertEqual(
            insert_params[stop_loss_level_index],
            65000.0,
            f"stop_loss_level must be 65000.0, got {insert_params[stop_loss_level_index]}",
        )

    def test_stop_loss_none_recorded_when_not_provided(self):
        """trade_logger_node must write NULL stop_loss_level when not in proposal."""
        from src.graph.agents.l3 import trade_logger as tl_mod

        captured: list = []
        mock_pool = self._make_mock_pool(captured)

        state = {
            "task_id": "test-task-002",
            "quant_proposal": {
                "symbol": "ETH-USD",
                "side": "sell",
                "quantity": 0.1,
                # no stop_loss key
            },
            "execution_result": {
                "execution_price": 3500.0,
                "success": True,
                "order_id": "PAPER-TEST-002",
            },
            "execution_mode": "paper",
            "metadata": {},
        }

        with patch.object(tl_mod, "get_pool", return_value=mock_pool):
            asyncio.run(tl_mod.trade_logger_node(state))

        insert_params = next(
            (row for row in captured if isinstance(row, tuple) and len(row) > 5),
            None,
        )
        self.assertIsNotNone(insert_params, "No INSERT params captured — DB was not called")
        stop_loss_level_index = 7
        self.assertIsNone(
            insert_params[stop_loss_level_index],
            f"stop_loss_level must be None when not provided, got {insert_params[stop_loss_level_index]}",
        )


if __name__ == "__main__":
    unittest.main()
