"""
Market Analysis Skills Module

Provides functions for market environment analysis, technical indicators,
and pattern recognition used by L2 agents.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Skill registry interface
SKILL_INTENT = "market_analysis"


def handle(state: dict) -> dict:
    """Handle a market_analysis intent by generating a basic market report."""
    symbol = (state.get("quant_proposal") or {}).get("symbol", "UNKNOWN")
    report = {"symbol": symbol, "skill": "market_analysis", "status": "ok"}
    return {
        "skill_result": report,
        "messages": [{"role": "assistant", "content": f"market_analysis skill: report for {symbol}"}],
    }


class MarketPhase(Enum):
    """Market phase classification"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"


class MarketHours:
    """Market hours utility"""

    # Market hours in UTC
    MARKETS = {
        "Tokyo": {"open": 0, "close": 7, "tz": "Asia/Tokyo"},
        "London": {"open": 7, "close": 16, "tz": "Europe/London"},
        "NY": {"open": 14, "close": 21, "tz": "America/New_York"},
        "Sydney": {"open": 22, "close": 24, "tz": "Australia/Sydney"}
    }

    @staticmethod
    def is_market_open(market: str, current_hour: int = None) -> bool:
        """Check if market is currently open"""
        if current_hour is None:
            now = datetime.utcnow()
            current_hour = now.hour

        market_hours = MarketHours.MARKETS.get(market)
        if not market_hours:
            return False

        open_hour = market_hours["open"]
        close_hour = market_hours["close"]

        # Handle Sydney wrap-around
        if market == "Sydney":
            return current_hour >= open_hour or current_hour < close_hour

        return open_hour <= current_hour < close_hour

    @staticmethod
    def get_open_markets(current_hour: int = None) -> List[str]:
        """Get list of currently open markets"""
        open_markets = []

        for market in MarketHours.MARKETS:
            if MarketHours.is_market_open(market, current_hour):
                open_markets.append(market)

        return open_markets


