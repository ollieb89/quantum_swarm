# Research: Phase 7 - Self-Improvement Loop

## 1. Objectives
- Harden the stop-loss enforcement layer with directional and numerical checks.
- Implement the Review Agent to analyze P&L drift and strategy performance.
- Implement the Rule Generator to automate the maintenance of `MEMORY.md`.

## 2. Technical Findings

### 2.1 Stop-Loss Hardening
- **OrderRouter**: Modify `execute()` in `src/agents/l3_executor.py` to add directional validation based on the `side` parameter.
- **Database Schema**: Update `src/core/persistence.py` to add `atr_at_entry`, `stop_loss_multiplier`, and `stop_loss_method`.
- **TradeRecord Model**: Update `src/models/data_models.py` to match the schema changes.

### 2.2 Weekly Review Agent
- **Data Source**: Needs to join `trades` and `audit_logs` tables.
- **Analysis Logic**: Compare `pnl` (actual) against the performance metrics in `strategy_context["backtest_result"]`.
- **Regime Awareness**: Fetch the `macro_report` from the audit log to correlate performance with market regimes.

### 2.3 Rule Generator & Injection
- **Persistence**: Use standard file I/O to append to `data/MEMORY.md`.
- **Injection**: Modify `src/graph/orchestrator.py` or the agent factory to load `MEMORY.md` and prepended it to the system prompts.

## 3. Implementation Strategy
1. **Schema & Model Update**: First task to ensure high-fidelity data collection for subsequent runs.
2. **Review Agent Logic**: Implement as a standalone service or a specific LangGraph node.
3. **CLI Integration**: Add `/review` or a similar trigger in `main.py`.

## 4. Risks & Mitigations
- **Insufficient Data for Review**: If few trades have occurred, the review agent might hallucinate or produce noisy rules. Mitigation: Minimum trade count threshold (e.g., 5 trades) before rule generation.
- **Prompt Bloat**: `MEMORY.md` could grow too large. Mitigation: Limit injection to the last 10-20 rules or use a summarization step.
