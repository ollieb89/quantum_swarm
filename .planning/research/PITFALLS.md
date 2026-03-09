# Domain Pitfalls

**Domain:** Adding LLM-as-Judge evaluation, token tracking, circuit breakers, KAMI rebalancing, and vector DB pruning to an existing LangGraph multi-agent financial analysis swarm
**Project:** Quantum Swarm v1.5 Reliable Infrastructure
**Researched:** 2026-03-09
**Confidence:** HIGH (derived from direct codebase analysis against known project constraints, cross-referenced with v1.4 shipped architecture)

> **Scope:** These pitfalls are specific to adding v1.5 features to THIS existing system -- a 300+ test, ~33,949 LOC LangGraph swarm with hash-chained MiFID II audit trail, PostgreSQL async persistence, synchronous file I/O constraints, lru_cache soul loading, KAMI merit scoring, CycleRunner-based persistence, and 5 fully authored HEXACO-6 personas. Generic pitfalls excluded unless they have concrete integration consequences here.

---

## Critical Pitfalls

Mistakes that cause rewrites, audit trail corruption, or production outages.

### Pitfall 1: PersonaScore LLM-as-Judge Creates Circular Evaluation Inside Graph

**What goes wrong:** The PersonaScore 5D evaluation calls the Gemini API to judge agent persona fidelity. If this evaluation runs as a LangGraph node during the main graph execution, it doubles API costs, inflates token counts tracked by BudgetManager, and creates a circular dependency: the LLM judges its own output within the same execution context. Worse, if the evaluation LLM call fails (rate limit, timeout), it could crash the entire graph run -- a persona fidelity check should never block trade execution.

**Why it happens:** Natural instinct is to add PersonaScore as a node after `merit_updater` in the existing graph chain. The graph already has `with_audit_logging` wrappers on every node, and the `merit_updater_node` already computes fidelity signals. Adding "just one more LLM call" seems trivial.

**Consequences:**
- BudgetManager `session_usd` includes judge costs, corrupting budget tracking for actual analysis work
- SafetyShutdown triggers prematurely because judge tokens count toward session ceiling (default: 100,000 tokens, $5.00 USD)
- If judge call fails, `merit_updater` returns `{}` (the established error pattern at line 126 of merit_updater.py), silently skipping ALL merit updates -- not just fidelity
- Hash-chained audit trail now includes judge LLM response content in `output_data`, permanently embedding evaluation artifacts in the MiFID II audit chain via `with_audit_logging`
- The `AUDIT_EXCLUDED_FIELDS` frozenset would need extension, but adding evaluation data there means it becomes invisible to compliance verification

**Prevention:**
- Run PersonaScore evaluation as a **post-cycle hook** in `CycleRunner`, not as a graph node. CycleRunner already sits outside the graph (Import Layer Law compliant) and has access to the final state after `run_cycle()` completes
- Use a separate BudgetManager instance (or a tagged cost category) for judge calls so they do not count toward session ceilings
- Store PersonaScore results in a dedicated table (e.g., `persona_scores`) keyed by `(cycle_id, soul_handle)`, then read them back in `merit_updater_node` on the *next* cycle via `merit_loader`
- Never let judge failure propagate -- wrap in try/except with fallback to previous fidelity score

**Detection:** Judge token costs appearing in `BudgetManager.summary()["session_input_tokens"]`. PersonaScore evaluation latency showing up in `node_exit` structured logs for merit_updater. Sudden doubling of per-cycle API costs.

---

### Pitfall 2: KAMI Weight Rebalancing Breaks Existing Merit Score Continuity

**What goes wrong:** Changing weights from `{alpha: 0.30, beta: 0.35, gamma: 0.25, delta: 0.10}` to (e.g.) `{alpha: 0.05, beta: 0.35, gamma: 0.25, delta: 0.35}` causes a discontinuous jump in all agents' composite scores. Since Accuracy is frozen at 0.5 and was weighted at 0.30 (contributing 0.15 to every composite), reducing alpha to 0.05 removes 0.125 from every agent's score while adding `(new_delta - 0.10) * fidelity` worth of fidelity weight. The `compute_merit()` formula in `kami.py` is applied immediately to existing dimension values with no transition.

