# Feature Research

**Domain:** Observable multi-agent trading swarm (cycle replay, persona diversity, execution observability, cross-cycle comparison)
**Researched:** 2026-03-08
**Confidence:** HIGH (existing codebase well-understood, LangGraph time-travel verified against official docs, HEXACO model verified against primary source)

## Context: What Already Exists (v1.3 baseline)

These shipped components directly shape what v1.4 builds on:

- **Audit infrastructure:** `with_audit_logging` wrapper records every node's input/output to PostgreSQL `audit_logs` with SHA-256 hash chain. `DecisionCard` + `audit.jsonl` captures immutable trade artifacts with agent contributions and risk snapshots.
- **Checkpointing:** `AsyncPostgresSaver` persists LangGraph checkpoints per super-step. `get_state_history()` and `update_state()` are available but never used.
- **Per-agent MEMORY.md:** Structured entries with `[MERIT_SCORE:]`, `[KAMI_DELTA:]`, `[DRIFT_FLAGS:]`, `[CYCLE_STATUS:]`, `[THESIS_SUMMARY:]`. Capped at 50 entries. Written by `memory_writer_node`.
- **KAMI merit scores:** 4-dimension composite (Accuracy, Recovery, Consensus, Fidelity) with EMA decay, stored in SwarmState `merit_scores` and persisted to PostgreSQL `agent_merit_scores`.
- **Soul system:** SoulLoader with `lru_cache`, frozen `AgentSoul` dataclass. AXIOM fully populated. 4 skeleton personas (MOMENTUM, CASSANDRA, SIGMA, GUARDIAN) with bare IDENTITY.md and thin SOUL.md -- no `drift_guard:` YAML block, no rich prose.
- **ARS drift auditor:** 5 metrics from MEMORY.md, breach counters, `evolution_suspended` flag. Daily systemd timer.
- **Debate:** DebateSynthesizer (pure aggregation, no LLM) with KAMI merit-weighted consensus. Soul-sync handshake exchanges peer summaries before debate.
- **Agent Church:** Out-of-band standalone script for soul proposal approval/rejection.

