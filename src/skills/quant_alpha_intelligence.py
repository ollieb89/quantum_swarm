"""
src.skills.quant_alpha_intelligence — Centralized technical indicator skill.

Provides a unified interface for calculating RSI, MACD, and Bollinger Bands
with strict validation, nested output, and error handling.
"""

import logging
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Skill registry interface
SKILL_INTENT = "quant-alpha-intelligence"


class TechnicalIndicators:
    """Robust technical analysis indicator calculations."""

    @staticmethod
    def _round(val: Any) -> Any:
        """Round values to 8 decimal places for precision compliance."""
        if isinstance(val, float):
            return round(val, 8)
        if isinstance(val, dict):
            return {k: TechnicalIndicators._round(v) for k, v in val.items()}
        if isinstance(val, list):
            return [TechnicalIndicators._round(v) for v in val]
        return val

    def rsi(self, prices: List[float], period: int = 14, full: bool = False) -> Union[float, List[float]]:
        """Relative Strength Index (Wilder's Smoothing)."""
        if not prices:
            raise ValueError("RSI requires a non-empty price series.")
        if len(prices) < period + 1:
            raise ValueError(f"RSI({period}) requires at least {period+1} data points; received {len(prices)}.")

        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Initial average gain/loss (SMA for the first period)
        up = [d if d > 0 else 0 for d in deltas[:period]]
        down = [-d if d < 0 else 0 for d in deltas[:period]]
        
        avg_gain = sum(up) / period
        avg_loss = sum(down) / period
        
        def calculate_rsi_val(g, l):
            if g == 0 and l == 0:
                return 50.0  # Neutral for constant series
            if l == 0:
                return 100.0
            rs = g / l
            return 100.0 - (100.0 / (1.0 + rs))

        rsi_series = [calculate_rsi_val(avg_gain, avg_loss)]
        
        # Wilder's Smoothed averages: (prev_avg * (N-1) + current) / N
        for i in range(period, len(deltas)):
            d = deltas[i]
            gain = d if d > 0 else 0
            loss = -d if d < 0 else 0
            
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
            
            rsi_series.append(calculate_rsi_val(avg_gain, avg_loss))
        
        result = rsi_series if full else rsi_series[-1]
        return self._round(result)

    def macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9, full: bool = False) -> Union[Dict[str, float], List[Dict[str, float]]]:
        """MACD (Moving Average Convergence Divergence)."""
        if not prices:
            raise ValueError("MACD requires a non-empty price series.")
        if len(prices) < slow + signal:
            raise ValueError(f"MACD({fast},{slow},{signal}) requires at least {slow+signal} data points; received {len(prices)}.")

        def ema_series(data: List[float], p: int) -> List[float]:
            alpha = 2 / (p + 1)
            ema = [data[0]]
            for i in range(1, len(data)):
                ema.append(data[i] * alpha + ema[-1] * (1 - alpha))
            return ema

        fast_ema = ema_series(prices, fast)
        slow_ema = ema_series(prices, slow)
        
        macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
        signal_line = ema_series(macd_line, signal)
        histogram = [m - s for m, s in zip(macd_line, signal_line)]
        
        combined = []
        for i in range(len(macd_line)):
            combined.append({
                "macd": macd_line[i],
                "signal": signal_line[i],
                "histogram": histogram[i]
            })
            
        result = combined if full else combined[-1]
        return self._round(result)

    def bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2.0, full: bool = False) -> Union[Dict[str, float], List[Dict[str, float]]]:
        """Bollinger Bands with Bandwidth."""
        if not prices:
            raise ValueError("Bollinger Bands require a non-empty price series.")
        if len(prices) < period:
            raise ValueError(f"Bollinger Bands({period}) requires at least {period} data points; received {len(prices)}.")

        bands = []
        for i in range(period - 1, len(prices)):
            window = prices[i - period + 1 : i + 1]
            sma = sum(window) / period
            # statistics.stdev requires at least 2 data points
            std = statistics.stdev(window) if len(window) > 1 else 0.0
            
            upper = sma + (std_dev * std)
            lower = sma - (std_dev * std)
            bandwidth = (upper - lower) / sma if sma != 0 else 0.0
            
            bands.append({
                "upper": upper,
                "middle": sma,
                "lower": lower,
                "bandwidth": bandwidth
            })
            
        result = bands if full else bands[-1]
        return self._round(result)

    def atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14, full: bool = False) -> Union[float, List[float]]:
        """Average True Range (Wilder's Smoothing)."""
        if not highs or not lows or not closes:
            raise ValueError("ATR requires 'high', 'low', and 'close' series.")
        if not (len(highs) == len(lows) == len(closes)):
            raise ValueError("ATR series (high, low, close) must be of equal length.")
        if len(highs) < period + 1:
            raise ValueError(f"ATR({period}) requires at least {period+1} data points; received {len(highs)}.")

        tr = []
        for i in range(1, len(highs)):
            tr.append(max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            ))
            
        # Initial ATR is SMA of TR for the first period
        atr_series = [sum(tr[:period]) / period]
        
        # Wilder's Smoothed ATR: (prev_atr * (N-1) + current_tr) / N
        for i in range(period, len(tr)):
            atr_series.append((atr_series[-1] * (period - 1) + tr[i]) / period)
            
        result = atr_series if full else atr_series[-1]
        return self._round(result)