**Why it happens:** The weights are read from `config/swarm_config.yaml` at runtime via `_get_weights()` in `merit_updater.py` (line 41-47). There is no migration path -- the next cycle simply applies the new formula to old dimension values. The `DebateSynthesizer` uses these composite scores for consensus weighting, meaning one config change silently reshuffles which agents dominate debate.

**Consequences:**
- Agent debate influence shifts overnight with no corresponding change in agent behavior
- If fidelity jumps from 0.10 to 0.35 weight and current fidelity is 1.0 (all 5 agents have non-empty IDENTITY.md per v1.4 completion), every agent gains +0.25 composite -- but this is meaningless earned merit, just a binary "has IDENTITY.md" check via `_extract_fidelity_signal()`
- Historical KAMI scores in `agent_merit_scores` table become incomparable across the weight change boundary
- ARS drift auditor's `_compute_kami_dimension_variance()` metric (line 180-188 of ars_auditor.py) may trigger false breach alerts because the composite/dimension relationship changes

**Prevention:**
- Add a `kami_version` or `weight_epoch` field to the `agent_merit_scores` table and `cycle_snapshots` to mark which weight regime produced each score
- Apply weight changes with a **transition window**: run 5-10 cycles with blended weights before switching fully. OR reset all composite scores to DEFAULT_MERIT (0.5) at the weight change boundary and document it as a known discontinuity
- CRITICAL: Update `_extract_fidelity_signal()` to use the new PersonaScore 5D output instead of the binary "has IDENTITY.md" check -- otherwise fidelity at 0.35 weight is still just a 0/1 signal (either 0.0 or 1.0), which is worse than the frozen Accuracy problem it replaces. A 0/1 signal at 35% weight means 35% of merit is either 0 or 0.35 with no gradient
- Wire PersonaScore dimensions into fidelity BEFORE changing weights, so the increased weight has meaningful data to amplify
- Add a one-time migration script that recalculates all composites from stored dimensions with new weights

**Detection:** Sudden composite score jumps in `agent_merit_scores` table. ARS KAMI variance metric breaching threshold (`kami_variance_threshold: 0.04` default). Debate synthesis `weighted_consensus_score` shifting without analyst behavior change.

---

### Pitfall 3: asyncio.run() in PersonaScore Judge Call Inside LangGraph

**What goes wrong:** This is a known project-breaking pattern (documented in PROJECT.md as "asyncio.run() inside nodes is project-breaking (MEM-06 defect)"). If PersonaScore evaluation uses `asyncio.run()` to call the Gemini API, it will crash with `RuntimeError: cannot be called from a running event loop` because LangGraph nodes execute within an existing asyncio event loop via `ainvoke()`.

**Why it happens:** The PersonaScore judge needs to call `ChatGoogleGenerativeAI.ainvoke()`. A developer might write it as a sync function with `asyncio.run()` for simplicity, especially if following the pattern in `_extract_fidelity_signal()` (kami.py line 220-241) which is currently sync and does only file I/O. The leap from "fidelity signal is sync file read" to "fidelity signal is sync LLM call via asyncio.run()" is the exact trap.

**Consequences:** Hard crash of the entire graph run. No graceful degradation. CycleSnapshot records `status='failed'` with an asyncio RuntimeError.

**Prevention:**
- If PersonaScore runs inside the graph: make it an `async` function and use `await` directly
- If PersonaScore runs in CycleRunner post-cycle hook (recommended): CycleRunner.run_cycle() is already async, so `await` works naturally
- Apply the same lazy-init pattern used for all LLM instances: `_judge_llm = None; def _get_judge_llm(): ...` to avoid import-time API key validation (the `ChatGoogleGenerativeAI validates API key at instantiation` constraint from MEMORY.md)
- The existing `with_audit_logging` wrapper already handles both sync and async node functions via `asyncio.iscoroutinefunction()` check (orchestrator.py line 200), but the PersonaScore evaluator itself MUST be async if it makes API calls

**Detection:** `RuntimeError: This event loop is already running` in structured logs during merit_updater or post-cycle evaluation.

---

### Pitfall 4: Token Cost Tracking Double-Counting via Reducer Accumulation

**What goes wrong:** The existing `BudgetManager` tracks token usage when explicitly called via `record_usage()`. The `total_tokens` field in SwarmState uses `Annotated[int, operator.add]` reducer -- meaning any value returned by a node is PERMANENTLY added to the running total within the graph run. If token tracking is added by intercepting LangChain callback metadata AND nodes also return `{"total_tokens": N}`, the same tokens are counted twice. The reducer makes this uncorrectable.

