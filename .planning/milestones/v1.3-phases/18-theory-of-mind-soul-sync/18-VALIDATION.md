---
phase: 18
slug: theory-of-mind-soul-sync
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python 3.12) |
| **Config file** | none — pytest.ini absent; uses default discovery |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py -x -q` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest tests/core/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py -x -q`
- **After every plan wave:** Run `.venv/bin/python3.12 -m pytest tests/core/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 0 | TOM-01 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py -x -q` | ❌ W0 | ⬜ pending |
| 18-01-02 | 01 | 1 | TOM-01 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestSwarmStateSoulSync -x` | ❌ W0 | ⬜ pending |
| 18-01-03 | 01 | 1 | TOM-01 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestSoulSyncHandshakeNode -x` | ❌ W0 | ⬜ pending |
| 18-01-04 | 01 | 1 | TOM-01 | smoke | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestGraphTopology -x` | ❌ W0 | ⬜ pending |
| 18-01-05 | 01 | 1 | TOM-01 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestNoLLMCalls -x` | ❌ W0 | ⬜ pending |
| 18-02-01 | 02 | 0 | TOM-02 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestAgentSoulUsers -x` | ❌ W0 | ⬜ pending |
| 18-02-02 | 02 | 1 | TOM-02 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestPublicSoulSummary -x` | ❌ W0 | ⬜ pending |
| 18-02-03 | 02 | 1 | TOM-02 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestPublicSoulSummary::test_drift_guard_excluded -x` | ❌ W0 | ⬜ pending |
| 18-02-04 | 02 | 1 | TOM-02 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestPublicSoulSummary::test_summary_length -x` | ❌ W0 | ⬜ pending |
| 18-02-05 | 02 | 1 | TOM-02 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestAgentSoulUsers::test_users_in_system_prompt -x` | ❌ W0 | ⬜ pending |
| 18-02-06 | 02 | 1 | TOM-02 | smoke | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestWarmupWithUsers -x` | ❌ W0 | ⬜ pending |
| 18-02-07 | 02 | 1 | TOM-02 | content | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestUserMdContent -x` | ❌ W0 | ⬜ pending |
| 18-02-08 | 02 | 1 | TOM-01/02 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestAgentSoulHashability -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/core/test_soul_sync.py` — stubs for TOM-01, TOM-02 (all 14 test cases)
- [ ] `src/graph/nodes/soul_sync_handshake.py` — new node module stub
- [ ] `src/core/souls/bullish_researcher/USER.md` — new content file
- [ ] `src/core/souls/bearish_researcher/USER.md` — new content file

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
