# Pitfalls Research

**Domain:** MBS Persona System — Adding Tier 1 + Tier 2 to existing LangGraph financial swarm (v1.3)
**Researched:** 2026-03-08
**Confidence:** HIGH (grounded in the actual codebase at v1.2, the persona_plan.md spec, and SOT_PERSONA_REWARD_SYSTEM.md)

> **Scope note:** These pitfalls are specific to adding MBS to *this* existing system — a 260+ test LangGraph swarm with hash-chained audit trail, PostgreSQL persistence, and a live compliance surface. Generic LLM persona pitfalls are excluded unless they have a concrete integration consequence here.

---

## Critical Pitfalls

### Pitfall 1: System Prompt Injected Into `messages` — Pollutes Debate Extraction

**What goes wrong:**
`macro_analyst_node` writes the soul system prompt into `state["messages"]` as a `{"role": "system", ...}` dict. The `DebateSynthesizer` in `src/graph/debate.py` extracts researcher output by scanning all `messages` for entries whose `.name` attribute matches `"bullish_research"` or `"bearish_research"`. A system message injected by every persona node bloats `messages`, can shadow message name matching if the soul content accidentally contains those tag strings, and corrupts the `debate_history` audit record that feeds the hash-chained `DecisionCard`.

**Why it happens:**
The persona_plan.md spec already addresses this (`system_prompt` goes in SwarmState, not `messages`), but the sample node code in Section 5 returns `"messages": [{"role": "assistant", ...}]` alongside the soul fields. The pattern of appending to `messages` is deeply established across every L2 node. Developers adding soul injection will follow the existing pattern without realising `system_prompt` must remain out of the reducer-accumulated `messages` list.

**How to avoid:**
Store the composed system prompt **only** in `state["system_prompt"]` (the dedicated field). The LLM call site assembles `[{"role": "system", "content": state["system_prompt"]}, *state["messages"]]` at invocation time — it is never appended to the reducer. Add a test asserting `load_soul("macro_analyst").system_prompt_injection` does not appear anywhere in `state["messages"]` after `macro_analyst_node` runs.

**Warning signs:**
- `weighted_consensus_score` becomes unusually close to 0.5 for all tasks (system message text length skewing bullish/bearish balance).
- `debate_history` entries in `audit.jsonl` contain soul DNA text in the `evidence` field.
- Test for `DebateSynthesizer` starts failing with spurious "bullish_research" matches.

**Phase to address:** Tier 1 — SoulLoader + LangGraph wiring phase. Must be caught before any agent uses the soul. Add an explicit test: `assert state["system_prompt"] not in [m.get("content","") for m in state["messages"]]`.

---

### Pitfall 2: `lru_cache` on `load_soul` Is Process-Global — Tests Contaminate Each Other

**What goes wrong:**
`load_soul` is decorated with `@lru_cache(maxsize=None)`. In the test suite, if one test modifies a soul file on disk (or monkey-patches `_read`), subsequent tests in the same pytest process receive the stale cached version. More dangerously: if a test calls `load_soul("macro_analyst")` against a temp directory, and the next test calls it expecting the real `src/core/souls/` path, the cache silently returns the first result. The 260+ existing tests run in a single pytest process; cache leakage is guaranteed without explicit teardown.

**Why it happens:**
`lru_cache` is a module-level singleton. Python's test isolation model (per-test function) does not reset module-level state between tests. Developers writing soul tests will call `load_soul()` directly and assume isolation.

**How to avoid:**
Every test that touches `load_soul` must call `load_soul.cache_clear()` in a `teardown` / `autouse` fixture. The integration test `test_graph_runs_without_error_with_soul_loaded` must also clear the cache before and after. Expose a `_clear_soul_cache()` helper in `soul_loader.py` specifically for test use. In tests that need a fake soul, patch `_read` at the module level and clear the cache.

```python
# conftest.py or per-test fixture
import pytest
from src.core.soul_loader import load_soul

@pytest.fixture(autouse=True)
def clear_soul_cache():
    load_soul.cache_clear()
    yield
    load_soul.cache_clear()
```

