"""
src.graph.agents.l3.order_router — NautilusTrader-backed OrderRouter LangGraph node.

Exports:
    order_router_node(state: SwarmState) -> dict    async LangGraph node

Dispatches order execution based on execution_mode and asset_class from SwarmState:
  - "paper"                            → SimulatedExchange (NautilusTrader paper fill)
  - "live" + asset_class="equity"      → Interactive Brokers adapter
  - "live" + asset_class in            → Binance adapter
    ("crypto", "futures")

Live mode is safely gated:
  - IB: TCP reachability check before connecting (fails gracefully if TWS/Gateway not running)
  - Binance: env var presence check (fails gracefully if keys not set)

All returned dicts contain only JSON-serializable Python primitives (str, float, int, bool, None).
No NautilusTrader objects ever appear in SwarmState.

State reads:
    state["execution_mode"]   "paper" | "live"
    state["risk_approved"]    bool — must be True to execute
    state["quant_proposal"]   dict: symbol, side, quantity, asset_class

State writes:
    "execution_result"  dict — order_id, execution_price, mode, success, [error]
    "messages"          list — one assistant message entry

ANTI-PATTERNS AVOIDED:
    - NEVER block the LangGraph event loop with synchronous calls
    - NEVER store NautilusTrader objects in SwarmState
    - NEVER call asyncio.run() inside an async node
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Any

from src.graph.state import SwarmState
from src.core.parsing import parse_quant_proposal
from src.agents.l3_executor import OrderRouter as Executor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public LangGraph async node
# ---------------------------------------------------------------------------

async def order_router_node(state: SwarmState) -> dict[str, Any]:
    """L3 OrderRouter — route order execution based on execution_mode and asset_class.

    Returns a partial state update dict with ``execution_result`` and ``messages`` keys.
    All values in execution_result are JSON-serializable Python primitives.

    Args:
        state: Current SwarmState shared across the LangGraph graph.

    Returns:
        Partial state update dict with ``execution_result`` and ``messages`` keys.
    """
    # ------------------------------------------------------------------
    # 1. Risk gate — halt immediately if risk not approved
    # ------------------------------------------------------------------
    risk_approved: bool = state.get("risk_approved", False)
    if not risk_approved:
        logger.warning("OrderRouter: risk_approved=False — order rejected")
        return {
            "execution_result": {
                "success": False,
                "order_id": None,
                "reason": "risk_not_approved",
                "failure_cause": "RISK_RULE_VIOLATION",
                "mode": state.get("execution_mode", "paper"),
            },
            "messages": [
                {
                    "role": "assistant",
                    "content": "OrderRouter: order rejected — risk_approved=False",
                }
            ],
        }

    # ------------------------------------------------------------------
    # 2. Extract order parameters from quant_proposal
    # ------------------------------------------------------------------
    execution_mode: str = state.get("execution_mode", "paper")
    quant_parsed = parse_quant_proposal(state)
    symbol: str = quant_parsed.get("symbol", "BTC-USD")
    side: str = quant_parsed.get("side", "buy")
    quantity: float = float(quant_parsed.get("quantity", 1.0))
    asset_class: str = quant_parsed.get("asset_class", "crypto" if "BTC" in symbol or "ETH" in symbol else "equity")
    
    # Required for executor compliance checks
    order_params = {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "asset_class": asset_class,
        "entry_price": quant_parsed.get("entry_price"),
        "stop_loss": quant_parsed.get("stop_loss"),
    }

    logger.info(
        "OrderRouter: mode=%s symbol=%s side=%s qty=%.2f asset_class=%s",
        execution_mode,
        symbol,
        side,
        quantity,
        asset_class,
    )

    # ------------------------------------------------------------------
    # 3. Dispatch to appropriate execution path via Executor
    # ------------------------------------------------------------------
    executor = Executor(config={"trading": {"default_mode": execution_mode}})
    
    try:
        # Delegate to the hardened executor which now handles compliance rejections
        result_obj = executor.execute(order_params)
        result = {
            "success": result_obj.success,
            "order_id": result_obj.order_id,
            "execution_price": result_obj.execution_price,
            "mode": execution_mode,
            "message": result_obj.message,
            "metadata": result_obj.metadata,
            "failure_cause": None,
        }
    except ValueError as compliance_err:
        # MANDATORY: Capture compliance rejections (stop-loss errors) in audit logs
        logger.error("OrderRouter Compliance Rejection: %s", compliance_err)
        result = {
            "success": False,
            "order_id": None,
            "reason": "compliance_rejection",
            "error": str(compliance_err),
            "failure_cause": "RISK_RULE_VIOLATION",
            "mode": execution_mode,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("OrderRouter unhandled error for %s: %s", symbol, exc)
        result = {
            "success": False,
            "order_id": None,
            "reason": "execution_failure",
            "error": str(exc),
            "failure_cause": "EXECUTION_FAILURE",
            "mode": execution_mode,
        }

    logger.info(
        "OrderRouter complete for %s — success=%s order_id=%s",
        symbol,
        result.get("success"),
        result.get("order_id"),
    )

    # ------------------------------------------------------------------
    # 4. Return partial state update
    # ------------------------------------------------------------------
    return {
        "execution_result": result,
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"OrderRouter: {symbol} {side} x{quantity} via {execution_mode} "
                    f"— success={result.get('success')} | reason={result.get('reason', 'ok')}"
                ),
            }
        ],
    }


# ---------------------------------------------------------------------------
# Paper execution — SimulatedExchange fill (no external dependencies)
# ---------------------------------------------------------------------------

async def _execute_paper(symbol: str, side: str, quantity: float) -> dict:
    """Execute order in paper mode using simulated fill with yfinance last price.

    Uses asyncio.to_thread to fetch the last price from yfinance without
    blocking the event loop.  Applies 0.01% simulated slippage.

    Args:
        symbol:   Ticker symbol, e.g. "AAPL".
        side:     "buy" or "sell".
        quantity: Number of shares/units.

    Returns:
        dict with success=True, PAPER- prefixed order_id, execution_price,
        mode="paper", slippage_pct=0.01.
    """
    try:
        last_price: float = await asyncio.to_thread(_fetch_last_price, symbol)
    except Exception as exc:  # noqa: BLE001
        logger.warning("OrderRouter paper: yfinance price fetch failed for %s: %s — using 100.0", symbol, exc)
        last_price = 100.0

    # Simulate slippage: buy fills slightly above last, sell slightly below
    slippage_pct = 0.01
    if side.lower() == "buy":
        execution_price = last_price * (1 + slippage_pct / 100)
    else:
        execution_price = last_price * (1 - slippage_pct / 100)

    order_id = f"PAPER-{uuid.uuid4().hex[:8].upper()}"

    logger.info(
        "OrderRouter paper fill: %s %s x%.2f @ %.4f (slippage %.2f%%)",
        symbol,
        side,
        quantity,
        execution_price,
        slippage_pct,
    )

    return {
        "success": True,
        "order_id": order_id,
        "execution_price": round(execution_price, 4),
        "mode": "paper",
        "slippage_pct": slippage_pct,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
    }


def _fetch_last_price(symbol: str) -> float:
    """Synchronous yfinance last-price fetch — called via asyncio.to_thread."""
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="1d")
    if hist.empty:
        raise RuntimeError(f"yfinance returned empty history for {symbol}")
    return float(hist["Close"].iloc[-1])


# ---------------------------------------------------------------------------
# Live equity execution — Interactive Brokers adapter
# ---------------------------------------------------------------------------

async def _execute_live_equity(symbol: str, side: str, quantity: float) -> dict:
    """Execute live equity order via NautilusTrader Interactive Brokers adapter.

    Reads IB config from environment:
        IB_ACCOUNT_ID   : IB paper/live account ID (e.g. U1234567 or DU1234567)
        IB_HOST         : TWS/Gateway host (default: 127.0.0.1)
        IB_PORT_PAPER   : TWS/Gateway port (default: 7497)

    TCP reachability is checked before attempting to connect.  If IB Gateway /
    TWS is not running, returns a graceful error dict.

    Args:
        symbol:   Ticker symbol (US equities), e.g. "AAPL".
        side:     "buy" or "sell".
        quantity: Number of shares.

    Returns:
        dict with success, order_id, execution_price, mode="live_equity", [error].
    """
    account_id = os.environ.get("IB_ACCOUNT_ID", "")
    host = os.environ.get("IB_HOST", "127.0.0.1")
    port = int(os.environ.get("IB_PORT_PAPER", "7497"))

    # ------------------------------------------------------------------
    # TCP reachability gate — fail fast before attempting NautilusTrader
    # ------------------------------------------------------------------
    reachable = await _check_tcp_reachable(host, port, timeout=3.0)
    if not reachable:
        logger.warning("OrderRouter: IB Gateway not reachable at %s:%d", host, port)
        return {
            "success": False,
            "order_id": None,
            "mode": "live_equity",
            "error": (
                f"IB Gateway not reachable at {host}:{port}. "
                "Start TWS or IB Gateway in paper/live mode."
            ),
        }

    # ------------------------------------------------------------------
    # Build NautilusTrader TradingNode with IB adapters (deferred imports)
    # ------------------------------------------------------------------
    try:
        result = await asyncio.to_thread(
            _run_ib_order_sync, symbol, side, quantity, account_id, host, port
        )
        return result
    except Exception as exc:  # noqa: BLE001
        logger.error("OrderRouter IB live execution failed: %s", exc)
        return {
            "success": False,
            "order_id": None,
            "mode": "live_equity",
            "error": str(exc),
        }


async def _check_tcp_reachable(host: str, port: int, timeout: float = 3.0) -> bool:
    """Check whether a TCP endpoint is reachable within the given timeout.

    Args:
        host:    Target hostname or IP.
        port:    Target port.
        timeout: Connection attempt timeout in seconds.

    Returns:
        True if the connection succeeds, False if it times out or is refused.
    """
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass
        return True
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
        return False


def _run_ib_order_sync(
    symbol: str,
    side: str,
    quantity: float,
    account_id: str,
    host: str,
    port: int,
) -> dict:
    """Synchronous IB order submission via NautilusTrader TradingNode.

    Called via asyncio.to_thread.  All NT imports are deferred inside this
    function to keep the module importable even if NT has install issues.

    Args:
        symbol:     US equity ticker.
        side:       "buy" or "sell".
        quantity:   Number of shares.
        account_id: IB account ID from env.
        host:       TWS/Gateway host.
        port:       TWS/Gateway port.

    Returns:
        Plain dict: success, order_id, execution_price, mode, [error].
    """
    # Deferred NT imports — keeps module importable if NT not installed
    from nautilus_trader.adapters.interactive_brokers.config import (
        InteractiveBrokersExecClientConfig,
        InteractiveBrokersInstrumentProviderConfig,
    )
    from nautilus_trader.adapters.interactive_brokers.factories import (
        InteractiveBrokersLiveExecClientFactory,
    )
    from nautilus_trader.config import TradingNodeConfig, LoggingConfig
    from nautilus_trader.live.node import TradingNode
    from nautilus_trader.model.identifiers import TraderId

    instrument_provider_config = InteractiveBrokersInstrumentProviderConfig(
        load_all=False,
    )
    exec_config = InteractiveBrokersExecClientConfig(
        ibg_host=host,
        ibg_port=port,
        ibg_client_id=1,
        account_id=account_id if account_id else None,
        instrument_provider=instrument_provider_config,
    )

    node_config = TradingNodeConfig(
        trader_id=TraderId("QUANTUM-SWARM-001"),
        logging=LoggingConfig(log_level="OFF", bypass_logging=True),
        exec_clients={"IB": exec_config},
        exec_factories=[InteractiveBrokersLiveExecClientFactory],
    )

    node = TradingNode(config=node_config)
    try:
        node.build()
        node.run()

        # Submit market order
        from nautilus_trader.model.enums import OrderSide
        from nautilus_trader.model.orders import MarketOrder
        from nautilus_trader.model.identifiers import InstrumentId

        instrument_id = InstrumentId.from_str(f"{symbol}.IDEALPRO")
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        from nautilus_trader.model.objects import Quantity as NtQuantity

        order = node.trader.order_factory.market(
            instrument_id=instrument_id,
            order_side=order_side,
            quantity=NtQuantity(quantity, 0),
        )
        node.trader.submit_order(order)

        # Wait for fill — simplified; real impl would await event
        import time
        time.sleep(30)

        return {
            "success": True,
            "order_id": str(order.client_order_id),
            "execution_price": None,
            "mode": "live_equity",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
        }
    finally:
        try:
            node.stop()
            node.dispose()
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# Live crypto execution — Binance adapter
# ---------------------------------------------------------------------------

async def _execute_live_crypto(symbol: str, side: str, quantity: float) -> dict:
    """Execute live crypto order via NautilusTrader Binance adapter.

    Reads Binance config from environment:
        BINANCE_API_KEY    : Binance API key
        BINANCE_API_SECRET : Binance API secret

    Returns a graceful error if keys are not set.

    Args:
        symbol:   Crypto symbol, e.g. "BTC-USDT" or "ETHUSDT".
        side:     "buy" or "sell".
        quantity: Number of units.

    Returns:
        dict with success, order_id, execution_price, mode="live_crypto", [error].
    """
    api_key = os.environ.get("BINANCE_API_KEY", "")
    api_secret = os.environ.get("BINANCE_API_SECRET", "")

    if not api_key or not api_secret:
        logger.warning("OrderRouter: Binance credentials not set in environment")
        return {
            "success": False,
            "order_id": None,
            "mode": "live_crypto",
            "error": "BINANCE_API_KEY or BINANCE_API_SECRET not set",
        }

    try:
        result = await asyncio.to_thread(
            _run_binance_order_sync, symbol, side, quantity, api_key, api_secret
        )
        return result
    except Exception as exc:  # noqa: BLE001
        logger.error("OrderRouter Binance live execution failed: %s", exc)
        return {
            "success": False,
            "order_id": None,
            "mode": "live_crypto",
            "error": str(exc),
        }


def _run_binance_order_sync(
    symbol: str,
    side: str,
    quantity: float,
    api_key: str,
    api_secret: str,
) -> dict:
    """Synchronous Binance order submission via NautilusTrader TradingNode.

    Called via asyncio.to_thread.  All NT imports deferred inside function body.

    Args:
        symbol:     Crypto symbol, e.g. "BTC-USDT".
        side:       "buy" or "sell".
        quantity:   Number of units.
        api_key:    Binance API key.
        api_secret: Binance API secret.

    Returns:
        Plain dict: success, order_id, execution_price, mode, [error].
    """
    # Deferred NT imports
    from nautilus_trader.adapters.binance.config import BinanceExecClientConfig
    from nautilus_trader.adapters.binance.factories import BinanceLiveExecClientFactory
    from nautilus_trader.config import TradingNodeConfig, LoggingConfig
    from nautilus_trader.live.node import TradingNode
    from nautilus_trader.model.identifiers import TraderId

    exec_config = BinanceExecClientConfig(
        api_key=api_key,
        api_secret=api_secret,
        is_testnet=False,
    )

    node_config = TradingNodeConfig(
        trader_id=TraderId("QUANTUM-SWARM-001"),
        logging=LoggingConfig(log_level="OFF", bypass_logging=True),
        exec_clients={"BINANCE": exec_config},
        exec_factories=[BinanceLiveExecClientFactory],
    )

    node = TradingNode(config=node_config)
    try:
        node.build()
        node.run()

        from nautilus_trader.model.enums import OrderSide
        from nautilus_trader.model.identifiers import InstrumentId
        from nautilus_trader.model.objects import Quantity as NtQuantity

        # Normalize symbol format for Binance (e.g. BTC-USDT → BTCUSDT)
        binance_symbol = symbol.replace("-", "").upper()
        instrument_id = InstrumentId.from_str(f"{binance_symbol}.BINANCE")
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

        order = node.trader.order_factory.market(
            instrument_id=instrument_id,
            order_side=order_side,
            quantity=NtQuantity(quantity, 4),
        )
        node.trader.submit_order(order)

        import time
        time.sleep(30)

        return {
            "success": True,
            "order_id": str(order.client_order_id),
            "execution_price": None,
            "mode": "live_crypto",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
        }
    finally:
        try:
            node.stop()
            node.dispose()
        except Exception:  # noqa: BLE001
            pass