**Why it happens:** LangChain/LangGraph provides callback hooks (`on_llm_end`) that report token usage. The natural approach is to add a global callback that feeds BudgetManager. But nodes like `MacroAnalyst` and `QuantModeler` already call tools via `BudgetedTool` which has its own cost tracking. Adding a global callback creates overlap. Furthermore, any node returning a dict with `total_tokens` key triggers the `operator.add` reducer to accumulate it.

**Consequences:**
- `session_usd` reports 1.5-2x actual cost
- SafetyShutdown triggers at 50-65% of actual budget (default: $5.00/day, 100K tokens/session)
- Per-cycle cost reports are unreliable for budgeting decisions
- The `operator.add` reducer is append-only -- once tokens are added, they cannot be subtracted within a graph run. A bug that reports 100,000 tokens instead of 1,000 triggers permanent SafetyShutdown

**Prevention:**
- Choose ONE authoritative token tracking path: either BudgetManager.record_usage() calls from within nodes, OR a LangChain callback handler -- never both
- Store per-cycle token costs in `CycleSnapshot` metadata (via CycleRunner, which already captures final state) rather than in SwarmState
- Use BudgetManager.summary() as the single source of truth. Do NOT return `{"total_tokens": N}` from nodes -- let BudgetManager track internally
- Track judge/evaluation tokens separately from analysis tokens in BudgetManager (add a `category` parameter to `record_usage()`)
- Consider adding a new non-reducer field `cycle_cost_breakdown: Optional[dict]` to SwarmState (plain dict, no `operator.add`) for per-cycle cost snapshots

**Detection:** `BudgetManager.summary()["total_tokens"]` exceeding theoretical maximum for model context window. Per-cycle costs being 2x expected. `total_tokens` in state growing faster than `BudgetManager.total_tokens`.

---

### Pitfall 5: Circuit Breaker Sticky State Prevents Recovery Without Restart

**What goes wrong:** A Gemini API circuit breaker implemented as a module-level singleton retains its "open" state across multiple `CycleRunner.run_cycle()` invocations. If the breaker opens during cycle N due to a transient Gemini outage, it stays open for cycles N+1, N+2, etc., even after the API recovers. The existing `_db_unavailable` sticky flag in `db.py` (line 21) demonstrates this exact pattern -- once PostgreSQL is marked unavailable, the module permanently returns None until process restart.

**Why it happens:** Python module-level state persists for the lifetime of the process. The `BudgetManager` handles this correctly by having `reset_session()` called between cycles. But a circuit breaker has no equivalent reset mechanism because its purpose is to *persist* failure state. The `db.py` pattern of `_db_unavailable = True` with no time-based recovery is the anti-pattern to avoid.

**Consequences:**
- Swarm permanently stops making LLM calls after a transient outage until process restart
- In a daemon/systemd deployment (like the ARS auditor cron), this means hours or days of no trading signals
- If the breaker is checked in `classify_intent` (the first LLM-calling node), the graph silently routes to END without any analysis
- No audit trail entry explains why cycles produce no output -- the breaker swallows errors silently

**Prevention:**
- Implement circuit breaker with a **time-based half-open state**: after N seconds (e.g., 120), allow one probe request. If it succeeds, close the breaker. If it fails, reset the timer
- Store breaker state with timestamps, not boolean flags: `_last_failure_time: Optional[float]`, `_failure_count: int`, `_state: Literal["closed", "open", "half_open"]`
- Log circuit breaker state transitions to audit.jsonl (same pattern as ARS breach events in ars_auditor.py line 596)
- The `soft-fail pause` requirement in PROJECT.md suggests the correct pattern: return a degraded result (e.g., cached previous analysis or a HOLD decision with reason="API_UNAVAILABLE") rather than raising SafetyShutdown
- Add breaker status to `CycleSnapshot` metadata so replay CLI shows when cycles ran in degraded mode
- Reset the breaker probe timer between cycles (like `budget.reset_session()`) -- do NOT reset the failure count, just allow probing

**Detection:** Multiple consecutive cycles with `status='failed'` or no `execution_result`. Structured logs showing no `node_enter` events for LLM-calling nodes. CycleSnapshot metadata missing analyst outputs.

