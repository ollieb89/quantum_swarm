---
phase: 24
slug: cycle-persistence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via `.venv/bin/python3.12 -m pytest`) |
| **Config file** | None (uses defaults) |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_snapshot.py tests/core/test_cycle_runner.py -x` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest tests/core/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3.12 -m pytest tests/core/test_cycle_snapshot.py tests/core/test_cycle_runner.py -x`
- **After every plan wave:** Run `.venv/bin/python3.12 -m pytest tests/core/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 24-01-01 | 01 | 1 | CYCL-02 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_snapshot.py -x` | ❌ W0 | ⬜ pending |
| 24-01-02 | 01 | 1 | CYCL-04 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_snapshot.py::test_manifest_fields -x` | ❌ W0 | ⬜ pending |
| 24-02-01 | 02 | 1 | CYCL-01 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_runner.py::test_completed_cycle_writes_snapshot -x` | ❌ W0 | ⬜ pending |
| 24-02-02 | 02 | 1 | CYCL-03 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_runner.py::test_cycle_id_allocation -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/core/test_cycle_snapshot.py` — stubs for CYCL-02, CYCL-04
- [ ] `tests/core/test_cycle_runner.py` — stubs for CYCL-01, CYCL-03
- [ ] Add `cycle_snapshot` and `cycle_runner` to `tests/core/test_import_boundaries.py`

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
