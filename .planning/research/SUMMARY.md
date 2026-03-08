# Project Research Summary

**Project:** Quantum Swarm v1.4 Beta: Observable Swarm
**Domain:** Multi-agent LLM trading swarm observability, persona diversity, cycle persistence and replay
**Researched:** 2026-03-08
**Confidence:** HIGH

## Executive Summary

Quantum Swarm v1.4 transforms a functioning but opaque multi-agent trading system into an observable one. The existing v1.3 codebase (300+ tests, ~30,600 LOC) has strong infrastructure -- LangGraph StateGraph orchestration, PostgreSQL-backed audit logging with SHA-256 hash chains, KAMI merit scoring, and a soul/persona system -- but 4 of 5 agent personas are skeletons, no complete cycle has run against real market data, and there is no way to review what the swarm decided or why. The v1.4 milestone closes these gaps: populate all personas with HEXACO-6-informed personality diversity, run end-to-end against real data, persist complete cycle snapshots, and provide a CLI replay tool for post-mortem analysis.

The recommended approach is strictly additive: the existing graph topology stays unchanged. New capabilities wrap the graph (CycleRunner for snapshot capture), extend it minimally (one new SwarmState field, one new PostgreSQL table), or consume its output read-only (replay CLI). The stack additions are minimal -- promote two transitive dependencies (typer, rich) to explicit, add structlog for structured logging. No new frameworks. HEXACO-6 persona profiles are a design-time authoring guide validated by Pydantic, not a runtime personality engine. The architecture research strongly recommends post-graph snapshot extraction rather than adding snapshot nodes inside the graph, avoiding the complexity of routing four distinct exit paths.

The primary risks are: (1) checkpoint state bloat from operator.add accumulator fields if cycle artifacts are naively stored in SwarmState, (2) yfinance rate limiting killing end-to-end pipeline runs during development, (3) persona collapse where Gemini's RLHF training overrides HEXACO-diverse persona instructions, and (4) silent failures from missing drift_guard YAML blocks and dummy paper fill prices masking data quality issues. All have concrete mitigations identified in the research. The critical ordering constraint is that persona population must come first -- everything downstream depends on agents producing meaningful, differentiated output.

---

## Key Findings

### Recommended Stack

The v1.4 stack is deliberately conservative. Two dependencies already installed as transitive deps (typer, rich) get promoted to explicit in pyproject.toml. One new dependency (structlog) is added for structured JSON logging. Everything else uses stdlib or existing installed packages.

**New explicit dependencies:**
- **typer** (>=0.24.0): CLI framework for replay tool -- already installed, type-hint-driven, built on Click
- **rich** (>=14.0.0): Terminal formatting for replay display -- already installed, provides tables/panels/syntax highlighting
- **structlog** (>=24.0.0): Structured JSON logging for production runs -- wraps stdlib logging, non-invasive

**Existing stack unchanged:** Python 3.12, LangGraph 1.0.10, psycopg 3.3.3, pydantic 2.12.5, pyyaml 6.0.3, langgraph-checkpoint-postgres 3.0.4.

**Explicitly rejected:** textual (TUI overkill), tenacity (15 lines of manual backoff suffice), loguru (replaces stdlib logging -- too invasive), SQLAlchemy (raw psycopg3 pattern works), any HEXACO personality runtime library (profiles are static metadata, not simulations).

### Expected Features

**Must have (table stakes for "observable beta" label):**
- Fully populated personas (MOMENTUM, CASSANDRA, SIGMA, GUARDIAN) with AXIOM-quality content and drift_guard YAML
- End-to-end pipeline execution against real market data (yfinance equities path)
- Per-cycle artifact persistence (CycleSnapshot to PostgreSQL cycle_snapshots table)
- Cycle list and single-cycle detail CLI commands
- Step-through replay CLI walking execution order
- Merit weight and drift flag time series from existing MEMORY.md data

