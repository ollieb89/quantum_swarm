---
phase: 10
slug: rule-validation-harness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-07
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pytest.ini` or `pyproject.toml` |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py -x -q` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py -x -q`
- **After every plan wave:** Run `.venv/bin/python3.12 -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 0 | MEM-06 | unit | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py -x -q` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | MEM-06 | unit | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::test_validate_proposed_rules_pass -x -q` | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 1 | MEM-06 | unit | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::test_validate_proposed_rules_fail -x -q` | ❌ W0 | ⬜ pending |
| 10-01-04 | 01 | 1 | MEM-06 | unit | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::test_min_trade_count_skip -x -q` | ❌ W0 | ⬜ pending |
| 10-01-05 | 01 | 1 | MEM-06 | unit | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::test_backtest_error_leaves_proposed -x -q` | ❌ W0 | ⬜ pending |
| 10-01-06 | 01 | 1 | MEM-06 | unit | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::test_evidence_written_to_registry -x -q` | ❌ W0 | ⬜ pending |
| 10-01-07 | 01 | 2 | MEM-06 | integration | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::test_rule_generator_calls_validator -x -q` | ❌ W0 | ⬜ pending |
| 10-01-08 | 01 | 2 | MEM-06 | integration | `.venv/bin/python3.12 -m pytest tests/test_rule_validator.py::test_audit_log_written -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_rule_validator.py` — TDD stubs for all MEM-06 behaviors (validator class, pass/fail/skip/error cases)
- [ ] Existing `tests/test_structured_memory.py` fixtures reusable — no new conftest needed

*Existing infrastructure (pytest, AsyncMock patterns from Phase 8/9) covers the framework. Only test file stub is new.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full end-to-end self-improvement cycle (generate → validate → active) | MEM-06 | Requires live GOOGLE_API_KEY + NautilusTrader + PostgreSQL | Run `python main.py` with a real API key; trigger weekly review; confirm a rule transitions proposed→active in data/memory_registry.json |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
