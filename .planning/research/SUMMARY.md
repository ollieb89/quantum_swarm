# Project Research Summary

**Project:** Quantum Swarm v1.5 -- Reliable Infrastructure
**Domain:** Multi-agent LLM financial analysis swarm (reliability, observability, evaluation)
**Researched:** 2026-03-09
**Confidence:** HIGH

## Executive Summary

Quantum Swarm v1.5 is an infrastructure stabilization milestone for an existing 33,949 LOC, 300+ test LangGraph-based multi-agent financial analysis swarm. The research confirms that every v1.5 feature can be built with zero new dependencies -- the existing stack (Python 3.12, LangGraph 1.0.10, Gemini 2.5 Flash, PostgreSQL 17, ChromaDB 1.5.2, Pydantic 2.12.5) provides all necessary capabilities. The marquee feature is PersonaScore 5D LLM-as-Judge, which replaces the currently inert binary fidelity signal in KAMI with a continuous 5-dimension persona evaluation. This is supported by a stdlib circuit breaker for Gemini API resilience, per-cycle token cost tracking via existing BudgetManager, ChromaDB prune-to-Obsidian lifecycle management, and KAMI weight rebalancing.

The recommended approach is to fix broken dependencies first (ccxt, chromadb test isolation, pytest-asyncio), then build the circuit breaker as a safety net before adding more LLM calls, then implement PersonaScore and wire it into KAMI fidelity before rebalancing weights. Token tracking and ChromaDB pruning are independent workstreams that slot in around the critical path. The most important architectural decision is that PersonaScore should merge INTO the existing fidelity dimension (delta) rather than adding a 5th KAMI dimension -- this avoids cascading changes across kami.py, merit_updater, merit_loader, KAMIDimensions dataclass, all tests, and config. PersonaScore evaluation must run as a CycleRunner post-cycle hook, not as a graph node, to avoid circular evaluation, budget contamination, and audit hash chain corruption.

The primary risks are: (1) PersonaScore creating circular evaluation if placed inside the graph, (2) KAMI weight rebalancing breaking score continuity if shipped before PersonaScore provides a continuous fidelity signal, and (3) circuit breaker becoming a sticky boolean that prevents recovery without restart (mirroring the existing `_db_unavailable` anti-pattern in db.py). All three have clear prevention strategies. A notable conflict exists between research files: ARCHITECTURE.md recommends PersonaScore as a graph node while PITFALLS.md warns against this. The PITFALLS analysis is more thorough on this point and should be followed -- post-cycle hook is the safer placement.

## Key Findings

### Recommended Stack

Zero new dependencies. Every feature builds on existing installed packages, consistent with the project's stdlib-first philosophy. The circuit breaker is ~60 lines of stdlib code (threading, time, enum). PersonaScore uses `ChatGoogleGenerativeAI.with_structured_output()` plus Pydantic. Token tracking extends the existing BudgetManager. ChromaDB pruning uses native collection.get/delete APIs.

**Core technologies (all already installed):**
- **Pydantic 2.12.5 + Gemini structured output:** PersonaScore 5D schema with `with_structured_output()` -- eliminates need for openevals/deepeval packages
- **BudgetManager + AIMessage.usage_metadata:** Token cost tracking per cycle -- eliminates need for Langfuse/LangSmith/LiteLLM
- **Python stdlib (threading, time, enum):** Circuit breaker 3-state machine -- eliminates need for pybreaker/aiobreaker/circuitbreaker packages
- **ChromaDB 1.5.2 native API:** Metadata-filtered delete + get for pruning -- eliminates need for chromadb-ops CLI

**Critical version note:** ccxt 4.5.41 is BROKEN (ModuleNotFoundError for lighter_client). Fix requires force-reinstall or version pin to pre-Lighter release (~4.4.x).

### Expected Features

**Must have (table stakes):**
- Token cost tracking per cycle -- BudgetManager already has the data, just needs persistence to CycleSnapshot
- Dependency restoration (ccxt, chromadb test isolation, pytest-asyncio) -- 13 broken tests erode CI trust
- Circuit breaker for Gemini API -- no failure-state management currently; 429/503 cascades burn budget
- KAMI weight rebalancing -- 30% of merit score is inert (Accuracy frozen at 0.5)

**Should have (differentiators):**
- PersonaScore 5D LLM-as-Judge -- no comparable open-source multi-agent system does per-cycle persona fidelity evaluation
- Prune-to-Obsidian ChromaDB lifecycle -- most vector DB deployments grow unbounded; archive creates searchable history