**Warning signs:**
- Tests pass in isolation but fail when run after another test that uses `load_soul`.
- `warmup_soul_cache()` in `create_orchestrator_graph` causes all subsequent soul tests to see graph-init state rather than test-controlled state.
- A content assertion test (`test_system_prompt_contains_sentinel_name`) fails only in CI (where test order differs from local).

**Phase to address:** Tier 1 — test suite. Add the `autouse` fixture to `tests/core/conftest.py` before writing any soul test.

---

### Pitfall 3: `SOULS_DIR` Path Resolves Relative to `soul_loader.py` — Breaks in Test Invocation Contexts

**What goes wrong:**
`SOULS_DIR = Path(__file__).parent / "souls"` resolves correctly when the module is imported from `src/core/soul_loader.py` but only if the file is at the expected location. If pytest is invoked from a different working directory (e.g., a CI runner that sets `PYTHONPATH` but runs from a temp dir), or if the module is imported as part of a zip/wheel artifact, `Path(__file__)` can resolve unexpectedly. More critically: when `warmup_soul_cache()` is called during `create_orchestrator_graph()`, and the graph is created inside a test with `patch("langgraph.graph.StateGraph.compile", fake_compile)`, the warmup runs against the real `souls/` directory — mixing production and test soul state.

**Why it happens:**
`Path(__file__).parent` is the standard Python pattern for finding sibling data files and it works in all normal circumstances. The failure is subtle: it emerges specifically when `create_orchestrator_graph()` is called in tests (as it is in `test_graph_wiring.py`), because `warmup_soul_cache()` is called inside it. The test intends to test graph topology only, not soul content, but the warmup side-effect populates the cache.

**How to avoid:**
Move `warmup_soul_cache()` out of `create_orchestrator_graph()` and into the application entry point (`main.py`). In tests, patch `warmup_soul_cache` to a no-op. Add an environment variable override `QUANTUM_SOULS_DIR` that `SOULS_DIR` checks first, allowing tests to point at a fixture souls directory.

**Warning signs:**
- `test_graph_wiring.py` tests become order-dependent (pass alone, fail after soul tests).
- `FileNotFoundError` for soul files appears in CI logs during graph-topology tests.
- `warmup_soul_cache()` logs appear in test output for tests that have nothing to do with personas.

**Phase to address:** Tier 1 — SoulLoader implementation. Split warmup from graph construction before the first test is written.

---

### Pitfall 4: KAMI Recovery Metric Is Trivially Gameable — Intentional Failure Farming

**What goes wrong:**
The SOT defines Recovery as "The agent's ability to self-correct after a tool failure or Hallucination Trap" and weights it at 60% of the KAMI score. If the KAMI score drives `DebateSynthesizer` consensus weighting (per SOT Section 3), an agent can maximize its weight by deliberately triggering tool failures and then recovering from them. A `BullishResearcher` that fails twice on yfinance calls and recovers earns a higher KAMI than one that succeeds immediately — even though the output quality is identical or worse.

**Why it happens:**
Recovery-as-primary-signal is borrowed from RLHF literature where the training environment controls what constitutes a "failure." In this swarm, tool failures are stochastic external events (API errors, network timeouts, bad data). The KAMI formula treats all recoveries as equally meritorious regardless of whether the failure was self-induced or externally caused.

**How to avoid:**
Weight Recovery only for recoveries from *external* failures (classified by the existing `INSUFFICIENT_DATA` vs `INVALID_INPUT` error taxonomy from Phase 5 CONTEXT.md). Self-induced failures (agent issues a malformed tool call that returns `INVALID_INPUT`) should penalize KAMI, not reward recovery from them. Cap the number of Recovery events counted per task cycle (e.g., max 2 recovery credits per debate round) to prevent failure-farming. The Fidelity component (persona consistency scoring) provides a check because deliberate failure farming produces off-persona behavior.

**Warning signs:**
- Agent KAMI scores are higher on days with high API error rates (spurious correlation with market data outages).
- `BullishResearcher` KAMI systematically higher than `BearishResearcher` when yfinance is flaky (different tool usage patterns create asymmetric failure opportunities).
- `weighted_consensus_score` shifts dramatically correlated with tool error rate rather than market data.

