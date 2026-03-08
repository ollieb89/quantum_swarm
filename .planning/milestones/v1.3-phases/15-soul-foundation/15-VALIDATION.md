---
phase: 15
slug: soul-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/core/ -x -q` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3.12 -m pytest tests/core/ -x -q`
- **After every plan wave:** Run `.venv/bin/python3.12 -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 0 | SOUL-01,SOUL-03,SOUL-04,SOUL-06 | unit stub | `.venv/bin/python3.12 -m pytest tests/core/test_soul_loader.py -x` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 0 | SOUL-02 | content stub | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py -x` | ❌ W0 | ⬜ pending |
| 15-01-03 | 01 | 0 | SOUL-05,SOUL-07 | integration stub | `.venv/bin/python3.12 -m pytest tests/core/test_macro_analyst_soul.py -x` | ❌ W0 | ⬜ pending |
| 15-01-04 | 01 | 1 | SOUL-01 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_loader.py -x` | ✅ W0 | ⬜ pending |
| 15-01-05 | 01 | 1 | SOUL-03 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_loader.py::test_warmup_completes -x` | ✅ W0 | ⬜ pending |
| 15-01-06 | 01 | 1 | SOUL-04 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_loader.py::test_swarmstate_fields -x` | ✅ W0 | ⬜ pending |
| 15-02-01 | 02 | 1 | SOUL-02 | content | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py::test_axiom_identity -x` | ✅ W0 | ⬜ pending |
| 15-02-02 | 02 | 2 | SOUL-05 | integration | `.venv/bin/python3.12 -m pytest tests/core/test_macro_analyst_soul.py -x` | ✅ W0 | ⬜ pending |
| 15-02-03 | 02 | 2 | SOUL-06,SOUL-07 | integration | `.venv/bin/python3.12 -m pytest tests/core/ -x -q` | ✅ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/core/__init__.py` — make `tests/core/` a package for proper pytest collection
- [ ] `tests/core/conftest.py` — `clear_soul_caches` autouse fixture calling `load_soul.cache_clear()` before and after every test
- [ ] `tests/core/test_soul_loader.py` — failing stubs for SOUL-01, SOUL-03, SOUL-04, SOUL-06
- [ ] `tests/core/test_persona_content.py` — failing stubs for SOUL-02
- [ ] `tests/core/test_macro_analyst_soul.py` — failing stubs for SOUL-05, SOUL-07
- [ ] `src/core/souls/macro_analyst/IDENTITY.md` — AXIOM identity content (required by all soul tests)
- [ ] `src/core/souls/macro_analyst/SOUL.md` — AXIOM soul content
- [ ] `src/core/souls/macro_analyst/AGENTS.md` — AXIOM agents content
- [ ] `src/core/souls/macro_analyst/RULES.md` — AXIOM rules content
- [ ] `src/core/souls/macro_analyst/CONTEXT.md` — AXIOM context content
- [ ] Four skeleton soul directories (bullish_researcher, bearish_researcher, risk_manager, trade_executor) with minimum viable content for `warmup_soul_cache()` to pass

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
