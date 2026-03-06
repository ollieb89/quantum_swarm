---
phase: 01-foundation-orchestration-l1
plan: "01-02"
subsystem: Security & Budget Guardrails
tags: [shell-guard, budget-manager, safety-shutdown, claw-guard, token-budget, swarm-safety]
---

# Phase 1 Plan 02: ClawGuard Sandboxing & Token Budget Manager Summary

One-liner: Added `ShellGuard` shell sandboxing (command whitelist + directory restriction + fcntl-free subprocess) and `BudgetManager` (token/USD ceiling enforcement with `SafetyShutdown`) wired into the orchestrator's `classify_intent` entry point.

## What Was Done

### Task 1: ShellGuard Shell Sandboxing (`src/tools/verification_wrapper.py`)
- Added `SafetyShutdown` exception (shared by ShellGuard and BudgetManager)
- Added `ShellGuard` class alongside existing `BudgetedTool`
- Command validation: base command must be in `_ALLOWED_BASE_COMMANDS` whitelist
- Pattern blocking: `rm -rf`, `sudo`, `dd`, `mkfs`, `curl|sh`, redirect to `/dev/*`, etc.
- Directory restriction: cwd must resolve within project root/data/src/tests/config
- Restricted subprocess env: only safe keys (PATH, HOME, LANG, etc.) forwarded
- Named `ShellGuard` (not `ClawGuard`) to avoid collision with existing state-validation `ClawGuard` in `src/security/claw_guard.py`

### Task 2: BudgetManager (`src/core/budget_manager.py`)
- Thread-safe token and USD tracking via `threading.Lock`
- `record_usage(input_tokens, output_tokens, model)` — accumulates totals + cost
- `check_budget()` — raises `SafetyShutdown` when `session_token_limit` or `daily_usd_limit` breached
- Pricing table defaults to Gemini 2.0 Flash rates; overridable via config
- `summary()` returns snapshot dict for logging/state inspection
- Added `budget:` section to `config/swarm_config.yaml` (100K session tokens, $5/day default)

### Task 3: Orchestrator Integration (`src/graph/orchestrator.py`, `src/graph/state.py`)
- Added `total_tokens: int` to `SwarmState`
- `create_orchestrator_graph()` instantiates `BudgetManager(config)` and passes to `classify_intent` via `partial()`
- `classify_intent_with_registry` now accepts `budget: Optional[BudgetManager]` — calls `budget.check_budget()` as first action before any work
- `run_task()` includes `total_tokens: 0` in initial state
- `BudgetManager` and `SafetyShutdown` imported in orchestrator for future use in additional nodes

## Files Changed

| File | Change |
|------|--------|
| `src/tools/verification_wrapper.py` | Added `SafetyShutdown`, `ShellGuard`, updated imports/docstring |
| `src/core/budget_manager.py` | Created — token spend tracking + safety shutdown |
| `src/graph/state.py` | Added `total_tokens: int` field |
| `src/graph/nodes/l1.py` | Added `budget` param + budget gate to `classify_intent_with_registry` |
| `src/graph/orchestrator.py` | Imports `BudgetManager`/`SafetyShutdown`, wires to `classify_intent` |
| `config/swarm_config.yaml` | Added `budget:` section with ceilings and pricing |

## Verification

- `ShellGuard`: `ls` allowed, `rm -rf /` blocked, `sudo` blocked, `nc` blocked, `/tmp` cwd blocked ✓
- `BudgetManager`: normal usage OK, token ceiling triggers shutdown, USD ceiling triggers shutdown ✓
- Budget gate in `classify_intent`: fires before classification when limits hit ✓
- 34/34 tests pass (no regressions)

## Must-Haves Status

| Requirement | Status |
|-------------|--------|
| Shell commands restricted to authorized dirs and commands | ✓ ShellGuard whitelist + dir check |
| Token usage tracked, swarm halts if budget exceeded | ✓ BudgetManager + SafetyShutdown |
| Budget ceilings configurable at L1 layer | ✓ swarm_config.yaml budget: section |