**Should have (differentiators, post-beta validation):**
- HEXACO-6 persona diversity profiles with pairwise distance validation
- Debate tension score quantifying Bull/Bear disagreement
- Cross-cycle comparison CLI (side-by-side diff of two cycles)
- Dashboard-ready JSON export for external visualization

**Defer (v2+):**
- Checkpoint fork / what-if replay (re-runs LLM calls, non-deterministic, expensive)
- PersonaScore 5D fidelity evaluation (5 extra LLM calls per evaluation)
- Real-time streaming dashboard (massive frontend complexity, low marginal value)
- Automated HEXACO diversity enforcement gate (diversity is design-time, not runtime)

### Architecture Approach

The architecture follows one principle: the existing graph topology is frozen. All new capabilities attach outside or alongside. CycleRunner wraps graph invocation, assigns a cycle_id, extracts a curated CycleSnapshot from the final state after ainvoke() returns, and persists it to a dedicated PostgreSQL table. The replay CLI is a pure read-only consumer of that table. Persona population is content-only changes to existing soul directories.

**Major components:**
1. **CycleRunner** (new, `src/core/cycle_runner.py`) -- wraps graph invocation, assigns cycle_id, captures and persists CycleSnapshot post-invocation
2. **cycle_snapshots table** (new PostgreSQL DDL) -- denormalized JSONB storage with indexed columns for fast filtering
3. **swarm-replay CLI** (new, `src/cli/replay.py`) -- list, show, diff, timeline commands using typer + rich
4. **src/runner.py** (new) -- proper end-to-end entry point replacing legacy main.py simulation stub
5. **Soul persona content** (modified files only) -- 4 agents x 3 files (IDENTITY.md, SOUL.md with drift_guard, AGENTS.md)

**Key patterns to follow:**
- Post-graph snapshot extraction (not an in-graph node) -- handles all 4 exit paths uniformly
- Cycle ID separate from LangGraph thread_id -- domain concept vs. checkpoint management concept
- Replay via direct PostgreSQL query (not LangGraph time-travel) -- one snapshot per cycle, decoupled from checkpoint internals
- LangGraphOrchestrator gets a new run_cycle_async() method; existing run_task_async() delegates to it (non-breaking)

### Critical Pitfalls

1. **Checkpoint state bloat** -- Do NOT store cycle artifacts in SwarmState. Write to dedicated PostgreSQL table or filesystem. operator.add fields checkpoint the FULL accumulated list at every step. Fix BEFORE implementing persistence.
2. **operator.add message list growth** -- messages accumulate 15-20 entries per cycle with no trimming. Implement message trimming or a custom sliding-window reducer. Fix BEFORE adding cycle persistence.
3. **yfinance rate limiting** -- No retry logic in data_fetcher_node. Add exponential backoff (3 retries), data caching layer for development, and a --cached-data flag. Fix FIRST in end-to-end hardening.
4. **Missing drift_guard YAML** -- 4 skeleton personas silently disable drift detection (empty rules = no flags). Require drift_guard YAML as a mandatory deliverable per persona. Validate at warmup_soul_cache().
5. **Audit hash chain breakage** -- Every new SwarmState field enters the audit hash by default. Add cycle_id and any new fields to AUDIT_EXCLUDED_FIELDS immediately. Test verify_chain() after integration.

---

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Full Persona Population + HEXACO-6 Profiles

**Rationale:** Critical path blocker. Everything downstream depends on agents producing meaningful, differentiated output. Skeleton personas produce shallow, convergent memos that make observability uninteresting. Zero code risk -- pure content authoring. HEXACO-6 profiling should happen during authoring, not after, because it informs SOUL.md prose.
**Delivers:** 4 fully populated personas (MOMENTUM, CASSANDRA, SIGMA, GUARDIAN) with AXIOM-quality IDENTITY.md, SOUL.md (including drift_guard YAML), AGENTS.md, and HEXACO.yaml profiles. Pairwise diversity validation passing minimum distance threshold.
**Addresses:** Fully populated personas (P1 table stake), HEXACO-6 diversity framework (P2 differentiator -- pulled forward because authoring is concurrent)
**Avoids:** Pitfall 4 (stale cache -- add --reload-souls flag), Pitfall 6 (persona collapse -- behavioral descriptions not raw trait scores), Pitfall 10 (missing drift YAML -- mandatory deliverable per persona)

