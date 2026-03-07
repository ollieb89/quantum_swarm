---
phase: 8
slug: portfolio-risk-governance
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-07
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` / `pyproject.toml` |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/test_institutional_guard.py -x -q` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3.12 -m pytest tests/test_institutional_guard.py -x -q`
- **After every plan wave:** Run `.venv/bin/python3.12 -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 8-01-01 | 01 | 1 | RISK-07 | unit | `.venv/bin/python3.12 -m pytest tests/test_institutional_guard.py::test_get_open_positions_sql -x -q` | W0 | pending |
| 8-01-02 | 01 | 1 | RISK-07 | unit | `.venv/bin/python3.12 -m pytest tests/test_institutional_guard.py::test_exit_time_index -x -q` | W0 | pending |
| 8-01-03 | 01 | 1 | RISK-07 | unit | `.venv/bin/python3.12 -m pytest tests/test_institutional_guard.py::test_drawdown_circuit_breaker -x -q` | W0 | pending |
| 8-01-04 | 01 | 2 | RISK-08 | unit | `.venv/bin/python3.12 -m pytest tests/test_institutional_guard.py::test_guard_node_metadata_propagation -x -q` | W0 | pending |
| 8-01-05 | 01 | 2 | RISK-07, RISK-08 | integration | `.venv/bin/python3.12 -m pytest tests/test_institutional_guard.py -x -q` | exists | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_institutional_guard.py` — add stubs for:
  - `test_get_open_positions_sql` — verifies column names match DDL (`position_size`, `entry_price`)
  - `test_exit_time_index` — verifies index exists on `exit_time` column
  - `test_drawdown_circuit_breaker` — verifies orders blocked when daily/cumulative drawdown exceeds config thresholds
  - `test_guard_node_metadata_propagation` — verifies approved orders populate `metadata["trade_risk_score"]` and `metadata["portfolio_heat"]`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live DB position query returns correct positions | RISK-07 | Requires running DB with real trades | Start system with paper trading, submit 2 orders, query open positions via debug endpoint, verify `position_size`/`entry_price` fields present |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
