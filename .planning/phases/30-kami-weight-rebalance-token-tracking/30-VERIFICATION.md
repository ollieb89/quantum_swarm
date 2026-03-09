---
phase: 30-kami-weight-rebalance-token-tracking
verified: 2026-03-10T12:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 30: KAMI Weight Rebalance & Token Tracking Verification Report

**Phase Goal:** Merit weights reflect actual signal quality and every cycle reports its token cost
**Verified:** 2026-03-10
**Status:** PASSED
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | KAMI DEFAULT_WEIGHTS show Accuracy at ~8% and Fidelity at ~32% (no longer 30% inert weight) | VERIFIED | `src/core/kami.py` line 29: `"alpha": 0.08`, line 32: `"delta": 0.32`. `config/swarm_config.yaml` lines 250/253 match. Sum = 1.0. |
| 2 | Weight transition preserves existing merit scores via EMA absorption (no score reset) | VERIFIED | `apply_ema()` operates on individual dimension scores independent of weights. No migration script, no dimension reset. Test `test_ema_absorption_preserves_dimensions` confirms EMA result is weight-independent. |
| 3 | After a cycle completes, CycleSnapshot contains per-agent token usage (prompt + completion) with USD cost estimate | VERIFIED | `cycle_snapshot.py` line 82: `token_usage: Optional[dict] = None`. `cycle_runner.py` line 330: `snapshot.token_usage = budget.per_agent_summary()` before persist. BudgetManager tracks input_tokens, output_tokens, usd_cost per agent_id. |
| 4 | Token cost data is visible in the replay CLI when showing a cycle | VERIFIED | `src/cli/replay.py` lines 291-304: renders "Token Usage:" with per-agent breakdown and total cost. |
| 5 | BudgetManager is the single authoritative source for token counts (no SwarmState reducer double-counting) | VERIFIED | No `token_usage` field in `src/graph/state.py` (grep returns empty). BudgetManager accumulates via `record_usage(agent_id=)`, CycleRunner reads via `per_agent_summary()`. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/core/kami.py` | Rebalanced DEFAULT_WEIGHTS | VERIFIED | alpha=0.08, delta=0.32, sum=1.0 |
| `config/swarm_config.yaml` | Matching YAML config weights | VERIFIED | alpha: 0.08, delta: 0.32 confirmed |
| `tests/test_kami.py` | Tests for rebalanced weights and EMA absorption | VERIFIED | 3 new tests, 26 total KAMI tests pass |
| `src/core/budget_manager.py` | Per-agent token tracking with record_usage(agent_id=) and per_agent_summary() | VERIFIED | agent_id param on record_usage, _per_agent dict, per_agent_summary() with deep copy, clear on reset_session |
| `src/core/cycle_snapshot.py` | token_usage field on CycleSnapshot | VERIFIED | `token_usage: Optional[dict] = None` at line 82 |
| `src/core/audit_logger.py` | token_usage excluded from audit hash | VERIFIED | "token_usage" in AUDIT_EXCLUDED_FIELDS at line 23 |
| `src/cli/replay.py` | Token usage rendering in handle_show | VERIFIED | Lines 291-304, renders "Token Usage:" with per-agent totals and USD cost |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/graph/agents/analysts.py` | `src/core/budget_manager.py` | `record_usage(agent_id=)` calls | WIRED | Line 159: agent_id="macro_analyst", line 235: agent_id="quant_modeler" |
| `src/graph/agents/researchers.py` | `src/core/budget_manager.py` | `record_usage(agent_id=)` calls | WIRED | Line 201: agent_id=agent_id, passed as "bullish_research"/"bearish_research" at lines 303/382 |
| `src/graph/nodes/l1.py` | `src/core/budget_manager.py` | `record_usage(agent_id=)` call | WIRED | Line 131: agent_id="classify_intent" |
| `src/core/cycle_runner.py` | `src/core/budget_manager.py` | `per_agent_summary()` populates snapshot | WIRED | Line 330: `snapshot.token_usage = budget.per_agent_summary()` before persist |
| `src/cli/replay.py` | `src/core/cycle_snapshot.py` | reads snapshot.token_usage for display | WIRED | Line 292: `if snapshot.token_usage:` then iterates and renders |
| `src/core/kami.py` | `config/swarm_config.yaml` | matching weight constants | WIRED | Both show alpha=0.08, delta=0.32 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| KAMI-06 | 30-01 | KAMI weights rebalanced: Accuracy ~8%, Fidelity ~32% | SATISFIED | DEFAULT_WEIGHTS alpha=0.08, delta=0.32 in code and config |
| KAMI-07 | 30-01 | Weight transition uses EMA absorption (no score reset) | SATISFIED | apply_ema operates on dimensions independently; no migration/reset code |
| OBS-02 | 30-02 | Token usage tracked per-agent per-cycle with USD cost | SATISFIED | BudgetManager per-agent tracking with 4 wired call sites |
| OBS-04 | 30-02 | Token cost data persisted to CycleSnapshot | SATISFIED | token_usage field on CycleSnapshot, populated in CycleRunner before persist |
| OBS-05 | 30-02 | Single authoritative source (BudgetManager, not SwarmState reducer) | SATISFIED | No token_usage in SwarmState; BudgetManager is sole accumulator |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | - | - | No anti-patterns detected |

### Test Results

61 tests pass across all phase-relevant test files (test_kami.py, test_budget_tracking.py, test_cycle_snapshot.py, test_replay.py).

### Human Verification Required

### 1. Token Usage Display Formatting

**Test:** Run a full cycle and use `replay show <cycle_id>` to view output
**Expected:** Token Usage line appears with per-agent breakdown and USD cost estimate
**Why human:** Cannot verify visual formatting and readability without running the full pipeline

---

_Verified: 2026-03-10_
_Verifier: Claude (gsd-verifier)_
