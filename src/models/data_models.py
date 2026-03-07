"""
Phase 3 data contracts — typed Pydantic models for all L3 executor results.
These models are the single source of truth for data flowing through SwarmState.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class MarketData(BaseModel):
    symbol: str
    price: float
    volume: float
    open: float
    high: float
    low: float
    close: float
    timestamp: datetime
    source: str        # "yfinance" | "ccxt"
    interval: str      # "1d", "1h", etc.


class SentimentData(BaseModel):
    symbol: str
    overall_sentiment: str    # "bullish" | "bearish" | "neutral"
    sentiment_score: float    # -1.0 to 1.0
    article_count: int
    timestamp: datetime
    source: str               # "finbert" | "mock"


class EconomicData(BaseModel):
    vix: Optional[float] = None
    usd_index: Optional[float] = None
    yield_10y: Optional[float] = None
    next_event_name: Optional[str] = None
    next_event_date: Optional[str] = None
    timestamp: datetime
    source: str               # "fred" | "mock"


class FundamentalsData(BaseModel):
    symbol: str
    raw_markdown: str         # Dexter STDOUT
    summary: Optional[str] = None
    timestamp: datetime
    source: str = "dexter"


class TradeRecord(BaseModel):
    trade_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    symbol: str
    side: str                       # "buy" | "sell"
    entry_price: float
    stop_loss_level: Optional[float] = None
    atr_at_entry: Optional[float] = None
    stop_loss_multiplier: Optional[float] = None
    stop_loss_method: str = "atr"
    trade_risk_score: Optional[float] = None
    portfolio_heat: Optional[float] = None
    exit_price: Optional[float] = None
    quantity: float
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    entry_time: datetime
    exit_time: Optional[datetime] = None
    execution_mode: str             # "paper" | "live"
    strategy_context: dict = Field(default_factory=dict)
