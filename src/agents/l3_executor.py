"""
L3 Executors - Stateless Workers

Specialized executors for data fetching, backtesting, and order routing.
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result from L3 executor"""
    success: bool
    order_id: Optional[str]
    execution_price: Optional[float]
    message: str
    metadata: Dict[str, Any]


@dataclass
class MarketData:
    """Market data payload"""
    symbol: str
    price: float
    volume: float
    timestamp: str
    source: str


class BaseExecutor:
    """Base class for L3 executors"""

    def __init__(self, config: Dict):
        self.config = config
        self.timeout = config.get("timeout", 30)

    def execute(self, *args, **kwargs) -> Any:
        """Execute the task"""
        pass

    def log_execution(self, task: Dict, result: Any) -> None:
        """Log execution result"""
        logger.info(f"Executor {self.__class__.__name__}: {result}")


class DataFetcher(BaseExecutor):
    """
    L3 Data Fetcher

    Retrieves raw economic data, news sentiment, and market data.
    Standardizes unstructured data into JSON formats.
    """

    def __init__(self, config: Dict):
        super().__init__(config)
        self.agent_id = "l3-data-fetcher"

    def execute(self, source: str, params: Dict) -> MarketData:
        """
        Fetch data from specified source.

        Sources:
        - yfinance: Yahoo Finance
        - ccxt: Crypto exchanges
        - news: News sentiment
        - economic: Economic calendar
        """
        logger.info(f"Fetching data from {source}: {params}")

        # Simulated data fetch
        if source == "yfinance":
            return self._fetch_yfinance(params)
        elif source == "ccxt":
            return self._fetch_ccxt(params)
        elif source == "news":
            return self._fetch_news(params)
        elif source == "economic":
            return self._fetch_economic(params)
        else:
            raise ValueError(f"Unknown source: {source}")

    def _fetch_yfinance(self, params: Dict) -> MarketData:
        """Fetch from Yahoo Finance"""
        symbol = params.get("symbol", "BTC-USD")
        period = params.get("period", "1d")

        # Simulated response
        return MarketData(
            symbol=symbol,
            price=67500.0,
            volume=25000000000,
            timestamp=datetime.utcnow().isoformat() + "Z",
            source="yfinance"
        )

    def _fetch_ccxt(self, params: Dict) -> MarketData:
        """Fetch from crypto exchange (CCXT)"""
        symbol = params.get("symbol", "BTC/USDT")
        timeframe = params.get("timeframe", "1h")

        # Simulated response
        return MarketData(
            symbol=symbol,
            price=67500.0,
            volume=35000,
            timestamp=datetime.utcnow().isoformat() + "Z",
            source="ccxt"
        )

    def _fetch_news(self, params: Dict) -> Dict:
        """Fetch news sentiment"""
        return {
            "sentiment": "bullish",
            "confidence": 0.72,
            "articles": [
                {"title": "Institutional Adoption", "sentiment": "positive"},
                {"title": "Regulatory Clarity", "sentiment": "positive"}
            ],
            "source": "news"
        }

    def _fetch_economic(self, params: Dict) -> Dict:
        """Fetch economic indicators"""
        return {
            "vix": 14.5,
            "usd_index": 104.2,
            "10y_yield": 4.25,
            "next_event": {
                "name": "CPI",
                "date": "2026-03-12",
                "expected": 3.1,
                "previous": 3.0
            },
            "source": "economic"
        }

    def fetch_historical(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d"
    ) -> List[Dict]:
        """
        Fetch historical price data.

        Returns list of OHLCV candles.
        """
        logger.info(f"Fetching historical data for {symbol}: {start_date} to {end_date}")

        # Simulated historical data
        candles = []
        base_price = 67000.0

        for i in range(30):
            candles.append({
                "timestamp": f"2026-02-{i+1:02d}T00:00:00Z",
                "open": base_price + (i * 100),
                "high": base_price + (i * 100) + 200,
                "low": base_price + (i * 100) - 200,
                "close": base_price + (i * 100) + 50,
                "volume": 25000000 + (i * 1000000)
            })

        return candles

    def to_json(self, data: MarketData) -> Dict:
        """Convert to JSON"""
        return {
            "symbol": data.symbol,
            "price": data.price,
            "volume": data.volume,
            "timestamp": data.timestamp,
            "source": data.source
        }


