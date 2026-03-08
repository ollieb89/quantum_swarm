# Phase 8 Context: Portfolio Risk Governance

Implementation decisions for aggregate portfolio constraints and pre-trade risk scoring.

## 1. Portfolio Risk Limits
- **Max Notional Exposure**: Global limit on total dollar value of all open positions.
- **Max Asset Concentration**: Limit on exposure to a single ticker (e.g., max 20% of portfolio).
- **Max Concurrent Trades**: Limit on the number of open positions.
- **Drawdown Circuit Breaker**: Hard stop if daily/weekly drawdown exceeds a threshold.

## 2. Pre-Trade Risk Scoring
- **Risk Score (0.0 to 1.0)**: Normalized metric based on:
    - Stop-loss distance.
    - Historical volatility (ATR).
    - Current portfolio "heat" (existing exposure).
    - Confidence of the proposing agents.
- **Auditability**: The risk score and its components will be recorded in the `trades` table.

## 3. Implementation Point
- **InstitutionalGuard**: `src/security/institutional_guard.py` will be the primary engine.
- **Data Source**: Needs access to current "open positions". For now, we will query the `trades` table for entries without an `exit_time`.

## Requirements Mapping
- **RISK-07**: Aggregate portfolio constraints.
- **RISK-08**: Pre-trade risk scoring and logging.
