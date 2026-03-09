---
phase: 25
slug: end-to-end-pipeline-runner
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via `.venv/bin/python3.12 -m pytest`) |
| **Config file** | None — pytest runs from project root |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_runner.py tests/test_cli_integration.py -x` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest tests/ -x --ignore=tests/test_persistence.py` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3.12 -m pytest tests/core/test_cycle_runner.py tests/core/test_soul_loader.py -x`
- **After every plan wave:** Run `.venv/bin/python3.12 -m pytest tests/ -x --ignore=tests/test_persistence.py`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 25-01-01 | 01 | 1 | PIPE-04 | unit | `.venv/bin/python3.12 -m pytest tests/test_logging_config.py -x` | No — W0 | ⬜ pending |
| 25-01-02 | 01 | 1 | PIPE-02 | unit | `.venv/bin/python3.12 -m pytest tests/test_yfinance_resilience.py -x` | No — W0 | ⬜ pending |
| 25-01-03 | 01 | 1 | PIPE-05 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_loader.py -x` | Partial | ⬜ pending |
| 25-01-04 | 01 | 1 | PIPE-03 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_runner.py::TestBuildInitialState -x` | Yes | ⬜ pending |
| 25-02-01 | 02 | 2 | PIPE-01 | integration | `.venv/bin/python3.12 -m pytest tests/test_cli_integration.py -x` | No — W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cli_integration.py` — stubs for PIPE-01 (subprocess CLI test)
- [ ] `tests/test_yfinance_resilience.py` — stubs for PIPE-02 (retry + disk cache)
- [ ] `tests/test_logging_config.py` — stubs for PIPE-04 (structlog configuration)
- [ ] `tests/core/test_soul_loader.py` — extend with `test_reload_souls` for PIPE-05
- [ ] `tests/core/test_import_boundaries.py` — extend with `test_logging_config_imports_cleanly`
- [ ] Framework install: `pip install structlog>=24.1.0`

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
