---
phase: 27
slug: environment-stabilization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/ -x -q` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest --tb=short` |
| **Estimated runtime** | ~330 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3.12 -m pytest -x -q --tb=short`
- **After every plan wave:** Run `.venv/bin/python3.12 -m pytest --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 330 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 27-01-01 | 01 | 1 | ENV-01 | unit | `.venv/bin/python3.12 -m pytest tests/test_data_fetcher.py::test_data_fetcher_ccxt -x` | ✅ | ⬜ pending |
| 27-01-02 | 01 | 1 | ENV-01 | unit | `.venv/bin/python3.12 -m pytest tests/test_data_fetcher.py -x` | ✅ | ⬜ pending |
| 27-01-03 | 01 | 1 | ENV-02 | unit | `.venv/bin/python3.12 -m pytest tests/test_memory.py -x -q` | ✅ | ⬜ pending |
| 27-01-04 | 01 | 1 | ENV-03 | unit | `.venv/bin/python3.12 -m pytest tests/test_calibration.py tests/test_dexter_bridge.py -x -q` | ✅ | ⬜ pending |
| 27-01-05 | 01 | 1 | ENV-04 | integration | `.venv/bin/python3.12 -m pytest --tb=short` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test files needed.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 330s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