All features below are net-new for v1.4.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that the "observable swarm beta" label implies. Missing any of these means the system is not meaningfully observable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Fully populated personas (MOMENTUM, CASSANDRA, SIGMA, GUARDIAN)** | 4 agents are skeletons with bare IDENTITY.md and thin SOUL.md but no `drift_guard:` YAML block, no rich Core Beliefs, no Archetype depth, no Non-Goals. Running real market data through skeleton personas produces shallow, undifferentiated output that makes observability uninteresting | HIGH | Authoring task, not code. Each persona needs AXIOM-quality content: rich IDENTITY.md (~300 words covering Identity, Archetype, Role in Swarm), full SOUL.md with Core Beliefs, Drift Guard (with `drift_guard:` YAML block matching AXIOM's schema), Voice, Non-Goals. AXIOM is the reference template. Existing skeleton content provides the starting scaffold |
| **End-to-end pipeline execution against real market data** | The swarm has never completed a full cycle against live data. Until it does, all observability is synthetic. This is the unlock for everything else | HIGH | Integration work: ensure DataFetcher returns real yfinance/ccxt data, PostgreSQL running on port 5433, Gemini API key set (`GOOGLE_API_KEY`), all 5 agents produce non-None canonical output. Known env issues: broken `ccxt` (crypto), missing `chromadb` -- yfinance equities path is the reliable route for first real cycle |
| **Per-cycle artifact persistence (CycleArtifact)** | Cannot replay what was not saved as a single unit. Current data is scattered: audit_logs in PostgreSQL, decision cards in `audit.jsonl`, MEMORY.md entries per agent. No single "cycle bundle" captures the full snapshot | MEDIUM | Pydantic model collecting all SwarmState fields at cycle end: agent outputs (macro_report, quant_proposal, bullish_thesis, bearish_thesis), debate resolution, consensus score, merit scores, decision card ref, drift flags, execution result, timestamps. Written to PostgreSQL `cycle_artifacts` table or JSON file per `task_id` |
| **Cycle list CLI** | Operator must see what cycles exist before replaying one | LOW | `qswarm cycles list` showing timestamp, task_id, ticker/query, consensus score, outcome. Pure read-only SQL against `cycle_artifacts` or `audit_logs` grouped by task_id. Click or argparse CLI |
| **Single-cycle detail view** | Drill into one cycle: see each node's input/output, debate text, consensus score, merit weights, risk gate decision, execution result | MEDIUM | `qswarm cycles show <task_id>` walks the node sequence in execution order and pretty-prints. Data already in `audit_logs` (input_data, output_data per node). Needs a CLI renderer with structured terminal output |
| **Step-through replay (forward walk)** | Given a cycle's `task_id`, walk through nodes in execution order showing node name, timestamp, key state mutations at each step. This is the minimum "replay" that justifies calling the system observable | MEDIUM | LangGraph already stores checkpoints per super-step via `AsyncPostgresSaver`. Use `graph.get_state_history({"configurable": {"thread_id": task_id}})` to enumerate checkpoints in reverse chrono, then display forward. `qswarm replay <task_id>` with optional `--step` flag for interactive pause-between-nodes mode. No LangGraph source changes needed -- purely a CLI consumer of existing APIs |
| **Merit weight time series** | Show how each agent's KAMI composite score evolves over time | LOW | Already stored: MEMORY.md has `[MERIT_SCORE:]` per entry per agent. `qswarm merit history` reads all 5 agent MEMORY.md files, parses entries, outputs CSV/JSON time series or formatted terminal table. Standalone -- no new dependencies |
| **Drift flag time series** | Show per-agent drift flags over time: which agents triggered recency_bias, narrative_capture, etc. | LOW | Already stored: MEMORY.md has `[DRIFT_FLAGS:]` per entry per agent. `qswarm drift history` parses and aggregates. Standalone |

### Differentiators (Competitive Advantage)

Features that make this system interesting beyond basic observability. Not required for beta launch, but high value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **HEXACO-6 persona diversity framework** | Ensures adversarial agents are genuinely cognitively diverse, not just superficially different. Maps each of the 5 agents onto distinct HEXACO-6 dimension profiles. Prevents convergent groupthink and makes debate structurally productive. Research confirms LLM agents can exhibit coherent HEXACO-aligned personality structure (arxiv:2508.00742) | MEDIUM | Authoring + lightweight validation. Define a HEXACO-6 profile (H/E/X/A/C/O scores on 1-5 scale) per agent in a `HEXACO.yaml` file inside each soul dir. Encode profile implications into SOUL.md prose (voice, conviction style, risk appetite). Validation script: compute pairwise Euclidean distance; flag if any two agents < 3.0 (convergence risk). No LLM calls. No runtime gate |
| **Debate tension score** | Quantify how much the Bull and Bear disagreed per cycle. Makes "the institution is uncertain" visible as a number, not just prose | LOW | Pure arithmetic on existing state: `tension = abs(bull_merit_weight - bear_merit_weight) * abs(consensus_score - 0.5) * 2`. Plus keyword scan for refutation markers in debate_history (soul_sync_context peer references). Add to CycleArtifact |
| **Cross-cycle comparison CLI** | Compare two cycles side-by-side: what changed in macro regime assessment, which agent flipped conviction, how merit weights shifted. The "institutional diff" -- seeing how the swarm changes its mind | MEDIUM | `qswarm compare <task_id_1> <task_id_2>` requires CycleArtifact persistence. Diff two artifacts field-by-field: highlight changed agent outputs, shifted scores, flipped risk gate decisions. Rich terminal output with color-coded changes (green = new conviction, red = reversed, yellow = shifted) |
| **Drift flag aggregation (dashboard-ready data)** | Export drift flag and merit time series as structured JSON for external visualization tools (Grafana, Streamlit, or Obsidian charts) | LOW | `qswarm export --format json` outputs structured data from MEMORY.md parsing. Already have the parsing logic in `ars_auditor.py` (reimplemented locally per Import Layer Law). Wrap existing parsers in an export command |
| **Checkpoint fork / "what-if" replay** | Fork a cycle at any node and re-run with modified state ("what if the macro regime was bearish?"). LangGraph natively supports this via `update_state` + `invoke(None, forked_config)` | HIGH | `graph.update_state(checkpoint_config, values={...})` creates a new checkpoint branch; `graph.invoke(None, new_config)` continues from fork point. Requires re-executing LLM calls downstream of the fork: costs tokens, is non-deterministic. Powerful for post-mortem analysis but expensive for routine use |
| **PersonaScore 5D fidelity evaluation** | LLM-as-Judge pipeline scoring each agent's output against its SOUL.md on 5 dimensions: voice fidelity, role boundary compliance, drift guard adherence, belief consistency, non-goal avoidance. Already spec'd as SOUL-09 in PROJECT.md | HIGH | Requires all personas populated first. 5 Gemini calls per evaluation (one per agent). Better as post-cycle batch evaluation than inline node. Provides ground truth for KAMI Fidelity dimension |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Real-time streaming dashboard (WebSocket UI)** | Looks impressive to watch agents thinking in real time | Massive complexity: web server, WebSocket layer, frontend framework, state management. The swarm runs cycles in seconds-to-minutes, not continuously -- there is nothing to "watch" most of the time. 90% of the value comes from post-cycle replay. WebSocket UI is an entire frontend project | Post-cycle CLI replay with rich terminal output. If live observation needed later, use LangGraph's `astream_events()` piped to a terminal renderer (zero frontend code) |
| **Global shared swarm personality (swarm-level SOUL.md)** | "Give the institution a unified identity" | Already ruled out in PROJECT.md: collapses adversarial diversity. The entire debate mechanism depends on AXIOM, MOMENTUM, CASSANDRA, and SIGMA thinking differently. A shared personality defeats the architecture | Per-agent personas with HEXACO-6 diversity validation ensuring genuine cognitive difference |
| **Automated HEXACO diversity enforcement gate** | "Block the pipeline if persona diversity drops" | Premature. Diversity is a design-time property set during persona authoring, not a runtime metric. Personas do not change mid-cycle (frozen `AgentSoul` + `lru_cache`). Runtime gates on personality scores couple the trade path to a metric that cannot change during execution. Already deferred in PROJECT.md | Design-time diversity validation script run during persona authoring. Check HEXACO profiles when writing SOUL.md, not when executing trades |
| **Real-time SOUL.md mutation during graph execution** | "Let agents evolve mid-debate" | Already ruled out: `lru_cache` race condition with concurrent fan-out. Soul files are loaded once at graph creation via `warmup_soul_cache()`. Mutating mid-run breaks cache consistency | Agent Church (out-of-band) processes proposals after cycle completion. Evolution happens between cycles, never during |
| **LLM-as-Judge for ARS drift detection** | "Use AI for nuanced drift evaluation" | Circular evaluation: same model family produces and judges output. Adds API cost to a background audit process. Already ruled out in PROJECT.md | Current 5-metric stdlib approach (Counter cosine, keyword matching, statistical thresholds) is deterministic, free, and auditable |
| **Sentence-transformers for ARS sentiment** | "Better semantic similarity for drift" | Adds heavy ML dependency (sentence-transformers, torch) for a daily background process. Counter cosine is sufficient at current scale. Already ruled out in PROJECT.md | Counter cosine with configurable term lists in swarm_config.yaml |
| **Full graph visualization (Mermaid in browser)** | "Show me the architecture" | The graph structure is static -- does not change per cycle. A one-time diagram in docs suffices. Dynamic state flow is different and belongs in replay | Static Mermaid diagram in docs (LangGraph can generate via `app.get_graph().draw_mermaid()`). Dynamic flow via step-through CLI |
| **Obsidian-native cycle viewer** | "View cycles in Obsidian vault" | The Obsidian vault already has symlinks to `.planning/`. Adding cycle artifacts to Obsidian creates a coupling between the trade pipeline and the documentation tool. Cycles are operational data, not planning data | Export structured JSON from CLI (`qswarm export`), then optionally symlink the export dir into the Obsidian vault if desired. One-way data flow |

---

## Feature Dependencies

```
[Fully Populated Personas]
    requires nothing (authoring task, AXIOM is the template)
    enables --> [End-to-End Pipeline Execution] (meaningful, differentiated output)
    enables --> [HEXACO-6 Diversity Framework] (needs rich SOUL.md to encode profiles)
    enables --> [PersonaScore 5D Evaluation] (needs populated SOUL.md to judge against)

[End-to-End Pipeline Execution]
    requires --> [Fully Populated Personas]
    requires --> PostgreSQL on port 5433 + GOOGLE_API_KEY
    enables --> [Per-Cycle Artifact Persistence] (needs real cycle data)
    enables --> [Step-Through Replay] (needs real checkpoints)

[Per-Cycle Artifact Persistence (CycleArtifact)]
    requires --> [End-to-End Pipeline Execution]
    enables --> [Cycle List CLI]
    enables --> [Single-Cycle Detail View]
    enables --> [Cross-Cycle Comparison]
    enables --> [Debate Tension Score]

[Step-Through Replay]
    requires --> existing audit_logs OR LangGraph checkpoints (both already persist)
    uses --> graph.get_state_history() (already in AsyncPostgresSaver)
    does NOT require --> CycleArtifact (can use raw audit_logs)

[HEXACO-6 Diversity Framework]
    requires --> [Fully Populated Personas]
    enhances --> debate quality (diverse personas produce higher tension)
    standalone validation (no runtime dependency)

[Cross-Cycle Comparison]
    requires --> [Per-Cycle Artifact Persistence]
    requires --> at least 2 completed cycles

[Merit Weight Visibility]
    requires --> existing MEMORY.md entries (already written by memory_writer_node)
    standalone (no new dependencies)

[Drift Flag Visibility]
    requires --> existing MEMORY.md entries
    standalone (no new dependencies)

[Checkpoint Fork / What-If]
    requires --> [Step-Through Replay] (need to identify fork point)
    requires --> LangGraph update_state API
    conflicts with --> determinism (re-runs LLM calls)
```

### Dependency Notes

- **Fully populated personas is the critical path.** Everything downstream depends on agents producing meaningful, differentiated output. Skeleton personas produce shallow, convergent memos that make observability uninteresting. This is authoring work, not code.
- **End-to-end execution is the second gate.** Until a real cycle completes successfully, there is nothing to observe. The yfinance equities path is the reliable route (avoids broken `ccxt`).
- **CycleArtifact persistence unlocks the replay/comparison cluster.** A single "cycle bundle" model that collects all SwarmState fields at cycle end into one retrievable document is the foundation for both replay and comparison.
- **Step-through replay and merit/drift visibility are parallel tracks.** They can proceed independently of CycleArtifact because they use existing data (audit_logs, checkpoints, MEMORY.md).
- **HEXACO-6 is a design-time activity that parallels persona authoring.** It should be done during persona population, not after.

---

## MVP Definition

### Launch With (v1.4 Beta)

The minimum that earns the label "observable swarm beta."

- [ ] **Fully populated 4 skeleton personas** -- MOMENTUM, CASSANDRA, SIGMA, GUARDIAN with AXIOM-quality IDENTITY.md (~300 words), SOUL.md (Core Beliefs, Drift Guard with YAML block, Voice, Non-Goals), AGENTS.md. Critical path blocker for everything else
- [ ] **End-to-end pipeline execution** -- One successful cycle against real market data (yfinance ticker, Gemini LLM calls, all 5 agents producing non-None output, debate synthesis, risk gate, decision card written). Proves the pipeline works
- [ ] **CycleArtifact persistence** -- Pydantic model capturing full cycle state written to PostgreSQL or JSON per task_id at cycle end
- [ ] **Cycle list CLI** -- `qswarm cycles list` showing recent cycles
- [ ] **Single-cycle detail CLI** -- `qswarm cycles show <task_id>` with agent-by-agent output, debate, consensus, risk, execution
- [ ] **Step-through replay CLI** -- `qswarm replay <task_id>` walking nodes in execution order via `get_state_history`
- [ ] **Merit weight time series** -- `qswarm merit history` from MEMORY.md
- [ ] **Drift flag time series** -- `qswarm drift history` from MEMORY.md

### Add After Validation (v1.4.x)

Once the beta is running and producing real cycles.

- [ ] **HEXACO-6 persona profiles** -- Define H/E/X/A/C/O scores per agent, embed in SOUL.md, validate pairwise diversity. Trigger: after all personas populated and producing differentiated output
- [ ] **Debate tension score** -- Quantify Bull/Bear disagreement per cycle. Trigger: after multiple cycles show variation in debate dynamics
- [ ] **Cross-cycle comparison CLI** -- `qswarm compare <id_1> <id_2>`. Trigger: after 5+ cycles accumulated
- [ ] **Dashboard-ready export** -- `qswarm export --format json` for drift flags, merit time series. Trigger: after 20+ cycles

### Future Consideration (v2+)

- [ ] **Checkpoint fork / what-if replay** -- Defer: requires re-running LLM calls (cost, non-determinism)
- [ ] **PersonaScore 5D fidelity evaluation** (SOUL-09) -- Defer: 5 extra LLM calls per evaluation, needs accumulated data
- [ ] **Real-time streaming observation** -- Defer: massive frontend complexity, low marginal value over post-cycle replay
- [ ] **HEXACO automated diversity enforcement gate** -- Defer: diversity is design-time, not runtime

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Depends On |
|---------|------------|---------------------|----------|------------|
| Fully populated personas | HIGH | HIGH (authoring) | P1 | Nothing |
| End-to-end pipeline execution | HIGH | MEDIUM | P1 | Personas |
| CycleArtifact persistence | HIGH | MEDIUM | P1 | Pipeline execution |
| Cycle list CLI | MEDIUM | LOW | P1 | CycleArtifact |
| Single-cycle detail CLI | HIGH | MEDIUM | P1 | CycleArtifact |
| Step-through replay CLI | HIGH | MEDIUM | P1 | Checkpoints (exist) |
| Merit weight time series | MEDIUM | LOW | P1 | MEMORY.md (exists) |
| Drift flag time series | MEDIUM | LOW | P1 | MEMORY.md (exists) |
| HEXACO-6 profiles | MEDIUM | MEDIUM | P2 | Populated personas |
| Debate tension score | MEDIUM | LOW | P2 | CycleArtifact |
| Cross-cycle comparison | HIGH | MEDIUM | P2 | 2+ CycleArtifacts |
| Dashboard-ready export | MEDIUM | LOW | P2 | MEMORY.md parsing |
| Checkpoint fork | MEDIUM | HIGH | P3 | Replay CLI |
| PersonaScore 5D | MEDIUM | HIGH | P3 | Populated personas |
| Real-time streaming | LOW | HIGH | P3 | Pipeline execution |

---

## Existing Infrastructure Reuse

The system already has significant infrastructure that new features build on directly. Understanding this prevents rebuilding what exists.

| Existing Component | What It Provides | New Feature It Enables |
|---|---|---|
| `with_audit_logging` wrapper (orchestrator.py) | Every node's input/output logged to PostgreSQL `audit_logs` with SHA-256 hash chain | Step-through replay, single-cycle detail |
| `AsyncPostgresSaver` checkpointer | LangGraph checkpoints per super-step persisted to PostgreSQL | `get_state_history()` for replay, `update_state()` for fork |
| `DecisionCard` + `audit.jsonl` | Immutable trade artifacts with agent contributions, risk snapshot, applied rules | CycleArtifact can reference or embed decision card |
| `MEMORY.md` per-agent entries | Structured log with `[MERIT_SCORE:]`, `[KAMI_DELTA:]`, `[DRIFT_FLAGS:]`, `[CYCLE_STATUS:]`, `[THESIS_SUMMARY:]` | Merit time series, drift time series, cross-cycle thesis comparison |
| `merit_scores` in SwarmState | Per-agent KAMI composite with 4 dimensions, persisted to PostgreSQL | Merit weight visibility, debate tension computation |
| `soul_sync_context` | Peer soul summaries exchanged before debate | Shows in cycle detail what each agent knew about opponent |
| ARS Auditor (`ars_auditor.py`) | 5 drift metrics, breach counters, suspension state | Drift flag visibility, parsing logic reusable for export |
| AXIOM persona (fully populated) | Reference template: IDENTITY.md (~300 words), SOUL.md with `drift_guard:` YAML block | Template for authoring MOMENTUM, CASSANDRA, SIGMA, GUARDIAN |
| `_parse_entries()` in memory_writer + ars_auditor | MEMORY.md entry parsing (regex-based, entry header detection) | Reusable for merit/drift time series extraction |

---

## HEXACO-6 Application Strategy

The HEXACO-6 model maps naturally to trading agent cognitive diversity. Each agent should occupy a distinct region of the 6-dimensional personality space. Recent research (arxiv:2508.00742) confirms that GPT-4 powered agents can exhibit coherent, reliable HEXACO-aligned personality structure.

**Dimensions and Trading Relevance:**

| HEXACO Dimension | Facets (from hexaco.org) | Trading Agent Interpretation |
|---|---|---|
| **H**onesty-Humility | Sincerity, Fairness, Greed Avoidance, Modesty | Transparency vs. strategic advocacy. High-H agents explicitly state uncertainty and limitations; low-H agents advocate aggressively for their position without qualification |
| **E**motionality | Fearfulness, Anxiety, Dependence, Sentimentality | Sensitivity to downside risk. High-E agents weight losses heavily and flag danger early; low-E agents tolerate drawdowns and focus on expected value |
| e**X**traversion | Social Self-Esteem, Social Boldness, Sociability, Liveliness | Conviction strength in debate. High-X agents push hard for their view with energy; low-X agents are methodical and reserved |
| **A**greeableness | Forgivingness, Gentleness, Flexibility, Patience | Willingness to converge with consensus. High-A agents seek compromise; low-A agents hold contrarian positions and resist peer pressure |
| **C**onscientiousness | Organization, Diligence, Perfectionism, Prudence | Methodological rigor. High-C agents demand exhaustive evidence before conviction; low-C agents act on pattern recognition and instinct |
| **O**penness | Aesthetic Appreciation, Inquisitiveness, Creativity, Unconventionality | Regime-shift adaptability. High-O agents update beliefs quickly on new data; low-O agents anchor to existing frameworks and historical patterns |

**Proposed Agent Profiles (to be refined during persona authoring):**

| Agent | H | E | X | A | C | O | Archetype Summary |
|-------|---|---|---|---|---|---|-------------------|
| AXIOM | 5 | 3 | 3 | 3 | 4 | 4 | Transparent regime analyst, probabilistic, moderate debate presence |
| MOMENTUM | 2 | 1 | 5 | 2 | 3 | 4 | Aggressive growth hunter, high conviction, low risk sensitivity |
| CASSANDRA | 4 | 4 | 4 | 1 | 4 | 3 | Transparent pessimist, high risk sensitivity, refuses consensus |
| SIGMA | 3 | 2 | 2 | 3 | 5 | 3 | Methodical quant, emotionless, evidence-bound, reserved |
| GUARDIAN | 4 | 5 | 2 | 4 | 5 | 2 | Cautious gatekeeper, rule-bound, risk-averse, process-oriented |

**Diversity Validation:** Minimum pairwise Euclidean distance across all 10 agent pairs should exceed 3.0 (on 1-5 scale across 6 dimensions). The proposed profiles yield minimum pairwise distance of approximately 4.2 (AXIOM-SIGMA pair), which passes comfortably. Maximum distance is approximately 7.5 (MOMENTUM-GUARDIAN pair), reflecting their intended adversarial positioning.

**Implementation:** Each soul directory gets a `HEXACO.yaml` file:
```yaml
hexaco_profile:
  version: 1
  scores:
    honesty_humility: 4
    emotionality: 4
    extraversion: 4
    agreeableness: 1
    conscientiousness: 4
    openness: 3
  rationale: "CASSANDRA's low agreeableness drives contrarian positioning..."
```

The HEXACO profile informs SOUL.md prose (Voice section reflects X, Drift Guard reflects E, Core Beliefs reflect H and O) but does not create runtime coupling. It is a design document, not a runtime artifact.

---

## LangGraph Time-Travel API for Replay

Verified against official LangGraph documentation. The replay CLI builds on these existing APIs:

**Get state history** (enumerate all checkpoints for a cycle):
```python
config = {"configurable": {"thread_id": task_id}}
states = list(graph.get_state_history(config))
# Returns StateSnapshot objects in reverse chronological order
# Each has: .values (SwarmState dict), .next (list of next node names),
# .config (with checkpoint_id), .created_at, .metadata
```

**Replay from checkpoint** (re-execute from a point):
```python
# Resume from a specific checkpoint without modification
graph.invoke(None, selected_state.config)
```

**Fork state** (what-if exploration):
```python
# Modify state at a checkpoint and create a new branch
new_config = graph.update_state(selected_state.config, values={"macro_report": modified_report})
# Execute from the fork point
graph.invoke(None, new_config)
```

The step-through replay CLI uses only `get_state_history` (read-only, no re-execution, no token cost). The fork feature uses `update_state` + `invoke` (re-executes downstream nodes, costs tokens).

---

## Sources

- [LangGraph Time Travel Documentation](https://docs.langchain.com/oss/python/langgraph/use-time-travel) -- get_state_history, update_state, checkpoint replay APIs. HIGH confidence (verified against official docs)
- [HEXACO Personality Inventory - Official](https://hexaco.org/) -- Six dimensions with 4 facets each. HIGH confidence (primary academic source)
- [HEXACO Scale Descriptions](https://hexaco.org/scaledescriptions) -- Facet-level trait definitions for all 6 dimensions. HIGH confidence
- [Applying Psychometrics to LLM Simulated Populations (2025)](https://arxiv.org/html/2508.00742v1) -- HEXACO applied to GPT-4 agents, coherent personality structure recoverable. MEDIUM confidence (single study, but directly relevant)
- [Psychologically Enhanced AI Agents (2025)](https://www.emergentmind.com/papers/2509.04343) -- Personality as vector in trait space, framework-agnostic conditioning. MEDIUM confidence
- [Observability for AI Agents: LangGraph, OpenAI Agents, and Crew AI](https://www.getmaxim.ai/articles/observability-for-ai-agents-langgraph-openai-agents-and-crew-ai/) -- 89% of orgs have agent observability; tracing is table stakes. MEDIUM confidence (industry survey)
- [LangGraph Studio Guide (2025)](https://mem0.ai/blog/visual-ai-agent-debugging-langgraph-studio) -- Visual debugging with intermediate state inspection. MEDIUM confidence
- [Top LLM Observability Platforms 2025](https://agenta.ai/blog/top-llm-observability-platforms) -- Industry patterns for agent tracing and replay. MEDIUM confidence
- [TradingAgents Framework](https://github.com/TauricResearch/TradingAgents) -- Multi-agent LLM financial trading framework. LOW confidence (not deeply analyzed)
- [Best LLM Observability Tools 2026](https://awesomeagents.ai/tools/best-llm-observability-tools-2026/) -- Current landscape of agent observability tools. MEDIUM confidence

---
*Feature research for: Observable Swarm Beta (v1.4)*
*Researched: 2026-03-08*
