---
phase: 11
slug: explainability-decision-cards
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + unittest (both used in project) |
| **Config file** | none — run directly |
| **Quick run command** | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py -x -q` |
| **Full suite command** | `.venv/bin/python3.12 -m pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python3.12 -m pytest tests/test_decision_card.py -x -q`
- **After every plan wave:** Run `.venv/bin/python3.12 -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 0 | EXEC-04 | unit | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py -x -q` | ❌ W0 | ⬜ pending |
| 11-02-01 | 01 | 1 | EXEC-04 (builder) | unit | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py::TestDecisionCardBuilder -x` | ❌ W0 | ⬜ pending |
| 11-02-02 | 01 | 1 | EXEC-04 (rule IDs) | unit | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py::TestDecisionCardBuilder::test_applied_rule_ids -x` | ❌ W0 | ⬜ pending |
| 11-02-03 | 01 | 1 | EXEC-04 (hash) | unit | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py::TestHashing -x` | ❌ W0 | ⬜ pending |
| 11-02-04 | 01 | 1 | EXEC-04 (null prev_hash) | unit | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py::TestHashing::test_verify_null_prev_hash -x` | ❌ W0 | ⬜ pending |
| 11-03-01 | 01 | 1 | EXEC-04 (write path) | integration | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py::TestDecisionCardWriter -x` | ❌ W0 | ⬜ pending |
| 11-03-02 | 01 | 1 | EXEC-04 (retry) | integration | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py::TestDecisionCardWriter::test_retry_behavior -x` | ❌ W0 | ⬜ pending |
| 11-03-03 | 01 | 1 | EXEC-04 (success-only) | unit | `.venv/bin/python3.12 -m pytest tests/test_decision_card.py::TestDecisionCardWriter::test_skips_failed_trades -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_decision_card.py` — stubs for all EXEC-04 behaviors (confirmed absent via research)
- [ ] No new framework install needed — pytest + unittest already in use

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full smoke run with live Google API key | EXEC-04 | Requires live network + API credentials | Run `python main.py` with `GOOGLE_API_KEY` set; confirm `data/audit.jsonl` contains `decision_card_created` entry after a trade |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
