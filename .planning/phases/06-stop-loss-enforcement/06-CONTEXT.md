# Phase 6 Context: Stop-Loss Enforcement

Implementation decisions for mandatory ATR-based stop-loss calculation and enforcement.

## 1. Stop-Loss Policy
- **Primary Mechanism**: ATR-based stop-loss.
- **Formula**: `stop_loss = entry_price - (ATR * multiplier)` for Longs, `stop_loss = entry_price + (ATR * multiplier)` for Shorts.
- **Default Multiplier**: 2.0 (Standard for swing/trend following).
- **Flexibility**: Agents can override the multiplier (range: 1.0 to 5.0) but cannot submit without a stop-loss.

## 2. Enforcement Points (Hard Gates)
- **QuantModeler**: Must include `stop_loss` in the `quant_proposal`.
- **OrderRouter**: The L3 executor will reject any order payload where `stop_loss` is missing or null.
- **RiskManager**: Validates that the stop-loss is present and consistent with the trade side (e.g., below entry for long).

## 3. Data & Auditability
- **PostgreSQL**: The `trades` table must be updated to include a `stop_loss` column.
- **Audit Logs**: The `audit_logs` entry for the trade must contain the calculated stop-loss level.
- **Metadata**: Store the `atr_multiplier` used in the `strategy_context` JSONB column.

## 4. Implementation Strategy (Phase 6A)
- **Calculation**: Use the `calculate_indicators` tool (from Phase 5) to get the current ATR.
- **Attachment**: The `QuantModeler` is responsible for fetching ATR and attaching the `stop_loss` to the proposal.
- **Validation**: `OrderRouter` acts as the final compliance gate.

## Out of Scope (for Phase 6)
- **Real-time Monitoring**: Automatic exit execution during the trade is deferred to post-v1.1.
- **Trailing Stops**: Dynamic stop-loss updates are deferred.

## Requirements Mapping
- **RISK-03**: ATR-based stop-loss calculation.
- **RISK-05**: OrderRouter hard gate/rejection.
- **RISK-06**: PostgreSQL recording.