### Phase 2: Cycle Persistence Infrastructure

**Rationale:** Core data contract. Without a CycleSnapshot schema and persistence layer, there is nothing to replay or compare. Must be built before the runner or CLI. The snapshot schema serves as the contract between producer (CycleRunner) and consumer (replay CLI).
**Delivers:** CycleSnapshot Pydantic model, cycle_snapshots PostgreSQL table with denormalized columns, CycleRunner class wrapping graph invocation, extract_cycle_snapshot() function, SwarmState.cycle_id field, AUDIT_EXCLUDED_FIELDS update.
**Uses:** pydantic (existing), psycopg (existing), pathlib/json (stdlib)
**Implements:** CycleRunner component, cycle_snapshots table, post-graph extraction pattern
**Avoids:** Pitfall 1 (state bloat -- artifacts go to dedicated table, not SwarmState), Pitfall 2 (message growth -- add trimming), Pitfall 3 (sync I/O -- use asyncio.to_thread), Pitfall 8 (audit hash -- update exclusion set)

### Phase 3: End-to-End Pipeline Runner + Hardening

**Rationale:** Must exercise the full pipeline with real data before building the replay tool. Validates that all 5 agents produce non-None output, debate synthesis works, risk gate fires, and CycleRunner persists a complete snapshot. Pipeline hardening (retry logic, structured logging, fallback price elimination) is inseparable from this phase.
**Delivers:** src/runner.py entry point, data_fetcher retry with exponential backoff, structlog integration, paper fill price validation (fail explicitly on bad data), data caching layer for development, deprecation of legacy main.py.
**Uses:** structlog (new), psycopg (existing), asyncio (stdlib)
**Addresses:** End-to-end pipeline execution (P1 table stake)
**Avoids:** Pitfall 5 (yfinance rate limiting -- retry + caching), Pitfall 9 (fallback prices -- fail explicitly), Pitfall 14 (wrong entrypoint -- new runner.py), Pitfall 15 (sleep blocking -- documented for future fix)

### Phase 4: Replay CLI + Observability Commands

**Rationale:** Read-only consumer of data from phases 2-3. Building last means real cycle data exists to test against. Merit and drift time series can be built in parallel since they read existing MEMORY.md data.
**Delivers:** swarm-replay CLI (list, show, diff, timeline), merit history command, drift history command, debate tension score computation. All using typer + rich.
**Uses:** typer (promoted), rich (promoted)
**Implements:** swarm-replay CLI component
**Avoids:** Pitfall 7 (event loop -- asyncio.run() only at CLI entry point, async internals), Pitfall 13 (schema dependency -- CycleSnapshot schema defined in Phase 2)

### Phase Ordering Rationale

- **Personas before infrastructure:** Content authoring has zero code risk and unblocks meaningful output from every subsequent phase. Running the pipeline with skeleton agents produces uninteresting data.
- **Persistence before runner:** The CycleSnapshot schema is the data contract. Defining it first prevents the runner and CLI from making incompatible format assumptions (Pitfall 13).
- **Runner before CLI:** The replay tool needs real data to test against. Without completed cycles in cycle_snapshots, the CLI is untestable.
- **Hardening bundled with runner:** Retry logic, structured logging, and fallback price elimination are prerequisites for producing trustworthy observable output, not afterthoughts.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Persona Population):** Needs research into effective HEXACO-to-prose translation patterns. Risk of persona collapse under Gemini Flash (Pitfall 6) requires iterative testing. The drift_guard YAML schema per persona needs careful design.
- **Phase 3 (Pipeline Runner):** Data fetcher retry strategy and caching layer design need implementation research. structlog configuration with existing logging infrastructure needs verification.

