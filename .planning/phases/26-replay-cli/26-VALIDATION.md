---
phase: 26
slug: replay-cli
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_store.py tests/cli/test_replay.py -x` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest tests/ -x --ignore=tests/integration` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3.12 -m pytest tests/core/test_cycle_store.py tests/cli/test_replay.py -x`
- **After every plan wave:** Run `.venv/bin/python3.12 -m pytest tests/ -x --ignore=tests/integration`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 1 | REPL-01 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_store.py::test_list_cycles -x` | ❌ W0 | ⬜ pending |
| 26-01-02 | 01 | 1 | REPL-02 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_cycle_store.py::test_load_cycle -x` | ❌ W0 | ⬜ pending |
| 26-02-01 | 02 | 1 | REPL-03 | unit | `.venv/bin/python3.12 -m pytest tests/cli/test_replay.py::test_show_by_id -x` | ❌ W0 | ⬜ pending |
| 26-02-02 | 02 | 1 | REPL-04 | unit | `.venv/bin/python3.12 -m pytest tests/cli/test_replay.py::test_merit_display -x` | ❌ W0 | ⬜ pending |
| 26-02-03 | 02 | 1 | REPL-05 | unit | `.venv/bin/python3.12 -m pytest tests/cli/test_replay.py::test_drift_display -x` | ❌ W0 | ⬜ pending |
| 26-02-04 | 02 | 2 | REPL-06 | unit | `.venv/bin/python3.12 -m pytest tests/cli/test_replay.py::test_compare -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/core/test_cycle_store.py` — stubs for REPL-01, REPL-02
- [ ] `tests/cli/__init__.py` — new test package
- [ ] `tests/cli/test_replay.py` — stubs for REPL-03, REPL-04, REPL-05, REPL-06
- [ ] `src/cli/__init__.py` — new source package
- [ ] Add `cycle_store` to `test_import_boundaries.py` TestCoreLeafImports
- [ ] Add `rich>=13.0` to pyproject.toml dependencies

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Rich output degrades in pipe | REPL-03 | TTY detection is runtime behavior | `python -m src.main replay list \| cat` — verify no ANSI codes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
