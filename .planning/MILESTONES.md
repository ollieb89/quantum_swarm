# Milestones

## v1.2 Risk Governance and Rule Validation (Shipped: 2026-03-08)

**Phases completed:** 6 phases (8, 9, 10, 11, 13, 14), 14 plans
**Tests:** 260+ passing, 0 failures
**LOC:** ~23,500 Python
**Timeline:** 2 days (2026-03-07 → 2026-03-08)

**Key accomplishments:**
1. Portfolio risk governance layer — `InstitutionalGuard` enforces drawdown circuit breaker (>5% daily loss), exposure/concentration limits, and restricted asset blocklist; wired as `claw_guard → institutional_guard` in LangGraph execution graph (closes RISK-07)
2. Structured JSON memory registry — `MemoryRegistry` with Pydantic-validated rules, one-way lifecycle transitions (proposed → active → archived), atomic file writes, and `update_status()` enforcement (closes MEM-04, MEM-05)
3. 2-of-3 backtest validation harness — `RuleValidator` runs NautilusTrader baseline + treatment backtests per proposed rule; promotes if ≥2 of Sharpe/drawdown/win-rate improve; MiFID II audit event written to `data/audit.jsonl` on every promotion/rejection (closes MEM-06)
4. Immutable decision cards — SHA-256 hash-chained `DecisionCard` JSON written by `decision_card_writer_node` for every trade; includes portfolio risk score, applied rule IDs, and analyst rationale (closes EXEC-04)
5. Gap closure (RISK-07/08, MEM-06) — `institutional_guard_node` wired with conditional routing; `trade_risk_score`/`portfolio_heat` propagate to DecisionCard fields; `asyncio.run()` replaced with `ThreadPoolExecutor` to fix silent async validation bypass
6. Full audit trail — MiFID II rule validation events + immutable trade decision cards in `data/audit.jsonl`

### Tech Debt (from audit)
- `risk_approved` not written to `True` on institutional_guard approval path — stays `None`; routing unaffected but audit trail incomplete
- Nyquist VALIDATION.md files missing for all v1.2 phases — address in v1.3 with `/gsd:validate-phase`
- Pre-existing: `ccxt` broken package import (Phase 3), Pydantic v1 class-based config in `src/models/audit.py`

---

## v1.1 Self-Improvement (Shipped: 2026-03-08)

**Phases completed:** 4 phases (5, 6, 7, 12), 7 plans
**Tests:** 246 passing, 0 failures
**LOC:** ~22,500 Python
**Timeline:** 3 days (2026-03-06 → 2026-03-08)

**Key accomplishments:**
1. Centralized `quant-alpha-intelligence` skill (RSI, MACD, Bollinger Bands) with `{name}_{period}` result keying — 12 unit tests covering all indicator paths
2. ATR-based stop-loss hard gate — OrderRouter rejects any trade missing valid stop-loss; `stop_loss_level`, `entry_price`, `position_size` written to PostgreSQL audit record on every trade
3. Weekly PerformanceReviewAgent + RuleGenerator self-improvement pipeline with `--review` CLI, lazy LLM init, and dual-source memory injection (JSON registry + MEMORY.md)
4. MEM-03 gap closed end-to-end — rules promoted to `active` after `persist_rules()`, institutional memory forwarded into MacroAnalyst/QuantModeler sub-graph invocations (closes MC-01, MC-02)

### Tech Debt (from audit)
- Advisory MC-03: ATR result key `atr_14` has no typed extraction layer — QuantModeler LLM must infer from period-suffixed key
- `datetime.utcnow()` deprecated in `l3_executor.py:332` — DeprecationWarning, no functional impact
- Column naming inconsistency: `review_agent.py:80` maps DB column `stop_loss_level` to dict key `stop_loss`
- Phase 12 VERIFICATION.md stale — describes superseded direct-promotion behavior (replaced by Phase 14)

---

## v1.0 MVP (Shipped: 2026-03-06)

**Phases completed:** 4 phases, 13 plans
**Tests:** 155 passing, 0 failures
**LOC:** ~14,600 Python
**Timeline:** 2 days (2026-03-05 → 2026-03-06)
**Git commits:** 67

**Key accomplishments:**
1. LangGraph StateGraph orchestrator (L1→L2 fan-out/fan-in→L3 chain) with ClawGuard security and skill registry
2. MacroAnalyst & QuantModeler ReAct agents with BudgetedTool/ToolCache wrapping
3. Adversarial debate layer (BullishResearcher vs BearishResearcher) with DebateSynthesizer and weighted consensus scoring (>0.6 risk gate)
4. Full L3 executor stack: real DataFetcher (yfinance/ccxt/news/economic), NautilusTrader backtesting, multi-venue OrderRouter (paper/IB/Binance)
5. PostgreSQL persistence with AsyncPostgresSaver, hash-chained immutable audit trail (SHA-256), and Trade Warehouse with full audit provenance
6. Institutional guardrails: leverage limits (max 10x), restricted asset blocklist, MiFID II audit trail

### Known Gaps
- REQUIREMENTS.md traceability never updated during development (all reqs show Pending)
- Phase 1 plan 03 summary created retroactively
- Phase 4 had no GSD-style PLAN files (implemented in single session)
- RISK-03 (stop-loss calculation), MEM-02/03 (weekly review loop, rule generator) — deferred to v1.1

---
