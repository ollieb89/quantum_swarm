# Phase 10: Rule Validation Harness - Research

**Researched:** 2026-03-08
**Domain:** Backtester integration, lifecycle state management, audit logging, pure-Python service pattern
**Confidence:** HIGH

## Summary

Phase 10 builds `RuleValidator` — a pure-Python service (no LLM, no graph node) that gates `proposed` memory rules through a two-run NautilusTrader replay before they are promoted to `active`. Every piece of infrastructure this phase needs already exists: `_run_nautilus_backtest` and `_extract_backtest_metrics` in `backtester.py`, `MemoryRegistry.update_status()` in `memory_registry.py`, and the append-only `data/audit.jsonl` file. The phase is additive: one new file (`src/agents/rule_validator.py`), one call added to `RuleGenerator.persist_rules()`, and two new YAML keys in `swarm_config.yaml`.

The only structural complexity is calling `_run_nautilus_backtest` twice per rule (baseline vs treatment) and interpreting the resulting metric dict. The backtester is synchronous and must be called via `asyncio.to_thread` (same pattern as `backtester_node`), or called synchronously if `RuleValidator` is not itself async. All test isolation is achieved by mocking `_run_nautilus_backtest` at the module level — no live NautilusTrader or network required.

**Primary recommendation:** Implement `RuleValidator` as a synchronous service with an async `validate_proposed_rules()` entry point that calls `asyncio.to_thread(_run_nautilus_backtest, ...)` twice per rule. Mock `_run_nautilus_backtest` using `patch` + `AsyncMock` / `side_effect` for all unit tests, following the exact pattern established in `test_backtester.py`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Two-run NautilusTrader replay: run `backtester_node` / `_run_nautilus_backtest` twice on the same historical window — baseline (rule not applied) then treatment (rule applied)
- Metrics compared: Sharpe ratio, max drawdown, and win rate
- Both baseline and treatment metric values stored in `MemoryRule.evidence` dict (e.g. `baseline_sharpe`, `treatment_sharpe`, `baseline_drawdown`, `treatment_drawdown`, `baseline_win_rate`, `treatment_win_rate`)
- Pass condition: At least 2 of 3 metrics (Sharpe, drawdown, win rate) must improve vs baseline
- Improvement threshold: Any positive delta — no minimum bar required
- On pass: Harness calls `MemoryRegistry.update_status(rule_id, 'active')` automatically
- On fail: Harness calls `MemoryRegistry.update_status(rule_id, 'rejected')` — terminal state
- Promotion and rejection events written to `audit.jsonl` with baseline/treatment metrics as payload (MiFID II audit trail)
- `RuleGenerator.persist_rules()` completes → `RuleValidator.validate_proposed_rules()` called immediately after (inline, same self-improvement loop cycle)
- Lives in `src/agents/rule_validator.py` — parallel to `rule_generator.py` and `review_agent.py`
- `RuleValidator` class with `validate_proposed_rules()` public entry point
- Batch operation: fetches all rules with `status='proposed'` from the registry and validates each in turn
- Historical lookback: configurable in `swarm_config.yaml` as `validation_lookback_days`, default `90`
- Minimum trade count: configurable in `swarm_config.yaml` as `validation_min_trades`, default `10`
  - If fewer than `validation_min_trades` trades in the window, skip validation and leave rule as `proposed`
- Instrument selection: use the same instrument(s) referenced in the rule's `condition` dict; fall back to all recent trades if no instrument constraint
- On backtest error: log the error, leave rule as `proposed`, do not reject or raise