class Backtester(BaseExecutor):
    """
    L3 Backtester

    Executes historical simulations of trading strategies.
    Returns structured performance metrics.
    """

    def __init__(self, config: Dict):
        super().__init__(config)
        self.agent_id = "l3-backtester"
        self.max_duration = config.get("max_duration", 300)

    def execute(
        self,
        strategy: Dict,
        data: List[Dict],
        initial_capital: float = 10000.0
    ) -> Dict:
        """
        Run backtest on historical data.

        Args:
            strategy: Trading strategy parameters
            data: Historical price data (OHLCV)
            initial_capital: Starting capital

        Returns:
            Performance metrics
        """
        logger.info(f"Running backtest: {strategy.get('name', 'unnamed')}")

        # Simulated backtest results
        result = {
            "strategy_name": strategy.get("name", "unnamed"),
            "period": {
                "start": data[0]["timestamp"] if data else "unknown",
                "end": data[-1]["timestamp"] if data else "unknown"
            },
            "pnl": {
                "absolute": 1250.0,
                "percentage": 12.5,
                "winning_trades": 8,
                "losing_trades": 4
            },
            "drawdown": {
                "max_drawdown": 8.5,
                "max_drawdown_duration": 72  # hours
            },
            "risk_adjusted": {
                "sharpe_ratio": 1.85,
                "sortino_ratio": 2.15,
                "calmar_ratio": 1.47
            },
            "turnover": {
                "total_trades": 12,
                "avg_hold_time": 4.5  # hours
            },
            "reliability_flags": []
        }

        # Add reliability warnings
        if result["drawdown"]["max_drawdown"] > 10:
            result["reliability_flags"].append({
                "type": "high_drawdown",
                "message": "Max drawdown exceeds 10% threshold"
            })

        logger.info(f"Backtest complete: Sharpe {result['risk_adjusted']['sharpe_ratio']:.2f}")
        return result

    def validate_strategy(self, strategy: Dict) -> bool:
        """Validate strategy parameters"""
        required = ["entry_conditions", "exit_conditions"]

        for field in required:
            if field not in strategy:
                logger.error(f"Strategy validation failed: missing {field}")
                return False

        return True


class OrderRouter(BaseExecutor):
    """
    L3 Order Router

    Interfaces with brokerages/exchanges to execute trades.
    Translates JSON parameters into API calls.
    """

    def __init__(self, config: Dict):
        super().__init__(config)
        self.agent_id = "l3-order-router"
        self.mode = config.get("trading", {}).get("default_mode", "paper")

    def execute(
        self,
        order_params: Dict,
        broker: str = "freqtrade"
    ) -> ExecutionResult:
        """
        Execute trade order.

        Args:
            order_params: Order parameters (symbol, side, quantity, stop_loss, etc.)
            broker: Broker/exchange name

        Returns:
            Execution result with order ID
        """
        logger.info(f"Routing order to {broker}: {order_params}")

        # MANDATORY: Compliance check for stop_loss
        stop_loss = order_params.get("stop_loss")
        entry_price = order_params.get("entry_price")
        side = order_params.get("side", "buy").lower()

        if stop_loss is None:
            logger.error("Order rejected: missing mandatory stop_loss calculation.")
            raise ValueError("Compliance Error: Every order must include a calculated stop_loss.")

        if entry_price is not None:
            # Directional validation
            if side in ["buy", "long"] and stop_loss >= entry_price:
                logger.error(f"Order rejected: LONG stop_loss ({stop_loss}) must be below entry ({entry_price}).")
                raise ValueError("Compliance Error: LONG stop_loss must be strictly below entry price.")
            
            if side in ["sell", "short"] and stop_loss <= entry_price:
                logger.error(f"Order rejected: SHORT stop_loss ({stop_loss}) must be above entry ({entry_price}).")
                raise ValueError("Compliance Error: SHORT stop_loss must be strictly above entry price.")

            # Numerical validity
            if abs(entry_price - stop_loss) < 1e-8:
                logger.error(f"Order rejected: stop_loss distance from entry is too small.")
                raise ValueError("Compliance Error: stop_loss must have a non-zero distance from entry price.")

        if self.mode == "paper":
            return self._execute_paper(order_params)
        else:
            return self._execute_live(order_params, broker)

    def _execute_paper(self, order_params: Dict) -> ExecutionResult:
        """Simulate order execution (paper trading)"""
        time.sleep(0.1)  # Simulate latency

        return ExecutionResult(
            success=True,
            order_id=f"PAPER-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            execution_price=order_params.get("entry_price", 67500.0),
            message="Paper trade executed successfully",
            metadata={
                "mode": "paper",
                "slippage": 0.0
            }
        )

    def _execute_live(self, order_params: Dict, broker: str) -> ExecutionResult:
        """Execute live order via broker API"""
        # In production, this would call broker API
        logger.warning(f"Live execution not implemented for {broker}")

        return ExecutionResult(
            success=False,
            order_id=None,
            execution_price=None,
            message=f"Live execution not implemented for {broker}",
            metadata={}
        )

    def get_order_status(self, order_id: str) -> Dict:
        """Get status of existing order"""
        # Simulated status
        return {
            "order_id": order_id,
            "status": "filled",
            "filled_quantity": 0.01,
            "remaining_quantity": 0.0,
            "average_price": 67500.0
        }

    def cancel_order(self, order_id: str) -> bool:
        """Cancel pending order"""
        logger.info(f"Cancelling order: {order_id}")
        return True


class ExecutorFactory:
    """Factory for creating L3 executors"""

    @staticmethod
    def create(executor_type: str, config: Dict) -> BaseExecutor:
        """Create executor by type"""
        executors = {
            "data_fetcher": DataFetcher,
            "backtester": Backtester,
            "order_router": OrderRouter
        }

        executor_class = executors.get(executor_type)
        if not executor_class:
            raise ValueError(f"Unknown executor type: {executor_type}")

        return executor_class(config)
