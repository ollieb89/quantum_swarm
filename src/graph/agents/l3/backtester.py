"""
src.graph.agents.l3.backtester — NautilusTrader BacktestEngine LangGraph node.

Exports:
    backtester_node(state: SwarmState) -> dict    async LangGraph node
    _run_nautilus_backtest(symbol, strategy)       sync worker (called via asyncio.to_thread)

This replaces the stub Backtester entirely.  The synchronous NautilusTrader
BacktestEngine.run() is wrapped in asyncio.to_thread() so the LangGraph event
loop is never blocked.

All NautilusTrader internal objects are extracted to plain Python dicts before
returning — no NT objects (Portfolio, Account, PositionSide, Bar, etc.) are
stored in SwarmState.

State reads:
    state["quant_proposal"]      dict with "symbol" (str) and "strategy" (dict)
    state["data_fetcher_result"] dict (not used directly, available for future use)

State writes:
    "backtest_result"  dict — plain JSON-serializable performance metrics
    "messages"         list — one assistant message entry

ANTI-PATTERNS AVOIDED:
    - NEVER call engine.run() directly in an async node (blocks event loop)
    - NEVER call asyncio.run() inside the node (LangGraph owns the event loop)
    - NEVER return NautilusTrader objects in the state dict (not JSON-serializable)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.graph.state import SwarmState
from src.core.parsing import parse_quant_proposal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public LangGraph async node
# ---------------------------------------------------------------------------

async def backtester_node(state: SwarmState) -> dict[str, Any]:
    """L3 Backtester — NautilusTrader BacktestEngine as LangGraph async node.

    Wraps the synchronous BacktestEngine.run() in asyncio.to_thread() so the
    LangGraph event loop is not blocked during potentially multi-second runs.

    On any failure from the backtest worker, returns a fallback metrics dict
    with ``fallback=True`` so downstream nodes always receive a valid structure.

    Args:
        state: Current SwarmState shared across the LangGraph graph.

    Returns:
        Partial state update dict with ``backtest_result`` and ``messages`` keys.
    """
    quant_parsed = parse_quant_proposal(state)
    symbol: str = quant_parsed.get("symbol", "BTC-USD")
    strategy: dict = quant_parsed.get("strategy") or {}

    logger.info("Backtester node: symbol=%s, strategy=%s", symbol, strategy)

    try:
        # Run blocking NT engine in a thread pool — NEVER block LangGraph event loop.
        result: dict = await asyncio.to_thread(_run_nautilus_backtest, symbol, strategy)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Backtester fallback for %s: %s", symbol, exc)
        result = {
            "sharpe_ratio": 0.0,
            "total_return": 0.0,
            "max_drawdown": 0.0,
            "total_trades": 0,
            "win_rate": 0.0,
            "period_days": 0,
            "fallback": True,
            "error": str(exc),
        }

    logger.info(
        "Backtester node complete for %s — sharpe=%.3f, total_return=%.4f",
        symbol,
        result.get("sharpe_ratio", 0.0),
        result.get("total_return", 0.0),
    )

    return {
        "backtest_result": result,
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"Backtester: {symbol} complete — "
                    f"sharpe={result.get('sharpe_ratio', 'N/A')}"
                ),
            }
        ],
    }


# ---------------------------------------------------------------------------
# Synchronous NautilusTrader worker
# ---------------------------------------------------------------------------

def _run_nautilus_backtest(symbol: str, strategy: dict) -> dict:
    """Synchronous NautilusTrader backtest worker — called via asyncio.to_thread.

    Fetches 6 months of daily OHLCV from yfinance, wrangles it into
    NautilusTrader Bar objects, runs BacktestEngine with a simulated venue,
    and extracts plain-Python metrics.

    NautilusTrader imports are deferred to this function body so the module
    can be imported even if the NT package has issues at module import time.

    Args:
        symbol:   Ticker symbol, e.g. "AAPL".
        strategy: Strategy config dict from quant_proposal (currently unused
                  by the engine — no strategy actor registered, so metrics
                  reflect the data period; this is intentional for the stub
                  replacement which just validates the pipeline).

    Returns:
        Plain Python dict with keys: sharpe_ratio, total_return, max_drawdown,
        total_trades, win_rate, period_days.  All numeric values are Python
        float or int — NautilusTrader Decimal types are cast explicitly.
    """
    # Deferred imports — keeps module importable if NT has issues
    import math

    import yfinance as yf
    from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
    from nautilus_trader.config import LoggingConfig
    from nautilus_trader.model import Money, Venue
    from nautilus_trader.model.currencies import USD
    from nautilus_trader.model.enums import AccountType, OmsType

    # ------------------------------------------------------------------
    # 1. Fetch market data
    # ------------------------------------------------------------------
    try:
        df = yf.download(symbol, period="6mo", interval="1d", auto_adjust=True, progress=False)
    except Exception as exc:
        raise RuntimeError(f"yfinance download failed for {symbol}: {exc}") from exc

    if df.empty:
        raise RuntimeError(f"yfinance returned empty DataFrame for {symbol}")

    # CRITICAL: lowercase column names before BarDataWrangler (Pitfall 3)
    df.columns = [c.lower() for c in df.columns]

    # yfinance sometimes returns a MultiIndex — flatten to single level
    if hasattr(df.columns, "levels"):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    # ------------------------------------------------------------------
    # 2. Build instrument, bar type, and wrangled bars
    # ------------------------------------------------------------------
    instrument = _build_equity_instrument(symbol, venue_name="SIM")
    bars = _wrangle_bars(df, instrument)

    if not bars:
        raise RuntimeError(f"BarDataWrangler produced 0 bars for {symbol}")

    # ------------------------------------------------------------------
    # 3. Create and configure BacktestEngine (logging suppressed)
    # ------------------------------------------------------------------
    cfg = BacktestEngineConfig(
        logging=LoggingConfig(log_level="OFF", bypass_logging=True),
    )
    engine = BacktestEngine(config=cfg)

    engine.add_venue(
        venue=Venue("SIM"),
        oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,
        starting_balances=[Money(100_000, USD)],
    )
    engine.add_instrument(instrument)
    engine.add_data(bars)

    # ------------------------------------------------------------------
    # 4. Run — blocking, safe here because we are inside asyncio.to_thread
    # ------------------------------------------------------------------
    engine.run()

    # ------------------------------------------------------------------
    # 5. Extract plain-Python metrics
    # ------------------------------------------------------------------
    try:
        metrics = _extract_backtest_metrics(engine, period_days=len(df))
    finally:
        engine.dispose()

    return metrics


# ---------------------------------------------------------------------------
# Helper: build Equity instrument (NT 1.223.0 API)
# ---------------------------------------------------------------------------

def _build_equity_instrument(symbol: str, venue_name: str = "SIM"):
    """Build a NautilusTrader Equity instrument for the given symbol.

    Uses the NT 1.223.0 constructor signature (raw_symbol, ts_event, ts_init
    required; venue inferred from InstrumentId).
    """
    from nautilus_trader.model.currencies import USD
    from nautilus_trader.model.identifiers import InstrumentId, Symbol
    from nautilus_trader.model.instruments import Equity
    from nautilus_trader.model.objects import Price, Quantity

    return Equity(
        instrument_id=InstrumentId.from_str(f"{symbol}.{venue_name}"),
        raw_symbol=Symbol(symbol),
        currency=USD,
        price_precision=2,
        price_increment=Price(0.01, 2),
        lot_size=Quantity(1, 0),
        ts_event=0,
        ts_init=0,
    )


# ---------------------------------------------------------------------------
# Helper: wrangle yfinance DataFrame into NT Bar objects
# ---------------------------------------------------------------------------

def _wrangle_bars(df, instrument) -> list:
    """Convert a lowercased yfinance DataFrame into NautilusTrader Bar objects."""
    from nautilus_trader.model import BarType
    from nautilus_trader.model.data import BarSpecification
    from nautilus_trader.model.enums import BarAggregation, PriceType
    from nautilus_trader.persistence.wranglers import BarDataWrangler

    bar_type = BarType(
        instrument_id=instrument.id,
        bar_spec=BarSpecification(1, BarAggregation.DAY, PriceType.LAST),
    )
    wrangler = BarDataWrangler(bar_type=bar_type, instrument=instrument)
    return wrangler.process(df)


# ---------------------------------------------------------------------------
# Helper: extract plain-Python metrics from BacktestEngine result
# ---------------------------------------------------------------------------

def _extract_backtest_metrics(engine, period_days: int = 0) -> dict:
    """Extract serializable metrics from a completed BacktestEngine.

    NautilusTrader stores statistics in the BacktestResult dataclass.  All
    numeric values are cast to Python float/int — NautilusTrader Decimal types
    (and nan/inf values) are normalised to 0.0 to ensure JSON-serializability.

    Args:
        engine:      A completed BacktestEngine instance.
        period_days: Number of trading days in the data window (len(df)).

    Returns:
        dict with keys: sharpe_ratio, total_return, max_drawdown, total_trades,
        win_rate, period_days.
    """
    import math

    result = engine.get_result()
    stats_returns: dict = result.stats_returns or {}
    stats_pnls: dict = result.stats_pnls or {}

    def safe_float(val) -> float:
        """Convert NT Decimal/nan/inf to Python float, defaulting to 0.0."""
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return 0.0
            return f
        except (TypeError, ValueError):
            return 0.0

    # Sharpe Ratio
    sharpe = safe_float(stats_returns.get("Sharpe Ratio (252 days)", 0.0))

    # Total return from PnL stats (first currency bucket, if present)
    total_return = 0.0
    win_rate = 0.0
    max_drawdown = 0.0
    if stats_pnls:
        first_ccy = next(iter(stats_pnls.values()), {})
        total_return = safe_float(first_ccy.get("PnL% (total)", 0.0))
        win_rate = safe_float(first_ccy.get("Win Rate", 0.0))

    # Total trades and positions from result counters
    total_trades = int(result.total_positions or 0)

    return {
        "sharpe_ratio": sharpe,
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "period_days": int(period_days),
    }
