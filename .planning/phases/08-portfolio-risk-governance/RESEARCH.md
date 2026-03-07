# Phase 8: Portfolio Risk Governance - Research

**Researched:** 2026-03-07
**Domain:** Python / psycopg3 / PostgreSQL / LangGraph / InstitutionalGuard
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Max Notional Exposure: global limit on total dollar value of all open positions.
- Max Asset Concentration: limit on exposure to a single ticker (e.g., max 20% of portfolio).
- Max Concurrent Trades: limit on the number of open positions.
- Drawdown Circuit Breaker: hard stop if daily/weekly drawdown exceeds a threshold (config-driven).
- Risk Score (0.0 to 1.0): normalized metric based on stop-loss distance, ATR, current portfolio heat, and agent confidence.
- Auditability: risk score and components recorded in the `trades` table.
- Implementation point: `src/security/institutional_guard.py` is the primary engine.
- Open positions data source: query `trades` table for entries WHERE exit_time IS NULL.

### Claude's Discretion
- (None listed in CONTEXT.md)

### Deferred Ideas (OUT OF SCOPE)
- (None listed in CONTEXT.md)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RISK-07 | Aggregate portfolio constraints — reject orders exceeding max notional exposure or asset concentration | InstitutionalGuard.check_compliance() is already wired; DB schema already has the columns; all 6 existing tests pass. Gap: no drawdown circuit breaker, no index on exit_time. |
| RISK-08 | Pre-trade risk scoring and logging — portfolio-level risk score calculated and recorded for every trade | calculate_risk_score() already exists and returns 0.0-1.0; trade_logger_node reads trade_risk_score and portfolio_heat from state["metadata"] and writes them to PostgreSQL. Gap: no test verifying the round-trip from institutional_guard_node into the metadata dict used by trade_logger. |
</phase_requirements>

---

## Summary

Phase 8 is almost entirely pre-implemented. The codebase reached a "plan-ahead" state where a previous planning pass wrote the full logic into `src/security/institutional_guard.py`, `src/graph/agents/l3/trade_logger.py`, `src/models/data_models.py`, and `src/core/persistence.py` before any formal phase execution.

All 6 tests in `tests/test_portfolio_risk.py` (3 tests) and `tests/test_institutional_guard.py` (3 tests) pass. The DB schema already includes `trade_risk_score NUMERIC` and `portfolio_heat NUMERIC` columns. The TradeRecord Pydantic model already carries these fields. The trade_logger_node already reads them from `state["metadata"]` and writes them to PostgreSQL.

**The planning problem is therefore verification and gap-closure, not net-new implementation.** The planner must confirm (a) what is already working, (b) the two genuine gaps below, and (c) write tests that prove RISK-07 and RISK-08 are fully satisfied end-to-end.

**Primary recommendation:** Treat Phase 8 as a verification + gap-closure phase. Identify the two concrete gaps (exit_time index, drawdown circuit breaker), close them, and add integration-style tests that prove the full rejection-to-logging pipeline works.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| psycopg3 (psycopg) | Project standard | Async PostgreSQL — `_get_open_positions()` query | Already used throughout; pool via `src/core/db.get_pool()` |
| psycopg_pool | Project standard | AsyncConnectionPool for DB access | Already configured |
| pydantic v2 | Project standard | TradeRecord model with `trade_risk_score`, `portfolio_heat` fields | `model_dump(mode="json")` pattern established |
| LangGraph | Project standard | SwarmState + node return dict pattern | `institutional_guard_node` already a LangGraph-compatible async node |
| pytest + unittest.mock | Project standard | AsyncMock for DB; `asyncio.run()` for sync test wrappers | Existing tests use `asyncio.run()` + `patch.object(..., new_callable=AsyncMock)` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python asyncio | 3.12 stdlib | `asyncio.new_event_loop()` in TestCase subclasses | Only when inheriting `unittest.TestCase` — plain test functions use `asyncio.run()` |

**Installation:** No new dependencies. All libraries are already in the project venv.

---

## Architecture Patterns

### Existing Project Structure (relevant paths)
```
src/
├── security/
│   └── institutional_guard.py   # InstitutionalGuard class + institutional_guard_node
├── graph/
│   └── agents/l3/
│       └── trade_logger.py      # trade_logger_node — reads metadata, writes to DB
├── core/
│   ├── db.py                    # get_pool() — psycopg3 AsyncConnectionPool
│   └── persistence.py           # setup_persistence() — CREATE TABLE IF NOT EXISTS trades
├── models/
│   └── data_models.py           # TradeRecord Pydantic model
tests/
├── test_institutional_guard.py  # 3 passing tests
└── test_portfolio_risk.py       # 3 passing tests
config/
└── swarm_config.yaml            # risk_limits section with all portfolio constraint values
```

