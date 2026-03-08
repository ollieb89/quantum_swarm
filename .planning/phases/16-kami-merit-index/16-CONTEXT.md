# Phase 16: KAMI Merit Index - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Every agent in the swarm has a multi-dimensional, EMA-decayed merit score that persists across sessions in PostgreSQL and replaces the character-length proxy in DebateSynthesizer. The score is composed from four independently-tracked dimensions: Accuracy, Recovery, Consensus, and Fidelity. `compute_merit(agent_id, signals)` returns a float in `[0.1, 1.0]`. DebateSynthesizer consensus weighting is fully rewired to use KAMI scores keyed by soul handle. Behavioral soul adherence scoring (Theory of Mind) and soul mutation review (Agent Church) are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Signal Inputs — Accuracy

- **Ground truth:** Post-trade resolved P&L outcome — the only honest signal for "was this agent actually right?"
- **Scoring rule:** Binary hit/miss (+1 / -1 / 0):
  - Advocated direction matched profitable P&L → `+1`
  - Advocated direction matched losing P&L → `-1`
  - Neutral / no clear directional stance → `0`
- **Sparsity:** Accuracy is sparse and delayed — this is correct. "Hard to observe" is evidence of correctness, not a flaw.
- **Thesis record:** At debate time, each agent emits a thesis record: `{agent_id (soul handle), decision_id, instrument, direction (long/short/neutral), timestamp}`. KAMI joins this to a later resolution event.
- **Update path:** Deferred async update — Accuracy EMA updates only when a trade resolves. Not in-cycle. Two-stage model: Recovery/Consensus/Fidelity update in-cycle; Accuracy updates async later.
- **Signal is NOT:** intra-cycle directional agreement with `final_decision` — that measures consensus-conformity, not real-world correctness.

### Signal Inputs — Recovery

- **Measures:** Self-induced operational reliability — "when called, does this agent produce a valid, structured output?"
- **Scoring rule:** Clean-call rate: `+1` for clean invocation, `0` for error invocation.
- **Errors that count:** `INVALID_INPUT`, schema failures, malformed outputs, tool invocation errors caused by the agent.
- **Blame attribution (critical):** Recovery tracks **self-induced errors only**.
  - Self-induced error → caller's Recovery is penalised.
  - Upstream-induced error (malformed state from a prior agent) → penalty attributed to the **producer** via `producer_agent_id` provenance in the malformed state, NOT the consumer.
  - Optional dual-fault: if the consumer also failed its own input-validation contract (could have safely rejected the bad input but instead propagated or crashed), both agents may be penalised.
- **EMA gives bounce-back implicitly:** `clean clean clean error clean clean` → EMA dips, then climbs. No streak detection needed.

### Signal Inputs — Consensus

- **Measures:** Convergence contribution — "did this agent's output help the swarm reach a clearer, more justified decision?"
- **NOT:** directional agreement with the majority verdict. That creates sycophancy incentive and systematically penalises contrarians (CASSANDRA). CASSANDRA must score positively when she raises real, evidence-backed risk that changes the swarm's confidence appropriately.
- **Positive signal:** contribution reduces uncertainty, strengthens argument quality, changes confidence in the right direction.
- **Negative signal:** contribution increases confusion, introduces unsupported claims, adds noise without evidence.
- **Operational proxy:** confidence resolution delta from `debate_resolution` — argument novelty, evidence quality, synthesizer confidence shift.
- **Implication for DebateSynthesizer:** Consensus dimension is evaluated at cycle close, not per-message. The debate_resolution confidence delta is the signal.

### Signal Inputs — Fidelity

- **Measures:** Structural soul presence — "is this a legitimate agent with a defined identity, or a skeleton placeholder?"
- **Scoring rule:** Binary gate: `IDENTITY.md exists AND size > 0` → `1.0`; otherwise → `0.0`.
- **Effect:** When `fidelity = 0.0`, skeleton agent contributes zero merit weight to DebateSynthesizer and cannot dominate consensus. This satisfies the SC's `weight_multiplier=0.0` requirement.
- **Phase 17–18 evolution path:** Phase 17 (Agent Church) adds structural section checks; Phase 18 (Theory of Mind) adds semantic persona adherence. Do NOT attempt LLM-judged or keyword-pattern Fidelity in Phase 16 — that belongs to Phase 18.

