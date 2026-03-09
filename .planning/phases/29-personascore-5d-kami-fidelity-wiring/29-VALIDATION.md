---
phase: 29
slug: personascore-5d-kami-fidelity-wiring
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/core/test_persona_scorer.py -x -q` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3.12 -m pytest tests/core/test_persona_scorer.py -x -q`
- **After every plan wave:** Run `.venv/bin/python3.12 -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 29-01-01 | 01 | 1 | SOUL-09 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_scorer.py -x -q` | ❌ W0 | ⬜ pending |
| 29-01-02 | 01 | 1 | SOUL-10 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_scorer.py -x -q` | ❌ W0 | ⬜ pending |
| 29-01-03 | 01 | 1 | SOUL-11 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_scorer.py -x -q` | ❌ W0 | ⬜ pending |
| 29-02-01 | 02 | 2 | SOUL-12 | integration | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_runner_persona.py -x -q` | ❌ W0 | ⬜ pending |
| 29-02-02 | 02 | 2 | SOUL-13 | integration | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_runner_persona.py -x -q` | ❌ W0 | ⬜ pending |
| 29-02-03 | 02 | 2 | KAMI-05 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_kami.py -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/core/test_persona_scorer.py` — stubs for SOUL-09, SOUL-10, SOUL-11
- [ ] `tests/core/test_cycle_runner_persona.py` — stubs for SOUL-12, SOUL-13
- [ ] Existing `tests/core/test_kami.py` covers KAMI-05 extension

*Existing test infrastructure covers framework needs. Only new test files needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LLM judge produces meaningful rationale | SOUL-09 | Subjective quality assessment | Run a real cycle with `python -m src.main analyze BTC --mode paper`, check rationale in persona_scores table |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
