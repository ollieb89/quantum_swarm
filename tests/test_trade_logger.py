"""TradeLogger node unit tests — stubs."""
import pytest


@pytest.mark.xfail(reason="stub — 03-04 implements TradeLogger node")
def test_trade_logger_appends_record():
    """trade_logger_node appends one TradeRecord dict to trade_history."""
    from src.graph.agents.l3.trade_logger import trade_logger_node
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="stub — 03-04 implements TradeLogger node")
def test_trade_history_window_enforced():
    """trade_history[-15:] slice enforces N=15 window in L2 agent read."""
    pytest.fail("not implemented")
