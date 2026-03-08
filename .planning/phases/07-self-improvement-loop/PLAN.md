# Plan: Phase 7 - Self-Improvement Loop

Implementation plan for the automated strategy refinement loop.

## 1. Goal
Implement a self-improving system that analyzes trade outcomes, compares them to backtests, and generates institutional knowledge rules in `MEMORY.md`.

## 2. Implementation Steps

### Step 1: Stop-Loss Hardening (Prerequisites)
- **Database**: Add `atr_at_entry`, `stop_loss_multiplier`, `stop_loss_method` to `trades` table.
- **Models**: Update `TradeRecord` and `QuantProposal` (if applicable) to include these fields.
- **Enforcement**: Update `OrderRouter.execute()` to validate stop-loss direction and minimum distance.
- **Logger**: Update `trade_logger_node` to persist the new metadata.

### Step 2: Weekly Review Agent (MEM-02)
- **File**: `src/agents/review_agent.py`
- **Actions**:
    - Implement `PerformanceReviewAgent` using `gemini-2.0-flash`.
    - Functionality to query `trades` joined with `audit_logs`.
    - Generate "Performance Drift Report" JSON.
- **Dependencies**: Step 1.

### Step 3: Rule Generator (MEM-03)
- **File**: `src/agents/rule_generator.py`
- **Actions**:
    - Implement `RuleGenerator` to process drift reports.
    - Write PREFER/AVOID/CAUTION rules to `data/MEMORY.md`.
    - Add CLI command `/review` in `main.py` to trigger the pipeline.
- **Dependencies**: Step 2.

### Step 4: Memory Injection
- **File**: `src/graph/orchestrator.py`
- **Actions**:
    - Implement logic to read `data/MEMORY.md` during graph initialization.
    - Inject rules into `MacroAnalyst` and `QuantModeler` system prompts as "Institutional Memory".
- **Dependencies**: Step 3.

### Step 5: Verification
- **File**: `tests/test_self_improvement.py`
- **Actions**:
    - Verify stop-loss directional rejection.
    - Verify review agent can parse trade history and detect drift.
    - Verify rules are correctly appended to `MEMORY.md` and injected into agent prompts.
- **Dependencies**: Steps 1-4.

## 3. Success Criteria
1. `OrderRouter` rejects LONG with stop > entry.
2. `/review` command produces a drift report and at least one rule in `MEMORY.md` (given enough data).
3. Agents' system prompts contain the generated rules from `MEMORY.md`.

## 4. Rollback Plan
- Revert prompt injection logic in `src/graph/orchestrator.py`.
- Clear generated rules from `data/MEMORY.md`.
- Keep database columns (nullable).
