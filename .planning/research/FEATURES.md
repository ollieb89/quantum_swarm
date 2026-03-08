# Feature Research — MBS Persona System (v1.3)

**Domain:** Multi-agent LLM persona persistence, merit-based reward, and drift auditing for a financial analysis swarm
**Researched:** 2026-03-08
**Confidence:** HIGH (primary sources: persona_plan.md, SOT_PERSONA_REWARD_SYSTEM.md, 4 claudedocs research files, live codebase inspection)

---

## Context: What Already Exists (v1.2 baseline)

These components in the live codebase directly shape what needs to be built:

- `DebateSynthesizer` (`src/graph/debate.py`) uses **character-length proxy** for `weighted_consensus_score` — a verbose wrong agent outweighs a terse correct one. No agent quality signal exists.
- `SwarmState` (`src/graph/state.py`) has no `merit_scores`, `active_persona`, `system_prompt`, or persona-related fields.
- L2 nodes (`macro_analyst_node`, `quant_modeler_node`, `BullishResearcher`, `BearishResearcher`) are stateless ReAct nodes with identical prompt structure. No persistent identity.
- `MEMORY.md` is referenced in claudedocs but no per-agent file is created or written to by any node.
- `src/core/souls/` directory does not exist. `SoulLoader` is specified in `persona_plan.md` but not implemented.
- `backtest_result`, `debate_history`, and `execution_result` are already in SwarmState — these are the observable signal sources for KAMI dimensions.

All features below are net-new additions for v1.3.

---

## Feature Landscape

### Table Stakes (Tier 1 — Foundation Must Exist Before Tier 2)