### Pattern 1: Async DB Mock in Tests
**What:** Patch `InstitutionalGuard._get_open_positions` with `AsyncMock` to avoid live PostgreSQL.
**When to use:** Any test of `check_compliance()`, `institutional_guard_node()`, or trade_logger_node.
**Example:**
```python
# Source: tests/test_portfolio_risk.py (existing, passing)
with patch.object(InstitutionalGuard, "_get_open_positions",
                  new_callable=AsyncMock) as mock_get:
    mock_get.return_value = open_positions
    result = await self.guard.check_compliance(state)
```

### Pattern 2: Sync test wrapper using asyncio.new_event_loop()
**What:** `unittest.TestCase` subclasses cannot use `asyncio.run()` inside test methods; use `loop.run_until_complete()` via a fresh loop instead.
**When to use:** Any TestCase class that inherits from `unittest.TestCase` and calls async code.
**Example:**
```python
# Source: tests/test_portfolio_risk.py (existing)
def test_exposure_rejection(self):
    loop = asyncio.new_event_loop()
    loop.run_until_complete(self._async_test_exposure_rejection())
```

### Pattern 3: State metadata passthrough for risk metrics
**What:** `institutional_guard_node` writes `trade_risk_score` and `portfolio_heat` into `state["metadata"]`. `trade_logger_node` reads them from `meta = state.get("metadata", {})`.
**When to use:** Any time guard output must be available downstream in the graph.
**Example:**
```python
# Source: src/security/institutional_guard.py line 143-147
return {
    "compliance_flags": compliance_flags,
    "metadata": {
        **state.get("metadata", {}),
        "trade_risk_score": result.get("risk_score"),
        "portfolio_heat": result.get("portfolio_heat")
    }
}
```

### Anti-Patterns to Avoid
- **Importing from `src.core.db` at module level in tests:** The pool is lazily initialized; importing triggers nothing, but calling `get_pool()` without a real DB will fail. Always mock `_get_open_positions`.
- **Using `asyncio.run()` inside `unittest.TestCase` methods:** This raises "Event loop is closed" on Python 3.12. Use `asyncio.new_event_loop()` + `loop.run_until_complete()` or refactor to plain functions (which can use `asyncio.run()`).
- **Querying `trades` without an index on `exit_time`:** The `_get_open_positions()` query filters on `exit_time IS NULL` but `src/core/persistence.py` only creates indexes on `task_id` and `symbol`. No `idx_trades_exit_time` exists yet — this is a genuine gap.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DB connection pooling | Custom pool management | `src/core/db.get_pool()` | Already an AsyncConnectionPool singleton; used by all other nodes |
| Trade record serialization | Custom JSON encoder | `TradeRecord.model_dump(mode="json")` | Pydantic v2 handles datetime ISO serialization |
| Portfolio heat calculation | Separate service | Inline in `InstitutionalGuard.check_compliance()` | Already calculated as `current_total_notional / self.max_notional_exposure` |

---

## Common Pitfalls

### Pitfall 1: Column name mismatch — `quantity` vs `position_size`, `execution_price` vs `entry_price`
**What goes wrong:** Tests or SQL queries reference old column names from the Phase 3 schema that were renamed in Phase 6.
**Why it happens:** The `_get_open_positions()` query selects `quantity` and `execution_price` (old names) but the `trades` DDL in `persistence.py` uses `position_size` and `entry_price` (Phase 6 names).
**How to avoid:** Confirm the SQL in `_get_open_positions()` matches the DDL. Current implementation at line 34 uses `SELECT symbol, quantity, execution_price FROM trades` — these column names DO NOT match the DDL which has `position_size` and `entry_price`. This is a latent bug.
**Warning signs:** SQL error `column "quantity" does not exist` on live DB; tests pass because they mock `_get_open_positions()` and never hit real SQL.

### Pitfall 2: `_get_open_positions()` SQL column name bug (confirmed)
**What goes wrong:** The live path of `_get_open_positions()` will fail with a PostgreSQL error because it selects `quantity` and `execution_price` — column names that no longer exist in the `trades` table (renamed to `position_size` and `entry_price` in Phase 6).
**How to avoid:** Fix the query to `SELECT symbol, position_size, entry_price FROM trades WHERE exit_time IS NULL;` and update the dict keys accordingly (`quantity` → `position_size`, `price` → `entry_price` or keep mapping internally).
**Note:** All existing tests mock `_get_open_positions()` and never expose this bug. A live integration test would catch it.

