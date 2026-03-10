---
phase: 30
slug: kami-weight-rebalance-token-tracking
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 30 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/core/test_kami.py tests/core/test_merit_updater.py tests/test_budget_tracking.py -x` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest tests/ -x --ignore=tests/test_e2e_pipeline.py` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 30-01-01 | 01 | 1 | KAMI-06 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_kami.py -x` | ✅ | ⬜ pending |
| 30-01-02 | 01 | 1 | KAMI-07 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_kami.py tests/core/test_merit_updater.py -x` | ✅ | ⬜ pending |
| 30-02-01 | 02 | 2 | OBS-02, OBS-05 | unit | `.venv/bin/python3.12 -m pytest tests/test_budget_tracking.py -x` | ✅ | ⬜ pending |
| 30-02-02 | 02 | 2 | OBS-04 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_snapshot.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements. Test files for KAMI and budget tracking already exist.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Replay CLI token display | OBS-04 | Visual rendering | Run `python -m src.main replay show 1` and verify token line appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
