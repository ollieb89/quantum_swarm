---
phase: 16
slug: kami-merit-index
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python 3.12) |
| **Config file** | none — use `.venv/bin/python3.12 -m pytest` directly |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/test_kami.py tests/core/test_merit_loader.py tests/core/test_merit_updater.py -x -q` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest -x -q` |
| **Estimated runtime** | ~15 seconds (quick), ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3.12 -m pytest tests/test_kami.py tests/core/test_merit_loader.py tests/core/test_merit_updater.py -x -q`
- **After every plan wave:** Run `.venv/bin/python3.12 -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 0 | KAMI-01 | unit | `.venv/bin/python3.12 -m pytest tests/test_kami.py::test_compute_merit_formula -x` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 0 | KAMI-01 | unit | `.venv/bin/python3.12 -m pytest tests/test_kami.py::test_default_weights_sum_to_one -x` | ❌ W0 | ⬜ pending |
| 16-01-03 | 01 | 0 | KAMI-02 | unit | `.venv/bin/python3.12 -m pytest tests/test_kami.py::test_apply_ema -x` | ❌ W0 | ⬜ pending |
| 16-01-04 | 01 | 0 | KAMI-02 | unit | `.venv/bin/python3.12 -m pytest tests/test_kami.py::test_cold_start_and_bounds -x` | ❌ W0 | ⬜ pending |
| 16-01-05 | 01 | 0 | KAMI-02 | unit | `.venv/bin/python3.12 -m pytest tests/test_kami.py::test_recovery_penalised_on_invalid_input -x` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 0 | KAMI-03 | integration | `.venv/bin/python3.12 -m pytest tests/core/test_merit_loader.py::test_merit_scores_field_no_accumulation -x` | ❌ W0 | ⬜ pending |
| 16-02-02 | 02 | 0 | KAMI-03 | integration | `.venv/bin/python3.12 -m pytest tests/core/test_merit_loader.py::test_merit_loader_cold_start -x` | ❌ W0 | ⬜ pending |
| 16-02-03 | 02 | 0 | KAMI-03 | integration | `.venv/bin/python3.12 -m pytest tests/core/test_merit_updater.py::test_merit_updater_persists -x` | ❌ W0 | ⬜ pending |
| 16-03-01 | 03 | 0 | KAMI-04 | unit | `.venv/bin/python3.12 -m pytest tests/test_adversarial_debate.py::test_debate_synthesizer_uses_merit -x` | ❌ W0 | ⬜ pending |
| 16-03-02 | 03 | 0 | KAMI-04 | unit | `.venv/bin/python3.12 -m pytest tests/test_kami.py::test_fidelity_zero_for_empty_identity -x` | ❌ W0 | ⬜ pending |
| 16-03-03 | 03 | 0 | KAMI-04 | unit | `.venv/bin/python3.12 -m pytest tests/test_adversarial_debate.py::test_debate_synthesizer_neutral_fallback -x` | ❌ W0 | ⬜ pending |
| 16-04-01 | 04 | 0 | All | unit | `.venv/bin/python3.12 -m pytest tests/test_audit_chain.py::test_merit_scores_in_audit_hash -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_kami.py` — unit tests for `compute_merit`, `apply_ema`, cold start, floor/ceil, fidelity gate; covers KAMI-01, KAMI-02, KAMI-04
- [ ] `tests/core/test_merit_loader.py` — mock DB, verify `merit_scores` populated and no accumulation; covers KAMI-03
- [ ] `tests/core/test_merit_updater.py` — mock state + DB, verify EMA update + persist; covers KAMI-03
- [ ] `tests/test_adversarial_debate.py` — add `test_debate_synthesizer_uses_merit` and `test_debate_synthesizer_neutral_fallback` to existing test file; covers KAMI-04
- [ ] `tests/test_audit_chain.py` — add `test_merit_scores_in_audit_hash`; covers audit requirement from CONTEXT.md

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Persisted merit score survives session restart | KAMI-02 | Requires live PostgreSQL with data across process restart | Run full cycle, stop process, restart, verify score loaded from DB matches last persisted value |
| Consensus signal proxy (confidence delta) produces sane weighting | KAMI-03 | Design decision within Claude's Discretion — not verifiable without live debate data | Inspect `weighted_consensus_score` in a full swarm run with two conflicting analyses |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
