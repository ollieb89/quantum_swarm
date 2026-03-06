---
phase: 3
slug: l3-executors-nautilus-trader-integration
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-06
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini or pyproject.toml |
| **Quick run command** | `pytest tests/test_phase3_smoke.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_phase3_smoke.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 0 | DataFetcher install | smoke | `python -c "import nautilus_trader; print('ok')"` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 1 | DataFetcher node | unit | `pytest tests/test_data_fetcher.py -x -q` | ❌ W0 | ⬜ pending |
| 3-01-03 | 01 | 1 | Dexter bridge | unit | `pytest tests/test_dexter_bridge.py -x -q` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 2 | Backtester node | unit | `pytest tests/test_backtester.py -x -q` | ❌ W0 | ⬜ pending |
| 3-02-02 | 02 | 2 | BacktestEngine async | unit | `pytest tests/test_backtester.py::test_async_run -x -q` | ❌ W0 | ⬜ pending |
| 3-03-01 | 03 | 3 | OrderRouter node | unit | `pytest tests/test_order_router.py -x -q` | ❌ W0 | ⬜ pending |
| 3-03-02 | 03 | 3 | IB adapter integration | integration | `pytest tests/test_order_router.py::test_ib_paper -x -q` | ❌ W0 | ⬜ pending |
| 3-04-01 | 04 | 4 | TradeLogger node | unit | `pytest tests/test_trade_logger.py -x -q` | ❌ W0 | ⬜ pending |
| 3-04-02 | 04 | 4 | Self-improvement loop | integration | `pytest tests/test_l3_integration.py::test_feedback_loop_l2_receives_trade_history -x -q` | ❌ W0 | ⬜ pending |
| 3-04-03 | 04 | 4 | Orchestrator wiring | e2e | `pytest tests/test_l3_integration.py::test_end_to_end_paper_graph -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_phase3_smoke.py` — nautilus_trader import + basic node stubs
- [ ] `tests/test_data_fetcher.py` — DataFetcher node stubs
- [ ] `tests/test_dexter_bridge.py` — Dexter bridge stubs
- [ ] `tests/test_backtester.py` — Backtester node stubs
- [ ] `tests/test_order_router.py` — OrderRouter node stubs
- [ ] `tests/test_trade_logger.py` — TradeLogger node stubs
- [ ] `tests/test_l3_integration.py` — self-improvement loop and e2e orchestrator wiring stubs
- [ ] `pip install nautilus_trader` — if not already in pyproject.toml/requirements

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| IB paper trading connection | OrderRouter live mode | Requires IB account + TWS/Gateway running | Start TWS in paper mode, run `pytest tests/test_order_router.py::test_ib_paper -s` and confirm order submission |
| Binance live execution | OrderRouter crypto mode | Requires API keys + network | Set BINANCE_API_KEY env, run `pytest tests/test_order_router.py::test_binance_live -s` |
| Dexter FINANCIAL_DATASETS_API_KEY | Dexter bridge | Requires external API key | Set env var, run `pytest tests/test_dexter_bridge.py::test_live_data -s` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
