# Phase 30: KAMI Weight Rebalance + Token Tracking - Research

**Researched:** 2026-03-10
**Domain:** KAMI merit system rebalancing + BudgetManager per-agent token observability
**Confidence:** HIGH

## Summary

This phase has two independent workstreams that share no code coupling: (1) rebalancing KAMI DEFAULT_WEIGHTS constants so Accuracy drops from 30% to 8% and Fidelity rises from 10% to 32%, and (2) extending BudgetManager with per-agent token tracking that flows into CycleSnapshot and the replay CLI.

The weight rebalance is a trivial constant change in `src/core/kami.py` and `config/swarm_config.yaml`. EMA absorption means individual dimension scores are unchanged -- only the composite weighting shifts. The existing `test_default_weights_sum_to_one` test validates the invariant. No migration, no score reset.

The token tracking workstream requires: (a) extending BudgetManager with an `agent_id` parameter on `record_usage()` and a `per_agent_summary()` method, (b) adding `token_usage: Optional[dict]` to CycleSnapshot, (c) populating it in CycleRunner after graph run, (d) adding `token_usage` to `AUDIT_EXCLUDED_FIELDS`, and (e) rendering token data in `handle_show()` in the replay CLI.

**Primary recommendation:** Implement as two plans -- Plan 01 for KAMI weight rebalance (small, isolated), Plan 02 for token tracking pipeline (BudgetManager -> CycleSnapshot -> replay CLI).

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Target weights: alpha (Accuracy) = 0.08, delta (Fidelity) = 0.32
- Remaining 60% split: beta (Recovery) = 0.35, gamma (Consensus) = 0.25 (unchanged)
- Weights must still sum to 1.0
- Change is a constant update in `src/core/kami.py` DEFAULT_WEIGHTS
- No score reset -- EMA naturally absorbs the weight change
- No migration script needed
- BudgetManager is the single authoritative source (OBS-05)
- Extend BudgetManager.summary() to include per-agent breakdown
- Agent nodes already call `budget.record_usage()` -- need to tag calls with agent_id
- Per-agent tracking: `{agent_id: {input_tokens, output_tokens, usd_cost}}` dict added to BudgetManager
- Add `token_usage: Optional[dict]` field to CycleSnapshot (excluded from audit hash)
- CycleRunner populates from BudgetManager.per_agent_summary() after graph run
- Persisted to PostgreSQL cycle_snapshots and filesystem snapshot.json
- Show token usage as compact inline in cycle show view: "Tokens: 12,450 ($0.0032) | AXIOM: 3,200 | MOMENTUM: 2,800 | ..."
- No separate panel -- compact inline format matching existing replay style

### Claude's Discretion
- Exact replay CLI formatting and column widths
- Whether to show tokens in the cycle list view (probably too noisy)
- BudgetManager internal data structure for per-agent tracking
- Test structure and naming

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| KAMI-06 | KAMI weights rebalanced: Accuracy 30%->8%, Fidelity 10%->32%, Recovery/Consensus adjusted | Direct constant change in `src/core/kami.py:28-33` and `config/swarm_config.yaml:250-253` |
| KAMI-07 | Weight transition uses EMA absorption (no score reset) | No code change needed -- `compute_merit()` recalculates composite from unchanged dimension scores each cycle |
| OBS-02 | Token usage tracked per-agent per-cycle with USD cost estimate | Extend `BudgetManager.record_usage()` with `agent_id` param, add `_per_agent` dict |
| OBS-04 | Token cost data persisted to CycleSnapshot for replay CLI visibility | Add `token_usage` field to CycleSnapshot, populate in CycleRunner, render in `handle_show()` |
| OBS-05 | Token tracking uses single authoritative source (BudgetManager) | BudgetManager already is the single source; extend it rather than adding SwarmState tracking |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.x | CycleSnapshot model (already in use) | Project standard for data models |
| rich | existing | Replay CLI rendering (already in use) | Project standard for terminal output |
| threading.Lock | stdlib | Thread-safe BudgetManager counters | Already used in BudgetManager |

### Supporting
No new dependencies required. All changes use existing project libraries.

## Architecture Patterns

### Pattern 1: BudgetManager Per-Agent Extension

**What:** Add `agent_id` parameter to `record_usage()` and maintain a `_per_agent` dict alongside existing session-level counters.

