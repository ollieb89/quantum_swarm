---
phase: 23
slug: full-persona-population
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via `.venv/bin/python3.12 -m pytest`) |
| **Config file** | None (default discovery) |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py tests/core/test_drift_eval.py tests/core/test_soul_loader.py -x -q` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest tests/core/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py tests/core/test_soul_loader.py -x -q`
- **After every plan wave:** Run `.venv/bin/python3.12 -m pytest tests/core/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 1 | PERS-05 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py -k hexaco -x -q` | ❌ W0 | ⬜ pending |
| 23-01-02 | 01 | 1 | PERS-06 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py -k drift -x -q` | ❌ W0 | ⬜ pending |
| 23-01-03 | 01 | 1 | PERS-01..04 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py -k structure -x -q` | ❌ W0 | ⬜ pending |
| 23-02-01 | 02 | 1 | PERS-01 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py -k momentum -x -q` | ❌ W0 | ⬜ pending |
| 23-02-02 | 02 | 1 | PERS-02 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py -k cassandra -x -q` | ❌ W0 | ⬜ pending |
| 23-02-03 | 02 | 1 | PERS-03 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py -k sigma -x -q` | ❌ W0 | ⬜ pending |
| 23-02-04 | 02 | 1 | PERS-04 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py -k guardian -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/core/test_persona_content.py` — extend with per-agent structural tests (MOMENTUM, CASSANDRA, SIGMA, GUARDIAN matching AXIOM's section structure)
- [ ] `tests/core/test_persona_content.py` — add HEXACO-6 pairwise distance validation test (all 10 pairs > 1.0)
- [ ] `tests/core/test_persona_content.py` — add drift_guard rule count and parseability tests for all 5 agents

*Existing infrastructure covers framework and fixture needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Voice distinctiveness | PERS-01..04 | Qualitative judgment — register, cadence, vocabulary | Read each SOUL.md Voice section; verify each agent is immediately recognizable |
| Persona depth quality | PERS-01..04 | Qualitative judgment — institutional vs theatrical | Read Core Beliefs; verify professional research-desk tone, not character roleplay |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
