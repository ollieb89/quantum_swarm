"""Backtester node unit tests — stubs."""
import pytest


@pytest.mark.xfail(reason="stub — 03-02 implements Backtester node")
def test_backtester_node_returns_sharpe():
    """backtester_node returns dict with sharpe_ratio key."""
    from src.graph.agents.l3.backtester import backtester_node
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="stub — 03-02 implements Backtester node")
def test_bar_data_wrangler_processes_dataframe():
    """BarDataWrangler.process(df) returns non-empty list of Bar objects."""
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="stub — 03-02 implements Backtester node")
def test_backtester_result_is_json_serializable():
    """BacktestEngine result dict is JSON-serializable (no NT internal objects)."""
    from src.graph.agents.l3.backtester import backtester_node
    pytest.fail("not implemented")