**When to use:** Every `record_usage()` call site.

**Current call sites (5 total):**
1. `src/graph/agents/analysts.py:159` -- MacroAnalyst (agent_id: `"macro_analyst"`)
2. `src/graph/agents/analysts.py:235` -- QuantModeler (agent_id: `"quant_modeler"`)
3. `src/graph/agents/researchers.py:200` -- BullishResearcher/BearishResearcher (uses `role` variable: `"bullish_research"` or `"bearish_research"`)
4. `src/graph/nodes/l1.py:131` -- classify_intent (agent_id: `"classify_intent"`)

**Key design consideration:** The `agent_id` parameter MUST be Optional with default None for backward compatibility. When None, per-agent tracking is skipped but session-level tracking still works. This prevents breaking existing tests.

```python
# Source: analysis of src/core/budget_manager.py
def record_usage(
    self,
    input_tokens: int,
    output_tokens: int,
    model: Optional[str] = None,
    agent_id: Optional[str] = None,  # NEW
) -> None:
    # ... existing session-level tracking ...
    if agent_id is not None:
        with self._lock:
            entry = self._per_agent.setdefault(agent_id, {
                "input_tokens": 0, "output_tokens": 0, "usd_cost": 0.0
            })
            entry["input_tokens"] += input_tokens
            entry["output_tokens"] += output_tokens
            entry["usd_cost"] += cost
```

### Pattern 2: CycleSnapshot Field Addition (follows persona_scores pattern)

**What:** Add `token_usage: Optional[dict] = None` to CycleSnapshot, same as `persona_scores` was added in Phase 29.

**Precedent:** `persona_scores` field (line 81) -- Optional dict, excluded from audit hash, populated post-graph-run.

```python
# In CycleSnapshot model:
token_usage: Optional[dict] = None

# In AUDIT_EXCLUDED_FIELDS:
AUDIT_EXCLUDED_FIELDS: frozenset[str] = frozenset({
    "system_prompt", "active_persona", "soul_sync_context",
    "soft_failed_nodes", "persona_scores", "token_usage",  # NEW
})
```

### Pattern 3: CycleRunner Token Population

**What:** After graph run completes (but before persona evaluation), extract token usage from BudgetManager and inject into snapshot.

**Where:** In `run_cycle()`, after `_extract_snapshot()` and before `_write_snapshot_file()`.

```python
# In run_cycle(), after snapshot extraction:
if budget is not None:
    snapshot.token_usage = budget.per_agent_summary()
```

**Important:** `budget.reset_session()` is called at the START of `run_cycle()` (line 294), so per-agent data is fresh for this cycle. The `per_agent_summary()` must be called BEFORE any subsequent reset.

### Pattern 4: Researchers Agent ID Mapping

**What:** The researcher ReAct loop in `_run_react_researcher()` is shared by both bullish and bearish researchers. The `role` parameter already distinguishes them.

**Current code (researchers.py:200):**
```python
budget.record_usage(input_tokens=inp, output_tokens=out)
```

**Needs to become:**
```python
budget.record_usage(input_tokens=inp, output_tokens=out, agent_id=role)
```

Where `role` is `"bullish_research"` or `"bearish_research"` (already available in scope).

### Anti-Patterns to Avoid
- **Adding token_usage to SwarmState:** This would create double-counting with the `total_tokens` reducer already in SwarmState. BudgetManager is the single source (OBS-05).
- **Resetting per-agent data separately from session data:** The `reset_session()` method must also clear `_per_agent` to keep them in sync.
- **Modifying _COMPLETED_REQUIRED_FIELDS:** Token usage is infrastructure metadata, not a required field for cycle completion.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| USD cost calculation | Custom pricing logic per agent | BudgetManager's existing `_pricing` dict | Already handles model-specific rates with thread-safe accounting |
| Token aggregation | Manual counter in each node | BudgetManager `_per_agent` dict | Single source of truth, thread-safe |

## Common Pitfalls

### Pitfall 1: Breaking Existing BudgetManager Tests
**What goes wrong:** Adding `agent_id` as a required parameter breaks all existing `record_usage()` calls.
**Why it happens:** The method signature change.
**How to avoid:** Make `agent_id` Optional with default None. Existing tests pass without change. New tests verify per-agent tracking.
**Warning signs:** `test_budget_tracking.py` tests fail.