### Pitfall 3: Missing exit_time index
**What goes wrong:** As trade history grows, the `WHERE exit_time IS NULL` query performs a full table scan.
**How to avoid:** Add `CREATE INDEX IF NOT EXISTS idx_trades_exit_time ON trades(exit_time);` to `setup_persistence()`.

### Pitfall 4: Drawdown circuit breaker not implemented
**What goes wrong:** `swarm_config.yaml` defines `max_daily_loss: 0.05` and `max_drawdown: 0.15`, and the CONTEXT.md lists "Drawdown Circuit Breaker" as a locked requirement, but `check_compliance()` does not enforce it.
**How to avoid:** Implement drawdown check using closed positions P&L from the `trades` table. The SQL pattern is: `SELECT SUM(pnl) FROM trades WHERE exit_time >= NOW() - INTERVAL '1 day'`.

### Pitfall 5: Risk score not verified end-to-end
**What goes wrong:** `test_risk_scoring_logic` verifies `calculate_risk_score()` in isolation. No test verifies that after `institutional_guard_node()` runs, the `metadata` dict contains the right keys that `trade_logger_node` would pick up.
**How to avoid:** Add a test for `institutional_guard_node()` approval path that asserts `update["metadata"]["trade_risk_score"]` is a float and `update["metadata"]["portfolio_heat"]` is a float — this is RISK-08's auditability requirement.

---

## Code Examples

### Corrected _get_open_positions() SQL (fix the bug)
```python
# Fix: use Phase 6 column names position_size and entry_price
query = "SELECT symbol, position_size, entry_price FROM trades WHERE exit_time IS NULL;"
# ... in the row loop:
open_trades.append({
    "symbol": row[0],
    "quantity": float(row[1]),   # keep dict key "quantity" for internal use
    "price": float(row[2])       # keep dict key "price" for internal use
})
```

### Adding the exit_time index to persistence.py
```python
# Source: src/core/persistence.py pattern — add after existing indexes
CREATE INDEX IF NOT EXISTS idx_trades_exit_time ON trades(exit_time);
```

### Drawdown circuit breaker query pattern (psycopg3 async)
```python
async with pool.connection() as conn:
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT COALESCE(SUM(pnl), 0.0) FROM trades WHERE exit_time >= NOW() - INTERVAL '1 day'"
        )
        row = await cur.fetchone()
        daily_pnl = float(row[0])
daily_loss_pct = abs(daily_pnl) / self.starting_capital
if daily_pnl < 0 and daily_loss_pct > self.max_daily_loss:
    return {"approved": False, "violation": f"Daily drawdown {daily_loss_pct:.1%} exceeds limit {self.max_daily_loss:.1%}"}
```

### Test pattern: verify risk score propagates into metadata
```python
# Source: tests/test_institutional_guard.py approval pattern + metadata assertion
def test_institutional_guard_node_risk_score_in_metadata():
    config = {
        "risk_limits": {
            "starting_capital": 1000000.0,
            "max_notional_exposure": 500000.0,
            "max_asset_concentration_pct": 0.20,
            "max_concurrent_trades": 10,
        }
    }
    state = {
        "quant_proposal": {
            "symbol": "BTC/USDT",
            "entry_price": 50000.0,
            "quantity": 1.0,
            "stop_loss": 47500.0,
            "confidence": 0.8,
        },
        "compliance_flags": [],
        "metadata": {},
    }
    with patch.object(InstitutionalGuard, "_get_open_positions",
                      new_callable=AsyncMock, return_value=[]):
        update = asyncio.run(institutional_guard_node(state, config))
    assert isinstance(update["metadata"]["trade_risk_score"], float)
    assert isinstance(update["metadata"]["portfolio_heat"], float)
    assert 0.0 <= update["metadata"]["trade_risk_score"] <= 1.0
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Column names: `quantity`, `execution_price` | Phase 6 renamed to `position_size`, `entry_price` | Phase 6 (2026-03-07) | `_get_open_positions()` SQL is stale — must be updated |
| No portfolio-level columns in `trades` | `trade_risk_score NUMERIC, portfolio_heat NUMERIC` added | Phase 6 DDL extension | Already in schema; no migration needed for fresh DBs |
| No drawdown enforcement in InstitutionalGuard | Still missing (gap) | — | Needs implementation to satisfy CONTEXT.md |

**Deprecated/outdated:**
- `_get_open_positions()` SQL `SELECT symbol, quantity, execution_price` — stale column names from pre-Phase-6 schema. Must be updated to `position_size, entry_price`.

---

## Open Questions

1. **Drawdown circuit breaker — daily vs weekly?**
   - What we know: CONTEXT.md says "daily/weekly drawdown". `swarm_config.yaml` defines `max_daily_loss: 0.05` and `max_drawdown: 0.15`.
   - What's unclear: Should the guard check both simultaneously, or daily only for now?
   - Recommendation: Implement daily drawdown check using `max_daily_loss` from config (5%). Weekly/cumulative drawdown can use `max_drawdown` (15%) against starting capital.

2. **Drawdown calculation basis**
   - What we know: `pnl` column in `trades` is populated by the trade logger but may be NULL for open/paper trades.
   - What's unclear: Can we rely on `pnl` being populated for closed positions in the paper trading path?
   - Recommendation: Guard against NULL with `COALESCE(SUM(pnl), 0.0)`. If pnl is consistently NULL, drawdown check is effectively disabled (safe-fail behaviour).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/test_portfolio_risk.py tests/test_institutional_guard.py -v` |