**Defer (v2+):**
- Multi-model fallback chains -- breaks soul fidelity assumptions; wrong for this architecture
- Automated KAMI weight optimization -- premature without 100+ cycles of PersonaScore data
- Real-time cost dashboard -- CLI replay queries are sufficient until WebSocket dashboard milestone
- Sentence-transformers for PersonaScore embeddings -- heavyweight torch dependency for marginal gain
- LLM-as-Judge for ARS drift detection -- creates circular evaluation; keep stdlib-only ARS metrics

### Architecture Approach

The existing LangGraph StateGraph topology is preserved with minimal modification. PersonaScore evaluation runs as a post-cycle hook in CycleRunner (not as a graph node) to avoid circular evaluation, budget contamination, and audit hash chain corruption. Token tracking uses BudgetManager as the single authoritative source with summary captured in CycleSnapshot after graph execution completes. The circuit breaker wraps LLM invocations via enhancement to the existing `with_audit_logging` wrapper in orchestrator.py, providing a single integration point with shared circuit state across all nodes. ChromaDB pruning is a CLI-only operation, never a graph node.

**Major components:**
1. **PersonaScore5D evaluator** (`src/core/persona_scorer.py`) -- pure core function, accepts plain dict args (not SwarmState), returns Pydantic-validated scores per agent. Called by CycleRunner post-hook for ALL agents that produced output
2. **GeminiCircuitBreaker** (`src/core/circuit_breaker.py`) -- stdlib 3-state machine (closed/open/half-open) with time-based recovery, thread-safe singleton. Integrated into `with_audit_logging` wrapper. Only wraps L2 analysis nodes, not compliance-critical paths
3. **Token cost extension** -- extend BudgetManager with per-agent counters and `category` parameter. Capture summary in CycleSnapshot before session reset. No LangChain callback handler needed (avoids known GoogleGenAI callback gap)
4. **ChromaPruner** (`src/core/chroma_pruner.py`) -- prune-to-Obsidian workflow via MemoryService API, triggered by CLI subcommand only. Archive-before-delete with rule-aware cutoff dates
5. **KAMI weight reconfig** -- merge PersonaScore INTO fidelity (delta=0.32), minimize frozen Accuracy (alpha=0.08). No 5th dimension

