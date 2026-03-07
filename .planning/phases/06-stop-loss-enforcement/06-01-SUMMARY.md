---
phase: 06-stop-loss-enforcement
plan: "01"
subsystem: trading
tags: [stop-loss, atr, order-routing, compliance, postgresql, psycopg3, trade-warehouse]

# Dependency graph
requires:
  - phase: 05-quant-alpha-intelligence
    provides: ATR calculation via quant_alpha_intelligence skill and calculate_indicators tool

provides:
  - ATR-based stop_loss field mandated in every QuantModeler trade proposal
  - Compliance gate in OrderRouter that rejects orders missing or directionally invalid stop_loss
  - stop_loss_level, atr_at_entry, stop_loss_multiplier, stop_loss_method columns in trades table
  - TradeLogger persists full stop-loss audit trail to PostgreSQL trades warehouse
  - 7 tests verifying enforcement and DB persistence

affects:
  - 07-self-improvement-loop
  - any phase reading from the trades table

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Compliance gate pattern: raise ValueError with explicit Compliance Error message before any order execution
    - Directional stop-loss validation: LONG must be below entry, SHORT must be above entry
    - AsyncMock DB test pattern: patch get_pool() to capture INSERT params without live PostgreSQL

key-files:
  created:
    - tests/test_stop_loss_enforcement.py
  modified:
    - src/core/persistence.py
    - src/models/data_models.py
    - src/graph/agents/analysts.py
    - src/agents/l3_executor.py
    - src/graph/agents/l3/order_router.py
    - src/graph/agents/l3/trade_logger.py

key-decisions:
  - "ATR multiplier 2.0 as default: LONG stop_loss = entry_price - (ATR * 2.0), SHORT = entry_price + (ATR * 2.0)"
  - "Compliance gate raises ValueError not returns error dict — prevents silent failure propagation"
  - "DB schema auto-fix: added atr_at_entry, stop_loss_multiplier, stop_loss_method, trade_risk_score, portfolio_heat columns that trade_logger INSERT required but schema was missing"

patterns-established:
  - "Compliance gate: validate mandatory fields in execute() before any routing logic"
  - "Directional validation: LONG stop must be below entry, SHORT stop must be above entry"
  - "DB test: use patch.object(module, 'get_pool', return_value=mock_pool) with side_effect capture on execute()"

requirements-completed: [RISK-03, RISK-05, RISK-06]

# Metrics
duration: 15min
completed: 2026-03-07
---

# Phase 6: Stop-Loss Enforcement Summary

**ATR-based stop_loss enforced end-to-end: QuantModeler mandates it in proposals, OrderRouter rejects missing/invalid values with compliance errors, TradeLogger writes stop_loss_level + ATR metadata to PostgreSQL trades warehouse**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-07T20:30:00Z
- **Completed:** 2026-03-07T20:45:00Z
- **Tasks:** 5
- **Files modified:** 7

## Accomplishments
- QuantModeler system prompt updated to mandate ATR calculation with 2.0x multiplier for LONG and SHORT
- OrderRouter compliance gate rejects orders with None/missing stop_loss or directionally invalid values (LONG stop above entry, SHORT stop below entry)
- TradeLogger writes stop_loss_level, atr_at_entry, stop_loss_multiplier, stop_loss_method to trades table
- PostgreSQL schema extended with all stop-loss audit columns
- 7 tests covering OrderRouter enforcement (5 cases) and DB persistence (2 mock cases)

## Task Commits

Each task was committed atomically:

1. **Step 1: DB schema + TradeRecord model** - `7d51359` (feat)
2. **Step 2: QuantModeler ATR prompt** - `a49c86d` (feat)
3. **Step 3: OrderRouter compliance gate** - `4758835` (feat)
4. **Step 4: TradeLogger stop_loss persistence** - `cf157ad` (feat)
5. **Step 5: Verification tests** - `22082ab` (test)

## Files Created/Modified
- `src/core/persistence.py` - Added atr_at_entry, stop_loss_multiplier, stop_loss_method, trade_risk_score, portfolio_heat columns to trades CREATE TABLE
- `src/models/data_models.py` - TradeRecord already had stop-loss fields (verified in sync)
- `src/graph/agents/analysts.py` - QuantModeler prompt mandates ATR stop_loss calculation with multiplier 2.0
- `src/agents/l3_executor.py` - OrderRouter.execute() compliance gate: None check + directional validation
- `src/graph/agents/l3/order_router.py` - order_router_node passes stop_loss from quant_proposal to executor
- `src/graph/agents/l3/trade_logger.py` - Extracts and persists stop_loss, atr_at_entry, stop_loss_multiplier
- `tests/test_stop_loss_enforcement.py` - 7 tests for OrderRouter gate and TradeLogger DB write

## Decisions Made
- Compliance gate raises `ValueError` with explicit "Compliance Error:" prefix rather than returning an error dict — prevents silent failure and produces clear audit messages
- Default ATR multiplier is 2.0 (plan specified); both LONG and SHORT formulas specified in QuantModeler prompt
- Added directional stop-loss validation as a correctness requirement: a LONG stop above entry price would immediately trigger, which is a logic error

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed DB schema out of sync with trade_logger INSERT**
- **Found during:** Step 1 (DB schema review)
- **Issue:** `trade_logger.py` INSERT included `atr_at_entry`, `stop_loss_multiplier`, `stop_loss_method`, `trade_risk_score`, `portfolio_heat` but `persistence.py` CREATE TABLE had none of these columns — live DB inserts would fail
- **Fix:** Added all 5 missing columns to the `trades` table DDL in `persistence.py` with migration comments
- **Files modified:** `src/core/persistence.py`
- **Verification:** INSERT tuple index 7 (stop_loss_level) verified via mock test
- **Committed in:** `7d51359` (Step 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - schema/code mismatch bug)
**Impact on plan:** Essential fix — trade persistence would have raised psycopg3 column-not-found errors in production. No scope creep.

## Issues Encountered
None — implementation was already complete in the working tree from prior work. Phase execution verified, extended tests, and fixed the schema gap.

## User Setup Required
None - no external service configuration required (DB column additions apply via `setup_persistence()` on next startup via `CREATE TABLE IF NOT EXISTS`).

Migration note for existing databases:
```sql
ALTER TABLE trades ADD COLUMN IF NOT EXISTS atr_at_entry NUMERIC;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS stop_loss_multiplier NUMERIC;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS stop_loss_method VARCHAR(32);
ALTER TABLE trades ADD COLUMN IF NOT EXISTS trade_risk_score NUMERIC;
ALTER TABLE trades ADD COLUMN IF NOT EXISTS portfolio_heat NUMERIC;
```

## Next Phase Readiness
- Phase 7 (Self-Improvement Loop) can proceed: trades table now has complete stop-loss audit trail
- Every trade flowing through the system will have stop_loss_level populated
- ATR metadata (atr_at_entry, multiplier, method) enables strategy review in weekly analysis

---
*Phase: 06-stop-loss-enforcement*
*Completed: 2026-03-07*
