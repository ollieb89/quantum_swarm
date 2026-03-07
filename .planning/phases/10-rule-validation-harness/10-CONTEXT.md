# Phase 10: Rule Validation Harness - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Gate newly-generated memory rules (status: `proposed`) through a backtest-based validation harness before promoting them to `active`. The harness runs two NautilusTrader backtests — baseline vs treatment — compares key metrics, and automatically promotes or rejects each rule. This is the bridge between Phase 9's `proposed` lifecycle state and a rule becoming `active` in the swarm.

</domain>

<decisions>
## Implementation Decisions

### Comparison Methodology
- Two-run NautilusTrader replay: run `backtester_node` / `_run_nautilus_backtest` twice on the same historical window — baseline (rule not applied) then treatment (rule applied)
- Metrics compared: Sharpe ratio, max drawdown, and win rate
- Both baseline and treatment metric values stored in `MemoryRule.evidence` dict (e.g. `baseline_sharpe`, `treatment_sharpe`, `baseline_drawdown`, `treatment_drawdown`, `baseline_win_rate`, `treatment_win_rate`)

### Promotion Criteria
- **Pass condition:** At least 2 of 3 metrics (Sharpe, drawdown, win rate) must improve vs baseline
- **Improvement threshold:** Any positive delta — no minimum bar required
- **On pass:** Harness calls `MemoryRegistry.update_status(rule_id, 'active')` automatically
- **On fail:** Harness calls `MemoryRegistry.update_status(rule_id, 'rejected')` — terminal state, consistent with Phase 9 lifecycle
- Promotion and rejection events written to `audit.jsonl` with baseline/treatment metrics as payload (MiFID II audit trail)

### Trigger & Integration Point
- `RuleGenerator.persist_rules()` completes → `RuleValidator.validate_proposed_rules()` called immediately after (inline, same self-improvement loop cycle)
- Lives in `src/agents/rule_validator.py` — parallel to `rule_generator.py` and `review_agent.py`
- `RuleValidator` class with `validate_proposed_rules()` public entry point (callable from tests, CLI, or RuleGenerator)
- Batch operation: fetches all rules with `status='proposed'` from the registry and validates each in turn

### Replay Window & Sample Size
- Historical lookback: configurable in `swarm_config.yaml` as `validation_lookback_days`, default `90`
- Minimum trade count: configurable in `swarm_config.yaml` as `validation_min_trades`, default `10`
  - If fewer than `validation_min_trades` trades in the window, skip validation and leave rule as `proposed` (retried next weekly cycle)
- Instrument selection: use the same instrument(s) referenced in the rule's `condition` dict; fall back to all recent trades if no instrument constraint in condition
- On backtest error (NautilusTrader failure, no data): log the error, leave rule as `proposed`, and allow the next self-improvement cycle to retry — do not reject or raise

### Claude's Discretion
- Exact schema keys in `evidence` dict (suggested above is a guide — can be snake_case variants)
- Internal structure of the two-run comparison (whether baseline/treatment are run sequentially or could be parallelized)
- How the `condition` dict is parsed to extract instrument scope
- Exact audit.jsonl payload format (must include rule_id, before_status, after_status, and metric deltas)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/core/memory_registry.py` — `MemoryRegistry.get_active_rules()`, `update_status()`, `_load()`: fetch proposed rules and drive lifecycle transitions
- `src/models/memory.py` — `MemoryRule` Pydantic model with `evidence: Dict[str, Any]` field ready to store validation metrics
- `src/graph/agents/l3/backtester.py` — `_run_nautilus_backtest()` and `_extract_backtest_metrics()`: already extract Sharpe, max drawdown, and trade stats from NautilusTrader output
- `data/audit.jsonl` — append-only audit log (existing pattern from SEC-04); harness writes promotion/rejection events here
- `swarm_config.yaml` — existing config file; add `validation_lookback_days` and `validation_min_trades` keys

### Established Patterns
- Lazy LLM init pattern (not needed here — validator is a pure Python service, no LLM calls)
- `RuleGenerator` instance attribute redirection for test isolation (same pattern applies to `RuleValidator.registry` and `RuleValidator.config`)
- `MemoryRegistry.update_status()` already enforces transition validity — harness just calls it; no need to re-implement transition guards
- AsyncMock pattern for DB tests: used in Phase 8 and 9; same approach for mocking backtester output in harness tests

### Integration Points
- `src/agents/rule_generator.py` `RuleGenerator.persist_rules()` — add a `RuleValidator` call at the end
- `config/swarm_config.yaml` — add `validation_lookback_days` and `validation_min_trades` to the risk/memory section
- `data/memory_registry.json` — read proposed rules, write updated status
- `data/audit.jsonl` — append validation outcome events

</code_context>

<specifics>
## Specific Ideas

- `RuleValidator` should behave like a service, not an agent — no LLM, no async graph node; pure Python with async if needed to call the backtester
- The harness is the bridge making Phase 9's `proposed → active` lifecycle path meaningful; without it, rules would need manual promotion
- Instrument scope extracted from `rule.condition` (e.g. `{"regime": "high_volatility_trend"}` may be instrument-agnostic; `{"instrument": "BTC-USDT"}` scopes to that ticker)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-rule-validation-harness*
*Context gathered: 2026-03-07*
