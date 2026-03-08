# Domain Pitfalls

**Domain:** Observable swarm beta features (cycle persistence, replay CLI, full personas, end-to-end hardening)
**Project:** Quantum Swarm v1.4
**Researched:** 2026-03-08
**Confidence:** HIGH (grounded in codebase analysis at v1.3 + verified against LangGraph docs, community issues, and published research)

> **Scope:** These pitfalls are specific to adding v1.4 beta features to THIS existing system -- a 300+ test, ~30,600 LOC LangGraph swarm with hash-chained MiFID II audit trail, PostgreSQL async persistence, synchronous file I/O constraints, lru_cache soul loading, and 4 skeleton personas. Generic pitfalls excluded unless they have concrete integration consequences here.

---

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or system-breaking regressions.

### Pitfall 1: Checkpoint State Bloat from Per-Cycle Artifact Storage

**What goes wrong:** Storing full agent memos, debate transcripts, consensus summaries, merit score snapshots, and decision cards directly in `SwarmState` fields causes LangGraph to checkpoint the entire accumulated payload at every graph step. With `operator.add` reducers on `messages` and `debate_history`, each checkpoint includes the full history. A single cycle through 20+ nodes with rich agent output can produce megabytes of checkpoint data. Over 50-100 cycles, the PostgreSQL checkpoint table balloons to gigabytes, queries slow dramatically, and `ainvoke` start-up time degrades as it hydrates prior state.

**Why it happens:** The system already uses `Annotated[List[dict], operator.add]` for `messages` and `debate_history`. The natural instinct when adding per-cycle persistence is to add more accumulating state fields (e.g., `cycle_artifacts: Annotated[List[dict], operator.add]`). LangGraph checkpoints the full state at every step -- not deltas. No checkpoint TTL is currently configured.

**Consequences:**
- PostgreSQL checkpoint table grows unboundedly
- `ainvoke` start-up latency increases linearly with cycle count
- Potential OOM on long-running sessions
- `audit_logs` table already stores full `input_data`/`output_data` JSONB -- double-storing in checkpoints wastes storage

**Prevention:**
- Write cycle artifacts to filesystem (`data/cycles/{task_id}/`) or a dedicated PostgreSQL table -- NOT to SwarmState
- Keep only lightweight references in state (e.g., `cycle_artifact_ref: str` pointing to file path or DB row ID)
- Add `messages` trimming: after debate, summarize and drop older messages to cap the list
- Configure checkpoint TTL or prune old checkpoints in a background job
- Consider `durability="exit"` mode if intermediate step checkpoints are not needed for crash recovery

**Detection:** Monitor PostgreSQL table sizes (`pg_total_relation_size`). If `checkpoints` table exceeds 100MB after fewer than 100 cycles, the pattern is wrong.

**Confidence:** HIGH -- verified against LangGraph persistence docs and community issue reports on `operator.add` growth.

**Phase relevance:** Must be decided BEFORE implementing per-cycle persistence. Retrofitting storage strategy after 100+ cycles of data in the wrong place is a migration nightmare.

---

### Pitfall 2: `operator.add` Message List Unbounded Growth

**What goes wrong:** The current `messages: Annotated[List[dict], operator.add]` field accumulates every assistant message from every node in the graph. A single cycle through the full pipeline (merit_loader -> classify_intent -> macro_analyst -> bullish_researcher -> bearish_researcher -> soul_sync -> debate_synthesizer -> ... -> trade_logger -> synthesize) appends 15-20 messages. After 10 cycles without clearing, the messages list contains 150-200 entries, all checkpointed at every step.

**Why it happens:** `operator.add` is append-only by design. LangGraph issue #2943 confirms there is no built-in way to clear `Annotated[list, operator.add]` fields during a workflow. The current codebase uses `state["trade_history"][-15:]` sliding window in L2 agents for `trade_history`, but `messages` has no such trimming.

**Consequences:**
- LLM context windows overflow when messages are passed to agents
- Token costs scale linearly with cycle count
- Checkpoint sizes grow quadratically (N messages x M nodes x K cycles)
- LangSmith state size limits can be exceeded

**Prevention:**
- Implement a `trim_messages` node or use a custom reducer that keeps only the last N messages
- Do NOT pass the full `messages` list to LLM agents -- construct per-agent context windows from specific state fields (`macro_report`, `quant_proposal`, etc.)
- Consider replacing `operator.add` with a custom reducer that enforces a sliding window
- The `add_messages` helper from LangGraph handles deduplication by message ID -- consider switching