# Indicator Registry for future expansion (Phase 8+)
def _get_indicators_instance():
    return TechnicalIndicators()


INDICATOR_REGISTRY = {
    "rsi": lambda calc, series, params, full: calc.rsi(series.get("close", []), params.get("period", 14), full),
    "macd": lambda calc, series, params, full: calc.macd(
        series.get("close", []), 
        params.get("fast", 12), 
        params.get("slow", 26), 
        params.get("signal", 9),
        full
    ),
    "bollinger_bands": lambda calc, series, params, full: calc.bollinger_bands(
        series.get("close", []), 
        params.get("period", 20), 
        params.get("std_dev", 2.0),
        full
    ),
    "atr": lambda calc, series, params, full: calc.atr(
        series.get("high", []),
        series.get("low", []),
        series.get("close", []),
        params.get("period", 14),
        full
    )
}


def handle(state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a quant-alpha-intelligence intent."""
    series = state.get("series", {})
    indicator_requests = state.get("indicators", [])
    full_series = state.get("full_series", False)
    
    if not series or not indicator_requests:
        return {
            "status": "error",
            "error": {"code": "INVALID_INPUT", "message": "Missing 'series' or 'indicators' list."}
        }
        
    calculator = _get_indicators_instance()
    results = {}
    metadata = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "series_length": len(series.get("close", []) or series.get("high", []) or []),
        "indicator_params": {}
    }
    
    for req in indicator_requests:
        name = req.get("name")
        params = req.get("params", {})

        # Build result key using {name}_{period} convention
        period = params.get("period", "")
        key = f"{name}_{period}" if period else name

        if name not in INDICATOR_REGISTRY:
            results[key] = {"error": {"code": "UNKNOWN_INDICATOR", "message": f"Indicator '{name}' is not supported."}}
            continue

        try:
            # Validate safe ranges for periods
            for p_name, p_val in params.items():
                if any(k in p_name for k in ["period", "fast", "slow", "signal"]):
                    if not (2 <= p_val <= 250):
                        raise ValueError(f"Parameter '{p_name}'={p_val} is outside safe range [2, 250].")

            result = INDICATOR_REGISTRY[name](calculator, series, params, full_series)

            # Annotate RSI with machine-readable state (only for scalar, not full series)
            if name == "rsi" and not full_series:
                rsi_val = result
                if rsi_val > 70:
                    rsi_state = "overbought"
                elif rsi_val < 30:
                    rsi_state = "oversold"
                else:
                    rsi_state = "neutral"
                result = {"value": rsi_val, "state": rsi_state}

            results[key] = result
            metadata["indicator_params"][key] = params

        except ValueError as e:
            msg = str(e)
            code = "INSUFFICIENT_DATA" if "requires at least" in msg else "INVALID_INPUT"
            results[key] = {"error": {"code": code, "message": msg}}
        except Exception as e:
            logger.exception("Error calculating indicator %s", name)
            results[key] = {"error": {"code": "CALCULATION_ERROR", "message": str(e)}}
            
    return {
        "status": "ok",
        "results": results,
        "metadata": metadata
    }
