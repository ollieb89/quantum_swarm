---
phase: 31
slug: chromadb-prune-to-obsidian
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/memory/ -x -q` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3.12 -m pytest tests/memory/ -x -q`
- **After every plan wave:** Run `.venv/bin/python3.12 -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 31-01-01 | 01 | 1 | OBS-03 | unit | `.venv/bin/python3.12 -m pytest tests/memory/test_prune.py -x -q` | ❌ W0 | ⬜ pending |
| 31-01-02 | 01 | 1 | OBS-06 | unit | `.venv/bin/python3.12 -m pytest tests/memory/test_prune.py -x -q` | ❌ W0 | ⬜ pending |
| 31-01-03 | 01 | 1 | OBS-07 | unit | `.venv/bin/python3.12 -m pytest tests/memory/test_prune.py -x -q` | ❌ W0 | ⬜ pending |
| 31-02-01 | 02 | 2 | OBS-03 | integration | `.venv/bin/python3.12 -m pytest tests/cli/test_prune_cli.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/memory/test_prune.py` — stubs for OBS-03, OBS-06, OBS-07 (prune core logic)
- [ ] `tests/cli/test_prune_cli.py` — stubs for CLI integration

*Existing infrastructure covers test framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Obsidian Markdown renders correctly | OBS-03 | Obsidian rendering | Open archived .md files in Obsidian, verify YAML frontmatter and content display |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