**Detection:** Log `len(state["messages"])` at entry and exit of each cycle. If it grows monotonically across cycles, the problem is active.

**Confidence:** HIGH -- confirmed by LangGraph GitHub issue #2943 and forum reports of exponential duplication.

**Phase relevance:** Fix BEFORE adding cycle persistence. The messages list is already the primary contributor to state size.

---

### Pitfall 3: Synchronous File I/O in Async Graph Blocks Event Loop

**What goes wrong:** The codebase has a documented decision: "Synchronous file I/O in node functions -- asyncio.run() inside nodes is project-breaking." The `memory_writer_node` is async but calls `_process_agent()` which does synchronous `Path.read_text()` and `Path.write_text()`. Adding per-cycle artifact persistence means MORE synchronous file writes inside async nodes. Each `Path.write_text()` blocks the event loop thread.

**Why it happens:** The system correctly avoids `asyncio.run()` inside nodes (which would crash with "cannot run nested event loop"). But the alternative -- raw synchronous I/O -- blocks the event loop. This is tolerable for small writes but becomes a bottleneck when writing 5+ agent memos + debate transcript + consensus card + decision card per cycle.

**Consequences:**
- Fan-out nodes that should run concurrently serialize if their downstream persistence writes block
- Under load, event loop starvation causes PostgreSQL connection pool timeouts (psycopg3 async connections expect timely `await` returns)
- The `with_audit_logging` wrapper uses `asyncio.to_thread()` for sync nodes but `_process_agent` is called from an async node without `to_thread`

**Prevention:**
- Wrap ALL file I/O in `asyncio.to_thread()` calls within async node functions
- OR: collect artifact data in-memory during the async node, write to disk in a dedicated "flush" node at end of cycle
- Do NOT use `asyncio.run()` -- use `await asyncio.to_thread(sync_write_fn, args)`
- Consider batching: one write per cycle (a single JSON file with all artifacts) rather than N writes per agent

**Detection:** Profile event loop blocking with `asyncio.get_event_loop().slow_callback_duration`. Any callback exceeding 100ms in a trading system is a red flag.

**Confidence:** HIGH -- directly observed in codebase (`memory_writer.py` lines 28-29 explicitly state the constraint).

**Phase relevance:** Must be addressed when adding per-cycle persistence. The existing synchronous I/O is marginal; adding more will cross the threshold.

---

### Pitfall 4: lru_cache Soul Invalidation During Persona Population

**What goes wrong:** `load_soul()` uses `@lru_cache(maxsize=None)` and `warmup_soul_cache()` is called once at `create_orchestrator_graph()` time. When populating the 4 skeleton personas with full HEXACO-6 profiles, the new SOUL.md content is invisible to any running graph instance. If you edit SOUL.md files and re-run without restarting the process, agents use stale persona content.

**Why it happens:** Frozen dataclass + `lru_cache` was the correct design for production (immutable, concurrent-read-safe). But it creates a trap during development: edit-test cycles silently use old soul content. The `clear_soul_caches` fixture exists in tests (`tests/core/conftest.py`) but not in the runtime path.

**Consequences:**
- Persona changes appear to have no effect during development (silent stale reads)
- If the graph is long-running (e.g., loop mode), soul updates require full process restart
- No runtime mechanism to detect stale cache

**Prevention:**
- Add a `clear_soul_caches()` utility function (call `load_soul.cache_clear()`) and expose it in the CLI
- For development: add an optional `--reload-souls` flag that clears cache before each cycle
- For production: accept that soul changes require process restart (this is fine for v1.4 beta)
- Do NOT add automatic mtime-based invalidation -- it breaks the frozen/immutable contract and introduces race conditions during fan-out

**Detection:** Compare SOUL.md file mtime against process start time. If SOUL.md is newer than process start, warn in logs.

**Confidence:** HIGH -- directly observed in `soul_loader.py` (`@lru_cache(maxsize=None)` on line 105).

**Phase relevance:** Must be handled BEFORE or DURING persona population phase. Otherwise persona development becomes a frustrating edit-restart-test loop.

---

### Pitfall 5: yfinance Rate Limiting Kills End-to-End Pipeline

**What goes wrong:** The `data_fetcher_node` calls `fetch_equity_data(symbol)` via yfinance and `fetch_crypto_ohlcv(symbol)` via ccxt. As of November 2024, Yahoo Finance tightened rate limits aggressively. In a rapid development cycle where you run 10-20 end-to-end tests against real data, you get 429 "Too Many Requests" errors. The `data_fetcher_node` has no retry logic -- it raises on failure, which halts the entire pipeline.