### Claude's Discretion
- Exact schema keys in `evidence` dict (suggested above is a guide — can be snake_case variants)
- Internal structure of the two-run comparison (sequential vs parallelized)
- How the `condition` dict is parsed to extract instrument scope
- Exact audit.jsonl payload format (must include rule_id, before_status, after_status, and metric deltas)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MEM-06 | Rule validation harness: backtest newly generated rules before promoting to active; validate proposed rules against baseline replay; auto-promote on pass, auto-reject on fail | Two-run `_run_nautilus_backtest` pattern documented; `update_status()` API confirmed; audit.jsonl append pattern confirmed; 2-of-3 metric comparison logic fully specifiable |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `src.graph.agents.l3.backtester._run_nautilus_backtest` | existing | Run synchronous NautilusTrader backtest, return plain metrics dict | Already extracts sharpe_ratio, max_drawdown, win_rate, total_trades — exact metrics needed |
| `src.core.memory_registry.MemoryRegistry` | existing | Load proposed rules, transition status, persist | update_status() already enforces lifecycle; no custom guard needed |
| `src.models.memory.MemoryRule` | existing | Pydantic model; evidence dict accepts any metric keys | evidence: Dict[str, Any] — no schema change required |
| `asyncio.to_thread` | stdlib | Wrap blocking `_run_nautilus_backtest` in async context | Established pattern from backtester_node; never block event loop |
| `json` / `pathlib` | stdlib | Append audit events to data/audit.jsonl | Append-only pattern established in Phase 4 (SEC-04) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `yaml` / `pyyaml` | existing | Read `validation_lookback_days`, `validation_min_trades` from swarm_config.yaml | Config init for RuleValidator |
| `logging` | stdlib | Log skip, error, promote, reject events at INFO/WARNING level | Always; consistent with rest of codebase |
| `datetime` / `timezone` | stdlib | ISO 8601 timestamps on audit events | Always; matches existing audit.jsonl format |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `asyncio.to_thread` for backtester calls | synchronous calls in synchronous `validate_proposed_rules()` | Synchronous is simpler and safe if RuleValidator itself is called from a non-async context (e.g. from `persist_rules()`); use async only if caller is async |
| `asyncio.gather` for parallel baseline+treatment | sequential calls | Sequential is simpler and avoids thread pool saturation with multiple rules; parallel is a discretion area |

**Installation:** No new dependencies. All imports are existing project packages or stdlib.

---

## Architecture Patterns

### Recommended Project Structure

```
src/agents/
├── rule_generator.py     # existing — adds call to RuleValidator at end of persist_rules()
├── rule_validator.py     # NEW — RuleValidator class
├── review_agent.py       # existing — unchanged
config/
├── swarm_config.yaml     # existing — add validation_lookback_days: 90, validation_min_trades: 10
tests/
├── test_rule_validator.py  # NEW — unit + integration tests
```

### Pattern 1: Two-Run Backtester Comparison

**What:** Call `_run_nautilus_backtest(symbol, strategy={})` twice per rule. First call is baseline (empty/default strategy dict, rule not applied). Second call passes rule metadata in strategy dict so downstream processing can apply the rule. Compare metric deltas.

**When to use:** For every rule with status `proposed`.

**Key insight from existing code:** `_run_nautilus_backtest` currently ignores the `strategy` dict (comment in backtester.py: "currently unused by the engine"). For the treatment run, the strategy dict signals the rule to apply, but since NT engine does not yet act on it, both runs will produce identical metrics. This is an acceptable baseline implementation — the validator logic and test harness are correct; the behavioural differentiation between baseline and treatment is a future concern. Tests must reflect this by supplying different mock return values for each call.

**Example:**
```python
# Source: backtester.py pattern + asyncio.to_thread convention
import asyncio
from src.graph.agents.l3.backtester import _run_nautilus_backtest

async def _run_two_pass(symbol: str, rule_strategy: dict) -> tuple[dict, dict]:
    baseline = await asyncio.to_thread(_run_nautilus_backtest, symbol, {})
    treatment = await asyncio.to_thread(_run_nautilus_backtest, symbol, rule_strategy)
    return baseline, treatment
```

### Pattern 2: 2-of-3 Metric Improvement Check

**What:** Compare three metrics (Sharpe, drawdown, win rate) between baseline and treatment. Count improvements. Pass if count >= 2.

**Drawdown improvement direction:** Lower (less negative) drawdown is better. If `baseline_drawdown = -0.10` and `treatment_drawdown = -0.07`, treatment improved (delta = +0.03). Improvement means `treatment_drawdown > baseline_drawdown` (less negative / closer to 0).

**Example:**
```python
def _passes_validation(baseline: dict, treatment: dict) -> bool:
    improvements = 0
    if treatment["sharpe_ratio"] > baseline["sharpe_ratio"]:
        improvements += 1
    # drawdown: less negative = better
    if treatment["max_drawdown"] > baseline["max_drawdown"]:
        improvements += 1
    if treatment["win_rate"] > baseline["win_rate"]:
        improvements += 1
    return improvements >= 2
```

