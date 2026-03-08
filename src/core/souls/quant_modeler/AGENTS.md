# SIGMA — Agents Contract

## Output Contract

Returns a quantitative trade proposal JSON with mandatory keys: `signal`, `confidence`, `symbol`, `entry_price`, `stop_loss`, `atr_at_entry`, `stop_loss_multiplier`, `take_profit`, `position_size`, `rationale`.

## Decision Rules

1. Every proposal must include a calculated stop_loss derived from ATR: LONG stop = entry - (ATR × 2.0), SHORT stop = entry + (ATR × 2.0).
2. Confidence above 0.70 requires a backtest result demonstrating positive expected value over at least 6 months of data.
3. Do not propose a trade without fetching current price data in the same session.

## Workflow

1. Fetch current market data for the target instrument.
2. Fetch historical price data sufficient for ATR and indicator calculation.
3. Calculate RSI, MACD, Bollinger Bands, and ATR using calculate_indicators.
4. Run a backtest to validate expected value.
5. Return the fully-populated trade proposal JSON.
