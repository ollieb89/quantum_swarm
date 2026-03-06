# Phase 3: L3 Executors & NautilusTrader Integration - Research

**Researched:** 2026-03-06
**Domain:** NautilusTrader backtesting, live execution, LangGraph async nodes, market data APIs, trade logging, self-improvement state loops
**Confidence:** MEDIUM-HIGH (NautilusTrader patterns HIGH from official docs; Alpaca adapter finding is a critical constraint change; LangGraph async patterns HIGH)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Self-improvement loop**
- Triggered by: trade outcome settled — when P&L is known after a trade closes
- Feeds back to: L2 Debate layer (BullishResearcher and BearishResearcher receive outcome signal)
- Mechanism: `trade_history` list added to SwarmState — L2 agents read it as context on next invocation
- History retention: sliding window of last N trades (10-20), oldest dropped when limit hit

**DataFetcher data sources**
- Implement all four sources for real: yfinance (equities), ccxt (crypto), news sentiment, economic calendar
- Separation of concerns: DataFetcher handles market data (prices, ccxt, news, economic); Dexter handles deep fundamental research (SEC filings, DCF, analyst estimates, insider trades)
- Dexter invocation: CLI subprocess — Python calls `bun run src/index.tsx --query "[QUERY]"` from the `src/agents/dexter/` directory, captures Markdown STDOUT
- Return format: Typed Pydantic models — `MarketData`, `FundamentalsData`, `SentimentData` dataclasses (type-safe, fits LangGraph state)
- Caching: in-memory cache per swarm run (same ticker queried twice in one session = one API call)

**NautilusTrader execution scope**
- Execution mode: paper + live switchable via `config/swarm_config.yaml` flag (paper by default)
- Market venues: equities (US stocks), crypto (spot), and futures/derivatives
- Broker for live equities: Alpaca — free paper + live API, NautilusTrader has a built-in Alpaca adapter
- Backtester: migrate to NautilusTrader's event-driven backtest engine (replace the stub Backtester entirely)

### Claude's Discretion
- Exact N value for trade history window (within 10-20 range)
- Specific Pydantic model schema details
- NautilusTrader crypto and futures adapter selection (Binance, Bybit, etc.)
- How trade_history is formatted/summarized before being injected into L2 agent context

### Deferred Ideas (OUT OF SCOPE)
- MCP server wrapping Dexter tools — proposed in deep_research doc as "Phase 2 (scalable)" path. Defer to a future phase.
- LangSmith trace injection for self-improvement (proposed in Phase 4 Dashboard) — self-improvement via SwarmState covers Phase 3 needs without it
- Full L1 routing weight updates from trade outcomes — only L2 debate layer in Phase 3
</user_constraints>

---

## CRITICAL FINDING: Alpaca Adapter Does Not Exist in Official NautilusTrader

**This changes the locked decision about Alpaca as the live equities broker.**