**Why it happens:** yfinance is not an official API -- it scrapes Yahoo Finance endpoints. Yahoo blocks IPs that make rapid sequential requests. The `_execute_paper` function also calls `_fetch_last_price` via yfinance. Two yfinance calls per cycle (data_fetcher + paper order fill) doubles the rate limit pressure. The ccxt dependency is already broken in the environment.

**Consequences:**
- End-to-end pipeline fails at `data_fetcher` node, never reaching downstream logic
- Paper execution fails silently (falls back to `last_price = 100.0` which is wrong for most assets)
- Development velocity tanks because each retry requires waiting for rate limit cooldown
- Broken ccxt means crypto path is non-functional

**Prevention:**
- Add a data caching layer: cache market data by (symbol, date) with 1-hour TTL for development
- Implement exponential backoff with max 3 retries in `data_fetcher_node`
- Add a `--cached-data` CLI flag for replay/development that uses stored market snapshots
- Fix or replace ccxt dependency
- For beta testing: pre-fetch and store market data snapshots, replay against stored data

**Detection:** Monitor HTTP 429 responses. If more than 5% of data_fetcher calls fail, rate limiting is active.

**Confidence:** HIGH -- yfinance rate limiting well-documented (GitHub issues #2422, #2431, #2128) and data_fetcher has no retry logic (verified in code).

**Phase relevance:** Must be addressed FIRST in end-to-end hardening. Without reliable data fetching, nothing downstream can be tested.

---

## Moderate Pitfalls

### Pitfall 6: HEXACO-6 Profile Collapse Under System Prompt Pressure

**What goes wrong:** When populating skeleton personas with HEXACO-6 personality profiles, Gemini tends to collapse diverse persona instructions into its default helpful-assistant voice after 2-3 turns. Personality "leaks" -- a high-Conscientiousness SIGMA starts sounding identical to a high-Openness MOMENTUM because Gemini's RLHF training dominates persona instruction.

**Why it happens:** Research shows LLMs treat persona prompts as weak signals relative to their RLHF training. Social stereotypes in training data provide a stronger signal than nuanced personality dimensions. Gemini Flash specifically optimizes for helpfulness, which can override persona-specific voice constraints.

**Prevention:**
- Keep persona descriptions behavioral, not trait-based ("SIGMA always quantifies uncertainty with confidence intervals" not "SIGMA scores 85 on Conscientiousness")
- Use the existing Drift Guard mechanism to detect persona collapse (add keyword rules for each persona's distinctive vocabulary)
- Reinforce persona at EVERY agent invocation (current system does this correctly via soul injection per node)
- Test persona distinctiveness: cosine similarity between agent outputs should be LOW for adversarial pairs
- Do NOT use raw HEXACO dimension scores in prompts -- translate into behavioral rules and voice patterns

**Detection:** If all 4 L2 agents produce outputs with high cosine similarity, personas have collapsed. ARS Drift Auditor can surface this.

**Confidence:** MEDIUM -- based on published research (Turing Institute, arxiv:2508.00742) but not yet tested with Gemini Flash specifically.

**Phase relevance:** Persona population phase. Validate EACH populated persona against Drift Guard before moving to next.

---

### Pitfall 7: CLI Replay Tool Creates Second Event Loop

**What goes wrong:** Building a cycle replay CLI that needs to read from PostgreSQL (async via psycopg3) and display cycle data. The naive approach wraps async DB calls in `asyncio.run()`. But if the CLI is ever invoked from within an existing async context (e.g., Jupyter notebook, future web UI), `asyncio.run()` crashes with "cannot be called from a running event loop."

**Why it happens:** The project uses psycopg3 async exclusively for database access (`get_pool()` pattern). A CLI tool needs to call these async functions from a synchronous entry point. Click does not support async commands natively. Typer has limited async support.

**Consequences:**
- CLI works standalone but crashes when imported as a library
- Cannot reuse existing async DB access functions -- must duplicate as sync versions
- If the CLI starts its own event loop, it cannot share the PostgreSQL connection pool

**Prevention:**
- Use `asyncio.run()` ONLY at the top-level CLI entry point (the `if __name__ == "__main__"` or Click command handler)
- Keep all internal replay logic as async functions that can be awaited from any context
- Use `asyncclick` or Typer with async support
- For the replay tool specifically: read from filesystem artifacts (not PostgreSQL) where possible, since per-cycle persistence will write to disk

**Detection:** Automated test that imports the replay module and calls its main function from within an `asyncio.run()` wrapper. If it raises "cannot be called from a running event loop," the design is wrong.

**Confidence:** MEDIUM -- standard Python async pitfall, well-documented.

**Phase relevance:** Replay CLI phase. Design the async boundary BEFORE writing commands.

---

### Pitfall 8: Audit Hash Chain Breaks When Adding New State Fields

**What goes wrong:** The `AuditLogger._calculate_hash()` hashes `input_data` and `output_data` from state. When new state fields are added for cycle persistence (e.g., `cycle_artifact_ref`, `replay_metadata`), they automatically enter the hash input. If a field contains non-deterministic data (timestamps, UUIDs, float precision jitter), the hash chain becomes non-reproducible and `verify_chain()` fails.

**Why it happens:** `with_audit_logging` captures `{k: v for k, v in state.items() if not k.startswith("_")}` as `input_snapshot`. New fields are included by default. The `AUDIT_EXCLUDED_FIELDS` frozenset exists but must be manually updated for each new field.

**Consequences:**
- MiFID II audit trail integrity check (`verify_chain()`) fails on legitimate data
- Compliance incident logged for non-issue
- If not caught early, breaks accumulate and cannot be repaired (hash chain is forward-only)

**Prevention:**
- Add new observability/replay fields to `AUDIT_EXCLUDED_FIELDS` immediately when creating them
- Review every new SwarmState field: "Is this trade-decision data or operational metadata?"
- Operational metadata (replay refs, cycle IDs, persona content) must be excluded
- Add a test that verifies `AUDIT_EXCLUDED_FIELDS` contains all non-trade fields
- Use `round(float_value, 4)` canonicalization for any float entering the hash (already done for merit_scores)

**Detection:** Run `verify_chain()` after every integration test that exercises the full pipeline with new state fields.

**Confidence:** HIGH -- directly observed pattern in `audit_logger.py`. The AUDIT_EXCLUDED_FIELDS mechanism exists precisely because this already happened with soul fields.

**Phase relevance:** Every phase that adds SwarmState fields. Must be a checklist item in every plan.

---

### Pitfall 9: Paper Fill Price Fallback Masks Real Failures

**What goes wrong:** The `_execute_paper` function catches all yfinance failures and falls back to `last_price = 100.0`. When running end-to-end against real market data, paper fills silently use a dummy price that makes all downstream calculations (PnL, risk scores, KAMI metrics) meaningless. The system "works" but produces garbage data that pollutes MEMORY.md, merit scores, and decision cards.

**Why it happens:** Graceful degradation was the right choice for the test phase. But for a beta that is supposed to produce observable, reviewable output, silent fallbacks create undetectable data quality issues.

**Consequences:**
- KAMI scores drift based on fictional trades at $100
- MEMORY.md entries reference thesis summaries for instruments trading at wrong prices
- Decision cards record nonsensical risk metrics
- ARS Drift Auditor may flag false drift

**Prevention:**
- Add a `data_quality` field to `execution_result` that marks whether real or fallback data was used
- In the memory_writer and merit_updater, skip updates when `data_quality == "fallback"`
- For beta: fail the cycle explicitly when market data is unavailable rather than using dummy data
- Log a WARNING when fallback prices are used and propagate to state

**Detection:** Check if `execution_result.execution_price` is exactly 100.0 for non-penny-stock instruments. This is a sentinel value.

**Confidence:** HIGH -- directly observed in `order_router.py` line 202: `last_price = 100.0`.

**Phase relevance:** End-to-end hardening phase. Must be fixed before running observable cycles.

---

### Pitfall 10: Missing `drift_guard` YAML in Skeleton Personas Silently Disables Drift Detection

**What goes wrong:** The 4 skeleton personas (MOMENTUM, CASSANDRA, SIGMA, GUARDIAN) have prose Drift Guard sections in SOUL.md but no `yaml drift_guard:` block. `parse_drift_guard_yaml()` returns an empty tuple when no YAML block is found. `evaluate_drift()` returns `[]` for empty rules. The memory_writer writes `[DRIFT_FLAGS:] none` for every cycle. The entire drift detection pipeline is silently disabled for 4 of 5 agents.

**Why it happens:** AXIOM (macro_analyst) is the only fully populated persona with YAML drift rules. The skeleton personas were explicitly documented as tech debt. But the fail-soft design means no errors are raised -- the system quietly does nothing.

**Consequences:**
- Drift detection only works for 1 of 5 agents (AXIOM)
- ARS Auditor accumulates meaningless "none" flags for 80% of agents
- DRIFT_STREAK trigger can never fire for skeleton agents
- Observable output is incomplete

**Prevention:**
- When populating each persona's HEXACO-6 profile, add YAML drift rules as a mandatory deliverable
- Define at minimum 2 rules per persona: one keyword-based, one regex-based
- Add a startup validation check: warn if any agent in `_KNOWN_AGENTS` has zero drift rules
- Do NOT ship the persona as "complete" without functional drift rules

**Detection:** At `warmup_soul_cache()` time, log a warning for agents with `len(soul.drift_rules) == 0`.

**Confidence:** HIGH -- directly observed. `parse_drift_guard_yaml` returns `()` for empty YAML blocks (verified in `drift_eval.py`).

**Phase relevance:** Persona population phase. Each persona must be validated against drift rule presence.

---

## Minor Pitfalls

### Pitfall 11: `thesis_records/` Stub Breaks Accuracy Dimension

**What goes wrong:** The KAMI Accuracy dimension is "deferred to async post-trade resolution path" using `thesis_records/`. This directory is a stub. Without Accuracy data, the merit composite formula weights Accuracy at 30% (`alpha=0.30`) using the cold-start default of 0.5. This means 30% of the merit score is permanently frozen at 0.5 for all agents, reducing the dynamic range of KAMI scores.

**Prevention:** Either implement thesis_records or reduce the Accuracy weight to 0.0 in `swarm_config.yaml` for the beta period. Document which weight configuration the beta uses.

**Confidence:** HIGH -- verified in `merit_updater.py` (`new_acc = agent_entry.get("accuracy", DEFAULT_MERIT)` never changes).

### Pitfall 12: PostgreSQL Connection Pool Race on First Use

**What goes wrong:** Multiple nodes call `get_pool()` followed by `pool.open()` wrapped in try/except. The `_check_evolution_suspended`, `_persist_merit`, and `AuditLogger` all independently try to open the pool. Under rapid concurrent access (fan-out nodes), multiple coroutines may race to open the pool simultaneously.

**Prevention:** Open the pool once at graph creation time in `create_orchestrator_graph()`. Pass the opened pool via config or closure. Do not rely on "open if not already open" patterns scattered across 10+ call sites.

**Confidence:** MEDIUM -- psycopg3 pool open is idempotent, but the pattern is fragile.

### Pitfall 13: Replay CLI Needs Artifacts That Do Not Yet Exist

**What goes wrong:** Building a replay CLI before implementing cycle persistence creates a dependency inversion. The replay tool needs structured artifact files to read, but the format of those files is not defined until the persistence layer is built. If the replay CLI is built first, it hardcodes format assumptions.

**Prevention:** Define the artifact schema (JSON structure, directory layout) BEFORE implementing either the persistence layer or the replay CLI. Both consume the schema; neither should define it.

**Confidence:** HIGH -- standard dependency management.

### Pitfall 14: `main.py` Entrypoint is Orphaned Legacy Code

**What goes wrong:** `src/main.py` imports from `agents.order_router_ccxt` (the broken ccxt module) and runs a hardcoded simulation loop. It does NOT use the LangGraph orchestrator. For v1.4 end-to-end execution, developers may accidentally run `src/main.py` instead of invoking through `LangGraphOrchestrator.run_task()`, getting a completely different (broken) codepath.

**Prevention:** Either update `main.py` to use the LangGraph orchestrator or rename to `main_legacy.py`. Create a proper entry point. Add a deprecation warning.

**Confidence:** HIGH -- directly observed. File imports `from agents.order_router_ccxt import route_order` which is the broken ccxt path.

### Pitfall 15: `time.sleep(30)` in Live Order Execution Blocks Thread Pool

**What goes wrong:** Both `_run_ib_order_sync` and `_run_binance_order_sync` use `time.sleep(30)` to wait for order fills. These are called via `asyncio.to_thread()`, so they block a thread pool thread for 30 seconds per order. If multiple live orders are submitted concurrently, the default thread pool (typically 5-8 threads) can be exhausted, blocking the entire event loop.

**Prevention:** Replace `time.sleep(30)` with proper NautilusTrader event-based fill notification. For beta, increase the thread pool size or add a timeout shorter than 30s with retry logic.

**Confidence:** HIGH -- directly observed in `order_router.py` lines 409 and 539.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Persona population (HEXACO-6) | Pitfall 4 (stale cache), Pitfall 6 (persona collapse), Pitfall 10 (no drift YAML) | Clear cache between edits, validate drift rules per persona, test persona distinctiveness |
| Per-cycle persistence | Pitfall 1 (state bloat), Pitfall 2 (message growth), Pitfall 3 (sync I/O blocking) | Write to filesystem not state, trim messages, use `asyncio.to_thread` |
| Cycle replay CLI | Pitfall 7 (event loop), Pitfall 13 (schema dependency) | Define artifact schema first, async-at-core with sync entry point boundary |
| End-to-end pipeline | Pitfall 5 (yfinance rate limit), Pitfall 9 (fallback prices), Pitfall 14 (wrong entrypoint), Pitfall 15 (sleep blocking) | Add data caching, fail explicitly on bad data, fix main.py, event-based fills |
| Observable output (merit, drift) | Pitfall 8 (audit hash), Pitfall 10 (drift disabled), Pitfall 11 (accuracy frozen) | Update AUDIT_EXCLUDED_FIELDS, require drift YAML, adjust KAMI weights |

---

## "Looks Done But Isn't" Checklist

- [ ] **Cycle persistence writes to state:** Check if any new `Annotated[List, operator.add]` fields were added for artifacts -- must use filesystem instead
- [ ] **Messages trimmed:** Verify `len(state["messages"])` is bounded after N cycles
- [ ] **Drift rules present:** All 5 agents have non-empty `drift_rules` tuple after persona population
- [ ] **Audit exclusion updated:** Every new SwarmState field reviewed against `AUDIT_EXCLUDED_FIELDS`
- [ ] **Data fetcher has retry:** `data_fetcher_node` handles 429 errors with backoff
- [ ] **Paper fill uses real price:** `execution_result.execution_price` is never 100.0 for production instruments
- [ ] **Replay reads from files:** Replay CLI reads filesystem artifacts, not PostgreSQL checkpoints
- [ ] **Soul cache clearable:** CLI has `--reload-souls` or equivalent for development
- [ ] **Artifact schema defined:** JSON schema exists before persistence or replay implementation starts
- [ ] **Entry point correct:** End-to-end test invokes `LangGraphOrchestrator`, not `src/main.py`

---

## Sources

- [LangGraph Persistence Documentation](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Issue #2943: Clearing operator.add fields](https://github.com/langchain-ai/langgraph/issues/2943)
- [LangGraph Forum: operator.add exponential duplication](https://forum.langchain.com/t/subject-operator-add-reducer-causes-exponential-duplication-in-annotated-list-state-fields-when-tools-update-state/1546)
- [LangGraph Checkpointing Best Practices 2025](https://sparkco.ai/blog/mastering-langgraph-checkpointing-best-practices-for-2025)
- [LangGraph State Management 2025](https://sparkco.ai/blog/mastering-langgraph-state-management-in-2025)
- [Turing Institute: Patterns Not People - Personality in LLM Agents](https://cetas.turing.ac.uk/publications/patterns-not-people-personality-structures-llm-powered-persona-agents)
- [arXiv: Recreating HEXACO with Generative Agents](https://arxiv.org/html/2508.00742)
- [Nature: Psychometric framework for LLM personality traits](https://www.nature.com/articles/s42256-025-01115-6)
- [yfinance Rate Limiting Issue #2422](https://github.com/ranaroussi/yfinance/issues/2422)
- [yfinance Rate Limiting Discussion #2431](https://github.com/ranaroussi/yfinance/discussions/2431)
- [Click Async Support Issue #2033](https://github.com/pallets/click/issues/2033)
- [BBC Cloudfit: Mixing Sync and Async Code](https://bbc.github.io/cloudfit-public-docs/asyncio/asyncio-part-5.html)
- Codebase: `src/graph/orchestrator.py`, `src/graph/state.py`, `src/core/soul_loader.py`, `src/core/audit_logger.py`, `src/graph/nodes/memory_writer.py`, `src/graph/nodes/merit_updater.py`, `src/graph/agents/l3/data_fetcher.py`, `src/graph/agents/l3/order_router.py`, `src/core/drift_eval.py`

---
*Pitfalls research for: v1.4 Beta Observable Swarm features integration into Quantum Swarm*
*Researched: 2026-03-08*