| Full suite command | `.venv/bin/python3.12 -m pytest --tb=short -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RISK-07 | Orders exceeding max notional exposure are rejected | unit | `.venv/bin/python3.12 -m pytest tests/test_portfolio_risk.py::TestPortfolioRisk::test_exposure_rejection -v` | Yes (passing) |
| RISK-07 | Orders exceeding asset concentration are rejected | unit | `.venv/bin/python3.12 -m pytest tests/test_portfolio_risk.py::TestPortfolioRisk::test_concentration_rejection -v` | Yes (passing) |
| RISK-07 | Drawdown circuit breaker rejects over-threshold | unit | `.venv/bin/python3.12 -m pytest tests/test_portfolio_risk.py::TestPortfolioRisk::test_drawdown_rejection -v` | No — Wave 0 gap |
| RISK-08 | Risk score is computed and returned in node metadata | unit | `.venv/bin/python3.12 -m pytest tests/test_institutional_guard.py::test_institutional_guard_node_risk_score_in_metadata -v` | No — Wave 0 gap |
| RISK-08 | Risk score is readable from trade_logger perspective | unit | `.venv/bin/python3.12 -m pytest tests/test_portfolio_risk.py::TestPortfolioRisk::test_risk_scoring_logic -v` | Yes (passing — isolated) |

### Sampling Rate
- **Per task commit:** `.venv/bin/python3.12 -m pytest tests/test_portfolio_risk.py tests/test_institutional_guard.py -v`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest --tb=short -q`
- **Phase gate:** Full suite green (181 currently passing, 5 pre-existing failures in test_order_router.py and test_persistence.py — do not regress)

### Wave 0 Gaps
- [ ] `tests/test_portfolio_risk.py::TestPortfolioRisk::test_drawdown_rejection` — covers RISK-07 drawdown arm
- [ ] `tests/test_institutional_guard.py::test_institutional_guard_node_risk_score_in_metadata` — covers RISK-08 auditability

*(Existing test infrastructure covers all other phase requirements)*

---

## Sources

### Primary (HIGH confidence)
- Direct source inspection: `src/security/institutional_guard.py` — full implementation read
- Direct source inspection: `src/core/persistence.py` — DDL schema confirmed
- Direct source inspection: `src/models/data_models.py` — TradeRecord fields confirmed
- Direct source inspection: `src/graph/agents/l3/trade_logger.py` — metadata passthrough confirmed
- Direct test execution: `tests/test_portfolio_risk.py` + `tests/test_institutional_guard.py` — 6/6 passing verified
- Direct source inspection: `config/swarm_config.yaml` — risk_limits section confirmed
- Direct source inspection: `.planning/phases/08-portfolio-risk-governance/08-CONTEXT.md`

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` accumulated context section — column rename history (Phase 6), psycopg3 async patterns, AsyncMock test patterns

### Tertiary (LOW confidence)
- (None — all findings verified directly from source)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed in existing code
- Architecture: HIGH — patterns extracted from existing passing tests
- Pitfalls: HIGH — column name bug is directly observable in source; confirmed by DDL vs SQL comparison
- Drawdown gap: HIGH — absence confirmed by reading full `check_compliance()` method

**Research date:** 2026-03-07
**Valid until:** 2026-04-07 (stable codebase; only invalidated if persistence.py DDL or trades schema changes)