### Pattern 3: Audit Event Append to audit.jsonl

**What:** After each rule validation outcome, append a JSON line to `data/audit.jsonl`. Must include rule_id, before_status, after_status, and metric deltas.

**Example:**
```python
import json
from datetime import datetime, timezone
from pathlib import Path

def _write_audit(audit_path: Path, rule_id: str, outcome: str,
                 baseline: dict, treatment: dict):
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "rule_validation",
        "rule_id": rule_id,
        "before_status": "proposed",
        "after_status": outcome,  # "active" or "rejected"
        "baseline_sharpe": baseline["sharpe_ratio"],
        "treatment_sharpe": treatment["sharpe_ratio"],
        "baseline_drawdown": baseline["max_drawdown"],
        "treatment_drawdown": treatment["max_drawdown"],
        "baseline_win_rate": baseline["win_rate"],
        "treatment_win_rate": treatment["win_rate"],
        "sharpe_delta": treatment["sharpe_ratio"] - baseline["sharpe_ratio"],
        "drawdown_delta": treatment["max_drawdown"] - baseline["max_drawdown"],
        "win_rate_delta": treatment["win_rate"] - baseline["win_rate"],
    }
    with open(audit_path, "a") as f:
        f.write(json.dumps(event) + "\n")
```

### Pattern 4: Instance Attribute Redirection for Test Isolation

**What:** Same pattern used in `RuleGenerator` — redirect `.registry`, `.config_path`, and `.audit_path` instance attributes in tests. No mock needed for filesystem-level isolation.

**Example:**
```python
# In test setUp:
validator = RuleValidator()
validator.registry = MemoryRegistry(str(self.test_registry_file))
validator.audit_path = Path(str(self.test_audit_file))
```

### Pattern 5: Proposed Rule Enumeration

**What:** `MemoryRegistry` has no `get_proposed_rules()` method. RuleValidator must filter `schema.rules` directly or the method must be added to MemoryRegistry. Recommended: add `get_proposed_rules()` to `MemoryRegistry` for symmetry with `get_active_rules()`.

```python
# src/core/memory_registry.py — add alongside get_active_rules():
def get_proposed_rules(self) -> List[MemoryRule]:
    return [r for r in self.schema.rules if r.status == "proposed"]
```

### Pattern 6: Config Loading

**What:** Load YAML config once at `RuleValidator.__init__`. Follow existing convention seen throughout the codebase (yaml.safe_load).

```python
import yaml
from pathlib import Path

class RuleValidator:
    def __init__(self, config_path: str = "config/swarm_config.yaml",
                 registry_path: str = "data/memory_registry.json",
                 audit_path: str = "data/audit.jsonl"):
        self.config_path = Path(config_path)
        self.audit_path = Path(audit_path)
        self.registry = MemoryRegistry(registry_path)
        cfg = yaml.safe_load(self.config_path.read_text()) if self.config_path.exists() else {}
        self.lookback_days: int = cfg.get("validation_lookback_days", 90)
        self.min_trades: int = cfg.get("validation_min_trades", 10)
```

### Anti-Patterns to Avoid

- **Calling `engine.run()` directly in async context:** Always use `asyncio.to_thread`. Blocking the event loop causes LangGraph graph hangs. (Source: backtester.py docstring, ANTI-PATTERNS AVOIDED section)
- **Calling `asyncio.run()` inside validate_proposed_rules() if it is itself async:** `asyncio.run()` cannot be called from within a running event loop. Use `await` throughout.
- **Raising on backtest error:** Locked decision — log and leave `proposed`. Do not call `update_status('rejected')` on an exception from NautilusTrader.
- **Rejecting a rule with fewer than min_trades:** Skip with log, leave `proposed`. Retried next cycle.
- **Re-implementing lifecycle guard:** `update_status()` already enforces `VALID_TRANSITIONS`. Just call it; do not re-check transitions in RuleValidator.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Lifecycle transition guard | Custom status check + write | `MemoryRegistry.update_status()` | Already enforces `VALID_TRANSITIONS`; raises `ValueError` on invalid transitions; increments version; calls `save()` |
| Backtest execution | New NautilusTrader setup | `_run_nautilus_backtest(symbol, strategy)` | Already handles yfinance fetch, bar wrangling, engine lifecycle, metric extraction, and `safe_float()` normalisation |
| JSON append with timestamp | Custom file writer | Thin wrapper on stdlib `json` + `open(..., "a")` | Existing audit.jsonl pattern is simple open/append — no logging framework needed |
| Instrument resolution from condition dict | Complex parsing | Simple `condition.get("instrument", None)` with fallback to config default symbol | The condition dict is free-form; over-engineering the parser creates fragility |

