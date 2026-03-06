"""OrderRouter node unit tests — stubs."""
import pytest


@pytest.mark.xfail(reason="stub — 03-03 implements OrderRouter node")
def test_order_router_paper_mode():
    """Paper mode returns dict with execution_result containing order_id."""
    from src.graph.agents.l3.order_router import order_router_node
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="stub — 03-03 implements OrderRouter node")
def test_execution_mode_routing():
    """execution_mode='paper' routes to simulated venue, 'live' routes to IB/Binance."""
    from src.graph.agents.l3.order_router import order_router_node
    pytest.fail("not implemented")
