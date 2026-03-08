# Research: Phase 6 - Stop-Loss Enforcement

## 1. Objectives
- Implement ATR-based stop-loss calculation in the `QuantModeler`.
- Enforce mandatory stop-loss presence in the `OrderRouter` (L3 executor).
- Record stop-loss data in the PostgreSQL trade warehouse.

## 2. Technical Findings

### 2.1 Integration Points
- **QuantModeler**: The `_get_quant_agent` in `src/graph/agents/analysts.py` uses `fetch_market_data` and `calculate_indicators`. It must be updated to use ATR for the `stop_loss` field in its JSON output.
- **OrderRouter**: Located in `src/agents/l3_executor.py`. Its `execute` method must be updated to validate the presence of `stop_loss` in the `order_params`.
- **Database Schema**: `src/core/persistence.py` needs a migration (or update) to add a `stop_loss` column to the `trades` table.
- **Trade Logging**: `src/graph/agents/l3/trade_logger.py` (referenced in `src/graph/orchestrator.py`) must be updated to pass the stop-loss to the database writer.

### 2.2 Requirement RISK-05 (Hard Gate)
- The `OrderRouter` should raise a `ValueError` (or a specific compliance exception) if `stop_loss` is missing.
- The `RiskManager` node in `src/graph/nodes/l1.py` can also act as an early gate before the trade reaches the executor.

### 2.3 Database Updates (Requirement RISK-06)
- The `trades` table schema needs the following columns:
    - `stop_loss` (NUMERIC)
    - `atr_multiplier` (NUMERIC, can be part of `strategy_context` or a separate column)

## 3. Implementation Strategy
1. **Schema Migration**: Update `src/core/persistence.py` and run it to update the database.
2. **QuantModeler Prompt**: Update the prompt in `src/graph/agents/analysts.py` to instruct the agent to fetch ATR and calculate the stop-loss.
3. **OrderRouter Logic**: Update `src/agents/l3_executor.py` to enforce the stop-loss requirement.
4. **Graph State**: Ensure `stop_loss` is passed through the LangGraph state (already exists in `SwarmState` but needs to be consistently populated).

## 4. Risks & Mitigations
- **Data Availability**: ATR calculation requires enough historical data. Mitigation: `QuantModeler` already has `fetch_historical_data`.
- **Agent Hallucination**: Agent might ignore the stop-loss instruction. Mitigation: Hard gate in `OrderRouter` will catch and reject the trade.
- **Schema Compatibility**: Adding columns to a live table. Mitigation: Use `ALTER TABLE IF NOT EXISTS` or standard idempotent SQL.
