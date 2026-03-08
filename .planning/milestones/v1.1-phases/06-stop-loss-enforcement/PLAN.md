# Plan: Phase 6 - Stop-Loss Enforcement

Implementation plan for mandatory ATR-based stop-loss calculation and enforcement.

## 1. Goal
Ensure every trade has an ATR-based stop-loss, enforce its presence at the execution gate, and persist it in the audit trail.

## 2. Implementation Steps

### Step 1: Update Database Schema
- **File**: `src/core/persistence.py`
- **Actions**:
    - Add `stop_loss_level NUMERIC` column to the `trades` table.
    - Run the persistence setup script to apply changes to PostgreSQL.
- **Dependencies**: None.

### Step 2: Update QuantModeler
- **File**: `src/graph/agents/analysts.py`
- **Actions**:
    - Enhance the `QuantModeler` system prompt to require ATR calculation for every trade proposal.
    - Specify the default multiplier (2.0) and how to calculate the `stop_loss` field based on `entry_price` and ATR.
- **Dependencies**: None.

### Step 3: Enforce Hard Gate in OrderRouter
- **File**: `src/agents/l3_executor.py`
- **Actions**:
    - Update `OrderRouter.execute()` to check for `stop_loss` in `order_params`.
    - If `stop_loss` is missing or null, raise a `ValueError` with an explicit compliance error message.
- **Dependencies**: None.

### Step 4: Record Stop-Loss in Trade Logger
- **Files**: `src/graph/agents/l3/trade_logger.py`, `src/graph/nodes/write_trade_memory.py`
- **Actions**:
    - Pass the `stop_loss` from the execution result/state to the `trades` table.
- **Dependencies**: Step 1.

### Step 5: Verification
- **File**: `tests/test_stop_loss_enforcement.py`
- **Actions**:
    - Test that `OrderRouter` rejects orders without `stop_loss`.
    - Test that `QuantModeler` includes `stop_loss` in its proposals.
    - Verify that `stop_loss` is written to the PostgreSQL `trades` table after a mock execution.
- **Dependencies**: Steps 1-4.

## 3. Success Criteria
1. `OrderRouter` raises an error for any order missing a `stop_loss`.
2. `QuantModeler` provides an ATR-based `stop_loss` in its trade proposals.
3. The `trades` table in PostgreSQL has a populated `stop_loss_level` for all new trades.

## 4. Rollback Plan
- Revert the prompt in `src/graph/agents/analysts.py`.
- Revert the enforcement logic in `src/agents/l3_executor.py`.
- (Optional) Keep the database column as it is backward compatible (nullable).
