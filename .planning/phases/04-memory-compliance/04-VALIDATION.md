---
phase: 4
slug: memory-compliance
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-07
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pytest.ini` or `pyproject.toml` |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/test_persistence.py tests/test_audit_logger.py tests/test_institutional_guard.py -x -q` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3.12 -m pytest tests/test_persistence.py tests/test_audit_logger.py tests/test_institutional_guard.py -x -q`
- **After every plan wave:** Run `.venv/bin/python3.12 -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 01 | 1 | MEM-01 | unit | `pytest tests/test_persistence.py -x -q` | ✅ | ⬜ pending |
| 4-01-02 | 01 | 1 | SEC-01 | unit | `pytest tests/test_audit_logger.py -x -q` | ✅ | ⬜ pending |
| 4-01-03 | 01 | 1 | SEC-02 | unit | `pytest tests/test_institutional_guard.py -x -q` | ✅ | ⬜ pending |
| 4-01-04 | 01 | 2 | SEC-04 | unit | `pytest tests/test_memory_service.py -x -q` | ✅ | ⬜ pending |
| 4-01-05 | 01 | 2 | RISK-02 | unit | `pytest tests/test_institutional_guard.py -x -q` | ✅ | ⬜ pending |
| 4-01-06 | 01 | 2 | MEM-01 | integration | `pytest tests/test_persistence.py -k integration -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_persistence.py` — AsyncPostgresSaver unit tests (mock pool)
- [ ] `tests/test_audit_logger.py` — hash-chain unit tests (no DB required)
- [ ] `tests/test_institutional_guard.py` — async compliance gate tests (mock trades table)
- [ ] `tests/conftest.py` — shared fixtures (mock pool, mock DB connection)

*Note: Fix async test mismatch — `check_compliance()` tests must use `asyncio.run()` or `pytest-asyncio`. Fix `exit_time` column in DDL before integration tests.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker PostgreSQL starts and accepts connections on port 5433 | MEM-01 | Requires live Docker | `docker compose up -d postgres && psql postgresql://swarm:swarm@localhost:5433/swarm -c '\l'` |
| Hash chain tamper detection (modify a log entry, verify chain breaks) | SEC-01 | State manipulation required | Insert row, modify SHA-256, run `verify_chain()` — expect `ChainIntegrityError` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
