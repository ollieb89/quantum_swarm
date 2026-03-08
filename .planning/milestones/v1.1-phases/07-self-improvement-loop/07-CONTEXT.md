# Phase 7 Context: Self-Improvement Loop

Implementation decisions for the automated strategy refinement loop.

## 1. Stop-Loss Hardening (Prerequisite)
- **Validation**: `OrderRouter` will be updated to validate:
    - Directional correctness: `stop_loss < entry` for LONG, `stop_loss > entry` for SHORT.
    - Numerical validity: `abs(entry - stop_loss) > 0`.
- **Metadata**: `TradeRecord` and `trades` table will include:
    - `atr_at_entry`: The ATR value used for calculation.
    - `stop_loss_multiplier`: The multiplier applied.
    - `stop_loss_method`: Set to "atr" by default.

## 2. Weekly Review Agent (MEM-02)
- **Goal**: Compare actual live/paper P&L against the `backtest_result` stored in the strategy context.
- **Input**: `trades` table data, `audit_logs` for rationale, and `backtest_result` metadata.
- **Output**: A structured "Performance Drift Report" identifying over/under-performing strategies and regimes.

## 3. Rule Generator (MEM-03)
- **Goal**: Translate the Drift Report into human-readable, agent-injectable rules in `MEMORY.md`.
- **Format**: 
    - `PREFER: [Strategy] in [Regime] due to [Evidence]`
    - `AVOID: [Strategy] when [Indicator Condition] due to [Evidence]`
- **Persistence**: Appends to `data/MEMORY.md`.

## 4. Integration
- **Command**: A new CLI command `/review` will trigger the full pipeline.
- **Agent Injection**: The `L1 Orchestrator` will load `MEMORY.md` and inject its contents into the `QuantModeler` and `MacroAnalyst` system prompts as "Institutional Knowledge".

## Requirements Mapping
- **MEM-02**: Drift report generation.
- **MEM-03**: Rule generation and persistence to MEMORY.md.
- **RISK-Hardening**: Directional and metadata improvements from user review.
