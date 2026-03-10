---
phase: 28
slug: gemini-api-circuit-breaker
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (via `.venv/bin/python3.12 -m pytest`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/core/test_circuit_breaker.py -x` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3.12 -m pytest tests/core/test_circuit_breaker.py -x`
- **After every plan wave:** Run `.venv/bin/python3.12 -m pytest -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 28-01-01 | 01 | 1 | SEC-03 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_circuit_breaker.py::test_state_transitions -x` | ❌ W0 | ⬜ pending |
| 28-01-02 | 01 | 1 | SEC-03 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_circuit_breaker.py::test_is_transient_llm_error -x` | ❌ W0 | ⬜ pending |
| 28-01-03 | 01 | 1 | SEC-04 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_circuit_breaker.py::test_open_returns_empty -x` | ❌ W0 | ⬜ pending |
| 28-01-04 | 01 | 1 | SEC-06 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_circuit_breaker.py::test_transition_logging -x` | ❌ W0 | ⬜ pending |
| 28-01-05 | 01 | 1 | SEC-07 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_circuit_breaker.py::test_half_open_recovery -x` | ❌ W0 | ⬜ pending |
| 28-02-01 | 02 | 2 | SEC-05 | unit | `.venv/bin/python3.12 -m pytest tests/test_circuit_breaker_integration.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/core/test_circuit_breaker.py` — stubs for SEC-03, SEC-04, SEC-06, SEC-07
- [ ] `tests/test_circuit_breaker_integration.py` — stubs for SEC-05 (with_audit_logging integration)

*Existing infrastructure covers framework requirements. 680 tests currently pass.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