### Pitfall 2: Config/Code Weight Mismatch
**What goes wrong:** Changing DEFAULT_WEIGHTS in code but not in `config/swarm_config.yaml` (or vice versa).
**Why it happens:** Weights are defined in two places: `src/core/kami.py:28-33` and `config/swarm_config.yaml:250-253`.
**How to avoid:** Update BOTH locations. The existing `test_default_weights_sum_to_one` test validates the code constant. Add a test or manually verify the YAML matches.
**Warning signs:** Merit scores don't reflect new weights despite code change.

### Pitfall 3: Per-Agent Data Not Cleared on reset_session()
**What goes wrong:** Per-agent token data accumulates across cycles even though session counters reset.
**Why it happens:** `reset_session()` only clears `_session_input_tokens`, `_session_output_tokens`, `_session_usd`.
**How to avoid:** Add `self._per_agent.clear()` to `reset_session()`.
**Warning signs:** Second cycle shows token counts from first cycle.

### Pitfall 4: Audit Hash Corruption from token_usage
**What goes wrong:** Adding `token_usage` to CycleSnapshot without excluding it from audit hashing breaks the chain.
**Why it happens:** Token counts are infrastructure data that varies between runs.
**How to avoid:** Add `"token_usage"` to `AUDIT_EXCLUDED_FIELDS` frozenset in `audit_logger.py`.
**Warning signs:** `verify_chain()` returns False after adding token_usage.

### Pitfall 5: Researcher Agent ID Inconsistency
**What goes wrong:** Using different agent_id strings for researchers than what KAMI uses.
**Why it happens:** KAMI uses `RESEARCHER_HANDLE_MAP = {"bullish_research": "MOMENTUM", "bearish_research": "CASSANDRA"}` while node names in orchestrator are `"bullish_researcher"` and `"bearish_researcher"`.
**How to avoid:** Use the `role` variable already passed to `_run_react_researcher()` which is `"bullish_research"` or `"bearish_research"` -- consistent with KAMI handles.
**Warning signs:** Per-agent summary shows different keys than merit_scores.

## Code Examples

### Weight Change (src/core/kami.py)
```python
# BEFORE:
DEFAULT_WEIGHTS: Dict[str, float] = {
    "alpha": 0.30,  # Accuracy weight
    "beta": 0.35,   # Recovery weight
    "gamma": 0.25,  # Consensus weight
    "delta": 0.10,  # Fidelity weight
}

# AFTER:
DEFAULT_WEIGHTS: Dict[str, float] = {
    "alpha": 0.08,  # Accuracy weight (reduced — frozen at 0.5 until thesis_records)
    "beta": 0.35,   # Recovery weight
    "gamma": 0.25,  # Consensus weight
    "delta": 0.32,  # Fidelity weight (increased — fed by continuous PersonaScore)
}
```

### Config Change (config/swarm_config.yaml)
```yaml
# BEFORE:
kami:
  alpha: 0.30
  beta: 0.35
  gamma: 0.25
  delta: 0.10

# AFTER:
kami:
  alpha: 0.08
  beta: 0.35
  gamma: 0.25
  delta: 0.32
```

### BudgetManager per_agent_summary()
```python
def per_agent_summary(self) -> Dict[str, Dict[str, Any]]:
    """Return per-agent token usage snapshot."""
    with self._lock:
        return {
            agent_id: {
                "input_tokens": data["input_tokens"],
                "output_tokens": data["output_tokens"],
                "total_tokens": data["input_tokens"] + data["output_tokens"],
                "usd_cost": round(data["usd_cost"], 6),
            }
            for agent_id, data in self._per_agent.items()
        }
```