---

### Pitfall 6: ChromaDB Pruning Deletes Vectors Referenced by Active Memory Rules

**What goes wrong:** The ChromaDB pruning workflow ("Prune-to-Obsidian") archives old vectors to Obsidian markdown and then deletes them from ChromaDB. But the `MemoryService` stores trade outcomes, research context, and external data that may be referenced by active rules in `MemoryRegistry` (`data/memory_registry.json`). If a pruning cutoff (e.g., "older than 90 days") deletes vectors that an active PREFER/AVOID/CAUTION rule was generated from, the rule's source context becomes unverifiable.

**Why it happens:** The pruning logic operates on ChromaDB metadata timestamps. The MemoryRegistry rules reference source data implicitly -- they were generated by RuleGenerator from patterns discovered in vector memory. There is no explicit foreign key between a rule in `memory_registry.json` and the ChromaDB document IDs that informed it. The `MemoryService` has `MemorySource` enum types (TRADE, RESEARCH, EXTERNAL_DATA) but no rule-linkage metadata.

**Consequences:**
- `RuleValidator` backtesting cannot re-validate pruned rules because source data is gone
- Rules remain active but become "orphaned" -- they assert patterns that can no longer be verified
- If an auditor (human or ARS) asks "why does this rule exist?", the evidence trail is broken
- MiFID II audit provenance is weakened -- trade decisions influenced by rules whose backing data has been deleted
- The `CalibrationReport` in `evaluation/calibration.py` depends on `trades` table data (PostgreSQL), not ChromaDB -- but vector memory provides the contextual evidence for rule justification

**Prevention:**
- Before pruning, scan `memory_registry.json` for all active rules and extract their creation timestamps. Set the pruning cutoff to MAX(oldest_active_rule.created_at, configured_retention_period)
- OR: tag ChromaDB documents that inform active rules with a `rule_referenced=true` metadata flag and exclude them from pruning
- Archive to Obsidian FIRST (write markdown files with YAML frontmatter), verify the archive write succeeded, THEN delete from ChromaDB. Never delete-then-archive
- Add a `pruning_manifest.json` per pruning run recording exactly which document IDs were archived vs retained, stored in `data/pruning/`
- Store the rule's source document_ids in `memory_registry.json` rule entries at generation time (requires RuleGenerator change)

**Detection:** Active rules in `memory_registry.json` whose creation date predates the last pruning cutoff. `MemoryService.search()` returning zero results for queries that previously had hits.

---

## Moderate Pitfalls

### Pitfall 7: Import Layer Law Violation in PersonaScore Module

**What goes wrong:** PersonaScore evaluation needs access to agent output (thesis text, debate contributions) to judge persona fidelity. The natural place for this data is in SwarmState fields like `bullish_thesis`, `bearish_thesis`, `macro_report`. A developer places the PersonaScore evaluator in `src/core/` (alongside `kami.py`) but imports SwarmState type hints from `src/graph/state.py`, violating the Import Layer Law.

**Why it happens:** The existing `_extract_fidelity_signal()` in `kami.py` accepts a plain `str` (agent_id) and calls `load_soul()` -- all within core. The temptation is to expand this function to also accept state data, which requires knowing about SwarmState fields.

**Prevention:**
- PersonaScore evaluator in `src/core/` must accept plain `dict` arguments (agent outputs as strings, not typed SwarmState fields), never import from `src/graph/`
- The adapter that maps SwarmState fields to evaluator inputs belongs in `src/graph/nodes/` or in `CycleRunner`
- Add the new module to `TestCoreLeafImports` in `tests/core/test_import_boundaries.py` immediately upon creation
- Follow the `kami.py` pattern: pure functions, frozen dataclasses, no LLM calls, no asyncio in the core module. The LLM call belongs in the graph-layer adapter or CycleRunner

---

### Pitfall 8: PersonaScore 5D Rubric Prompt Produces Non-Deterministic Scores

**What goes wrong:** The LLM-as-Judge prompt defining the 5 dimensions (Consistency, Tone, Logic, Depth, Bias) produces inconsistent scores across identical inputs due to LLM non-determinism. A score of 0.7 on "Consistency" today means something different next week. Since PersonaScore feeds into KAMI fidelity (which feeds into DebateSynthesizer consensus weighting), this non-determinism propagates to trade decisions.

