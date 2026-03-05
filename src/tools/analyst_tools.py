"""
Analyst Tools — LangChain-compatible tool wrappers for L3 executor capabilities.

These tools expose L3 executor functionality (DataFetcher, Backtester) as
@tool-decorated functions that LangGraph ReAct agents can discover and call.

Each tool returns a plain dict so the LLM can reason over the result directly.
"""

import logging
from typing import Any

from langchain_core.tools import tool

from src.agents.l3_executor import DataFetcher, Backtester

logger = logging.getLogger(__name__)

# Shared singleton instances with a minimal config (no external connections needed
# for the simulated data layer used in phase 2 development).
_data_fetcher = DataFetcher(config={"timeout": 30})
_backtester = Backtester(config={"timeout": 30, "max_duration": 300})


@tool
def fetch_market_data(symbol: str, timeframe: str) -> dict[str, Any]:
    """Fetch current market data for a given symbol and timeframe.

    Use this tool to retrieve price, volume, and timestamp information for any
    tradeable asset. Delegates to the DataFetcher L3 executor.

    Args:
        symbol: Ticker symbol to look up, e.g. "BTC-USD", "ETH-USD", "SPY".
        timeframe: Candle interval, e.g. "1h", "4h", "1d".

    Returns:
        A dict containing:
          - symbol (str): The requested ticker.
          - price (float): Current or last-close price.
          - volume (float): 24-hour trading volume.
          - timestamp (str): ISO-8601 UTC timestamp.
          - source (str): Data source identifier.
    """
    logger.info("fetch_market_data called: symbol=%s timeframe=%s", symbol, timeframe)

    market_data = _data_fetcher.execute(
        source="yfinance",
        params={"symbol": symbol, "period": timeframe},
    )

    return _data_fetcher.to_json(market_data)


@tool
def run_backtest(strategy: str, params: dict[str, Any]) -> dict[str, Any]:
    """Run a historical backtest for a named trading strategy.

    Use this tool to evaluate strategy performance using simulated historical data.
    Delegates to the Backtester L3 executor.

    Args:
        strategy: Human-readable strategy name, e.g. "RSI_Reversal", "MACD_Crossover".
        params: Additional strategy parameters, e.g.::

            {
                "entry_conditions": ["rsi < 30"],
                "exit_conditions": ["rsi > 70"],
                "initial_capital": 10000
            }

    Returns:
        A dict containing:
          - strategy_name (str): Strategy identifier.
          - period (dict): Backtest start/end timestamps.
          - pnl (dict): Profit/loss metrics (absolute, percentage, win/loss counts).
          - drawdown (dict): Max drawdown percentage and duration.
          - risk_adjusted (dict): Sharpe, Sortino, and Calmar ratios.
          - turnover (dict): Trade count and average hold time.
          - reliability_flags (list): Any risk warnings raised.
    """
    logger.info("run_backtest called: strategy=%s params=%s", strategy, params)

    # Build a minimal strategy dict the Backtester expects
    strategy_dict = {
        "name": strategy,
        "entry_conditions": params.get("entry_conditions", ["default_entry"]),
        "exit_conditions": params.get("exit_conditions", ["default_exit"]),
    }

    # Use the DataFetcher to produce representative historical data
    historical_data = _data_fetcher.fetch_historical(
        symbol=params.get("symbol", "BTC-USD"),
        start_date="2026-01-01",
        end_date="2026-03-01",
        interval="1d",
    )

    result = _backtester.execute(
        strategy=strategy_dict,
        data=historical_data,
        initial_capital=float(params.get("initial_capital", 10000.0)),
    )

    return result


@tool
def fetch_economic_data(indicator: str, region: str) -> dict[str, Any]:
    """Fetch macroeconomic indicator data for a given region.

    Use this tool to retrieve economic environment metrics such as VIX, USD
    index, 10-year bond yields, and upcoming calendar events. Delegates to the
    DataFetcher L3 executor.

    Args:
        indicator: Name of the economic indicator, e.g. "VIX", "USD_INDEX",
            "10Y_YIELD", "CPI", "NFP".
        region: Geographic region, e.g. "US", "EU", "JP", "GLOBAL".

    Returns:
        A dict containing:
          - vix (float): CBOE Volatility Index level.
          - usd_index (float): DXY US Dollar index.
          - 10y_yield (float): US 10-year Treasury yield.
          - next_event (dict): Upcoming high-impact economic event.
          - source (str): Data source identifier.
    """
    logger.info(
        "fetch_economic_data called: indicator=%s region=%s", indicator, region
    )

    result = _data_fetcher.execute(
        source="economic",
        params={"indicator": indicator, "region": region},
    )

    return result
