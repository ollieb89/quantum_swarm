---
phase: 30-kami-weight-rebalance-token-tracking
plan: 01
subsystem: kami-merit
tags: [kami, weights, rebalance, fidelity, accuracy]
dependency_graph:
  requires: [29-02]
  provides: [kami-rebalanced-weights]
  affects: [merit-composite, persona-score-impact]
tech_stack:
  added: []
  patterns: [tdd-red-green]
key_files:
  created: []
  modified:
    - src/core/kami.py
    - config/swarm_config.yaml
    - tests/test_kami.py
decisions:
  - Shift 22% weight from Accuracy to Fidelity to eliminate inert composite contribution
metrics:
  duration_seconds: 136
  completed: "2026-03-09T23:40:48Z"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 3
  tests_total: 26
---

# Phase 30 Plan 01: KAMI Weight Rebalance Summary

Rebalanced KAMI composite weights from alpha=0.30/delta=0.10 to alpha=0.08/delta=0.32, eliminating the 30% inert weight problem where Accuracy was frozen at 0.5 with no thesis_records system feeding it.

## What Changed

- **DEFAULT_WEIGHTS in `src/core/kami.py`**: alpha reduced 0.30 -> 0.08, delta increased 0.10 -> 0.32. Recovery (0.35) and Consensus (0.25) unchanged. Sum remains 1.0.
- **`config/swarm_config.yaml` kami section**: Matching weight values updated with explanatory comments.
- **`tests/test_kami.py`**: Three new tests added (test_rebalanced_weights, test_weight_rebalance_shifts_composite, test_ema_absorption_preserves_dimensions).

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 (RED) | e36291a | Add failing tests for weight rebalance |
| 2 (GREEN) | cd1d175 | Rebalance weights in code and config |

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

1. **Shift 22% weight from Accuracy to Fidelity** -- Accuracy has been frozen at 0.5 since there is no thesis_records system, making 30% of the composite inert. Fidelity now receives continuous PersonaScore input from Phase 29, so shifting weight there makes the merit system responsive to actual agent behavior.

## Verification

- All 26 KAMI tests pass
- alpha=0.08 confirmed in both src/core/kami.py and config/swarm_config.yaml
- delta=0.32 confirmed in both files
- Weights sum to 1.0

## Self-Check: PASSED