**Why it happens:** Gemini Flash optimizes for speed and may vary outputs significantly between calls. The existing `_extract_fidelity_signal()` is deterministic (file existence check). Replacing it with an LLM call introduces noise into a previously stable signal.

**Prevention:**
- Use `temperature=0.0` for the judge LLM call to maximize determinism
- Include few-shot calibration examples in the judge prompt (3-5 examples with known scores per dimension)
- Use Gemini's structured output / JSON mode to force score format compliance (prevents parsing failures)
- Store the judge prompt version/hash alongside scores in the persona_scores table
- Apply EMA smoothing to PersonaScore over multiple cycles (the KAMI system already uses EMA via `apply_ema()`) to dampen single-call variance
- Run periodic calibration checks: evaluate the same frozen agent output and compare scores across runs. If standard deviation exceeds 0.1, the prompt needs refinement

**Detection:** PersonaScore fidelity dimension fluctuating more than 0.15 between consecutive cycles for the same agent with similar output. KAMI composite score variance increasing after PersonaScore integration.

---

### Pitfall 9: Circuit Breaker Placement Blocks Compliance-Critical Paths

**What goes wrong:** If the circuit breaker wraps ALL Gemini API calls globally (e.g., via a wrapper around `ChatGoogleGenerativeAI`), and the breaker is open, the system cannot generate decision cards for rejected trades (if PersonaScore evaluation is added to the card flow). This violates the MiFID II audit requirement -- every trade decision must be recorded regardless of execution outcome.

**Why it happens:** The simplest circuit breaker implementation wraps the LLM client at construction time. All nodes sharing that client inherit the breaker. But some nodes are compliance-critical (decision card writer) while others are optional (persona evaluation).

**Prevention:**
- Circuit breaker should wrap only the L2 agent LLM calls (analysts + researchers + debate synthesizer), NOT the L3 executor chain
- Decision card generation (`build_decision_card()`) is a pure function that does not call the LLM -- verify it stays that way
- Use tiered LLM clients: `_analysis_llm` (with breaker) and `_compliance_llm` (with retry-backoff, no breaker) and `_judge_llm` (with breaker, separate budget)
- The `institutional_guard_node` and `risk_manager_node` are rules-based (no LLM call) -- verify they stay that way and never gain a breaker dependency
- Log which LLM client tier each node uses in structured logs for auditability

---

### Pitfall 10: Token Cost Tracking Misses BudgetedTool Cache Hits and PersonaScore

**What goes wrong:** The existing `BudgetedTool` wrapper includes a `ToolCache` that deduplicates identical tool calls. Cached responses use zero tokens. If token tracking hooks into LLM completion callbacks, it misses the cost savings from cache hits, overreporting costs. Conversely, if it only tracks BudgetManager, it misses any LLM calls that bypass BudgetedTool (e.g., the PersonaScore judge, soul injection system_prompt construction if it calls an LLM).

**Prevention:**
- Token tracking must report BOTH gross (all LLM API calls) and net (minus cache) costs
- Add a `cache_hits` counter to BudgetManager alongside token counters
- Include a `cost_breakdown` dict in CycleSnapshot: `{"analysis_tokens": N, "judge_tokens": M, "cache_saves": K, "total_usd": X.XX}`
- Require every LLM call path to route through BudgetManager.record_usage() with a `category` tag

---

### Pitfall 11: ChromaDB Version Mismatch Breaks MemoryService API

**What goes wrong:** Fixing the broken `chromadb` dependency may install a different version than what `MemoryService` was coded against. ChromaDB has had significant breaking changes between 0.4.x and 0.5.x (collection API changes, embedding function signature changes, `get_or_create_collection` vs `create_collection` patterns). The `MemoryService` at line 1 imports from `chromadb` -- the exact API surface matters.

**Why it happens:** The `chromadb` package is currently missing from the environment entirely (~13 tests affected). When installing it fresh, `pip install chromadb` grabs the latest version, which may not match what was originally coded against.

**Prevention:**
- Pin exact version in requirements: `chromadb==0.4.24` (or whatever version the MemoryService API matches)
- Run `MemoryService` unit tests immediately after installation before making any code changes
- Check for `client.get_or_create_collection()` vs `client.create_collection()` pattern compatibility
- Similarly pin `pytest-asyncio` and configure `asyncio_mode` explicitly in `pyproject.toml`
- For `ccxt`: check if `order_router_ccxt.py` (untracked file) uses exchange class names or API patterns that changed