**Phase to address:** Tier 2a — KAMI Merit Index. Error classification must feed into KAMI calculation from day one. Define the failure taxonomy in the KAMI spec before implementing the formula.

---

### Pitfall 5: EMA Cold Start at 0.5 Creates Instant High-Stakes Weighting

**What goes wrong:**
New agents start with KAMI = 0.5. The `DebateSynthesizer` uses KAMI to weight consensus. A freshly created `risk_manager` soul with no track record immediately receives 50% weight in any debate it joins. If skeleton soul dirs (bullish_researcher, bearish_researcher, quant_modeler, risk_manager) are activated before being populated with content, they run with cold-start KAMI = 0.5 and empty system prompts — meaning they produce LLM output without persona context but with non-trivial debate weight.

**Why it happens:**
The cold-start value 0.5 is correct for a single-agent context (neutral prior). It is incorrect for the multi-agent debate where 0.5 applied to a content-free skeleton agent dilutes the weight of established agents with actual track records.

**How to avoid:**
Cold start KAMI should be 0.5 only when the agent's soul files are *populated*. Skeleton agents (empty soul files) must receive a `merit_multiplier = 0.0` until their IDENTITY.md contains at least the minimum required fields (Name, Linguistic Habit, Drift Guard). Gate KAMI wiring in `DebateSynthesizer` with `if soul.identity` check. Alternatively: don't wire KAMI weighting to `DebateSynthesizer` until all four agent souls are fully populated (defer Tier 2a KAMI wiring until Tier 1 soul content is complete for all agents).

**Warning signs:**
- `weighted_consensus_score` becomes less decisive after skeleton agents are activated (score regresses toward 0.5 regardless of market signal strength).
- Debate outputs from skeleton agents appear in `debate_history` with no substantive content but non-zero weighting.

**Phase to address:** Tier 1 (skeleton soul creation) must define "soul activation" criteria; Tier 2a KAMI must not wire weighting until activation criteria are met.

---

### Pitfall 6: Agent Church Approval Gate With L1 Orchestrator as Judge of Its Own Subordinates — Deadlock and Conflict of Interest

**What goes wrong:**
EVOL-02 specifies "Agent Church (L1 Orchestrator) approval gate" for SOUL.md diffs. The L1 Orchestrator is itself an agent in the same graph. If the L1 Orchestrator's soul evolves and proposes a diff to its own SOUL.md, it becomes the judge of its own proposal — a structural conflict of interest. Worse: if approval requires L1 to run as a LangGraph node, and the evolution event is triggered inside a task cycle, the approval gate blocks until L1 completes, creating a synchronous bottleneck in what is otherwise an async graph.

**Why it happens:**
The Agent Church concept is borrowed from SOUL.md governance literature where "Church" is an external review entity. Mapping it to L1 Orchestrator conflates the governance layer with an operational agent.

**How to avoid:**
Implement Agent Church as an **out-of-band process**, not a LangGraph node. Evolution proposals accumulate in each agent's `MEMORY.md`. The Church review runs as a separate script (analogous to `PerformanceReviewAgent` which runs weekly) — not during the trade task cycle. Self-proposals by L1 must require human approval (ops alert + manual `git commit` of the diff), enforced by a check `if proposing_agent_id == "l1_orchestrator": require_human_approval()`. The existing `audit.jsonl` append pattern is the right model: fire-and-forget proposal write, async review.

**Warning signs:**
- Task cycle latency increases on days with active soul evolution proposals.
- L1 Orchestrator SOUL.md diffs appear in MEMORY.md and are self-approved without human review.
- Evolution proposals accumulate indefinitely (never reviewed) because no out-of-band Church process exists.

**Phase to address:** Tier 2b — MEMORY.md evolution. Design the Church as a standalone script before implementing EVOL-02.

---

### Pitfall 7: MEMORY.md Unbounded Growth Corrupts Existing MemoryRegistry Pattern

