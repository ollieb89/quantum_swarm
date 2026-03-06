---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Yellow
stopped_at: Completed 03-l3-executors-nautilus-trader-integration-03-03-PLAN.md
last_updated: "2026-03-06T01:12:38.327Z"
progress:
  total_phases: 2
  completed_phases: 1
  total_plans: 10
  completed_plans: 9
---

# Project State

> Machine-readable state lives in YAML frontmatter above.
> This markdown body is auto-generated — do not edit manually.

## Current Phase

**Phase 3** — L3 Stateless Executors (NautilusTrader Integration)
- Status: In Progress
- Started: 2026-03-06
- Current Plan: 03-01 (completed 2026-03-06)
- Next: Plan 03-02 (NautilusTrader Backtester migration)
- Previous: Phase 2 (L2 Domain Managers & Adversarial Debate Layer) — Completed 2026-03-05

## Health

Status: Yellow

### Risks
- [0] Schema drift if payload format changes without script updates

## Architecture

- Runtime: Langgraph
- Pattern: Hierarchical Swarm (Strategic Orchestrator > Domain Managers > Stateless Executors)
- Communication: File Protocol
- Dashboard: Flask Socketio

## Key Paths

| Component | Path |
|-----------|------|
| Entry | `main.py` |
| Graph State | `src/graph/state.py` |
| Orchestrator | `src/graph/orchestrator.py` |
| L2 Agents | `src/agents/__init__.py` |
| L3 Executors | `src/graph/agents/l3/` |
| Data Models | `src/models/data_models.py` |
| Config | `config/swarm_config.yaml` |
| Planning | `.planning/` |
| Vault | `quantum-swarm/` |

## Decisions

- Phase 03-l3-executors-nautilus-trader-integration: Pinned nautilus_trader==1.223.0 for deterministic backtesting in Phase 3
- Phase 03-l3-executors-nautilus-trader-integration: Used xfail stubs pattern — each plan wave writes stubs; subsequent wave replaces with real tests + implementation
- Phase 03-l3-executors-nautilus-trader-integration: Pydantic v2 BaseModel as single source of truth for all L3 executor data contracts
- Phase 03-01: Pinned ccxt==4.4.60 — ccxt 5.x has broken lighter_client static dep that raises ModuleNotFoundError on import
- Phase 03-01: FRED uses DTWEXBGS (Broad USD Index) not DXY — DXY is not a FRED series identifier
- [Phase 03-02]: NT 1.223.0 Equity constructor uses raw_symbol (not symbol) and requires ts_event/ts_init — RESEARCH.md documented old API; fixed in implementation and tests
- [Phase 03-02]: NautilusTrader imports deferred inside _run_nautilus_backtest body — keeps module importable if NT has install issues
- [Phase 03-l3-executors-nautilus-trader-integration]: Interactive Brokers selected for live equities — NautilusTrader 1.223.0 has no Alpaca adapter; user confirmed IB (option-ib) at Task 0 checkpoint
- [Phase 03-l3-executors-nautilus-trader-integration]: TCP reachability gate (asyncio.wait_for open_connection, 3s timeout) used before IB TradingNode init — cheap fast-fail with clear error message
- [Phase 03-l3-executors-nautilus-trader-integration]: Paper mode uses yfinance last price + 0.01% slippage instead of BacktestEngine — simpler, no venue state, sufficient for single-order paper simulation

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 03-l3-executors-nautilus-trader-integration | 00 | 12min | 2 | 8 |
| 03-l3-executors-nautilus-trader-integration | 01 | 8min | 2 | 11 |
| Phase 03-l3-executors-nautilus-trader-integration P02 | 8min | 1 tasks | 2 files |
| Phase 03-l3-executors-nautilus-trader-integration P03 | 15min | 1 tasks | 2 files |

## Session

- **Stopped At:** Completed 03-l3-executors-nautilus-trader-integration-03-03-PLAN.md
- **Last session:** 2026-03-06T01:12:38.326Z
