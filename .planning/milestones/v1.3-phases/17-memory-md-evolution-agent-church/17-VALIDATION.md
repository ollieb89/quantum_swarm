---
phase: 17
slug: memory-md-evolution-agent-church
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (installed in .venv) |
| **Config file** | pytest.ini / pyproject.toml (existing) |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/core/test_memory_writer.py tests/core/test_soul_proposal.py tests/core/test_agent_church.py -x -q` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3.12 -m pytest tests/core/test_memory_writer.py tests/core/test_soul_proposal.py tests/core/test_agent_church.py -x -q`
- **After every plan wave:** Run `.venv/bin/python3.12 -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 0 | EVOL-01 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_memory_writer.py::test_memory_entry_written -x` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 0 | EVOL-01 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_memory_writer.py::test_memory_cap_enforced -x` | ❌ W0 | ⬜ pending |
| 17-01-03 | 01 | 0 | EVOL-01 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_memory_writer.py::test_skip_on_no_output -x` | ❌ W0 | ⬜ pending |
| 17-01-04 | 01 | 0 | EVOL-01 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_memory_writer.py::test_kami_delta_computed -x` | ❌ W0 | ⬜ pending |
| 17-01-05 | 01 | 0 | EVOL-01 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_memory_writer.py::test_memory_writer_silent -x` | ❌ W0 | ⬜ pending |
| 17-01-06 | 01 | 0 | EVOL-01 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_memory_writer.py::test_memory_writer_nonblocking -x` | ❌ W0 | ⬜ pending |
| 17-02-01 | 02 | 0 | EVOL-02 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_proposal.py::test_proposal_schema_valid -x` | ❌ W0 | ⬜ pending |
| 17-02-02 | 02 | 0 | EVOL-02 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_proposal.py::test_proposal_atomic_write -x` | ❌ W0 | ⬜ pending |
| 17-02-03 | 02 | 0 | EVOL-02 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_proposal.py::test_trigger_kami_delta -x` | ❌ W0 | ⬜ pending |
| 17-02-04 | 02 | 0 | EVOL-02 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_proposal.py::test_trigger_drift_streak -x` | ❌ W0 | ⬜ pending |
| 17-02-05 | 02 | 0 | EVOL-02 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_proposal.py::test_trigger_merit_floor -x` | ❌ W0 | ⬜ pending |
| 17-02-06 | 02 | 0 | EVOL-02 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_proposal.py::test_merged_proposal -x` | ❌ W0 | ⬜ pending |
| 17-02-07 | 02 | 0 | EVOL-02 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_proposal.py::test_rate_limit -x` | ❌ W0 | ⬜ pending |
| 17-03-01 | 03 | 0 | EVOL-03 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_agent_church.py::test_church_approves -x` | ❌ W0 | ⬜ pending |
| 17-03-02 | 03 | 0 | EVOL-03 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_agent_church.py::test_church_rejects_missing_section -x` | ❌ W0 | ⬜ pending |
| 17-03-03 | 03 | 0 | EVOL-03 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_agent_church.py::test_church_rejects_too_long -x` | ❌ W0 | ⬜ pending |
| 17-03-04 | 03 | 0 | EVOL-03 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_agent_church.py::test_church_l1_raises -x` | ❌ W0 | ⬜ pending |
| 17-03-05 | 03 | 0 | EVOL-03 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_agent_church.py::test_church_cache_refresh -x` | ❌ W0 | ⬜ pending |
| 17-04-01 | ALL | 0 | All | smoke | `.venv/bin/python3.12 -m pytest tests/core/test_import_boundaries.py -x` | ✅ (new assertion) | ⬜ pending |
| 17-04-02 | ALL | 1 | All | integration | `.venv/bin/python3.12 -m pytest tests/test_graph_wiring.py -x` | ✅ (new assertion) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/core/test_memory_writer.py` — stubs for EVOL-01 (6 tests)
- [ ] `tests/core/test_soul_proposal.py` — stubs for EVOL-02 (7 tests)
- [ ] `tests/core/test_agent_church.py` — stubs for EVOL-03 (5 tests)
- [ ] `src/graph/nodes/memory_writer.py` — LangGraph node (needed before tests can import)
- [ ] `src/core/soul_proposal.py` — SoulProposal Pydantic model + helpers
- [ ] `src/core/agent_church.py` — standalone `__main__` review script
- [ ] `RequiresHumanApproval` — add to `src/core/soul_errors.py`
- [ ] `tests/core/test_import_boundaries.py` — add `test_agent_church_imports_cleanly` + `test_soul_proposal_imports_cleanly` to `TestCoreLeafImports`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SOUL.md diff visually coherent after Agent Church apply | EVOL-03 | Content correctness requires human judgment | Run `python -m src.core.agent_church`, inspect the updated SOUL.md section diff in git |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