Research confirmed: As of NautilusTrader 1.223.0 (February 2026), there is **no official Alpaca adapter** in the NautilusTrader codebase. An RFC (#3374) was opened January 2026 and a community PR (#3375) exists but is unmerged. The project maintainers stated Alpaca is "not in the near term."

**Recommended resolution for the planner:** Use **Interactive Brokers** as the official live equities adapter. IB has a full, documented, production-quality adapter (`nautilus_trader.adapters.ib`) supporting equities (US stocks), and IB offers paper trading at no cost. The crypto/futures adapters (Binance, Bybit) are official and well-documented.

The CONTEXT.md decision to "use Alpaca" should be treated as a broker preference that cannot be fulfilled via NautilusTrader natively. Plans must either:
1. Use IB for live equities (recommended — production-ready adapter exists)
2. Build a thin NautilusTrader-compatible Alpaca adapter from the community PR (risky, out of scope)
3. Route live equities through Alpaca's direct REST API bypassing NautilusTrader (breaks the unified execution layer)

**Resolution chosen for research:** Use Interactive Brokers for live equities. Alpaca remains usable as a direct API for paper-only scenarios if needed as a future option.

---

## Summary

Phase 3 migrates three stub L3 executor classes into real LangGraph nodes backed by live data and execution infrastructure, then adds a self-improvement feedback loop into SwarmState.

The DataFetcher stub becomes a real async LangGraph node wiring yfinance (equities OHLCV), ccxt (crypto spot), news sentiment, and economic calendar into typed Pydantic models. A critical bridge is the Dexter subprocess invocation — the existing `docs/deep_research_dexter_integration.md` spec defines exactly how Python calls `bun run src/index.tsx --query "..."` and captures Markdown STDOUT. Both calls use `asyncio.create_subprocess_exec` with a 90-second timeout.

The Backtester stub is replaced entirely by NautilusTrader's `BacktestEngine` (low-level API). Wrangling yfinance DataFrames into Nautilus `Bar` objects requires `BarDataWrangler` with an `Equity` instrument definition (or `CryptoPerpetual`/`CurrencyPair` for crypto). The `BacktestEngine` runs synchronously internally but is wrapped in `asyncio.to_thread()` inside the LangGraph async node to avoid blocking.

The OrderRouter becomes a NautilusTrader execution node: in paper mode it uses a simulated venue; in live mode it delegates to the Interactive Brokers adapter (equities) or Binance/Bybit adapter (crypto). Live mode requires the IB Gateway/TWS process to be running externally.

The self-improvement loop is implemented as a `trade_history` field (Annotated list reducer) added to SwarmState. After `OrderRouter` closes a position and P&L is known, a `TradeLogger` node appends a `TradeRecord` Pydantic model to the list. A sliding window of N=15 trades is enforced. L2 BullishResearcher and BearishResearcher read `trade_history` from state as additional context on their next invocation.

**Primary recommendation:** Build Phase 3 as four wave-sequenced plans: (1) DataFetcher real implementation + Dexter bridge, (2) NautilusTrader Backtester migration, (3) OrderRouter + execution adapters, (4) TradeLogger + self-improvement loop + orchestrator wiring.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `nautilus_trader` | >= 1.210.0 (latest 1.223.0) | Event-driven backtest engine, live execution, adapter layer | Project's chosen execution framework; high-performance Rust core |
| `yfinance` | >= 0.2 | Equities OHLCV + fundamental data from Yahoo Finance | Reliable free source; already in requirements.txt |
| `ccxt` | >= 4.0 | Crypto exchange market data and order routing | Standard multi-exchange library; already in requirements.txt |
| `pydantic` | v2 (bundled with langchain) | Typed data models for DataFetcher results | Type safety for LangGraph state; already used in project |
| `asyncio` | stdlib | Async subprocess calls and non-blocking data fetches | LangGraph async node pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `nautilus_trader.adapters.ib` | bundled | Live equities execution via Interactive Brokers | When `execution_mode: live` and equities trading |
| `nautilus_trader.adapters.binance` | bundled | Live crypto spot/futures execution | When `execution_mode: live` and crypto trading |
| `nautilus_trader.adapters.bybit` | bundled | Alternative crypto futures execution | Claude's discretion for futures/derivatives |
| `pandas` | >= 2.0 | DataFrame for yfinance data; input to BarDataWrangler | Already in requirements.txt |
| `functools.lru_cache` or simple dict | stdlib | In-memory per-run cache for DataFetcher | Same ticker = one API call per swarm run |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Interactive Brokers (equities live) | Alpaca direct REST API | Alpaca has no official NT adapter; IB adapter is production-ready |
| `asyncio.create_subprocess_exec` | `subprocess.run` | Blocking subprocess freezes LangGraph event loop; async version required |
| `BarDataWrangler` | Manual Nautilus `Bar` construction | Wrangler handles ts_init/ts_event correctly; manual construction error-prone |

**Installation:**
```bash
pip install nautilus_trader==1.223.0 yfinance ccxt pandas pydantic
# NautilusTrader is already in requirements.txt at >= 1.210.0
```

---

## Architecture Patterns

### Recommended Project Structure
```
src/
├── graph/
│   ├── state.py                # Add trade_history, execution_mode fields
│   ├── orchestrator.py         # Add L3 nodes after risk_manager
│   └── agents/
│       └── l3/
│           ├── __init__.py
│           ├── data_fetcher.py     # Real DataFetcher LangGraph node
│           ├── backtester.py       # NautilusTrader BacktestEngine wrapper
│           ├── order_router.py     # NautilusTrader execution client wrapper
│           └── trade_logger.py     # TradeLogger node + self-improvement loop
├── tools/
│   ├── data_sources/
│   │   ├── yfinance_client.py   # yfinance fetch + BarDataWrangler prep
│   │   ├── ccxt_client.py       # ccxt async OHLCV + ticker fetch
│   │   ├── news_sentiment.py    # News/sentiment API client
│   │   └── economic_calendar.py # Economic calendar client
│   └── dexter_bridge.py         # Async subprocess wrapper for Dexter CLI
├── models/
│   └── data_models.py           # Pydantic: MarketData, FundamentalsData, SentimentData, TradeRecord
└── agents/
    └── l3_executor.py           # Existing stub — migrate methods to src/graph/agents/l3/
config/
└── swarm_config.yaml            # Add execution_mode, alpaca/IB credentials sections
```

### Pattern 1: LangGraph Async Node with asyncio.to_thread for Blocking I/O

**What:** Wrap synchronous NautilusTrader `BacktestEngine.run()` and synchronous yfinance/ccxt calls in `asyncio.to_thread()` inside an `async def` node function so LangGraph's event loop is not blocked.

**When to use:** Any L3 node that calls blocking I/O (NautilusTrader engine, yfinance download, ccxt fetch).

```python
# Source: LangGraph async best practices + asyncio stdlib
import asyncio

async def backtester_node(state: SwarmState) -> dict:
    """L3 Backtester — NautilusTrader BacktestEngine as LangGraph async node."""
    strategy = state.get("quant_proposal", {})
    symbol = strategy.get("symbol", "AAPL")

    # Run blocking NT engine in thread pool — never block LangGraph event loop
    result = await asyncio.to_thread(_run_nautilus_backtest, symbol, strategy)

    return {
        "backtest_result": result,
        "messages": [{"role": "assistant", "content": f"Backtester: {symbol} complete"}],
    }

def _run_nautilus_backtest(symbol: str, strategy: dict) -> dict:
    """Synchronous NautilusTrader backtest — called via asyncio.to_thread."""
    from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
    # ... engine setup, run, extract results
    engine.run()
    return _extract_results(engine)
```

### Pattern 2: NautilusTrader BacktestEngine with yfinance Data

**What:** Download OHLCV from yfinance, define an `Equity` instrument, use `BarDataWrangler` to produce Nautilus `Bar` objects, run `BacktestEngine`.

**When to use:** Whenever the `Backtester` node is invoked with a symbol and date range.

```python
# Source: NautilusTrader official docs — backtest_fx_bars tutorial + instruments concepts page
import yfinance as yf
from decimal import Decimal
from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.model import BarType, Money, Venue
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.enums import AccountType, OmsType, BarAggregation, PriceType
from nautilus_trader.model.identifiers import InstrumentId, Symbol
from nautilus_trader.model.instruments import Equity
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.model.data import BarSpecification
from nautilus_trader.persistence.wranglers import BarDataWrangler

def _build_equity_instrument(symbol: str, venue_name: str = "SIM") -> Equity:
    return Equity(
        instrument_id=InstrumentId.from_str(f"{symbol}.{venue_name}"),
        symbol=Symbol(symbol),
        venue=Venue(venue_name),
        currency=USD,
        price_precision=2,
        size_precision=0,
        price_increment=Price(0.01, 2),
        size_increment=Quantity(1, 0),
        lot_size=Quantity(1, 0),
    )

def _fetch_and_wrangle(symbol: str, period: str = "6mo") -> tuple:
    df = yf.download(symbol, period=period, interval="1d", auto_adjust=True)
    df.columns = [c.lower() for c in df.columns]  # NT expects lowercase column names
    instrument = _build_equity_instrument(symbol)
    bar_type = BarType(
        instrument_id=instrument.id,
        bar_spec=BarSpecification(1, BarAggregation.DAY, PriceType.LAST),
    )
    wrangler = BarDataWrangler(bar_type=bar_type, instrument=instrument)
    bars = wrangler.process(df)
    return instrument, bars
```

### Pattern 3: Dexter CLI Bridge (Async Subprocess)

**What:** Python async subprocess calling `bun run src/index.tsx --query "..."` from the Dexter directory, capturing STDOUT Markdown, with 90-second timeout.

**When to use:** When DataFetcher receives a request tagged as fundamental/DCF research.

```python
# Source: docs/deep_research_dexter_integration.md spec + asyncio subprocess docs
import asyncio
from pathlib import Path

DEXTER_DIR = Path(__file__).parent.parent / "agents" / "dexter"
DEXTER_TIMEOUT = 90  # seconds per deep_research_dexter_integration.md

async def invoke_dexter(query: str) -> str:
    """Invoke Dexter CLI and return Markdown STDOUT."""
    proc = await asyncio.create_subprocess_exec(
        "bun", "run", "src/index.tsx", "--query", query,
        cwd=str(DEXTER_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=DEXTER_TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        raise TimeoutError(f"Dexter exceeded {DEXTER_TIMEOUT}s timeout for query: {query}")
    if proc.returncode != 0:
        raise RuntimeError(f"Dexter failed (exit {proc.returncode}): {stderr.decode()}")
    return stdout.decode()
```

### Pattern 4: SwarmState trade_history Sliding Window

**What:** Append-reducer field in SwarmState. `TradeLogger` node appends one `TradeRecord` dict per closed trade; enforces sliding window of N=15 (Claude's discretion within 10-20 range).

**When to use:** After every trade close (paper or live) when P&L is settled.

```python
# Source: Phase 2 established pattern — mirrors debate_history reducer in state.py
import operator
from typing import Annotated, List

class SwarmState(TypedDict):
    # ... existing fields ...

    # Phase 3: L3 state additions
    trade_history: Annotated[List[dict], operator.add]   # sliding window, append-only
    execution_mode: str                                   # "paper" | "live"
    data_fetcher_result: Optional[dict]                  # typed MarketData/SentimentData
    backtest_result: Optional[dict]                      # NautilusTrader metrics
    execution_result: Optional[dict]                     # OrderRouter output

# In TradeLogger node — enforce sliding window after append
TRADE_HISTORY_WINDOW = 15

def trade_logger_node(state: SwarmState) -> dict:
    new_record = _build_trade_record(state)
    # LangGraph reducer handles append; trimming must happen at read time
    # Trim to last N when reading in L2 agents:
    #   recent_trades = state["trade_history"][-TRADE_HISTORY_WINDOW:]
    return {
        "trade_history": [new_record],
        "messages": [{"role": "assistant", "content": f"TradeLogger: recorded {new_record['symbol']}"}],
    }
```

### Pattern 5: NautilusTrader Live Execution via TradingNode (IB)

**What:** Long-running `TradingNode` for Interactive Brokers live/paper equities execution. Requires IB Gateway or TWS running externally.

**When to use:** When `execution_mode == "live"` and asset class is equities.

```python
# Source: NautilusTrader Interactive Brokers official docs
from nautilus_trader.adapters.interactive_brokers.config import (
    InteractiveBrokersDataClientConfig,
    InteractiveBrokersExecClientConfig,
    InteractiveBrokersInstrumentProviderConfig,
    IBMarketDataTypeEnum,
    SymbologyMethod,
)
from nautilus_trader.adapters.interactive_brokers.factories import (
    InteractiveBrokersLiveDataClientFactory,
    InteractiveBrokersLiveExecClientFactory,
)
from nautilus_trader.adapters.interactive_brokers.common import IB
from nautilus_trader.config import TradingNodeConfig, LoggingConfig
from nautilus_trader.live.node import TradingNode

def build_ib_trading_node(account_id: str, paper: bool = True) -> TradingNode:
    port = 7497 if paper else 7496  # TWS paper=7497, live=7496
    instrument_config = InteractiveBrokersInstrumentProviderConfig(
        symbology_method=SymbologyMethod.IB_SIMPLIFIED,
        load_ids=frozenset(["AAPL.NASDAQ"]),
    )
    data_cfg = InteractiveBrokersDataClientConfig(
        ibg_host="127.0.0.1", ibg_port=port, ibg_client_id=1,
        market_data_type=IBMarketDataTypeEnum.DELAYED_FROZEN,
        instrument_provider=instrument_config,
    )
    exec_cfg = InteractiveBrokersExecClientConfig(
        ibg_host="127.0.0.1", ibg_port=port, ibg_client_id=2,
        account_id=account_id,
        instrument_provider=instrument_config,
    )
    node_config = TradingNodeConfig(
        trader_id="SWARM-TRADER-001",
        logging=LoggingConfig(log_level="INFO"),
        data_clients={IB: data_cfg},
        exec_clients={IB: exec_cfg},
    )
    node = TradingNode(config=node_config)
    node.add_data_client_factory(IB, InteractiveBrokersLiveDataClientFactory)
    node.add_exec_client_factory(IB, InteractiveBrokersLiveExecClientFactory)
    return node
```

### Anti-Patterns to Avoid

- **Calling `engine.run()` directly in a sync LangGraph node:** NautilusTrader `BacktestEngine.run()` is blocking and CPU-intensive. Always wrap in `asyncio.to_thread()`.
- **Using `asyncio.run()` inside a LangGraph node function:** LangGraph manages the event loop. Calling `asyncio.run()` creates a nested loop and causes runtime errors.
- **Storing full Nautilus `Bar` objects in SwarmState:** These are not JSON-serializable. Extract metrics as plain dicts before returning from the node.
- **Appending to `trade_history` without a sliding window guard:** The LangGraph `operator.add` reducer always appends. Trim at read time (slice `[-N:]`) in L2 agents; never replace the field.
- **Invoking Dexter synchronously:** `subprocess.run()` will block for 45-90 seconds. Use `asyncio.create_subprocess_exec`.
- **Hardcoding `execution_mode`:** Must always read from `SwarmState["execution_mode"]` which is loaded from `config/swarm_config.yaml` at startup.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Event-driven backtest simulation | Custom backtest loop | `NautilusTrader BacktestEngine` | Handles order matching, slippage, fill simulation, commission, cash accounting |
| OHLCV DataFrame → Nautilus types | Manual Bar construction | `BarDataWrangler.process(df)` | ts_init/ts_event alignment is subtle; wrangler handles nanosecond precision correctly |
| Exchange adapter for Binance | Custom WebSocket + REST | `nautilus_trader.adapters.binance` | Rate limiting, reconnection, order state tracking are all handled |
| Exchange adapter for IB equities | Custom TWS API wrapper | `nautilus_trader.adapters.ib` | IB TWS API has complex state machine; NT adapter handles all of it |
| Multi-exchange OHLCV fetching | Custom REST clients per exchange | `ccxt.async_support` | Unified API across 100+ exchanges; handles rate limits |
| Yahoo Finance data download | Custom scraping | `yfinance.download()` | Stable, maintained; returns pandas DataFrame with correct OHLCV column names |
| In-memory API result caching | Redis or file cache | Simple `dict` with `(symbol, source)` key | Per-run lifetime; no persistence needed; plain dict is sufficient |

**Key insight:** NautilusTrader's complexity is justified — order matching with realistic slippage, fill probability, and position P&L calculation have dozens of edge cases. The BacktestEngine captures years of production hardening; a hand-rolled version would be systematically incorrect.

---

## Common Pitfalls

### Pitfall 1: NautilusTrader Not Installed in Project Environment
**What goes wrong:** `nautilus_trader` is listed in `requirements.txt` but the project Python environment does not have it installed (confirmed: `ModuleNotFoundError` when running `python -c "import nautilus_trader"` in the project venv).
**Why it happens:** NautilusTrader has native Rust extensions and requires a specific build; `pip install nautilus_trader` may fail silently or require build tools.
**How to avoid:** Wave 0 of Phase 3 must include `pip install nautilus_trader==1.223.0` and a smoke test verifying import succeeds before any implementation work.
**Warning signs:** `ModuleNotFoundError: No module named 'nautilus_trader'` at test time.

### Pitfall 2: Alpaca Adapter Does Not Exist in NautilusTrader
**What goes wrong:** Plans that reference `nautilus_trader.adapters.alpaca` will fail at import time.
**Why it happens:** The RFC is open but the adapter is unmerged and unsupported as of 1.223.0.
**How to avoid:** Use Interactive Brokers for live equities. Crypto stays with Binance/Bybit. Document this constraint clearly in plan files.
**Warning signs:** ImportError on any `nautilus_trader.adapters.alpaca` reference.

### Pitfall 3: yfinance DataFrame Column Name Mismatch
**What goes wrong:** `BarDataWrangler.process(df)` raises `KeyError` or produces incorrect bars.
**Why it happens:** yfinance returns columns with capital letters (`Open`, `High`, `Low`, `Close`, `Volume`). NautilusTrader expects lowercase (`open`, `high`, `low`, `close`, `volume`).
**How to avoid:** Always apply `df.columns = [c.lower() for c in df.columns]` before passing to `BarDataWrangler`.
**Warning signs:** KeyError in wrangler or zero-price bars in backtest results.

### Pitfall 4: trade_history Growing Unbounded
**What goes wrong:** `trade_history` in SwarmState grows indefinitely because `operator.add` reducer always appends.
**Why it happens:** LangGraph reducers are append-only by design. There is no built-in sliding window.
**How to avoid:** The sliding window is enforced at READ time in L2 agents (`recent_trades = state["trade_history"][-15:]`), not at write time. Document this pattern clearly.
**Warning signs:** SwarmState serialization errors or very slow state merges after many trades.

### Pitfall 5: Dexter Bridge Environment Variables Not Set
**What goes wrong:** Dexter subprocess exits with error because `FINANCIAL_DATASETS_API_KEY`, `EXASEARCH_API_KEY`, or `ANTHROPIC_API_KEY` are missing from the Dexter `.env` file.
**Why it happens:** Dexter runs in its own directory (`src/agents/dexter/`) with its own `.env` file, separate from the main project `.env`.
**How to avoid:** Check for all three env vars before invoking Dexter. Fail with a clear error message listing the missing keys. Add to Wave 0 checklist.
**Warning signs:** `Dexter failed (exit 1): Error: FINANCIAL_DATASETS_API_KEY is not set`.

### Pitfall 6: Blocking the LangGraph Event Loop
**What goes wrong:** `BacktestEngine.run()` or synchronous `yfinance.download()` inside a sync LangGraph node causes the entire graph to stall for seconds.
**Why it happens:** LangGraph uses an async event loop internally. Synchronous blocking calls prevent other nodes from running.
**How to avoid:** Use `asyncio.to_thread()` for all blocking I/O in L3 nodes. Define node functions as `async def`.
**Warning signs:** Graph appears to hang; no other nodes make progress while backtester runs.

### Pitfall 7: NautilusTrader BacktestEngine Results Not JSON-Serializable
**What goes wrong:** Returning NautilusTrader internal objects (e.g., `Portfolio`, `Account`, `PositionSide`) from a node causes LangGraph state serialization failure.
**Why it happens:** NautilusTrader objects are Rust-backed C extensions that cannot be pickled or JSON-serialized.
**How to avoid:** Always extract metrics into a plain Python dict before returning from the node. Define a `_extract_backtest_metrics(engine) -> dict` helper.
**Warning signs:** `TypeError: Object of type PositionSide is not JSON serializable`.

---

## Code Examples

### ccxt Async OHLCV Fetch

```python
# Source: ccxt official docs + ccxt/examples/py/async-fetch-ohlcv-multiple-symbols-continuously.py
import ccxt.async_support as ccxt

async def fetch_crypto_ohlcv(symbol: str, exchange_id: str = "binance", timeframe: str = "1h") -> list:
    exchange = getattr(ccxt, exchange_id)()
    try:
        bars = await exchange.fetch_ohlcv(symbol, timeframe, limit=100)
        return bars  # [[timestamp_ms, open, high, low, close, volume], ...]
    finally:
        await exchange.close()
```

### yfinance Download + BarDataWrangler

```python
# Source: NautilusTrader backtest_low_level docs + yfinance docs
import yfinance as yf
from nautilus_trader.persistence.wranglers import BarDataWrangler

def fetch_equity_bars(symbol: str, period: str = "6mo") -> list:
    df = yf.download(symbol, period=period, interval="1d", auto_adjust=True)
    df.columns = [c.lower() for c in df.columns]
    instrument = _build_equity_instrument(symbol)
    bar_type = BarType(
        instrument_id=instrument.id,
        bar_spec=BarSpecification(1, BarAggregation.DAY, PriceType.LAST),
    )
    wrangler = BarDataWrangler(bar_type=bar_type, instrument=instrument)
    return wrangler.process(df)
```

### Pydantic Models for DataFetcher Results

```python
# Source: CONTEXT.md decision — Pydantic models for typed state
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MarketData(BaseModel):
    symbol: str
    price: float
    volume: float
    open: float
    high: float
    low: float
    close: float
    timestamp: datetime
    source: str  # "yfinance" | "ccxt"
    interval: str  # "1d", "1h", etc.

class SentimentData(BaseModel):
    symbol: str
    overall_sentiment: str        # "bullish" | "bearish" | "neutral"
    sentiment_score: float        # -1.0 to 1.0
    article_count: int
    timestamp: datetime
    source: str

class FundamentalsData(BaseModel):
    symbol: str
    raw_markdown: str             # Dexter STDOUT
    summary: Optional[str]        # Extracted key findings
    timestamp: datetime
    source: str = "dexter"

class TradeRecord(BaseModel):
    trade_id: str
    symbol: str
    side: str                     # "buy" | "sell"
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: Optional[float]          # None until position closed
    pnl_pct: Optional[float]
    entry_time: datetime
    exit_time: Optional[datetime]
    execution_mode: str           # "paper" | "live"
    strategy_context: dict        # snapshot of quant_proposal at entry
```

### In-Memory Cache Pattern for DataFetcher

```python
# Source: CONTEXT.md decision — per-run cache
from functools import wraps

_data_cache: dict = {}  # module-level, cleared between swarm runs

def cached_fetch(source: str, symbol: str, **kwargs):
    cache_key = (source, symbol, frozenset(kwargs.items()))
    if cache_key not in _data_cache:
        _data_cache[cache_key] = _real_fetch(source, symbol, **kwargs)
    return _data_cache[cache_key]

def clear_cache():
    """Call at the start of each new swarm run."""
    _data_cache.clear()
```

### swarm_config.yaml Additions

```yaml
# Additions to config/swarm_config.yaml for Phase 3
trading:
  execution_mode: paper  # paper | live — paper is default (CONTEXT.md decision)

  # Interactive Brokers (live equities — replaces Alpaca which has no NT adapter)
  interactive_brokers:
    host: "127.0.0.1"
    port_paper: 7497   # TWS paper trading
    port_live: 7496    # TWS live trading
    account_id: "${IB_ACCOUNT_ID}"
    client_id_data: 1
    client_id_exec: 2

  # Crypto execution adapters (Claude's discretion: Binance as primary)
  crypto_adapter: "binance"  # binance | bybit

  # Dexter bridge config
  dexter:
    timeout_seconds: 90
    max_iterations: 10

  # Trade history window (N=15 within Claude's discretion range 10-20)
  trade_history_window: 15
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `BacktestEngine` manual setup with `BacktestEngineConfig()` | Same API stable | NautilusTrader 1.210+ | No breaking changes; PoC in `src/poc/nautilus_integration_poc.py` confirmed API works |
| FX-only wrangler examples | `BarDataWrangler` works for equities with `Equity` instrument class | NT 1.x | Equities backtesting is fully supported |
| Alpaca as planned equities adapter | Interactive Brokers (NT official) | RFC opened Jan 2026, no merge | Alpaca must be deferred; IB adapter is mature and documented |
| Custom in-memory caching | Plain dict (sufficient for per-run) | N/A | No external dependency needed |
| Synchronous LangGraph nodes | Async nodes with `asyncio.to_thread` | LangGraph best practice | Required for blocking I/O like NT engine and yfinance |

**Deprecated/outdated:**
- `freqtrade` as broker (referenced in existing `OrderRouter._execute_live()`) — replace with NautilusTrader execution clients
- The existing `MarketData` dataclass in `l3_executor.py` — migrate to Pydantic `BaseModel` for validation

---

## Open Questions

1. **IB Gateway vs. TWS for paper trading**
   - What we know: IB paper mode uses port 7497 (TWS) or 4002 (IB Gateway). Both work with the NT adapter.
   - What's unclear: Does the project owner have an IB paper account? IB requires account registration even for paper trading.
   - Recommendation: Plan files should include a prerequisite check: "IB paper account + TWS or IB Gateway installed." If no IB access, paper mode falls back to NautilusTrader's simulated venue (full backtest mode).

2. **News sentiment data source**
   - What we know: The existing stub returns hardcoded "bullish/bearish" from `_fetch_news()`. The config references FinBERT endpoint.
   - What's unclear: Is the HuggingFace FinBERT endpoint (`ProsusAI/finbert`) still the intended source? No API key appears required (inference API). Alternatively, a NewsAPI key could provide real articles.
   - Recommendation: Use HuggingFace inference API (free tier) for FinBERT sentiment. If `HUGGINGFACE_API_KEY` is set, use it; else degrade gracefully to a mock.

3. **Economic calendar source**
   - What we know: The stub returns VIX, USD index, 10Y yield, and next event. These are point-in-time snapshots.
   - What's unclear: Which live source to use? Options: Alpha Vantage (VIX/yields — requires API key), investpy (deprecated), FRED API (free, official Fed data).
   - Recommendation: Use FRED API (`fredapi` Python library) for VIX and yield data (free, official). Register for a free FRED API key.

4. **Dexter environment variable availability**
   - What we know: Dexter needs `FINANCIAL_DATASETS_API_KEY`, `EXASEARCH_API_KEY`, `ANTHROPIC_API_KEY` in `src/agents/dexter/.env`.
   - What's unclear: Are these keys available in the current environment?
   - Recommendation: DataFetcher should check for Dexter env vars before invoking; if missing, skip Dexter and return `FundamentalsData` with `raw_markdown="Dexter unavailable: missing env vars"`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, used in Phase 2) |
| Config file | `conftest.py` at repo root (adds repo root to sys.path) |
| Quick run command | `pytest tests/test_l3_executors.py -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| DataFetcher yfinance returns valid `MarketData` for equity symbol | unit | `pytest tests/test_l3_executors.py::test_data_fetcher_yfinance -x` | ❌ Wave 0 |
| DataFetcher ccxt returns valid `MarketData` for crypto symbol | unit | `pytest tests/test_l3_executors.py::test_data_fetcher_ccxt -x` | ❌ Wave 0 |
| DataFetcher cache returns same object on second call (one API hit) | unit | `pytest tests/test_l3_executors.py::test_data_fetcher_cache -x` | ❌ Wave 0 |
| Dexter bridge raises `TimeoutError` after 90s (mocked) | unit | `pytest tests/test_l3_executors.py::test_dexter_timeout -x` | ❌ Wave 0 |
| Dexter bridge returns Markdown string on success (mocked subprocess) | unit | `pytest tests/test_l3_executors.py::test_dexter_success -x` | ❌ Wave 0 |
| NautilusTrader `BacktestEngine` initializes without error | smoke | `pytest tests/test_l3_executors.py::test_nautilus_import -x` | ❌ Wave 0 |
| Backtester node returns dict with `sharpe_ratio` key | unit | `pytest tests/test_l3_executors.py::test_backtester_node -x` | ❌ Wave 0 |
| `BarDataWrangler` processes yfinance DataFrame into `Bar` objects | unit | `pytest tests/test_l3_executors.py::test_bar_data_wrangler -x` | ❌ Wave 0 |
| OrderRouter paper mode returns `ExecutionResult` with `order_id` | unit | `pytest tests/test_l3_executors.py::test_order_router_paper -x` | ❌ Wave 0 |
| `trade_history` sliding window trims to N=15 | unit | `pytest tests/test_l3_executors.py::test_trade_history_window -x` | ❌ Wave 0 |
| TradeLogger node appends `TradeRecord` to SwarmState | unit | `pytest tests/test_l3_executors.py::test_trade_logger_append -x` | ❌ Wave 0 |
| L2 researchers receive `trade_history` context in state | integration | `pytest tests/test_l3_integration.py::test_feedback_loop -x` | ❌ Wave 0 |
| Full graph: data → debate → risk → execute → log completes | integration | `pytest tests/test_l3_integration.py::test_end_to_end_paper -x` | ❌ Wave 0 |
| `execution_mode` config flag routes to paper vs live branch | unit | `pytest tests/test_l3_executors.py::test_execution_mode_routing -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_l3_executors.py -x -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_l3_executors.py` — unit tests for all DataFetcher, Backtester, OrderRouter, TradeLogger behaviors
- [ ] `tests/test_l3_integration.py` — integration tests for full graph pipeline with L3 nodes
- [ ] NautilusTrader install verification: `pip install nautilus_trader==1.223.0 && python -c "import nautilus_trader; print(nautilus_trader.__version__)"`
- [ ] `src/models/__init__.py` and `src/models/data_models.py` — Pydantic model definitions (prerequisite for all node tests)
- [ ] `src/graph/agents/l3/__init__.py` — package init for L3 node subpackage

---

## Sources

### Primary (HIGH confidence)
- NautilusTrader official docs — backtesting concepts, instruments, IB adapter: https://nautilustrader.io/docs/nightly/
- NautilusTrader backtest FX bars tutorial (import paths, BarDataWrangler, BacktestEngine setup): https://nautilustrader.io/docs/nightly/tutorials/backtest_fx_bars/
- NautilusTrader instruments concepts (Equity class constructor): https://nautilustrader.io/docs/latest/concepts/instruments/
- NautilusTrader Interactive Brokers integration: https://nautilustrader.io/docs/nightly/integrations/ib/
- NautilusTrader adapters list: https://nautilustrader.io/docs/nightly/concepts/adapters/
- GitHub RFC #3374 — Alpaca adapter status (unmerged): https://github.com/nautechsystems/nautilus_trader/issues/3374
- NautilusTrader 1.223.0 release notes: https://github.com/nautechsystems/nautilus_trader/releases/tag/v1.223.0
- `docs/deep_research_dexter_integration.md` — Dexter CLI invocation spec (project document)
- LangGraph async best practices: https://www.baihezi.com/mirrors/langgraph/how-tos/async/index.html

### Secondary (MEDIUM confidence)
- NautilusTrader Chapter 4 Data Import (BarDataWrangler with pandas, verified against official docs): https://dev.to/henry_lin_3ac6363747f45b4/nautilustrader-chapter-4-data-import-and-processing-5can
- ccxt async OHLCV examples (GitHub official examples repo): https://github.com/ccxt/ccxt/blob/master/examples/py/async-fetch-ohlcv-multiple-symbols-continuously.py

### Tertiary (LOW confidence — needs validation)
- FinBERT HuggingFace endpoint for news sentiment (mentioned in swarm_config.yaml; not independently verified for current availability)
- FRED API as economic calendar source (recommended but not yet validated against project requirements)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — NautilusTrader official docs confirmed, ccxt and yfinance are well-established
- Architecture: HIGH — Patterns derived directly from official NautilusTrader docs and established Phase 2 patterns
- Alpaca finding: HIGH — Confirmed via GitHub RFC; no official adapter exists as of 1.223.0
- Pitfalls: HIGH — NautilusTrader install issue confirmed empirically; column naming confirmed from docs
- News/economic data sources: LOW — sources identified but not fully validated

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (NautilusTrader is fast-moving; re-verify if more than 30 days pass before planning)