These features are prerequisites. KAMI weighting, ToM handshakes, and ARS auditing all have nothing to anchor to without them.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **SoulLoader with `lru_cache`** | Every downstream feature reads soul files; caching prevents repeated disk I/O on every graph invocation. LangGraph fan-out means multiple L2 nodes may call `load_soul()` concurrently | LOW | Path-traversal guard (reject `..`, `/`, `\` in `agent_id`) is a security requirement — exploitable without it. `warmup_soul_cache()` at graph init ensures cache is hot before any parallel node reads it |
| **5-file soul directory per agent** (SOUL.md, IDENTITY.md, AGENTS.md, USER.md, MEMORY.md) | The 5-file split separates alignment (governance layer) from workflow (operational layer) from peer modelling (ToM layer). Merging them collapses the governance boundary that Agent Church needs to know what it is approving | MEDIUM | Only `macro_analyst` needs populated content in Tier 1. Other 4 agents are skeleton dirs with empty files. Token budget: SOUL+IDENTITY+AGENTS combined < 500 tokens to stay within efficient context injection |
| **`AgentSoul` dataclass (frozen=True, immutable)** | Soul identity must not mutate during a graph run. LangGraph fan-out means multiple nodes may read the same `AgentSoul` concurrently. Mutability would create race conditions | LOW | `system_prompt_injection` property composes IDENTITY+SOUL+AGENTS. `user_model_context` property is separate and only consumed by ToM handshake, not the system prompt |
| **SwarmState fields: `active_persona`, `system_prompt`** | Without state fields, no downstream node can read which persona is active or what system prompt was injected. Cannot audit, cannot route, cannot weight | LOW | `system_prompt` goes in SwarmState fields, NOT in `messages`. The `messages` field uses `operator.add` reducer — putting system prompts there causes unbounded accumulation across nodes. Inject at LLM call time as `{"role": "system", "content": state["system_prompt"]}` |
| **`macro_analyst_node` soul injection** | Reference implementation of the injection pattern. All other agents copy this pattern. Also the anchor for the test suite | LOW | Sets `active_persona` and `system_prompt` in returned state dict before LLM call. Test suite validates this without any LLM call |
| **Drift Guard embedded in `IDENTITY.md`** | BIG5-CHAT (ACL 2025) confirms prompt-only persona induction produces surface-level traits that drift under task load. In-prompt Drift Guard is the cheapest mitigation that runs inside the model's reasoning loop where drift actually occurs | LOW | Per-agent Drift Guard tailored to each agent's specific failure mode: macro_analyst = resist definitiveness and consensus capitulation; bearish_researcher = resist optimism pressure; bullish_researcher = resist pessimism pressure; risk_manager = never yield on compliance flags |
| **Deterministic test suite (no LLM calls)** | Persona loading, injection, and state wiring must be verifiable in CI without API keys. Tests: load/cache/path-traversal/system-prompt-composition/node-integration | LOW | String assertions against static soul files only. Four categories: unit (SoulLoader), content (persona fidelity), determinism (stable across calls), integration (node returns correct state fields) |

### Differentiators (Tier 2 — Features That Make the System Novel)

#### Tier 2a — KAMI Merit Index

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Multi-dimensional merit formula** `Merit = α·Accuracy + β·Recovery + γ·Consensus + δ·Fidelity` | Single-scalar rewards collapse in multi-agent settings (EMNLP 2025, UCL MARL research). Four orthogonal dimensions capture signal that a single number hides: an agent can be accurate but poor at recovery, or high-fidelity but consistently wrong on direction | MEDIUM | Default weights: α=0.30 (Accuracy), β=0.35 (Recovery — highest signal per literature), γ=0.25 (Consensus), δ=0.10 (Fidelity). All configurable. Weights sum to 1.0 |
| **EMA decay with configurable λ** `Merit(t) = λ·Merit(t-1) + (1-λ)·NewSignal(t)` | Prevents single-session gaming. Recent performance matters more than historical baseline. Without decay, an agent that did well 50 sessions ago still benefits from that legacy score | LOW | λ=0.9 recommended for financial domain (slow decay; regime changes are infrequent). Cold start: Merit=0.5 for new agents (neutral, avoids "punishment for being new"). Bounds: Merit ∈ [0.1, 1.0] — floor prevents permanent demotion; ceiling prevents "god-agent" concentration risk |
| **KAMI scores wired to `DebateSynthesizer` consensus weighting** | Current `DebateSynthesizer` uses character-length as a quality proxy. Replacing it with merit-weighted scoring makes the consensus system reflect actual agent reliability | HIGH | This is a breaking change to `src/graph/debate.py`. Requires `merit_scores: Dict[str, float]` in SwarmState before this change is safe. Weight formula: `weight = merit_scores.get(agent_id, 0.5)` multiplied by raw signal strength |
| **KAMI scores stored in SwarmState and persisted to PostgreSQL** | Merit scores are only useful if they survive across sessions. In-memory only means cold start (Merit=0.5) on every graph initialization, eliminating the learning effect | MEDIUM | `merit_scores: Dict[str, float]` added to SwarmState. Persist to PostgreSQL at session end via dedicated KAMI writer node or extended `write_trade_memory_node`. Load at graph init if available |

**Observable KAMI signal sources — tied to existing v1.2 swarm events, not hypothetical:**

| Dimension | Observable Event | Signal Computation |
|-----------|-----------------|-------------------|
| **Accuracy** | `backtest_result` in SwarmState contains Sharpe ratio, win rate per strategy. Agent's directional signal (bullish/bearish) is in `debate_history[source]` | When agent's side matches final trade direction AND backtest outcome is positive: `accuracy_delta = +1`. Mismatch: `-1`. EMA-decayed |
| **Recovery** | ReAct tool errors are observable within node invocations. A node that produces tool error then a corrected non-error output has recovered | `+1` if tool error occurs AND same node invocation produces valid final output. `0` if node terminates on error without recovery |
| **Consensus** | `debate_resolution["hypothesis"]` and `weighted_consensus_score` already record which side won | BullishResearcher: `+1` if `weighted_consensus_score > 0.5`. BearishResearcher: `+1` if `< 0.5`. Losing side: `-1` |
| **Fidelity** | `AGENTS.md` output contract specifies required fields per agent (e.g., macro_analyst requires `confidence_level`, `key_risks`, `what_would_change_my_mind`) | Check `state["macro_report"]` for required fields after node returns. `+1` all present, `-1` any missing |

All four signals are computable without LLM evaluation, post-hoc, from existing SwarmState fields. No new data sources required.

**Note on KAMI naming:** The real Kamiwaza Agentic Merit Index (arxiv:2511.08042) is a model-selection benchmark for enterprise agentic tasks, not a per-agent runtime merit tracker. The project docs use "KAMI" as internal shorthand. Acceptable for a private system. The underlying mechanism (multi-dimensional EMA-decayed merit with cold start and bounds) is valid regardless of naming.

#### Tier 2b — MEMORY.md Per-Agent Evolution

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Per-agent `MEMORY.md` updated after each task cycle** | Agents accumulate evidence of what works for their specific persona — not shared swarm memory but per-persona learning signal. Also the data source for ARS drift detection in Tier 2d | MEDIUM | Append-only log. Each entry: task_id, timestamp, KAMI delta per dimension, self-reflection text, structured machine-readable markers. Cap at last 50 entries to bound file growth |
| **Self-reflection LLM generation + MEMORY.md append** | Reflexion (2023) — the direct basis for Self-Evolve — shows that prompting an agent to articulate why it succeeded or failed produces better subsequent performance than reward signal alone | MEDIUM | LLM-generated text appended to MEMORY.md post-task. Must not block the graph's critical path — write async or in a dedicated post-hoc node that does not gate execution |
| **SOUL.md diff proposals in MEMORY.md with Agent Church approval gate** | Prevents unchecked persona mutation. An agent "learning" to be more aggressive after winning debates must have that proposal reviewed. Without governance, persona drift accelerates | HIGH | Diff proposal format: structured block in MEMORY.md with `## SOUL.md DIFF PROPOSAL [STATUS: pending] [SECTION: essence|alignment|heartbeat]`. Agent Church (L1 Orchestrator adds a governance routing path) reads pending proposals, approves or rejects with reason. Approved: patch applied to SOUL.md + `load_soul.cache_clear()`. Rejected: logged with reason, no file mutation |

#### Tier 2c — Theory of Mind Soul-Sync Handshake

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Soul-Sync Handshake before debate** | Agents that know their opponent's priors produce better-targeted refutations. Without this, debate degenerates into parallel monologue where each side restates its position without engaging the other's reasoning framework | MEDIUM | Truncated SOUL.md summary exchange — see truncation approach below. Prepended to the debate message context, not a separate LangGraph node |
| **Empathetic Refutation pattern** | Forces agents to address the persona logic behind a claim rather than the claim alone. Reduces deadlock ("this is wrong" → "as a skeptical quant, you are over-weighting the outlier, but macro trend data shows...") | MEDIUM | Implemented as few-shot examples in BullishResearcher and BearishResearcher system prompts. Low implementation cost once the Soul-Sync summary is available |

**Truncation approach for SOUL.md summaries without losing identity signal:**

The identity-relevant content in SOUL.md concentrates in three elements: (1) the persona archetype label ("The Macro Sentinel"), (2) 2-3 distinctive values that explain why this agent argues the way it does ("Intellectual honesty before consensus comfort"), and (3) the agent's current merit score as a proxy for how much weight to grant their epistemic priors.

Everything else — linguistic habits, workflow rules, output contract fields, data staleness rules — is implementation detail that is irrelevant to debate dynamics. The opponent does not need to know that the macro_analyst flags data older than 48h as STALE; they need to know this agent prioritizes intellectual honesty and argues probabilistically.

Truncation format (deterministic, no LLM summarization needed, cache-safe, ~80-100 tokens):

```
Opponent: {persona_name} | Role: {role} | Values: {top_2_values} | Merit: {score:.2f}
```

Example: `Opponent: The Macro Sentinel | Role: Global Macro Analyst | Values: Signal over noise, Intellectual honesty before consensus comfort | Merit: 0.72`

This is constructable directly from `AgentSoul.identity` (persona name, role) and `AgentSoul.soul` (values), plus the current `merit_scores[agent_id]` from SwarmState.

#### Tier 2d — ARS Drift Auditor

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **ARS Auditor computes drift score from MEMORY.md evolution logs** | Detects when an agent's proposed SOUL.md diffs and self-reflection logs are diverging from the original persona definition — "ego hijacking" or gradual persona corruption | MEDIUM | Pure file processing — no LLM evaluation required. Five observable metrics from structured MEMORY.md log entries (detailed below) |
| **Agents exceeding ARS drift threshold flagged; ops alert + evolution suspended** | Prevents runaway self-modification. A bearish agent that consistently proposes "become more open to upside scenarios" diffs is drifting toward the bullish agent's role — a structural risk to debate validity and adversarial diversity | MEDIUM | Drift threshold: configurable float, default 0.3. Suspension: `evolution_suspended: True` flag in MEMORY.md header block. Ops alert: log at ERROR level and append to `data/audit.jsonl` (already exists in the v1.2 audit chain) |

**Observable drift metrics from MEMORY.md without LLM evaluation:**

Requires structured machine-readable markers in each MEMORY.md entry:

```
[KAMI_DELTA: +0.03] [DIM: accuracy=+0.05,recovery=-0.02,consensus=+0.03,fidelity=+0.01]
[REFLECTION]: Agent correctly identified inflation data as STALE before synthesis.
```

And for diff proposals:

```
## SOUL.md DIFF PROPOSAL [STATUS: pending|approved|rejected] [SECTION: essence|alignment|heartbeat]
[REASON_IF_REJECTED]: Proposal would expand macro_analyst scope into quant domain.
```

With these markers, all five drift metrics are pure text processing:

| Metric | What it Measures | Computation |
|--------|-----------------|-------------|
| **Diff Rejection Rate** | Fraction of SOUL.md proposals rejected — high rejection rate signals repeated out-of-bounds evolution attempts | `count(STATUS: rejected) / count(total proposals)` over last 20 cycles |
| **KAMI Dimension Variance** | Whether one dimension is consistently trending opposite to others — signals gaming a specific metric | `std_dev` across dimension deltas in `[DIM: ...]` markers over last 20 cycles |
| **Persona Section Mutation Count** | How many approved diffs touch the Alignment section — Alignment is the governance-protected layer | `count(STATUS: approved AND SECTION: alignment)` over last 50 entries |
| **Self-Reflection Sentiment Shift** | Whether the agent's self-narrative is shifting from failure-acknowledgement to persistent success framing | Ratio of `[KAMI_DELTA: +` to `[KAMI_DELTA: -` in last 20 entries; flag if ratio > 4:1 (suspiciously positive) |
| **Role Boundary Vocabulary** | Agent's reflections mentioning another agent's domain vocabulary — signals identity bleed | Regex match on configurable per-agent cross-domain vocabulary list in `[REFLECTION]` lines (e.g., bearish_researcher matching "macro trend", "inflation regime") |

Drift score: configurable weighted sum of normalized metrics. Default threshold 0.3. All computable in under 100ms via Python file read + regex + arithmetic.

---

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **LLM-as-Judge for ARS drift detection** | Seems more nuanced than keyword counting | Creates LLM-on-LLM circular evaluation. The judge and the agents likely share the same base model, creating systematic blind spots. Adds latency and API cost to what should be a lightweight background audit. If the judge LLM drifts in the same direction as the agent, it will fail to detect the drift it is supposed to catch | Five observable keyword and count metrics (above) are deterministic, zero-cost, and run without API calls. Flag for human review when drift score exceeds threshold |
| **Emotional state model (valence/arousal, HMM-based)** | arXiv:2511.20657 survey shows affective state affects output quality; "frustrated" agent should hedge more | Full HMM-based emotional state requires per-invocation intra-session state transitions that must survive fan-out, is non-deterministic to test, and is not tied to any existing observable event in the swarm. claudedocs deep-dive (research_soul_rewards_deep_dive) identifies this as a gap but explicitly defers it | The Fidelity dimension of KAMI captures output quality degradation implicitly (required fields missing when agent is "struggling"). Defer emotional state to v2.0 |
| **Fine-tuning for persona enforcement** | Fine-tuning would embed personas at the weight level, surviving context window turnover | Training cost is infeasible with Gemini Flash managed API. Requires custom model serving infrastructure not in scope for v1.3 | Drift Guard in IDENTITY.md + few-shot examples as persona-reset mechanism when Fidelity KAMI drops below 0.4. This is the practical ceiling for prompt-only persona enforcement per BIG5-CHAT (ACL 2025) |
| **Global SOUL.md (one shared swarm identity)** | Simplifies file management; one persona file to maintain | Collapses adversarial diversity. If BullishResearcher and BearishResearcher share the same SOUL.md values, their debate degenerates into an echo chamber. The adversarial debate architecture exists precisely to force tension between opposing priors | Per-agent soul directories. Enforce HEXACO-6 personality diversity: BullishResearcher and BearishResearcher must have opposing trait profiles on at least 3 of 6 HEXACO dimensions (documented in IDENTITY.md HEXACO-6 Profile section) |
| **`merit_scores` stored in `messages` list** | Seems like a natural inter-node data passing mechanism | `messages` uses `operator.add` reducer — any dict appended to messages accumulates unboundedly across graph runs. This is the same problem that motivated keeping `system_prompt` out of messages (confirmed in persona_plan.md §5) | Dedicated `merit_scores: Dict[str, float]` field in SwarmState with standard dict last-write-wins reducer |
| **Real-time SOUL.md mutation mid-graph-run** | Agent "learns" during a single graph execution and updates its persona immediately | LangGraph fan-out means multiple nodes may be reading the same soul concurrently from the `lru_cache`. Mutating soul files mid-run creates cache inconsistency and potential read/write race conditions. The `frozen=True` `AgentSoul` dataclass exists specifically to prevent in-run mutation | All SOUL.md mutations happen post-run via Agent Church approval gate. `load_soul.cache_clear()` called between runs, never within a run |
| **SoulZip relational history in Tier 1** | claudedocs recommends SoulZip for shared relational peer context | SoulZip relational history requires cross-session memory of peer interactions — it depends on MEMORY.md evolution logs which are Tier 2b. Building SoulZip without the log has no data to populate it from; the USER.md files would be empty placeholders that add context window cost without value | USER.md files created as empty skeletons in Tier 1. SoulZip content is populated in Tier 2b+ once MEMORY.md logs have accumulated peer-interaction evidence |

---

## Feature Dependencies

```
[SoulLoader + AgentSoul frozen dataclass]
    └──required-by──> [SwarmState: active_persona, system_prompt fields]
    └──required-by──> [macro_analyst_node soul injection]
    └──required-by──> [Soul-Sync Handshake: reads AgentSoul.identity + AgentSoul.soul]
    └──required-by──> [KAMI Fidelity dimension: reads AGENTS.md output contract via AgentSoul.agents]

[5-file soul directories (all 5 agents)]
    └──required-by──> [SoulLoader.load_soul() + warmup_soul_cache()]
    └──required-by──> [MEMORY.md per-agent evolution log (Tier 2b)]
    └──required-by──> [ARS Auditor: reads MEMORY.md from soul dir (Tier 2d)]

[SwarmState: active_persona, system_prompt]
    └──required-by──> [LLM call pattern: system message injection]
    └──required-by──> [deterministic test suite: validates state field presence]

[KAMI multi-dimensional formula + EMA decay]
    └──required-by──> [SwarmState: merit_scores: Dict[str, float]]

[SwarmState: merit_scores]
    └──required-by──> [DebateSynthesizer KAMI-weighted consensus (breaking change)]
    └──required-by──> [Soul-Sync Handshake truncated summary: includes Merit score]
    └──required-by──> [PostgreSQL merit persistence]

[Observable swarm events: backtest_result, tool errors, debate_history]
    └──feeds──> [KAMI: Accuracy, Recovery, Consensus dimension signals]

[AGENTS.md output contract fields in soul dir]
    └──feeds──> [KAMI: Fidelity dimension signal]

[MEMORY.md per-agent structured log]
    └──required-by──> [Self-reflection append (Tier 2b)]
    └──required-by──> [SOUL.md diff proposals (Tier 2b)]
    └──required-by──> [ARS Auditor: all 5 drift metrics (Tier 2d)]

[SOUL.md diff proposals in MEMORY.md]
    └──required-by──> [Agent Church approval gate (Tier 2b)]

[Agent Church approval gate]
    └──required-by──> [SOUL.md patch application]
    └──required-by──> [load_soul.cache_clear() to invalidate stale cache after diff]
    └──required-by──> [ARS Auditor: rejection count metric (Tier 2d)]

[Soul-Sync Handshake: truncated summary exchange]
    └──depends-on──> [SoulLoader (AgentSoul.identity + AgentSoul.soul)]
    └──depends-on──> [SwarmState merit_scores]
    └──enhances──> [Empathetic Refutation few-shot pattern]
    └──feeds-into──> [DebateSynthesizer (via improved debate message content)]

[ARS Auditor]
    └──depends-on──> [MEMORY.md with structured markers ([KAMI_DELTA:], [DIM:], [REFLECTION], DIFF PROPOSAL blocks)]
    └──depends-on──> [Agent Church rejection log entries in MEMORY.md]
    └──produces──> [ops alert at ERROR log level + data/audit.jsonl event]
```

### Dependency Notes

- **SoulLoader is the foundation of everything in Tier 2.** Nothing in Tier 2 is implementable until Tier 1 is complete and the test suite is green.
- **`merit_scores` in SwarmState must exist before DebateSynthesizer is rewired.** Changing the synthesizer without a populated `merit_scores` field would produce KeyError at runtime.
- **DebateSynthesizer rewiring is the highest-risk change in the milestone.** It modifies a node that currently has passing tests. Run existing synthesizer test suite after the change to confirm no regressions.
- **ARS Auditor depends on MEMORY.md log structure quality.** If entries don't use the structured markers, drift metrics degrade to noise. The marker format must be enforced in the MEMORY.md append function (Tier 2b) as a prerequisite for Tier 2d being reliable.
- **Agent Church is the L1 Orchestrator in a new role.** No new agent class is needed. The existing L1 intent classifier gains a `soul_governance` routing path that handles pending proposals. Scope carefully to avoid bloating L1 with governance logic that should live in a dedicated utility function.
- **`load_soul.cache_clear()` after approved diff is easy to miss.** If omitted, the next graph run reads the old soul from cache even after the SOUL.md file has been patched. Document as a required step in the Agent Church approval function, not a best-effort cleanup.

---

## MVP Definition

### Launch With (Tier 1 — v1.3.0)

Minimum viable persona system. Validates the architecture. Required before any Tier 2 work.

- [ ] `SoulLoader` with `lru_cache`, path-traversal guard, `AgentSoul` frozen dataclass — SOUL-01
- [ ] `macro_analyst` persona files (IDENTITY.md, SOUL.md, AGENTS.md) with Drift Guard — SOUL-02
- [ ] 4 skeleton soul dirs (bullish_researcher, bearish_researcher, quant_modeler, risk_manager) with empty files — SOUL-03
- [ ] SwarmState: `active_persona` and `system_prompt` fields — SOUL-04
- [ ] `macro_analyst_node` injects soul before LLM execution — SOUL-05
- [ ] `warmup_soul_cache()` at graph creation — SOUL-06
- [ ] Deterministic test suite, no LLM calls — SOUL-07

### Add After Tier 1 Validation (Tier 2a — v1.3.1)

Once Tier 1 tests pass and soul injection is confirmed working in graph runs.

- [ ] KAMI merit formula + EMA decay + cold start 0.5 + bounds [0.1, 1.0] — KAMI-01, KAMI-02
- [ ] `merit_scores: Dict[str, float]` added to SwarmState — KAMI-04 (prerequisite, must land before KAMI-03)
- [ ] DebateSynthesizer KAMI-weighted consensus — KAMI-03 (breaking change; land after KAMI-04)
- [ ] PostgreSQL persistence for merit scores — KAMI-04

### Add After Merit Validation (Tier 2b-2d — v1.3.2+)

Once KAMI scores are accumulating and DebateSynthesizer weighting is confirmed working.

- [ ] Per-agent MEMORY.md structured log append (post-task, async, capped at 50 entries) — EVOL-01
- [ ] Self-reflection LLM generation + MEMORY.md append — EVOL-01
- [ ] SOUL.md diff proposal format + Agent Church approval gate + cache invalidation — EVOL-02, EVOL-03
- [ ] Soul-Sync Handshake: deterministic truncated summary exchange before debate — TOM-01
- [ ] Empathetic Refutation few-shot examples in researcher system prompts — TOM-02
- [ ] ARS Auditor: 5 observable drift metrics from MEMORY.md, threshold alerting — ARS-01, ARS-02

### Future Consideration (v2+)

- [ ] Emotional state model (valence/arousal, HMM-based intra-session) — deferred; no existing observable event hooks
- [ ] SoulZip relational history in USER.md — deferred; requires accumulated MEMORY.md cross-session peer data
- [ ] PersonaScore 5D periodic evaluation (LLM-as-Judge fidelity measurement) — deferred; cost vs. benefit decision needed
- [ ] HEXACO-6 diversity enforcement gate (automated check that Bull/Bear have opposing trait profiles) — deferred until all 4 researcher personas are fully populated

---

## Feature Prioritization Matrix

| Feature | Swarm Value | Implementation Cost | Priority |
|---------|-------------|---------------------|----------|
| SoulLoader + AgentSoul dataclass | HIGH — all Tier 2 blocked | LOW | P1 |
| `macro_analyst` persona files | HIGH — reference + test anchor | LOW | P1 |
| Skeleton soul dirs (4 agents) | HIGH — `warmup_soul_cache()` requires them | LOW | P1 |
| SwarmState: `active_persona`, `system_prompt` | HIGH — prerequisite for node integration | LOW | P1 |
| `macro_analyst_node` soul injection | HIGH — validates full chain | LOW | P1 |
| Drift Guard in IDENTITY.md | HIGH — cheapest persona stability | LOW | P1 |
| Deterministic test suite | HIGH — CI gate, no API key | LOW | P1 |
| KAMI multi-dimensional formula | HIGH — replaces character-length proxy | MEDIUM | P1 |
| EMA decay + cold start + bounds | HIGH — prevents single-session gaming | LOW | P1 |
| `merit_scores` in SwarmState | HIGH — prerequisite for synthesizer rewiring | LOW | P1 |
| DebateSynthesizer KAMI rewiring | HIGH — core value proposition | HIGH (breaking change) | P1 |
| KAMI PostgreSQL persistence | MEDIUM — cross-session value | MEDIUM | P2 |
| MEMORY.md structured log append | HIGH — prerequisite for ARS | MEDIUM | P2 |
| Self-reflection LLM append | MEDIUM — improves future performance | MEDIUM | P2 |
| SOUL.md diff + Agent Church gate | HIGH — governance safety | HIGH | P2 |
| Soul-Sync Handshake | MEDIUM — improves debate quality | MEDIUM | P2 |
| Empathetic Refutation few-shot | MEDIUM — reduces deadlock | LOW | P2 |
| ARS Auditor (5 drift metrics) | HIGH — safety, detects ego-hijacking | MEDIUM | P2 |
| Emotional state model | LOW — v2.0 | HIGH | P3 |
| SoulZip relational history | LOW — no data until MEMORY.md accumulates | MEDIUM | P3 |
| PersonaScore 5D LLM-as-Judge | LOW — cost unclear | HIGH | P3 |

---

## Persona File Loading: Expected Behavior and Edge Cases in LangGraph

### Expected Behavior

`load_soul()` is called at the start of each L2 node invocation. Because LangGraph fans out L2 nodes in parallel (macro_analyst and quant_modeler may run concurrently), `lru_cache` must be safe for concurrent reads. Python's `lru_cache` on CPython is GIL-protected for dict reads and is safe for concurrent reads from multiple threads. Warmup via `warmup_soul_cache()` at graph init ensures all soul loads during fan-out hit the cache — no first-call disk latency in the hot path.

`system_prompt` is written to SwarmState by the node before any LLM call. The LLM call layer reads `state["system_prompt"]` and prepends it as `{"role": "system", "content": ...}` to the messages list at call time only, not stored in `messages`.

### Edge Cases

| Edge Case | Risk | Mitigation |
|-----------|------|------------|
| Soul file deleted between warmup and node invocation | `lru_cache` returns the cached copy from warmup — no error | `warmup_soul_cache()` at graph init is the primary guard. Add `try/except FileNotFoundError` in node code with fallback to empty soul string |
| `active_persona` in stale state doesn't match any current soul dir | `FileNotFoundError` on `load_soul()` if state checkpoint is from an older version | Validate `agent_id` existence before calling `load_soul()` — already in the spec (path check returns `FileNotFoundError` if dir missing) |
| Approved SOUL.md diff applied mid-session | Cache returns old soul to nodes reading after the diff was applied | Agent Church applies diffs only between sessions. Documented as operational constraint. Never trigger diff application while a graph run is in progress |
| MEMORY.md grows unbounded | Disk usage, slow ARS regex computation | Cap MEMORY.md at last 50 entries in the append function. ARS metrics only look at last N=20 entries — enforce this window at read time |
| Multiple agents propose conflicting SOUL.md diffs for the same file in one session | Agent Church receives two proposals for the same agent | Queue proposals chronologically. Process one proposal per session cycle per agent. Second proposal remains `pending` for next cycle |
| `system_prompt` from different agents appears to conflict in SwarmState | fan-in after fan-out — last writer wins | `system_prompt` is intentionally last-write-wins. Each node sets its own persona when it runs. This is not a conflict — it reflects the currently active node, which is what audit needs |

---

## KAMI Measurement: Tied to Observable v1.2 Swarm Events

The four KAMI dimensions map directly to events and fields that already exist in v1.2 SwarmState. No new data sources are needed.

**Accuracy:** `backtest_result` already contains Sharpe ratio, win rate, and max drawdown per strategy. `debate_history` records which researcher argued which side. When an agent's directional signal matches the backtest outcome: `accuracy_delta = +1`. Mismatch: `-1`. EMA applied.

**Recovery:** LangGraph ReAct nodes already handle tool errors. A `Recovery` signal is observable when: (a) a tool invocation returns an error state in the ReAct loop, AND (b) the same node invocation produces a non-error final output. Add a success/error counter to the ReAct node wrapper. No new infrastructure — this is a small addition to existing agent node code.

**Consensus:** `debate_history` in `debate_resolution` already records which side produced content and the `weighted_consensus_score` records the outcome. BullishResearcher consensus_delta = `+1` if `weighted_consensus_score > 0.5` (bullish side won), `-1` if `< 0.5`. BearishResearcher is the inverse.

**Fidelity:** `AGENTS.md` specifies the output contract fields for each agent. After each node returns, the KAMI scorer checks that the returned state dict includes all required fields. For `macro_analyst`: requires `confidence_level`, `key_risks`, `what_would_change_my_mind` in `macro_report`. `fidelity_delta = +1` if all present, `-1` if any missing.

---

## Sources

| Source | What It Informs | Confidence |
|--------|----------------|-----------|
| `.planning/PHASES/persona_plan.md` | Tier 1 file architecture, SoulLoader API, LangGraph integration pattern, SwarmState fields | HIGH — project design document |
| `docs/SOT_PERSONA_REWARD_SYSTEM.md` | MBS architecture, KAMI components, ToM/ARS specification, Agent Church governance | HIGH — project source of truth |
| `claudedocs/research_soul_rewards_deep_dive_20260305.md` | KAMI naming conflict, 4-dimensional merit formula from EMNLP 2025 and UCL MARL, PersonaScore 5D, HEXACO-6 rationale, OpenClaw 5-file split | HIGH — research synthesis |
| `claudedocs/research_personas_merit_20260305.md` | Merit-based routing, ARS security requirements, adversarial RLAF approach | HIGH — research synthesis |
| `claudedocs/research_agent_persona_soul_20260305.md` | MBS architecture, SoulZip pattern, Theory of Mind, static vs dynamic vs emergent options | HIGH — research synthesis |
| `src/graph/debate.py` (live code) | Existing DebateSynthesizer: character-length scoring, `debate_history` structure, what state fields it reads/writes | HIGH — primary codebase |
| `src/graph/state.py` (live code) | Existing SwarmState fields, reducer patterns, what is currently missing | HIGH — primary codebase |
| PersonaGym (arxiv:2407.18416) | Drift Guard design, PersonaScore 5 evaluation dimensions | MEDIUM — academic paper |
| BIG5-CHAT (ACL 2025) | Prompting insufficiency for deep persona traits — Drift Guard necessity | MEDIUM — academic paper |
| EMNLP 2025 "Reward-driven Self-organizing LLM-based Multi-Agent System" | Multi-dimensional reward rationale for MARL | MEDIUM — academic paper |
| UCL RLC 2024 Trust-based Consensus MARL | Binary consensus reward formula | MEDIUM — academic paper |
| Reflexion (2023) | Self-reflection as downstream performance improver — basis for EVOL-01 | HIGH — well-established paper |
| arxiv:2511.08042 (real KAMI paper) | Confirms naming conflict with project's internal use of "KAMI" | HIGH — directly relevant |

---
*Feature research for: MBS Persona System (Tier 1 + Tier 2) — Quantum Swarm v1.3*
*Researched: 2026-03-08*
