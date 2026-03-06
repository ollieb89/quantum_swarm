"""DataFetcher node unit tests — stubs."""
import pytest


@pytest.mark.xfail(reason="stub — 03-01 implements DataFetcher node")
def test_data_fetcher_yfinance():
    from src.graph.agents.l3.data_fetcher import data_fetcher_node
    # Expect: node returns dict with data_fetcher_result containing MarketData for "AAPL"
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="stub — 03-01 implements DataFetcher node")
def test_data_fetcher_ccxt():
    from src.graph.agents.l3.data_fetcher import data_fetcher_node
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="stub — 03-01 implements DataFetcher node")
def test_data_fetcher_cache():
    """Same ticker queried twice returns same object (one API call)."""
    from src.graph.agents.l3.data_fetcher import data_fetcher_node
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="stub — 03-01 implements DataFetcher node")
def test_data_fetcher_news_sentiment():
    from src.graph.agents.l3.data_fetcher import data_fetcher_node
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="stub — 03-01 implements DataFetcher node")
def test_data_fetcher_economic():
    from src.graph.agents.l3.data_fetcher import data_fetcher_node
    pytest.fail("not implemented")