### EMA Architecture

- **Per-dimension EMA, then compose:** Each dimension has its own EMA history. Final composite is weighted sum.
  ```
  EMA_acc = λ * acc_t + (1-λ) * EMA_acc_prev
  EMA_rec = λ * rec_t + (1-λ) * EMA_rec_prev
  EMA_con = λ * con_t + (1-λ) * EMA_con_prev
  EMA_fid = λ * fid_t + (1-λ) * EMA_fid_prev
  merit = α·EMA_acc + β·EMA_rec + γ·EMA_con + δ·EMA_fid
  ```
- **Why per-dimension:** Each signal evolves on a different timescale (Accuracy is delayed, Recovery is cycle-local). Per-dimension allows delayed Accuracy updates without distorting the other EMAs. Composite-first EMA loses per-dimension debuggability.
- **λ (decay rate):** Configurable from `swarm_config.yaml`, default `0.9`. May use different λ per dimension in future (e.g., `λ_acc=0.05` for long horizon, `λ_rec=0.2` for fast ops feedback) — architecture must support this.
- **Cold start:** Uniform initial merit for all agents (e.g., 0.5 as per SC). Not seeded from `reliability_weight`. Clean separation between static config priors and earned merit.
- **Merit range:** `[0.1, 1.0]` as per SC (floor ensures no agent is fully silenced beyond skeleton detection).

### EMA Update Trigger and Timing

- **In-cycle EMA update:** Fires after `execution_result` is written, in a new `merit_updater` node placed after `decision_card_writer`.
- **Dimensions updated in-cycle:** Recovery, Consensus, Fidelity (signals materially available at execution boundary).
- **Accuracy:** NOT updated in-cycle. Updated async when trade resolves (separate deferred path).
- **Aborted cycles (no `execution_result`):** No KAMI update. Aborts are logged as operational telemetry (separate from merit EMA). "No `execution_result` → no KAMI update."
- **Update frequency:** Once per completed evaluable cycle (never per debate message, never per intermediate node).
- **Valid evaluable cycle requires:** cycle reached execution, `execution_result` is a persisted terminal outcome, and Recovery/Consensus/Fidelity signals are materially available.

### DebateSynthesizer Rewiring

- **Character-length proxy removed entirely.** `len(text)` no longer used as `bullish_strength` or `bearish_strength`. Length is not multiplied by merit — that would smuggle the old proxy back in.
- **New formula:**
  ```
  weighted_consensus_score = merit[bullish_agent] / (merit[bullish_agent] + merit[bearish_agent])
  ```
  Generalised: `sum(merit of bullish agents) / (sum(merit of bullish agents) + sum(merit of bearish agents))`
- **Cold start fallback:** If both sides have zero or missing merit → `weighted_consensus_score = 0.5` (neutral).
- **Merit key:** Soul handles — `AXIOM`, `MOMENTUM`, `CASSANDRA`, `SIGMA`, `GUARDIAN`. Natural join with `state["active_persona"]`. Lookup: `state["merit_scores"].get(state["active_persona"], DEFAULT_MERIT)`.
- **Merit load point:** Session start — merit_loader node (or orchestrator setup step) reads `agent_merit_scores` PostgreSQL table once per session and writes into `SwarmState["merit_scores"]`. DebateSynthesizer only reads from state; no DB calls at synthesis time.

### merit_scores in SwarmState

- **New field:** `merit_scores: Dict[str, Any]` — keyed by soul handle. Value is either a composite float or a dict of dimension EMAs + composite.
- **Recommended storage structure per agent:**
  ```python
  merit_scores = {
      "AXIOM": {"accuracy": 0.71, "recovery": 0.94, "consensus": 0.63, "fidelity": 1.0, "composite": 0.79},
      "MOMENTUM": {...},
      ...
  }
  ```
  Or simplified to composite-only if planner decides: `merit_scores = {"AXIOM": 0.79, ...}` with per-dimension values persisted to DB only.