**What goes wrong:**
Each agent's `MEMORY.md` is an append-only evolution log ("unbounded" per the persona plan). The existing `MemoryRegistry` uses a Pydantic-validated JSON file with structured lifecycle transitions (proposed → active → deprecated/rejected). `MEMORY.md` is raw Markdown text. If EVOL-01 (per-agent MEMORY.md updated after each task cycle) runs on every trade cycle, a busy swarm generates one MEMORY.md append per agent per cycle. After 6 months of weekly trade cycles: thousands of unstructured entries, no lifecycle management, no way to determine which self-reflections are "active" vs historical.

**Why it happens:**
MEMORY.md is designed as a human-readable log, not a machine-readable registry. The evolution loop uses it as both log and proposal medium. There is no truncation or archival mechanism defined.

**How to avoid:**
Separate the log from the proposal. Use MEMORY.md as a rotating buffer (last N entries, e.g., N=50) for human readability. Machine-readable soul evolution proposals go into a structured JSON file (`data/soul_proposals/{agent_id}.json`) with the same Pydantic lifecycle pattern as `MemoryRegistry`. The `MemoryRegistry` pattern (atomic save via `os.replace`, one-way transitions, audit log append) must be reused for soul proposals. Add a `max_entries` config to the soul MEMORY.md writer and trim on write.

**Warning signs:**
- `src/core/souls/macro_analyst/MEMORY.md` file size grows unboundedly.
- ARS Auditor (Tier 2d) cannot parse MEMORY.md because it has no structured format.
- Git diffs on MEMORY.md files become unreadable (thousands of appended lines).

**Phase to address:** Tier 2b — define the proposal format and retention policy before EVOL-01 starts writing.

---

### Pitfall 8: Soul-Sync Handshake Adds Per-Debate Latency — Blocks Async Graph