**Key architectural decisions resolved:**
- **Merge vs add dimension:** PersonaScore IS fidelity at higher resolution. Merge into delta, do not add epsilon. Dramatically simpler.
- **Graph node vs post-cycle hook:** Post-cycle hook in CycleRunner. Avoids 5 pitfalls simultaneously (circular eval, budget contamination, audit corruption, asyncio.run crash, single-agent limitation).
- **Callback vs BudgetManager for tokens:** BudgetManager only. Avoids double-counting (Pitfall #4) and ChatGoogleGenerativeAI callback gaps (GitHub #927).
- **pybreaker vs stdlib:** Stdlib. Zero new dependencies for a reliability milestone. ~60 LOC.
- **Lagged signal pattern:** PersonaScore from cycle N feeds fidelity in cycle N+1, same pattern as existing Accuracy dimension. Eliminates circular dependency.

### Critical Pitfalls

1. **PersonaScore circular evaluation inside graph** -- If run as a graph node, judge tokens contaminate BudgetManager session ceiling (premature SafetyShutdown at ~50% actual budget), judge output enters audit hash chain, and judge failure triggers `return {}` that skips ALL merit updates. **Prevention:** CycleRunner post-cycle hook with separate budget category and try/except fallback to previous score.

2. **KAMI weight rebalancing without continuous fidelity signal** -- Increasing fidelity weight from 0.10 to 0.32 while `_extract_fidelity_signal()` still returns binary 0/1 makes 32% of merit a meaningless constant (worse than the frozen Accuracy it replaces). **Prevention:** Wire PersonaScore into fidelity BEFORE changing weights. Never ship weight change without PersonaScore.

3. **Circuit breaker sticky open state** -- Module-level singleton retains "open" state across CycleRunner invocations, mirroring the `_db_unavailable` anti-pattern in db.py. **Prevention:** Time-based half-open recovery with probe timer, not boolean flag. Log state transitions to structlog and audit.jsonl.

4. **Token cost double-counting via operator.add reducer** -- SwarmState `total_tokens` uses `Annotated[int, operator.add]` which permanently accumulates. If both BudgetManager.record_usage() and a callback report the same tokens, counts inflate 2x and trigger premature SafetyShutdown. **Prevention:** BudgetManager as single authoritative source. Store cost in CycleSnapshot, not SwarmState.

5. **ChromaDB pruning orphans active memory rules** -- No foreign key between MemoryRegistry rules and ChromaDB document IDs. Age-based pruning can delete vectors that inform active PREFER/AVOID rules, breaking MiFID II evidence trail. **Prevention:** Rule-aware cutoff dates, archive-before-delete with verification, pruning manifest in `data/pruning/`.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 27: Environment Stabilization + Dependency Fixes
**Rationale:** Unblocks all testing; 13 broken tests undermine CI trust. Must come first because ChromaDB pruning requires working chromadb, and all features need green tests to validate against.
**Delivers:** Green CI, restored ccxt/chromadb/pytest-asyncio, version pins in pyproject.toml
**Addresses:** ENV-01 (dependency restoration)
**Avoids:** Pitfall #11 (ChromaDB version mismatch breaks MemoryService API)

### Phase 28: Gemini API Circuit Breaker
**Rationale:** Safety net must exist before adding more LLM calls (PersonaScore adds 5 per cycle). Independent of other features, clean stdlib implementation. Establishes the `with_audit_logging` enhancement pattern.
**Delivers:** `src/core/circuit_breaker.py`, enhanced `with_audit_logging`, soft-fail pause behavior, failure type classification (429 vs 5xx vs auth), structlog state transitions
**Addresses:** SEC-03 (circuit breaker)
**Avoids:** Pitfall #5 (sticky open state), Pitfall #9 (compliance path blocking), Pitfall #15 (failure type conflation)

### Phase 29: PersonaScore 5D LLM-as-Judge + KAMI Fidelity Wiring
**Rationale:** The marquee differentiator. Must ship WITH KAMI fidelity wiring as a single unit -- Pitfall #16 makes them inseparable. PersonaScore replaces binary fidelity signal with continuous gradient data, justifying subsequent weight rebalancing.
**Delivers:** `src/core/persona_scorer.py`, CycleRunner post-cycle evaluation hook, 5D rubric (Consistency, Tone, Logic, Depth, Bias) with anchored examples, PersonaScore persistence to DB, `_extract_fidelity_signal()` updated to read PersonaScore composite, evaluation of ALL agents per cycle
**Addresses:** SOUL-09 (PersonaScore 5D), partial KAMI-05 (fidelity signal wiring)
**Avoids:** Pitfall #1 (circular evaluation), Pitfall #3 (asyncio.run crash), Pitfall #7 (Import Layer Law), Pitfall #8 (non-deterministic scores), Pitfall #13 (single-agent evaluation)

### Phase 30: KAMI Weight Rebalancing + Token Cost Tracking
**Rationale:** Weight rebalancing is safe only after PersonaScore provides continuous fidelity data (Phase 29). Token tracking is independent but low-complexity and groups well with this config-focused phase.
**Delivers:** Updated DEFAULT_WEIGHTS (alpha=0.08, beta=0.35, gamma=0.25, delta=0.32), weight epoch tagging in DB, extended BudgetManager with per-agent counters and category parameter, cost field in CycleSnapshot, cost display in replay CLI
**Addresses:** KAMI-05 (weight rebalancing), OBS-02 (token cost tracking)
**Avoids:** Pitfall #2 (score discontinuity), Pitfall #4 (double-counting), Pitfall #16 (binary fidelity -- resolved by Phase 29)

### Phase 31: ChromaDB Prune-to-Obsidian
**Rationale:** Least urgent, most self-contained. Requires stable MemoryService (Phase 27 fixes). Destructive operation benefits from all safety infrastructure being in place first.
**Delivers:** `src/core/chroma_pruner.py`, CLI `prune` subcommand with --dry-run, Obsidian markdown export with YAML frontmatter, configurable age/source thresholds, rule-aware cutoff dates, pruning manifest, re-import script
**Addresses:** OBS-03 (ChromaDB lifecycle management)
**Avoids:** Pitfall #6 (orphaned active rules), Pitfall #12 (non-parseable archive)

### Phase Ordering Rationale

- **Dependencies first (Phase 27):** Every subsequent phase needs green tests to validate. ChromaDB pruning cannot be built without working chromadb.
- **Circuit breaker before PersonaScore (Phase 28 before 29):** PersonaScore adds 5 LLM calls per cycle; the safety net must exist first. Also the simplest feature (~60 LOC stdlib), establishing patterns for later phases.
- **PersonaScore + fidelity wiring as atomic unit (Phase 29):** Research unanimously identifies shipping weight changes without continuous fidelity data as the most dangerous pitfall. These must be a single phase.
- **Weight rebalancing after PersonaScore (Phase 30):** Hard dependency on Phase 29. Grouped with token tracking because both are config/schema extensions with low implementation risk.
- **ChromaDB pruning last (Phase 31):** Fully independent, least urgent. Can be deferred to v1.6 if timeline is tight without impacting other features.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 29 (PersonaScore):** Judge prompt rubric design with anchored examples needs careful iteration. Non-deterministic scoring requires calibration testing. Post-cycle hook integration with CycleRunner needs exact hook point design. merit_updater single-agent limitation (Pitfall #13) may need fixing in this phase.

Phases with standard patterns (skip research-phase):
- **Phase 27 (Dependency fixes):** Package version pinning and diagnosis. No architectural decisions.
- **Phase 28 (Circuit breaker):** Well-documented 3-state pattern. Implementation sketch complete in STACK.md. Integration point identified.
- **Phase 30 (KAMI weights + token tracking):** Config changes plus BudgetManager extension. Existing patterns fully cover this.
- **Phase 31 (ChromaDB pruning):** ChromaDB API is stable. MemoryService already provides the needed interface.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies already installed and verified via `uv pip list`. Zero new dependencies. |
| Features | HIGH | Feature landscape well-mapped. Dependencies between features clearly identified. Anti-features have explicit rejection rationale. |
| Architecture | HIGH | Based on direct codebase analysis with specific file/line references. Integration points verified. Import Layer Law compliance checked. |
| Pitfalls | HIGH | 16 pitfalls identified with concrete codebase references. Integration risk matrix maps every new feature to every existing system at risk. |

**Overall confidence:** HIGH

### Gaps to Address

- **ccxt fix strategy:** The lighter_client ModuleNotFoundError is not widely documented. May need version bisection. Confidence MEDIUM on first-try fix.
- **PersonaScore judge prompt calibration:** No existing calibration data. The 5D rubric with anchored examples needs iterative refinement against real agent outputs. Plan for 2-3 prompt iterations.
- **ChatGoogleGenerativeAI callback behavior:** Known GitHub issue #927 where usage_metadata may not flow through callbacks. Recommendation is to avoid callbacks entirely and use BudgetManager direct recording, but validate if callback approach is attempted.
- **merit_updater single-agent limitation:** Currently updates only the last agent's merit per cycle. PersonaScore evaluates all agents, but merit_updater may need fixing too. Scope during Phase 29 planning.
- **KAMI weight transition strategy:** Changing weights mid-lifecycle causes one-time shift in all composites. Decide whether to reset scores to cold-start (0.5) at weight boundary or let EMA absorb. Document as decision record.
- **Research file conflicts resolved:** FEATURES.md recommends pybreaker (rejected -- stdlib per STACK.md). ARCHITECTURE.md places PersonaScore as graph node (rejected -- post-cycle hook per PITFALLS.md analysis). These resolutions should be treated as binding for roadmap planning.

## Sources

### Primary (HIGH confidence)
- Existing codebase: orchestrator.py, kami.py, cycle_runner.py, budget_manager.py, audit_logger.py, state.py, merit_updater.py, analysts.py, researchers.py, memory/service.py, db.py, persistence.py
- [ChatGoogleGenerativeAI reference](https://reference.langchain.com/python/integrations/langchain_google_genai/ChatGoogleGenerativeAI/) -- structured output, usage_metadata
- [LangChain UsageMetadata API](https://python.langchain.com/api_reference/core/messages/langchain_core.messages.ai.UsageMetadata.html) -- token tracking
- [ChromaDB delete data docs](https://docs.trychroma.com/docs/collections/delete-data) -- pruning API
- Import Layer Law enforcement: `tests/core/test_import_boundaries.py`

### Secondary (MEDIUM confidence)
- [Langfuse: LLM-as-a-Judge Guide](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge) -- pointwise scoring best practices
- [Evidently AI: LLM-as-a-Judge Guide](https://www.evidentlyai.com/llm-guide/llm-as-a-judge) -- rubric design
- [arXiv 2411.15594: Survey on LLM-as-a-Judge](https://arxiv.org/abs/2411.15594) -- CoT elicitation, few-shot calibration
- [ChromaDB Cookbook: Maintenance](https://cookbook.chromadb.dev/running/maintenance/) -- WAL pruning, auto-compaction
- [ChatGoogleGenerativeAI usage_metadata issue #927](https://github.com/langchain-ai/langchain-google/issues/927) -- callback gap
- [ccxt static_dependencies issue #23307](https://github.com/ccxt/ccxt/issues/23307) -- analogous packaging bug
- [Portkey: Circuit Breakers in LLM Apps](https://portkey.ai/blog/retries-fallbacks-and-circuit-breakers-in-llm-apps/) -- pattern reference

### Tertiary (LOW confidence)
- ccxt lighter_client fix strategy -- not widely documented, may require version bisection

---
*Research completed: 2026-03-09*
*Ready for roadmap: yes*