### Replay CLI Token Line (handle_show)
```python
# After Merit Weights section, before Decision Card:
if snapshot.token_usage:
    parts = []
    total_tokens = 0
    total_cost = 0.0
    for agent_id, usage in snapshot.token_usage.items():
        agent_total = usage.get("total_tokens", 0)
        total_tokens += agent_total
        total_cost += usage.get("usd_cost", 0.0)
        parts.append(f"{agent_id}: {agent_total:,}")

    token_line = f"Tokens: {total_tokens:,} (${total_cost:.4f})"
    if parts:
        token_line += " | " + " | ".join(parts)
    con.print(f"\n[bold]Token Usage:[/bold] {token_line}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Accuracy at 30% weight | Accuracy at 8% weight | Phase 30 | Reduces inert weight (frozen at 0.5) from 15% to 4% of composite |
| Fidelity at 10% weight | Fidelity at 32% weight | Phase 30 | PersonaScore continuous signal has 3.2x more influence on composite |
| Session-only token tracking | Per-agent + session tracking | Phase 30 | Enables cost attribution and optimization per agent |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none (uses pytest defaults) |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/test_kami.py tests/test_budget_tracking.py tests/cli/test_replay.py -x -q` |
| Full suite command | `.venv/bin/python3.12 -m pytest -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| KAMI-06 | DEFAULT_WEIGHTS alpha=0.08, delta=0.32, sum=1.0 | unit | `.venv/bin/python3.12 -m pytest tests/test_kami.py::TestConstants -x` | Existing test `test_default_weights_sum_to_one` covers sum; need new test for specific values |
| KAMI-07 | EMA absorption preserves dimension scores (no reset) | unit | `.venv/bin/python3.12 -m pytest tests/test_kami.py::TestComputeMerit -x` | Existing `test_compute_merit_formula` validates formula; need new test showing composite changes with new weights while dims stay same |
| OBS-02 | Per-agent token tracking with USD cost | unit | `.venv/bin/python3.12 -m pytest tests/test_budget_tracking.py -x` | Needs new tests |
| OBS-04 | Token data in CycleSnapshot and replay CLI | unit | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_snapshot.py tests/cli/test_replay.py -x` | Needs new tests |
| OBS-05 | BudgetManager single source (no double-counting) | unit | `.venv/bin/python3.12 -m pytest tests/test_budget_tracking.py -x` | Architecture constraint; verify BudgetManager is sole recorder |

### Sampling Rate
- **Per task commit:** `.venv/bin/python3.12 -m pytest tests/test_kami.py tests/test_budget_tracking.py tests/cli/test_replay.py tests/core/test_cycle_snapshot.py -x -q`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_kami.py::TestConstants::test_rebalanced_weights` -- covers KAMI-06 (specific alpha/delta values)
- [ ] `tests/test_kami.py::TestComputeMerit::test_weight_rebalance_shifts_composite` -- covers KAMI-07 (EMA absorption)
- [ ] `tests/test_budget_tracking.py::test_per_agent_tracking` -- covers OBS-02
- [ ] `tests/test_budget_tracking.py::test_per_agent_cleared_on_reset` -- covers OBS-02 pitfall
- [ ] `tests/core/test_cycle_snapshot.py::test_token_usage_field` -- covers OBS-04
- [ ] `tests/cli/test_replay.py::test_show_renders_token_usage` -- covers OBS-04

## Open Questions

1. **Researcher agent_id naming convention**
   - What we know: The `role` variable in `_run_react_researcher()` uses `"bullish_research"` / `"bearish_research"` which maps to KAMI's `RESEARCHER_HANDLE_MAP`
   - What's unclear: Whether the replay CLI should display the KAMI handle names (MOMENTUM, CASSANDRA) or the role names (bullish_research, bearish_research)
   - Recommendation: Use role names for recording (consistency with BudgetManager), but display KAMI handles in the CLI for user familiarity. This can be Claude's discretion per CONTEXT.md.

## Sources

### Primary (HIGH confidence)
- Direct code analysis of `src/core/kami.py` -- current weights, compute_merit formula, EMA function
- Direct code analysis of `src/core/budget_manager.py` -- current record_usage signature, threading model, summary()
- Direct code analysis of `src/core/cycle_snapshot.py` -- CycleSnapshot model, persona_scores pattern
- Direct code analysis of `src/core/cycle_runner.py` -- run_cycle flow, budget.reset_session() location
- Direct code analysis of `src/core/audit_logger.py` -- AUDIT_EXCLUDED_FIELDS, _strip_excluded()
- Direct code analysis of `src/cli/replay.py` -- handle_show rendering pattern
- Direct code analysis of `src/graph/orchestrator.py` -- budget injection via partial()
- Direct code analysis of `src/graph/agents/analysts.py` + `researchers.py` -- record_usage call sites

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies, all existing project libraries
- Architecture: HIGH - Clear patterns from existing code (persona_scores precedent, BudgetManager extension)
- Pitfalls: HIGH - Identified from direct code analysis of all integration points

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable internal architecture, no external dependency changes)