---

### Pitfall 12: Obsidian Archive Format Prevents Future Re-Import

**What goes wrong:** The "Prune-to-Obsidian" workflow archives ChromaDB vectors as Obsidian markdown. If the markdown format is purely human-readable (prose paragraphs with no structured metadata), the data is effectively write-only -- useful for review but impossible to re-import if needed (e.g., to rebuild ChromaDB after corruption or to re-validate rules against historical data).

**Prevention:**
- Use YAML frontmatter in archived markdown files with structured metadata: `document_id`, `source` (MemorySource enum value), `chunk_index`, `timestamp`, `collection_name`, `embedding_model_version`
- Store the raw text content in a fenced code block or clearly delimited section
- Do NOT store embeddings in Obsidian (they are model-specific and can be regenerated from text)
- Include a `re-import.py` script that reads archived markdown back into ChromaDB
- Follow the existing Obsidian convention in the project: the vault root is `quantum-swarm/` with symlinks to `.planning/` and `.gemini-kit/`

---

### Pitfall 13: PersonaScore Evaluates Only `active_persona`, Missing Fan-Out Agents

**What goes wrong:** The `active_persona` field in SwarmState holds only ONE agent handle at a time. But LangGraph fan-out runs `bullish_researcher` and `bearish_researcher` in parallel (orchestrator.py lines 333-336), each setting `active_persona`. By the time the post-debate chain runs, `active_persona` reflects whichever agent finished last. The `merit_updater` already has this problem (it only updates the last agent's merit per cycle). PersonaScore evaluation targeting only `active_persona` misses the other agents.

**Why it happens:** `active_persona: Optional[str]` is a plain field with no reducer -- it gets overwritten, not accumulated. This was acceptable when fidelity was a binary file check (`_extract_fidelity_signal()` takes agent_id as argument). But PersonaScore needs to evaluate ALL agents that contributed to the cycle.

**Prevention:**
- PersonaScore must evaluate ALL agents that produced output in the cycle: extract from `bullish_thesis`, `bearish_thesis`, `macro_report`, `quant_proposal` (which fields are non-None)
- Map state fields to agent handles: `bullish_thesis -> MOMENTUM`, `bearish_thesis -> CASSANDRA`, `macro_report -> AXIOM`, `quant_proposal -> SIGMA`
- Run evaluation per-agent in a loop in the post-cycle hook
- Store per-agent scores: `{soul_handle: {consistency: X, tone: X, logic: X, depth: X, bias: X}}` in the persona_scores table
- Consider whether `merit_updater` itself needs fixing to update ALL agents per cycle (currently only updates one)

---

## Minor Pitfalls

### Pitfall 14: Audit Hash Chain Corruption from New State Fields

**What goes wrong:** Adding new SwarmState fields for token tracking (e.g., `cycle_cost_breakdown: Optional[dict]`) or circuit breaker status (e.g., `breaker_state: Optional[str]`) automatically includes them in audit hash input. `with_audit_logging` captures `{k: v for k, v in state.items() if not k.startswith("_")}` as `input_snapshot` (orchestrator.py line 190). Non-deterministic values (timestamps, float precision) in new fields make `verify_chain()` non-reproducible.

**Prevention:**
- Add ALL new operational/observability fields to `AUDIT_EXCLUDED_FIELDS` in `audit_logger.py` immediately upon creation
- Review every new SwarmState field with the question: "Is this trade-decision data or operational metadata?"
- Token costs, breaker state, persona scores = operational metadata = MUST be excluded
- Add a test that verifies `AUDIT_EXCLUDED_FIELDS` contains all non-trade fields in SwarmState

---

### Pitfall 15: Circuit Breaker Hides Root Cause by Conflating Failure Types

**What goes wrong:** A circuit breaker that treats all Gemini API errors identically (429 rate limit, 503 service unavailable, 401 auth error, network timeout) cannot distinguish between "wait and retry" (rate limit), "service is down" (outage), and "credentials are wrong" (permanent). Different failures need different responses.

**Prevention:**
- Classify failures into categories:
  - **Rate limit (429):** Exponential backoff with jitter. Do NOT open circuit breaker -- this is expected behavior under load
  - **Server error (5xx):** Open circuit breaker with half-open probe after recovery_window
  - **Auth error (401/403):** Halt immediately, alert operator. API key revoked/expired is not recoverable by waiting
  - **Network timeout:** Retry with increasing timeout, then open breaker
- Track failure type distribution in structured logs and CycleSnapshot metadata
- The existing KAMI `_EXTERNAL_CAUSES` / `_SELF_INDUCED_CAUSES` classification taxonomy in `kami.py` (lines 55-69) is a good precedent for this pattern

---

### Pitfall 16: Fidelity Signal Remains Binary After Weight Increase

**What goes wrong:** If KAMI weights are rebalanced (fidelity from 0.10 to 0.35) but `_extract_fidelity_signal()` still returns 0.0 or 1.0 (binary: "has IDENTITY.md or not"), then 35% of the merit score becomes a meaningless binary signal. All 5 agents have fully authored IDENTITY.md files (v1.4 complete), so fidelity is permanently 1.0 for every agent. This means 35% of merit is identical across all agents, reducing KAMI's discriminating power more than the frozen Accuracy problem it replaces.

**Prevention:**
- Wire PersonaScore 5D scores into fidelity signal BEFORE increasing the weight. The implementation order must be: PersonaScore evaluation -> fidelity signal wiring -> weight rebalancing
- If PersonaScore is not ready when weight rebalancing ships, use a transitional approach: keep fidelity weight at 0.10 until PersonaScore is live, then increase
- Do not ship the weight change and the PersonaScore evaluation in separate phases with a gap between them

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| PersonaScore 5D LLM-as-Judge | Circular evaluation inside graph (#1), asyncio.run crash (#3), Import Layer Law violation (#7), non-deterministic scores (#8), evaluates only one agent (#13) | Post-cycle hook in CycleRunner, async-only, pure core functions, temperature=0 with few-shot, evaluate all agents |
| Token cost tracking | Double-counting via reducer (#4), cache hit misreporting (#10), audit hash corruption (#14) | Single authoritative source (BudgetManager), non-reducer field, add to AUDIT_EXCLUDED_FIELDS |
| KAMI weight rebalancing | Score discontinuity (#2), binary fidelity signal (#16) | Version-tag scores, wire PersonaScore BEFORE weight change, transition window |
| ChromaDB pruning + Obsidian | Orphaned active rules (#6), non-parseable archive (#12), ChromaDB version mismatch (#11) | Rule-aware cutoff, YAML frontmatter, pin exact dependency versions |
| Gemini API circuit breaker | Sticky open state (#5), blocks compliance paths (#9), conflates failure types (#15) | Time-based half-open, tiered LLM clients, failure classification |
| Dependency fixes (ccxt/chromadb/pytest-asyncio) | Breaking API changes (#11) | Pin exact versions, run full suite before code changes |

---

## Integration Risk Matrix

| New Feature | Existing System at Risk | Specific Danger |
|-------------|------------------------|-----------------|
| PersonaScore | Audit trail (SHA-256 hash chain) | Judge output entering `output_data` in `with_audit_logging` corrupts hash chain continuity |
| PersonaScore | BudgetManager ($5/day ceiling) | Judge tokens counted against session ceiling, premature SafetyShutdown |
| PersonaScore | merit_updater error handling | Judge failure triggers `return {}`, skipping ALL merit updates, not just fidelity |
| Token tracking | SwarmState `total_tokens` reducer | `operator.add` prevents correction; bug permanently inflates count |
| Token tracking | BudgetedTool / ToolCache | Double-counting from callback + explicit recording |
| KAMI rebalancing | DebateSynthesizer | Consensus weighting shifts overnight without agent behavior change |
| KAMI rebalancing | ARS Auditor KAMI variance | False breach alerts on weight change (default threshold: 0.04) |
| KAMI rebalancing | _extract_fidelity_signal | Binary 0/1 at 35% weight = less discriminating than frozen Accuracy at 30% |
| ChromaDB pruning | MemoryRegistry active rules | Active rules lose source context, MiFID II evidence trail weakened |
| ChromaDB pruning | RuleValidator backtesting | Cannot re-validate rules whose source vectors were pruned |
| Circuit breaker | CycleRunner (daemon mode) | Sticky open state prevents recovery without process restart (mirrors db.py anti-pattern) |
| Circuit breaker | institutional_guard / risk_manager | Must NOT wrap rules-based nodes that never call LLM |
| Circuit breaker | decision_card_writer | Must NOT block compliance-critical audit trail writes |
| Dependency fixes | MemoryService | ChromaDB 0.4.x vs 0.5.x API surface differences |
| Dependency fixes | order_router_ccxt.py | ccxt exchange class API may have changed |

---

## Implementation Ordering Constraints

Based on pitfall analysis, the following ordering prevents the most dangerous pitfalls:

1. **Dependencies first** -- Fix ccxt/chromadb/pytest-asyncio before any feature work. Pitfall #11 blocks testing.
2. **PersonaScore before KAMI rebalancing** -- Wire 5D scores into fidelity before changing weights. Pitfall #16 makes weight change counterproductive without real fidelity data.
3. **Token tracking independent of other features** -- Can be done in parallel but must choose single tracking source early. Pitfall #4 gets worse the longer it is deferred.
4. **Circuit breaker before ChromaDB pruning** -- Pruning triggers Obsidian writes which may interact with API availability. Breaker provides safety net.
5. **ChromaDB pruning last** -- Requires stable MemoryService (dependency fix), stable budget tracking (to know archive cost), and understanding of active rules (MemoryRegistry).

---

## "Looks Done But Isn't" Checklist

- [ ] **PersonaScore runs outside graph:** Evaluation is a CycleRunner post-hook, not a graph node
- [ ] **PersonaScore evaluates all agents:** Not just `active_persona` -- checks all non-None thesis fields
- [ ] **Fidelity signal is continuous:** `_extract_fidelity_signal()` returns gradient values, not 0/1
- [ ] **KAMI weights change AFTER PersonaScore wired:** Weight epoch documented in config
- [ ] **Token tracking has single source:** No double-counting between BudgetManager and callbacks
- [ ] **New state fields in AUDIT_EXCLUDED_FIELDS:** `cycle_cost_breakdown`, `breaker_state`, persona scores
- [ ] **Circuit breaker has half-open state:** Not a sticky boolean like `_db_unavailable`
- [ ] **Circuit breaker is tiered:** Analysis LLM has breaker, compliance LLM does not
- [ ] **ChromaDB version pinned:** Exact version matches MemoryService API
- [ ] **Pruning respects active rules:** Cutoff date cannot predate oldest active rule
- [ ] **Archive is re-importable:** Obsidian markdown has YAML frontmatter with document_id
- [ ] **Import boundaries tested:** New core modules in `TestCoreLeafImports`
- [ ] **judge LLM lazy-init:** `_get_judge_llm()` pattern, no import-time instantiation

---

## Sources

- Direct codebase analysis: `src/graph/orchestrator.py` (graph construction, `with_audit_logging`, routing), `src/core/kami.py` (merit formula, weights, signal extractors), `src/core/audit_logger.py` (hash chain, AUDIT_EXCLUDED_FIELDS), `src/core/budget_manager.py` (token tracking, SafetyShutdown thresholds), `src/core/ars_auditor.py` (drift metrics, breach escalation), `src/graph/state.py` (SwarmState fields, reducer annotations), `src/graph/nodes/merit_updater.py` (KAMI update flow, error handling), `src/core/db.py` (_db_unavailable sticky flag anti-pattern), `src/core/cycle_runner.py` (post-graph hook point), `src/memory/service.py` (ChromaDB interface, MemorySource), `src/evaluation/calibration.py` (existing evaluation patterns), `src/core/persistence.py` (schema definitions)
- PROJECT.md: known constraints, asyncio.run defect history, architectural decisions
- v1.2 defect history: asyncio.run() inside LangGraph nodes (MEM-06)
- Import Layer Law enforcement: `tests/core/test_import_boundaries.py`
- AUDIT_EXCLUDED_FIELDS precedent: `src/core/audit_logger.py` lines 17-21
- BudgetManager reset pattern: `reset_session()` between CycleRunner cycles
- `_db_unavailable` sticky flag: `src/core/db.py` lines 21-31

---
*Pitfalls research for: v1.5 Reliable Infrastructure features integration into Quantum Swarm*
*Researched: 2026-03-09*