**What goes wrong:**
TOM-01 specifies that before debate, agents exchange truncated SOUL.md summaries. In the current graph, `BullishResearcher` and `BearishResearcher` run as separate LangGraph nodes that can be fanned out in parallel. If the Soul-Sync Handshake is implemented as a pre-debate synchronization point (each agent reads the other's soul file from disk), it introduces a sequential barrier that prevents parallel fan-out. Even if reads are fast (~1ms), the synchronization logic (both agents must complete handshake before either starts debate) forces a join point that does not exist in the current graph topology.

**Why it happens:**
The handshake concept implies bidirectional exchange ("agents exchange summaries"). In a LangGraph node model, bidirectional synchronous exchange requires either a shared state write-then-read pattern (which requires two graph nodes and an edge between them, or a pre-debate barrier node) or loading both souls in a single pre-debate node.

**How to avoid:**
Implement the Soul-Sync Handshake as a **pre-debate context injection node** (`soul_sync_node`) that runs before `BullishResearcher` and `BearishResearcher` fan-out. This single node reads all debating agents' soul summaries and writes them to SwarmState fields (`peer_soul_contexts: dict[str, str]`). Each researcher node then reads its peer's context from state — no disk I/O during the debate, no bidirectional coupling. The soul summaries are loaded from `lru_cache`, so the `soul_sync_node` is effectively zero-latency after warmup.

**Warning signs:**
- `BullishResearcher` and `BearishResearcher` nodes can no longer run in parallel (serialization appears in LangGraph trace).
- Debate latency doubles on cold starts (soul files read twice, once per researcher).
- `test_adversarial_debate.py` timeout increases after TOM-01 is wired.

**Phase to address:** Tier 2c — Theory of Mind. Design `soul_sync_node` as the barrier before implementing individual researcher handshake logic.

---

### Pitfall 9: SOUL.md Exposure in Handshake — Internal Agent Psychology Leaked to Peer

**What goes wrong:**
The full `SOUL.md` contains the agent's "Core Wounds/Fears" and "behavioral triggers used to prevent Consensus Caving" (per SOT Section 2). If the Soul-Sync Handshake exchanges the *full* SOUL.md content, a `BearishResearcher` learns exactly what psychological triggers would cause the `BullishResearcher` to capitulate. This undermines adversarial debate integrity — it is the equivalent of showing a poker player their opponent's tells before the hand.

**Why it happens:**
The spec says "truncated SOUL.md summaries" without defining what is truncated. Without an explicit truncation schema, implementers will likely use `soul.soul[:N_chars]` — which includes the most sensitive sections (Core Wounds, Drift Guard pressure responses) that happen to appear early in the file.

**How to avoid:**
Define a `public_soul_summary()` method on `AgentSoul` that returns only the Persona Traits and Social Mode — the sections an agent would genuinely "present" to a peer. Core Wounds, Drift Guard triggers, and ALIGNMENT beliefs stay private. The `AGENTS.md` workflow rules (public output contract) are shareable; the `SOUL.md` values are not. Implement `public_soul_summary()` in `soul_loader.py` as a first-class method, not a string slice.

**Warning signs:**
- Bearish researcher refutations start precisely targeting bullish researcher's stated "fears" — indicating prompt leakage rather than genuine argument.
- SOUL.md content appears in `debate_history` entries in `audit.jsonl` (compliance risk: internal agent psychology in MiFID II audit record).

**Phase to address:** Tier 2c — before TOM-01 is implemented, define the `public_soul_summary()` API. Tier 1 can stub it as a no-op.

---

### Pitfall 10: ARS Drift Detection Baseline Is Undefined — False Positives Block Production Trading

**What goes wrong:**
ARS-02 specifies "Agents exceeding ARS drift threshold flagged; ops alert + evolution suspended." If the drift threshold is calibrated with no baseline (first week of operation, all agents are new, all scores are volatile), ARS will fire false positives and suspend evolution during the period when agents most need to evolve. Worse: if ARS suspension is implemented as a hard gate on the trade cycle (not just evolution), false positives block production trading.

**Why it happens:**
Drift detection without a baseline is a known pattern failure in statistical process control. The baseline must be established from a stable period before thresholds are enforced. ARS is defined before any agent has history, so the first N observations are necessarily outside any reasonable threshold.

**How to avoid:**
ARS must have an explicit warm-up period (e.g., first 30 evolution cycles per agent) during which drift scores are recorded but no alerts are fired. The suspension gate must apply only to soul **evolution** (SOUL.md diff approval), never to trade execution. Trade execution is gated by `InstitutionalGuard` and `RiskManager` — ARS is a governance layer, not a trading circuit breaker. Document this separation explicitly in the ARS spec. After warm-up, derive thresholds from the observed distribution (mean + 2 standard deviations), not from a hardcoded constant.

**Warning signs:**
- ARS fires on every agent after deployment (no baseline established).
- Trade execution is blocked when ARS suspension is triggered (scope creep from governance into execution path).
- ARS drift scores are monotonically increasing as agents evolve — indicates threshold is too tight, not that agents are unsafe.

**Phase to address:** Tier 2d — ARS Auditor. Warm-up logic and scope boundaries (governance only, not trade gate) must be in the ARS spec before implementation.

---

### Pitfall 11: `system_prompt` Field in SwarmState Pollutes Hash-Chained Audit Records

**What goes wrong:**
`state["system_prompt"]` contains the full composed soul injection (~500 tokens of Markdown). `AuditLogger.log_transition()` in `src/core/audit_logger.py` captures `input_snapshot = {k: v for k, v in state.items() if not k.startswith("_")}` — which includes `system_prompt`. Every node transition for every soul-bearing agent writes ~500 tokens of persona content into `audit_logs.input_data` JSONB. Over a trade cycle with 10+ nodes, this adds ~5,000 tokens of redundant soul content to PostgreSQL per task. The `data/audit.jsonl` file (used for MiFID II compliance) also receives this through `decision_card_writer_node`.

**Why it happens:**
The audit logger was designed before the persona system. Its state snapshot includes all SwarmState fields by default. Adding a 500-token field to SwarmState is a new cost that was not anticipated.

**How to avoid:**
Add `system_prompt` and `active_persona` to an explicit audit exclusion list in `with_audit_logging`. Pattern: `AUDIT_EXCLUDED_FIELDS = {"system_prompt", "active_persona", "peer_soul_contexts"}` — these are derivable from soul files, not forensically meaningful. The `DecisionCard` spec (Phase 11) already uses `state["metadata"]["trade_risk_score"]` to avoid SwarmState top-level pollution; follow the same pattern and store `active_persona` in `state["metadata"]["active_persona"]`.

**Warning signs:**
- `audit_logs` PostgreSQL table grows faster than expected after soul wiring.
- `data/audit.jsonl` file size per entry increases by ~10x after soul integration.
- `AuditLogger._last_hash` computation slows due to larger JSON payloads (SHA-256 over larger strings).

**Phase to address:** Tier 1 — when adding SwarmState fields. Define the audit exclusion list before `macro_analyst_node` is wired into the audit-logged graph.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems specific to this integration.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Put soul content directly in node docstring / comment rather than SOUL.md files | No file I/O, no lru_cache complexity | Impossible to evolve, audit, or review per EVOL-02; breaks KAMI lineage | Never |
| Use `state["messages"][0]` as the de-facto system prompt slot | No new SwarmState field needed | `DebateSynthesizer` scans all messages; system prompt becomes evidence; `operator.add` reducer duplicates it every cycle | Never |
| Hardcode KAMI weights (α=0.4, β=0.6, γ=0, δ=0) rather than making them configurable | Simpler implementation | Cannot tune without code change; formula drift undetectable by tests | Only during initial implementation — make configurable before Tier 2a ships |
| Skip `public_soul_summary()` and send full SOUL.md in handshake | Simpler Tier 2c | Leaks Core Wounds to adversarial peers; SOUL.md content in MiFID II audit records | Never |
| Wire ARS suspension to trade gate rather than evolution-only gate | Single enforcement point | ARS false positive halts production trading; regulatory incident if live trades blocked | Never |
| Implement Agent Church as a synchronous LangGraph node | Fits existing node pattern | Approval blocks task cycle; L1 self-reviews own proposals | Never |

---

## Integration Gotchas

Common mistakes when connecting MBS to the existing system.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `DebateSynthesizer` + KAMI | Pass raw KAMI score as consensus multiplier; score of 0.5 (cold start) silently neutralizes established agent | Gate KAMI weighting on `soul.identity != ""`; skeleton agents get `weight_multiplier = 0.0` |
| `with_audit_logging` wrapper + `system_prompt` | `input_snapshot` includes full soul content in every node audit record | Add `AUDIT_EXCLUDED_FIELDS` set; exclude `system_prompt`, `active_persona` |
| `warmup_soul_cache()` + `create_orchestrator_graph()` | Warmup called in graph factory; test for graph topology triggers real soul file loading | Move warmup to `main.py`; patch to no-op in topology tests |
| `lru_cache` + pytest | Soul content cached across tests; test that patches `_read` leaks into subsequent tests | `autouse` fixture calls `load_soul.cache_clear()` before and after every test |
| `MEMORY.md` + `MemoryRegistry` | Treat per-agent MEMORY.md as unstructured text log; ARS Auditor cannot parse it | Use structured JSON for machine-readable proposals; MEMORY.md is human-readable summary only |
| `InstitutionalGuard` + ARS | Wire ARS suspension flag into `route_after_institutional_guard` conditional | ARS governs evolution only; `InstitutionalGuard` governs trades; never combine |
| Soul-Sync Handshake + parallel fan-out | Add handshake inside each researcher node (forces sequential disk reads) | Pre-debate `soul_sync_node` runs before fan-out, writes peer contexts to state |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Soul file disk reads on every node invocation | Task cycle latency increases linearly with active agents | `@lru_cache` on `load_soul` + `warmup_soul_cache()` at startup; confirm cache hit in tests | Immediately without caching; ~10ms per read × 5 agents × N nodes |
| MEMORY.md file appended on every task cycle without truncation | File size grows unboundedly; git diffs unreadable; ARS parse time O(n) | Rolling buffer: write last 50 entries only; structured proposals to separate JSON | After ~100 trade cycles (few weeks in weekly operation) |
| Full soul content in PostgreSQL audit JSONB | `audit_logs` table bloat; hash computation over large payloads; index scan slowdown | Exclude soul fields from audit snapshot; store only `active_persona` (agent ID string) | After ~1000 trade cycles |
| EMA decay with λ close to 1.0 and sparse updates | KAMI score decays to 0.1 between weekly cycles; agents appear to lose merit between runs | Set λ based on update frequency (weekly cycle → λ ≈ 0.3 for meaningful decay) | Visible after 2-3 weekly cycles with λ > 0.7 |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Agent ID not validated before constructing soul path (path traversal) | Attacker injects `../../etc/passwd` as agent_id; arbitrary file read | The `soul_loader.py` spec includes path traversal guard; verify test coverage includes `../`, `/abs`, `\back` cases |
| Full SOUL.md (including Core Wounds) sent in Soul-Sync Handshake | Adversarial peer learns psychological triggers; debate integrity compromised; internal psychology in MiFID II audit record | `public_soul_summary()` method returns only public-facing persona traits; never shares Core Wounds or Drift Guard triggers |
| SOUL.md diff committed directly without Agent Church review | Unreviewed SOUL.md changes bypass alignment governance; agent belief system modified without audit | All SOUL.md changes must go through structured proposal in `data/soul_proposals/`; direct file writes to `SOUL.md` fail CI lint check |
| L1 Orchestrator self-approves its own SOUL.md evolution proposal | Circular authority; L1 can rewrite its own alignment constraints | `if proposing_agent_id == "l1_orchestrator": raise RequiresHumanApproval()` enforced in Church script |

---

## "Looks Done But Isn't" Checklist

- [ ] **SoulLoader tests:** `test_cache_returns_same_object` passes — but verify `lru_cache` teardown fixture exists; without it, passing order matters.
- [ ] **System prompt injection:** `macro_analyst_node` writes `system_prompt` to state — verify it is absent from `state["messages"]` by asserting in the node integration test.
- [ ] **KAMI wired to DebateSynthesizer:** `weighted_consensus_score` changes when KAMI scores change — verify skeleton agents with empty souls do not dilute the score (test with `soul.identity == ""`).
- [ ] **Agent Church:** Approval gate exists in code — verify it is invoked as an out-of-band script, not a blocking LangGraph node; verify L1 self-proposal raises `RequiresHumanApproval`.
- [ ] **ARS suspension scope:** ARS flag is set on drift — verify it only suspends evolution (no path from ARS flag to `route_after_institutional_guard` or `order_router_node`).
- [ ] **MEMORY.md retention:** MEMORY.md writer exists — verify it trims to max N entries on write; verify it does not call `os.replace` (that is for registry JSON, not human-readable logs).
- [ ] **Soul-Sync Handshake:** Handshake node exists — verify BullishResearcher and BearishResearcher can still run in parallel after handshake (soul contexts are in state, no runtime peer file reads).
- [ ] **Audit exclusion:** `with_audit_logging` wraps soul nodes — verify `system_prompt` is not in `input_data` column of `audit_logs` after a full graph run.
- [ ] **Hash chain integrity:** New soul-bearing nodes are added to the graph — verify `test_audit_chain.py` still passes after node additions (new nodes = new audit entries = chain must extend correctly).

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| System prompt in `messages` corrupts debate history | MEDIUM | Remove soul content from messages (filter on `"### SOUL DNA"` prefix); recompute `weighted_consensus_score` from remaining researcher messages; re-run affected task |
| `lru_cache` leakage across tests | LOW | Add `load_soul.cache_clear()` to `conftest.py`; run `pytest --forked` (if available) to force process isolation; no production impact |
| MEMORY.md grown to unmanageable size | LOW | Truncate to last 50 entries by running `scripts/trim_memory_md.py {agent_id}`; no audit trail impact (MEMORY.md is not in hash chain) |
| ARS false positive blocks evolution | LOW | Set `ars_suspended = False` in agent state; extend warm-up period; no trade impact if ARS scope is correctly limited |
| Agent Church deadlock (approval never granted) | MEDIUM | Stale proposals in `data/soul_proposals/` can be manually rejected via CLI; pending proposals do not block trade cycles |
| Soul content in PostgreSQL audit bloat | HIGH | `ALTER TABLE audit_logs` to remove historical soul content from JSONB is destructive and violates immutability; prevention is the only option — exclusion list must be in place before first production run |
| SOUL.md drift without governance (direct file edit) | HIGH | Restore `SOUL.md` from git history; append incident to `data/audit.jsonl` manually; review agent output quality for period between unreviewed edit and restoration |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| System prompt in `messages` (Pitfall 1) | Tier 1 — SoulLoader + LangGraph wiring | Test: `state["system_prompt"] not in [m["content"] for m in state["messages"]]` |
| `lru_cache` test contamination (Pitfall 2) | Tier 1 — test suite setup | `autouse` fixture in `conftest.py`; all soul tests pass in any order with `pytest --randomly` |
| `SOULS_DIR` path resolution + warmup (Pitfall 3) | Tier 1 — before first test | `warmup_soul_cache` patched to no-op in all graph topology tests |
| KAMI Recovery gaming (Pitfall 4) | Tier 2a — KAMI formula design | Error classification (INVALID_INPUT vs INSUFFICIENT_DATA) feeds KAMI; unit test confirms self-induced failures penalize score |
| EMA cold start for skeleton agents (Pitfall 5) | Tier 1 (define activation criteria) + Tier 2a (gate weighting) | Test: skeleton agent KAMI weight = 0 in DebateSynthesizer |
| Agent Church conflict of interest + deadlock (Pitfall 6) | Tier 2b — MEMORY.md evolution design | Church implemented as standalone script; L1 self-proposal raises exception; task cycle latency unaffected by pending proposals |
| MEMORY.md unbounded growth (Pitfall 7) | Tier 2b — before EVOL-01 ships | MEMORY.md writer trims to N=50; structured proposals in separate JSON file |
| Soul-Sync Handshake blocks fan-out (Pitfall 8) | Tier 2c — Theory of Mind design | BullishResearcher and BearishResearcher run in parallel in LangGraph trace after handshake node |
| SOUL.md Core Wounds leakage in handshake (Pitfall 9) | Tier 2c — before TOM-01 | `public_soul_summary()` tested to exclude Core Wounds, Drift Guard; SOUL.md raw content absent from `debate_history` in audit.jsonl |
| ARS no-baseline false positives (Pitfall 10) | Tier 2d — ARS spec | Warm-up period configurable; ARS suspension not reachable from any trade execution node path |
| `system_prompt` in hash-chained audit records (Pitfall 11) | Tier 1 — before `macro_analyst_node` wired into `with_audit_logging` | `audit_logs.input_data` does not contain `system_prompt` key; audit.jsonl entries for soul nodes are same size order-of-magnitude as non-soul nodes |

---

## Sources

- `docs/SOT_PERSONA_REWARD_SYSTEM.md` — MBS architecture, KAMI formula, Soul-Sync Handshake, ARS spec
- `.planning/PHASES/persona_plan.md` — SoulLoader implementation, SwarmState field definitions, test strategy
- `.planning/PROJECT.md` — v1.2 architecture constraints, hash-chain design decisions, audit trail requirements
- `src/graph/debate.py` — DebateSynthesizer message extraction logic (pitfalls 1, 5 grounded here)
- `src/core/audit_logger.py` — state snapshot inclusion logic (pitfall 11 grounded here)
- `src/core/memory_registry.py` — atomic save pattern, lifecycle transitions (pitfall 7 comparison)
- `src/graph/orchestrator.py` — `with_audit_logging` wrapper, `create_orchestrator_graph` (pitfalls 3, 11)
- `src/graph/state.py` — SwarmState reducer patterns, `operator.add` on `messages` (pitfall 1)
- PersonaGym (arxiv:2407.18416) — Drift Guard effectiveness; prompting-only insufficiency
- Python `functools.lru_cache` documentation — process-global cache lifecycle

---
*Pitfalls research for: MBS Persona System (Tier 1 + Tier 2) integration into Quantum Swarm v1.3*
*Researched: 2026-03-08*
