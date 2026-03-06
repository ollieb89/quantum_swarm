"""L3 integration tests — stubs."""
import pytest


@pytest.mark.xfail(reason="stub — 03-04 wires orchestrator end-to-end")
def test_feedback_loop_l2_receives_trade_history():
    """L2 BullishResearcher receives trade_history in state on second invocation."""
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="stub — 03-04 wires orchestrator end-to-end")
def test_end_to_end_paper_graph():
    """Full graph: data_fetcher -> debate -> risk -> order_router -> trade_logger completes."""
    pytest.fail("not implemented")