- **Audit inclusion:** `merit_scores` is **included in the MiFID II audit hash** — NOT in `AUDIT_EXCLUDED_FIELDS`. Merit scores are quantitative decision context (they influence debate weighting), not identity narrative. Canonicalize with `round(score, 4)` before hashing to prevent float jitter.
- **Contrast with soul fields:** `system_prompt` and `active_persona` are excluded because they are narrative/prose. `merit_scores` are numeric operational state — they must be hash-anchored.

### PostgreSQL Persistence

- **Table:** `agent_merit_scores` (new table, created in `setup_persistence()`).
- **Persistence pattern:** Follows existing `psycopg`/`AsyncConnectionPool` pattern from `src/core/db.py` and `src/core/persistence.py`.
- **Write:** After each in-cycle EMA update (in `merit_updater` node), persist updated scores to DB.
- **Read:** At session start (merit_loader), read from DB into `SwarmState["merit_scores"]`.
- **SC requirement:** "the value loaded at session start matches the last persisted value" — write-then-read idempotency.

### reliability_weight Disposition

- **Preserved as a separate concern.** Not removed, not merged with KAMI.
- **Documented distinction in `swarm_config.yaml`:**
  - `reliability_weight` = static orchestration prior (routing hint, budget allocation, tie-break fallback). Used by L1 orchestrator/scheduler, NOT by DebateSynthesizer.
  - `merit_scores` (KAMI) = dynamic earned merit. Owned by KAMI. Read by DebateSynthesizer.
- **DebateSynthesizer reads KAMI only.** `reliability_weight` has no role in debate weighting post-Phase 16.
- **Future:** After several phases of KAMI operation, decide whether to deprecate `reliability_weight` or keep permanently as a static safety floor. Not a Phase 16 decision.

### Claude's Discretion

- Exact `swarm_config.yaml` schema for KAMI weights (α, β, γ, δ) and λ values
- `agent_merit_scores` table schema (columns, indexes)
- Whether per-dimension EMA values are persisted to DB as separate columns or as a JSONB blob
- `SwarmState["merit_scores"]` internal structure (flat composite float vs. nested dimension dict)
- How Consensus dimension signal is computed from `debate_resolution` in practice (confidence delta proxy implementation)
- Exact error classification logic for Recovery blame attribution (producer provenance tagging mechanism)
- Whether `merit_updater` is a LangGraph node or a post-node hook
- How deferred Accuracy updates are triggered (async task, next-session reconciliation, or explicit resolution event)

</decisions>

<specifics>
## Specific Ideas

- **Two-stage merit model:** In-cycle EMA updates Recovery/Consensus/Fidelity immediately at execution boundary. Accuracy updates async when trade resolves. This is the correct architecture because "hard to observe" is evidence of signal quality, not a flaw.
- **Soul handle as merit key:** `state["merit_scores"].get(state["active_persona"], DEFAULT_MERIT)` — natural join with Phase 15's identity layer. Merit attached to identity, not to node execution machinery.
- **CASSANDRA protection:** Consensus dimension explicitly rewards convergence contribution, not directional agreement. A contrarian who surface genuine risk and shifts confidence appropriately scores positively. This prevents KAMI from creating a sycophancy incentive.
- **EMA gives bounce-back implicitly:** No streak detection needed. EMA naturally captures recovery dynamics: `clean clean error clean clean` → `1.0 1.0 drop climb climb`.
- **Thesis record at debate time:** `{soul_handle, decision_id, instrument, direction, timestamp}` — emitted by each agent during debate. KAMI joins to resolution event later. Enables delayed Accuracy without losing provenance.
- **merit_scores in audit hash, not excluded:** Numeric decision context must be hash-anchored for MiFID forensic replay. Two runs with same state hash but different merit scores would produce different behavior — that violates auditability.
- **`reliability_weight` stays:** "Prove what KAMI measures before deciding whether config-level reliability becomes redundant." Mirrors the Phase 15 principle: "clear only the caches that actually exist in the current phase."

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets

- `src/graph/debate.py:DebateSynthesizer` — pure aggregation node, no LLM calls. Currently uses `len(bullish_text)` as strength proxy. The character-length calculation is the surgical replacement point. Interface is stable (`SwarmState → dict`).
- `src/core/db.py` + `src/core/persistence.py` — `AsyncConnectionPool`, `psycopg`, `setup_persistence()` with `CREATE TABLE IF NOT EXISTS` pattern. Exact pattern to follow for `agent_merit_scores` table creation.
- `src/core/audit_logger.py` — `AUDIT_EXCLUDED_FIELDS` frozenset and `_strip_excluded()` pattern. `merit_scores` must NOT be added here — it goes in the hash, not excluded.
- `src/core/soul_loader.py` — `load_soul(agent_id)` for Fidelity check: call `load_soul(agent_id)` and check `AgentSoul.identity` is non-empty; OR simpler: `Path(soul_dir / "IDENTITY.md").stat().st_size > 0`.
- `src/graph/nodes/write_research_memory.py` — example of a lightweight post-execution node. Pattern for `merit_updater` node (pure Python, no LLM, reads SwarmState, writes to DB + state).
- `config/swarm_config.yaml` — existing `reliability_weight` fields. Add KAMI weights (α, β, γ, δ) and λ to same config under a new `kami:` section.

### Established Patterns

- `operator.add` Annotated reducers in SwarmState: `merit_scores` must be a plain `Dict` field (no reducer) — same pattern as `macro_report`, `risk_approved`. Not a list; no accumulation.
- Phase 15 soul identity: `state["active_persona"]` (soul handle string) is already in SwarmState. Merit key lookup is `merit_scores[active_persona]`.
- LangGraph node ordering: `decision_card_writer` is currently the terminal node post-execution. `merit_updater` goes after it.
- Phase 11: `decision_card_status`, `decision_card_error`, `decision_card_audit_ref` pattern for node outcome fields — follow same pattern for any merit update status fields.
- Lazy init pattern from Phase 15: if KAMI module has any module-level state, apply lazy init. `merit_updater` is pure Python (no LLM) so lazy init likely not needed.

### Integration Points

- `src/graph/state.py:SwarmState` — add `merit_scores: Optional[Dict[str, Any]]` as a plain TypedDict field (no Annotated reducer).
- `src/graph/debate.py:DebateSynthesizer` — replace `len(bullish_text)` with `state["merit_scores"].get(active_persona_bullish, DEFAULT_MERIT)`. Replace `len(bearish_text)` equivalently.
- `src/graph/orchestrator.py` — add `merit_loader` node at session start (pre-DebateSynthesizer); add `merit_updater` node after `decision_card_writer`.
- `src/core/persistence.py:setup_persistence()` — add `CREATE TABLE IF NOT EXISTS agent_merit_scores` block.
- `config/swarm_config.yaml` — add `kami:` section with α, β, γ, δ weights and λ decay rate.
- `src/core/audit_logger.py` — **no changes needed for AUDIT_EXCLUDED_FIELDS**. `merit_scores` stays in the hash.

</code_context>

<deferred>
## Deferred Ideas

- **Semantic Fidelity (LLM-judged persona adherence):** Measuring whether agent output matches its soul archetype requires soul-sync infrastructure. Deferred to Phase 18 (Theory of Mind Soul-Sync).
- **Per-dimension λ (different decay rates per dimension):** Architecture should support this, but Phase 16 can start with uniform λ. Phase 17+ can tune independently.
- **Adaptive KAMI weights (α/β/γ/δ):** Dynamic weight adjustment based on market regime or meta-learning. Future phase.
- **`reliability_weight` deprecation:** Whether to remove `reliability_weight` from `swarm_config.yaml` once KAMI has proven itself over several phases. Not a Phase 16 decision.
- **Accuracy resolution event infrastructure:** Linking trade resolution to thesis records at scale. Phase 16 establishes the thesis record format and deferred update path; robust resolution-event infrastructure may need its own phase.
- **Merit dashboard / observability UI:** Displaying per-agent, per-dimension merit history. Future phase.

</deferred>

---

*Phase: 16-kami-merit-index*
*Context gathered: 2026-03-08*