**Key insight:** This phase is almost entirely wiring. The two hard problems (running backtests, enforcing lifecycle) are solved. The only new logic is the 2-of-3 metric comparison and the audit write.

---

## Common Pitfalls

### Pitfall 1: Drawdown Comparison Direction

**What goes wrong:** Code checks `treatment["max_drawdown"] < baseline["max_drawdown"]` (treating lower as better numerically), but `max_drawdown` in the codebase is already stored as a negative fraction (e.g. `-0.10`). A drawdown of `-0.07` is *better* than `-0.10` yet numerically greater.

**Why it happens:** Naming convention ambiguity — "max drawdown" sometimes means the magnitude (positive) and sometimes the signed value.

**How to avoid:** Confirm `_extract_backtest_metrics` returns `max_drawdown` as a non-positive value or zero (confirmed from `backtester.py`: `max_drawdown = 0.0` initialized, never set to a positive value in current implementation). Treat improvement as `treatment_drawdown > baseline_drawdown` (less negative is better).

**Warning signs:** Both baseline and treatment return `max_drawdown = 0.0` (current behaviour since `_extract_backtest_metrics` doesn't yet extract drawdown from NT result). This means drawdown will be a tie (no improvement, no degradation) for all rules until the metric is wired up in the backtester. The 2-of-3 logic still works correctly — it will just count 0 for drawdown.

### Pitfall 2: Both Backtest Runs Return Identical Results

**What goes wrong:** Because `strategy` dict is currently unused by `_run_nautilus_backtest`, both baseline and treatment runs on the same symbol+window return identical metrics. No rule will ever show improvement.

**Why it happens:** NautilusTrader engine has no strategy actor registered, so the strategy dict has no effect (documented in backtester.py comments).

**How to avoid:** The harness implementation is still correct — it establishes the plumbing and produces the correct pass/fail logic and audit trail. The test suite must supply *different* mock return values for the two calls (baseline vs treatment) to exercise the logic. Document in code comments that real differentiation is a future backtester enhancement.

**Warning signs:** Every rule gets rejected in integration testing. Verify mock is returning different values for baseline vs treatment.

### Pitfall 3: asyncio Context for validate_proposed_rules()

**What goes wrong:** `RuleValidator.validate_proposed_rules()` is called from `RuleGenerator.persist_rules()`, which is synchronous. If `validate_proposed_rules()` is defined as `async`, the caller must use `asyncio.run()` or `await`. But if called from within an already-running event loop (e.g. inside a LangGraph node), `asyncio.run()` will raise `RuntimeError`.

**Why it happens:** The call site (`persist_rules()`) is synchronous but the backtester requires async.

**How to avoid:** Two safe options:
1. Make `validate_proposed_rules()` synchronous and call `asyncio.run()` inside it — valid only if called from outside any running event loop (standalone self-improvement loop).
2. Make `validate_proposed_rules()` async and require `RuleGenerator.persist_rules()` to be called with `await` — requires `persist_rules()` to become async too.

**Recommended:** Option 1 for minimal disruption. `persist_rules()` is called synchronously in `test_persist_rules_stores_proposed()` and existing tests. Validate by checking whether the self-improvement loop call site is inside an async context.

**Warning signs:** `RuntimeError: This event loop is already running` during integration.

### Pitfall 4: Stale Registry After Status Update

**What goes wrong:** `RuleValidator` loads `MemoryRegistry` in `__init__`. If `persist_rules()` adds rules after the validator is instantiated, `self.registry.schema.rules` won't include the new rules.

**Why it happens:** `MemoryRegistry._load()` is called once in `__init__`; in-memory state is not refreshed.

**How to avoid:** Either re-instantiate `MemoryRegistry` inside `validate_proposed_rules()` (reading fresh from disk) or call `self.registry.schema = self.registry._load()` at the start of validation. Simplest: re-instantiate with the same file path at validation time.

**Warning signs:** `validate_proposed_rules()` returns 0 rules validated even after `persist_rules()` added rules.

### Pitfall 5: audit.jsonl Concurrency

**What goes wrong:** Two concurrent self-improvement cycles write to `audit.jsonl` simultaneously, producing interleaved lines or partial writes.

**Why it happens:** `open(..., "a")` + `write()` is not atomic across processes.

**How to avoid:** Phase 10 runs as a single-process weekly cycle — concurrency is not a concern for the current scope. Document the limitation. Do not add file locking unless required.

---

## Code Examples

Verified patterns from existing codebase:

### Backtester Mock Pattern (from test_backtester.py)

```python
# Source: tests/test_backtester.py — test_backtester_node_returns_sharpe
from unittest.mock import AsyncMock, patch
import asyncio

mock_result = {
    "sharpe_ratio": 1.5,
    "total_return": 0.12,
    "max_drawdown": -0.05,
    "total_trades": 10,
    "win_rate": 0.6,
    "period_days": 180,
}

with patch(
    "src.graph.agents.l3.backtester.asyncio.to_thread",
    new_callable=AsyncMock,
    return_value=mock_result,
):
    result = asyncio.run(backtester_node(state))
```

For RuleValidator tests, patch `_run_nautilus_backtest` directly with `side_effect` to return different values for baseline vs treatment:

```python
# Baseline returns mediocre metrics; treatment returns improved metrics
call_count = [0]
def mock_backtest(symbol, strategy):
    call_count[0] += 1
    if call_count[0] == 1:   # baseline
        return {"sharpe_ratio": 0.5, "max_drawdown": -0.10, "win_rate": 0.40, "total_trades": 15, ...}
    else:                     # treatment
        return {"sharpe_ratio": 1.2, "max_drawdown": -0.06, "win_rate": 0.55, "total_trades": 15, ...}

with patch("src.agents.rule_validator._run_nautilus_backtest", side_effect=mock_backtest):
    ...
```

### Registry Instance Attribute Redirect (from test_structured_memory.py)

```python
# Source: tests/test_structured_memory.py — TestRuleGeneratorIntegration
rg = RuleGenerator()
rg.registry = MemoryRegistry(str(self.test_registry_file))
rg.memory_md_path = self.test_memory_md
```

Same pattern for RuleValidator:
```python
validator = RuleValidator()
validator.registry = MemoryRegistry(str(self.test_registry_file))
validator.audit_path = Path(str(self.test_audit_file))
```

### asyncio.run() Pattern for Sync Test Runner (from test_self_improvement.py)

```python
# Source: tests/test_self_improvement.py — test_rule_generator_logic
loop = asyncio.new_event_loop()
rules = loop.run_until_complete(generator.generate_rules({"status": "ok"}))
```

For Phase 10 tests (using `asyncio.run()` which is Python 3.12 preferred):
```python
import asyncio
result = asyncio.run(validator.validate_proposed_rules())
```

### Lifecycle Transition (from memory_registry.py)

```python
# Source: src/core/memory_registry.py — update_status()
rule = self.registry.update_status(rule_id, "active")   # returns updated MemoryRule
rule = self.registry.update_status(rule_id, "rejected")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual rule promotion (human reviews MEMORY.md) | Automated harness: backtest-gated promotion | Phase 10 | Rules only reach `active` if they pass quantitative validation |
| Flat MEMORY.md rules (string-based, no lifecycle) | Structured `MemoryRule` Pydantic model with governed status transitions | Phase 9 | Rule state is machine-readable; promotion/rejection is auditable |
| `_run_nautilus_backtest` called once (forward-looking) | Called twice (baseline + treatment) for A/B comparison | Phase 10 | Enables relative performance measurement per rule |

**Deprecated/outdated:**
- Manual calls to `update_status('active')` from outside the harness: after Phase 10, the harness is the canonical promotion path for `proposed` rules.

---

## Open Questions

1. **Is `validate_proposed_rules()` sync or async?**
   - What we know: `persist_rules()` is synchronous; `_run_nautilus_backtest` is blocking (needs thread).
   - What's unclear: Whether the self-improvement loop call site is inside an async context.
   - Recommendation: Implement as synchronous with `asyncio.run()` internally for the initial implementation. If called from within LangGraph graph, refactor to async.

2. **How to differentiate baseline vs treatment in `_run_nautilus_backtest`?**
   - What we know: The strategy dict is currently ignored by the NT engine.
   - What's unclear: Whether Phase 10 should stub the differentiation or wait for Phase 11.
   - Recommendation: Pass rule metadata in strategy dict and document that behavioural differentiation is a TODO. Both runs will return identical metrics in the current implementation; tests use mocks to exercise the comparison logic.

3. **`get_proposed_rules()` on MemoryRegistry — add or filter inline?**
   - What we know: `get_active_rules()` exists; there is no `get_proposed_rules()`.
   - What's unclear: Whether to extend `MemoryRegistry` or filter in `RuleValidator`.
   - Recommendation: Add `get_proposed_rules()` to `MemoryRegistry` for consistency and to make the Phase 10 integration test match the style of existing structured memory tests.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `unittest.TestCase` (project standard; pytest runner used via `python3.12 -m pytest`) |
| Config file | none — `pytest` discovers via naming convention |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py -x -q` |
| Full suite command | `.venv/bin/python3.12 -m pytest tests/ -x -q --ignore=tests/test_audit_chain.py --ignore=tests/test_persistence.py --ignore=tests/test_order_router.py` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MEM-06 | `validate_proposed_rules()` fetches all proposed rules from registry | unit | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::TestRuleValidator::test_fetches_proposed_rules -x` | ❌ Wave 0 |
| MEM-06 | Two backtester calls made per rule (baseline + treatment) | unit | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::TestRuleValidator::test_two_backtest_calls_per_rule -x` | ❌ Wave 0 |
| MEM-06 | Rule passing 2-of-3 metrics is promoted to `active` | unit | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::TestRuleValidator::test_pass_promotes_to_active -x` | ❌ Wave 0 |
| MEM-06 | Rule failing 2-of-3 metrics is moved to `rejected` | unit | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::TestRuleValidator::test_fail_rejects_rule -x` | ❌ Wave 0 |
| MEM-06 | Rule with fewer than `min_trades` in baseline is left `proposed` (skipped) | unit | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::TestRuleValidator::test_insufficient_trades_skipped -x` | ❌ Wave 0 |
| MEM-06 | Backtest error leaves rule `proposed`, does not raise | unit | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::TestRuleValidator::test_backtest_error_leaves_proposed -x` | ❌ Wave 0 |
| MEM-06 | Promotion event written to audit.jsonl with required fields | unit | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::TestRuleValidator::test_audit_event_on_promotion -x` | ❌ Wave 0 |
| MEM-06 | Rejection event written to audit.jsonl with required fields | unit | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::TestRuleValidator::test_audit_event_on_rejection -x` | ❌ Wave 0 |
| MEM-06 | Baseline/treatment metric values stored in `MemoryRule.evidence` | unit | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::TestRuleValidator::test_evidence_written_to_rule -x` | ❌ Wave 0 |
| MEM-06 | `RuleGenerator.persist_rules()` triggers `validate_proposed_rules()` | integration | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::TestRuleValidatorIntegration::test_persist_then_validate -x` | ❌ Wave 0 |
| MEM-06 | `swarm_config.yaml` keys `validation_lookback_days` and `validation_min_trades` are read by validator | unit | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::TestRuleValidator::test_config_keys_read -x` | ❌ Wave 0 |

### Backtester Mock Strategy for Unit Tests

All unit tests mock `_run_nautilus_backtest` at the import level in `src.agents.rule_validator`:

```python
from unittest.mock import patch, MagicMock

# Pattern A: same return for both calls (testing skip / error paths)
with patch("src.agents.rule_validator._run_nautilus_backtest",
           return_value={"sharpe_ratio": 0.5, "max_drawdown": 0.0, "win_rate": 0.4,
                         "total_trades": 15, "total_return": 0.05, "period_days": 90}):
    ...

# Pattern B: different returns per call (testing pass/fail logic)
call_responses = [
    # baseline
    {"sharpe_ratio": 0.5, "max_drawdown": -0.10, "win_rate": 0.40, "total_trades": 15,
     "total_return": 0.03, "period_days": 90},
    # treatment
    {"sharpe_ratio": 1.2, "max_drawdown": -0.06, "win_rate": 0.55, "total_trades": 15,
     "total_return": 0.09, "period_days": 90},
]
with patch("src.agents.rule_validator._run_nautilus_backtest",
           side_effect=call_responses):
    ...

# Pattern C: raise on call (testing error handling)
with patch("src.agents.rule_validator._run_nautilus_backtest",
           side_effect=RuntimeError("NT engine failed")):
    ...
```

**Note:** `_run_nautilus_backtest` must be imported at the top of `rule_validator.py` (not called as `backtester._run_nautilus_backtest`) for `patch("src.agents.rule_validator._run_nautilus_backtest")` to work.

### Integration Test Strategy

One integration test class `TestRuleValidatorIntegration` in `tests/test_rule_validator.py`:

1. Create a `MemoryRegistry` backed by a temp file.
2. Add a `MemoryRule` with status `proposed` directly.
3. Create a `RuleValidator` with the same temp registry and a temp audit file.
4. Mock `_run_nautilus_backtest` with `side_effect` returning baseline then treatment.
5. Call `validator.validate_proposed_rules()`.
6. Assert registry rule status is `active` or `rejected`.
7. Assert audit.jsonl contains one line with required fields.
8. Assert `rule.evidence` contains the six metric keys.

This mirrors the `TestRuleGeneratorIntegration` pattern in `test_structured_memory.py`.

### Sampling Rate

- **Per task commit:** `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py -x -q`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py tests/test_structured_memory.py -x -q`
- **Phase gate:** Full suite green (excluding known pre-existing failures) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_rule_validator.py` — covers all MEM-06 behaviors (11 test methods across 2 classes)
- [ ] `src/core/memory_registry.py` — add `get_proposed_rules()` method (1-liner, follows `get_active_rules()` pattern)
- [ ] `config/swarm_config.yaml` — add `validation_lookback_days: 90` and `validation_min_trades: 10` keys

---

## Sources

### Primary (HIGH confidence)
- `src/graph/agents/l3/backtester.py` — `_run_nautilus_backtest`, `_extract_backtest_metrics`, metric keys, fallback pattern, asyncio.to_thread convention
- `src/core/memory_registry.py` — `update_status()` API, `VALID_TRANSITIONS`, `get_active_rules()` pattern, atomic save
- `src/models/memory.py` — `MemoryRule.evidence: Dict[str, Any]`, status Literal type
- `src/agents/rule_generator.py` — `persist_rules()` call site, lazy LLM pattern, instance attribute redirect pattern
- `tests/test_backtester.py` — backtester mock pattern with `asyncio.to_thread` + `AsyncMock`
- `tests/test_structured_memory.py` — registry temp file pattern, instance attribute redirect, `assertLogs` pattern
- `tests/test_self_improvement.py` — `asyncio.run()` / `asyncio.new_event_loop()` in sync test methods
- `data/audit.jsonl` — existing event payload structure (timestamp, event, status fields)
- `config/swarm_config.yaml` — existing YAML structure; `self_improvement` section is the natural home for validation config keys

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` Accumulated Context section — lazy LLM pattern, AsyncMock pattern, instance attribute redirection confirmation
- `.planning/phases/10-rule-validation-harness/10-CONTEXT.md` — all locked decisions

### Tertiary (LOW confidence)
None — all findings verified against codebase directly.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are existing project code or stdlib; verified by reading source files
- Architecture: HIGH — patterns directly extracted from existing tests and agent implementations
- Pitfalls: HIGH — drawdown direction and asyncio context pitfalls verified against backtester.py and test_self_improvement.py; stale registry pitfall verified against MemoryRegistry._load() implementation

**Research date:** 2026-03-08
**Valid until:** 2026-06-08 (stable; no external dependencies)