class TechnicalIndicators:
    """Technical analysis indicators"""

    @staticmethod
    def sma(prices: List[float], period: int) -> float:
        """Simple Moving Average"""
        if len(prices) < period:
            period = len(prices)
        return sum(prices[-period:]) / period

    @staticmethod
    def ema(prices: List[float], period: int) -> float:
        """Exponential Moving Average"""
        if len(prices) < period:
            period = len(prices)

        multiplier = 2 / (period + 1)
        ema = prices[0]

        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema

    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> float:
        """Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0  # Neutral

        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(
        prices: List[float],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Dict[str, float]:
        """MACD (Moving Average Convergence Divergence)"""
        fast_ema = TechnicalIndicators.ema(prices, fast)
        slow_ema = TechnicalIndicators.ema(prices, slow)

        macd_line = fast_ema - slow_ema
        signal_line = macd_line  # Simplified
        histogram = macd_line - signal_line

        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
            "trend": "bullish" if macd_line > signal_line else "bearish"
        }

    @staticmethod
    def bollinger_bands(
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, float]:
        """Bollinger Bands"""
        sma = TechnicalIndicators.sma(prices, period)

        if len(prices) < period:
            return {"upper": sma, "middle": sma, "lower": sma}

        import statistics
        std = statistics.stdev(prices[-period:])

        return {
            "upper": sma + (std_dev * std),
            "middle": sma,
            "lower": sma - (std_dev * std)
        }

    @staticmethod
    def atr(highs: List[float], lows: List[float], period: int = 14) -> float:
        """Average True Range"""
        if len(highs) < period + 1:
            return 0.0

        tr = []
        for i in range(1, len(highs)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - lows[i-1])
            low_close = abs(lows[i] - lows[i-1])
            tr.append(max(high_low, high_close, low_close))

        return sum(tr[-period:]) / period


class PatternRecognition:
    """Chart pattern recognition"""

    @staticmethod
    def detect_trend(prices: List[float], period: int = 20) -> str:
        """Detect price trend"""
        if len(prices) < period:
            return "neutral"

        recent = prices[-period:]
        first_half = sum(recent[:period//2]) / (period // 2)
        second_half = sum(recent[period//2:]) / (period - period // 2)

        if second_half > first_half * 1.02:
            return "bullish"
        elif second_half < first_half * 0.98:
            return "bearish"
        return "neutral"

    @staticmethod
    def detect_divergence(
        prices: List[float],
        indicator: List[float]
    ) -> Optional[str]:
        """Detect bullish/bearish divergence"""
        if len(prices) < 10 or len(indicator) < 10:
            return None

        # Check for bullish divergence (price lower low, indicator higher low)
        if prices[-1] < prices[-10] and indicator[-1] > indicator[-10]:
            return "bullish"

        # Check for bearish divergence
        if prices[-1] > prices[-10] and indicator[-1] < indicator[-10]:
            return "bearish"

        return None

    @staticmethod
    def detect_support_resistance(prices: List[float]) -> Dict[str, List[float]]:
        """Detect support and resistance levels"""
        levels = {
            "support": [],
            "resistance": []
        }

        if len(prices) < 20:
            return levels

        # Simple swing point detection
        for i in range(2, len(prices) - 2):
            # Support (swing low)
            if prices[i] < prices[i-1] and prices[i] < prices[i-2] and \
               prices[i] < prices[i+1] and prices[i] < prices[i+2]:
                levels["support"].append(prices[i])

            # Resistance (swing high)
            if prices[i] > prices[i-1] and prices[i] > prices[i-2] and \
               prices[i] > prices[i+1] and prices[i] > prices[i+2]:
                levels["resistance"].append(prices[i])

        return levels


class MarketEnvironment:
    """Market environment analysis"""

    @staticmethod
    def analyze_vix(vix: float) -> Dict[str, Any]:
        """Analyze VIX level and implications"""
        if vix < 15:
            return {
                "level": "low",
                "classification": "complacent",
                "implication": "Low volatility - potential for sudden moves",
                "risk_adjusted": "increase_caution"
            }
        elif vix < 20:
            return {
                "level": "normal",
                "classification": "neutral",
                "implication": "Normal market conditions",
                "risk_adjusted": "normal"
            }
        elif vix < 30:
            return {
                "level": "elevated",
                "classification": "cautious",
                "implication": "Elevated volatility - reduce position sizes",
                "risk_adjusted": "reduce_exposure"
            }
        else:
            return {
                "level": "high",
                "classification": "fear",
                "implication": "High volatility - avoid new positions",
                "risk_adjusted": "close_positions"
            }

    @staticmethod
    def analyze_market_phase(
        prices: List[float],
        vix: float = None
    ) -> MarketPhase:
        """Determine overall market phase"""
        trend = PatternRecognition.detect_trend(prices)

        if vix and vix > 30:
            return MarketPhase.VOLATILE
        elif trend == "bullish":
            return MarketPhase.BULLISH
        elif trend == "bearish":
            return MarketPhase.BEARISH
        return MarketPhase.NEUTRAL


def generate_market_report(
    symbol: str,
    prices: List[float],
    vix: float = None
) -> Dict[str, Any]:
    """
    Generate comprehensive market environment report.

    This is the main function used by the L2 Macro Analyst.
    """
    logger.info(f"Generating market report for {symbol}")

    # Calculate indicators
    current_price = prices[-1] if prices else 0
    sma_20 = TechnicalIndicators.sma(prices, 20)
    sma_50 = TechnicalIndicators.sma(prices, 50) if len(prices) >= 50 else sma_20
    rsi = TechnicalIndicators.rsi(prices)
    macd = TechnicalIndicators.macd(prices)
    bb = TechnicalIndicators.bollinger_bands(prices)

    # Determine phase
    phase = MarketEnvironment.analyze_market_phase(prices, vix)

    # VIX analysis
    vix_analysis = MarketEnvironment.analyze_vix(vix or 15)

    # Trend detection
    trend = PatternRecognition.detect_trend(prices)

    report = {
        "symbol": symbol,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "phase": phase.value,
        "trend": trend,
        "price": current_price,
        "indicators": {
            "sma_20": sma_20,
            "sma_50": sma_50,
            "rsi": rsi,
            "macd": macd,
            "bollinger_bands": bb,
            "position": "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral"
        },
        "vix": {
            "level": vix,
            "analysis": vix_analysis
        },
        "market_hours": {
            "open": MarketHours.get_open_markets()
        },
        "outlook": {
            "short_term": "bullish" if trend == "bullish" and rsi < 70 else "bearish" if trend == "bearish" and rsi > 30 else "neutral",
            "confidence": 0.75
        }
    }

    logger.info(f"Market report generated: {phase.value}, RSI: {rsi:.1f}")
    return report