Phases with standard patterns (skip research-phase):
- **Phase 2 (Cycle Persistence):** Well-documented patterns. Pydantic model + PostgreSQL JSONB + post-invocation extraction is straightforward. Architecture research provides complete schema and code patterns.
- **Phase 4 (Replay CLI):** Standard typer + rich CLI patterns. Read-only PostgreSQL queries. No novel design decisions.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Minimal additions. Two deps already installed, one new. All verified against pyproject.toml and uv pip list. |
| Features | HIGH | Feature landscape well-mapped. Clear P1/P2/P3 prioritization. Dependency chain validated against codebase. |
| Architecture | HIGH | All patterns grounded in existing codebase analysis. Integration points identified with line-level specificity. |
| Pitfalls | HIGH | 15 pitfalls identified, all verified against specific source files. Critical pitfalls have concrete prevention strategies. |

**Overall confidence:** HIGH

### Gaps to Address

- **Gemini Flash persona fidelity:** No empirical data on whether Gemini Flash maintains HEXACO-diverse personas across multi-turn interactions. Pitfall 6 is based on general LLM research, not Gemini-specific testing. Validate during Phase 1 with comparative output analysis.
- **yfinance reliability for beta:** Rate limiting is well-documented but the exact threshold for "rapid development" is unknown. The data caching layer in Phase 3 is the mitigation, but cache invalidation strategy needs definition.
- **KAMI Accuracy dimension frozen at 0.5:** 30% of merit score is permanently inert (Pitfall 11). Decision needed: reduce Accuracy weight to 0.0 for beta, or implement thesis_records. This is a product decision, not a research gap.
- **PostgreSQL connection pool race (Pitfall 12):** Pool open pattern is scattered across 10+ call sites. Low severity (psycopg3 pool open is idempotent) but should be consolidated during Phase 3 runner work.

---

## Sources

### Primary (HIGH confidence)
- Project codebase (v1.3, ~30,600 LOC) -- orchestrator, state, persistence, soul_loader, audit_logger, memory_writer, drift_eval, order_router, decision_card, kami
- [HEXACO-PI-R Official Scale Descriptions](https://hexaco.org/scaledescriptions)
- [LangGraph Persistence Documentation](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Time Travel Documentation](https://docs.langchain.com/oss/python/langgraph/use-time-travel)
- pyproject.toml + uv pip list (verified dependency set)
- [Rich PyPI](https://pypi.org/project/rich/), [Typer PyPI](https://pypi.org/project/typer/)

### Secondary (MEDIUM confidence)
- [LangGraph Issue #2943: operator.add field clearing](https://github.com/langchain-ai/langgraph/issues/2943)
- [Applying Psychometrics to LLM Simulated Populations (arxiv:2508.00742)](https://arxiv.org/html/2508.00742v1)
- [Turing Institute: Patterns Not People](https://cetas.turing.ac.uk/publications/patterns-not-people-personality-structures-llm-powered-persona-agents)
- [yfinance Rate Limiting Issues #2422, #2431](https://github.com/ranaroussi/yfinance/issues/2422)
- [LangGraph Checkpointing Best Practices 2025](https://sparkco.ai/blog/mastering-langgraph-checkpointing-best-practices-for-2025)
- [Observability for AI Agents](https://www.getmaxim.ai/articles/observability-for-ai-agents-langgraph-openai-agents-and-crew-ai/)
- [Psychologically Enhanced AI Agents (2025)](https://www.emergentmind.com/papers/2509.04343)
- [Nature: Psychometric framework for LLM personality traits](https://www.nature.com/articles/s42256-025-01115-6)

### Tertiary (LOW confidence)
- [TradingAgents Framework](https://github.com/TauricResearch/TradingAgents) -- multi-agent LLM trading reference, not deeply analyzed
- [Best LLM Observability Tools 2026](https://awesomeagents.ai/tools/best-llm-observability-tools-2026/)

---
*Research completed: 2026-03-08*
*Ready for roadmap: yes*
