# Feature Landscape

**Domain:** Reliability and observability features for multi-agent financial analysis swarm (v1.5)
**Researched:** 2026-03-09

## Table Stakes

Features that are expected for a production-grade multi-agent system at this maturity level. Missing = operational blind spots.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Token cost tracking per cycle | BudgetManager already enforces ceilings but discards per-cycle breakdown after session reset. Without per-cycle cost attribution, budget analysis is impossible. | Low | Existing `BudgetManager.summary()` returns the right shape; just needs persistence to `cycle_snapshots` and aggregation queries. |
| Dependency restoration (ccxt, chromadb, pytest-asyncio) | 13 tests broken by environment issues. A system that ships with known broken deps erodes CI trust. | Low | Package pinning and env isolation. No architectural change. |
| Circuit breaker for Gemini API | LLM API calls currently have no failure-state management. A 429/503 cascade during a cycle can burn budget on retries while producing nothing. | Medium | Standard 3-state (closed/open/half-open) pattern. Existing `BudgetedTool` already wraps tool calls; circuit breaker wraps LLM invocations one layer up. |
| KAMI weight rebalancing | Accuracy dimension frozen at 0.5 (30% of merit score) makes 30% of KAMI inert. Merit-weighted consensus is undermined. | Low | Config change in `swarm_config.yaml` + update `DEFAULT_WEIGHTS` in `kami.py`. The formula and EMA mechanics are already correct. |

## Differentiators

Features that go beyond operational hygiene and create genuine capability advantages. Not expected at this stage, but high-value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| PersonaScore 5D LLM-as-Judge | Closes the KAMI Accuracy gap by measuring whether agents actually behave according to their soul definitions. No comparable open-source multi-agent system does per-cycle persona fidelity evaluation. | High | Requires a judge prompt, 5 rubric dimensions, structured output parsing, score normalization to [0,1], and integration as a new KAMI dimension. |
| Prune-to-Obsidian ChromaDB lifecycle | Most vector DB deployments have no pruning strategy and grow unbounded. Archiving old vectors to markdown before deletion creates a searchable historical record in Obsidian. | Medium | ChromaDB has `collection.delete()` and metadata-based filtering. The novel part is the export-then-prune workflow with age/relevance thresholds. |

## Anti-Features

Features to explicitly NOT build. Each has been considered and rejected for stated reasons.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| LLM-as-Judge for ARS drift detection | Creates circular evaluation: an LLM judging whether another LLM drifted. Adds API cost to a background audit that runs on a systemd timer. Already explicitly out-of-scope in PROJECT.md. | Keep stdlib-only ARS metrics (Counter cosine, MEMORY.md parsing). PersonaScore is different -- it evaluates output quality, not drift detection. |
| Real-time token cost dashboard | Over-engineering for current scale. The swarm runs cycles in CLI mode, not as a long-running service. WebSocket dashboards are deferred to OBS-01. | Persist cost summaries to cycle_snapshots; query via replay CLI or SQL. |
| Automatic KAMI weight optimization | Using gradient descent or RL to find "optimal" weights introduces instability. Weights encode design intent (e.g., Recovery matters more than Accuracy because accuracy requires trade resolution). | Manual rebalancing via config. Document the rationale. Revisit after 100+ cycles of PersonaScore data. |
| Multi-model fallback chain for circuit breaker | The system is built around Gemini-specific prompt patterns and pricing. Falling back to a different model mid-cycle would produce inconsistent persona behavior and break soul fidelity assumptions. | Circuit breaker should pause (soft-fail), not switch models. Return a degraded-but-honest result. |
| PersonaScore as pairwise comparison | Pairwise LLM-as-Judge (comparing Agent A vs Agent B) is more reliable for ranking but wrong for this use case. We need absolute fidelity scores per agent, not relative rankings. | Pointwise scoring with anchored rubrics. Each agent evaluated independently against their own soul definition. |
| Sentence-transformers for PersonaScore embeddings | Adds a heavyweight dependency (torch, transformers) for marginal improvement over structured rubric scoring. Already rejected for ARS in PROJECT.md. | Direct LLM-as-Judge with structured JSON output. No embedding comparison needed. |

---

## Feature Deep Dives

### 1. PersonaScore 5D LLM-as-Judge

**What it is:** An evaluation pipeline that runs after each agent produces output, using the same LLM (Gemini 2.5 Flash) as a judge to score how well the output matches the agent's soul definition across 5 dimensions.

**The 5 Dimensions:**

| Dimension | What It Measures | Rubric Anchor Examples |
|-----------|------------------|----------------------|
| **Consistency** | Does the output align with the agent's stated Core Beliefs and analytical framework? | AXIOM should reference macro indicators; MOMENTUM should reference price action and flow data. |
| **Tone** | Does the writing style match the agent's personality profile (HEXACO-6)? | CASSANDRA should be cautious/skeptical; MOMENTUM should be assertive/conviction-driven. |
| **Logic** | Is the reasoning structure sound and consistent with the agent's analytical methodology? | SIGMA should show quantitative rigor; AXIOM should show macro-to-micro reasoning chains. |
| **Depth** | Does the analysis demonstrate appropriate domain expertise depth? | Surface-level bullet points score low; structured multi-factor analysis scores high. |
| **Bias** | Does the agent maintain its designated perspective without inappropriate drift? | CASSANDRA should maintain bearish scrutiny even in bull markets; MOMENTUM should not hedge excessively. |

**How LLM-as-Judge Typically Works (evidence-based):**

1. **Pointwise scoring** is the correct paradigm here -- each agent's output is scored independently against its own rubric (not compared to other agents). Confirmed by Langfuse guide, Evidently AI guide, and arXiv survey 2411.15594. **Confidence: HIGH**

2. **Structured rubrics with anchored examples** significantly improve scoring consistency. Each score level (1-5) should have explicit behavioral descriptions, not just numeric scales. **Confidence: HIGH**

3. **Chain-of-thought elicitation** before the final score reduces position bias and improves calibration. The judge should explain its reasoning before assigning numbers. **Confidence: HIGH**

4. **Self-consistency via multiple passes** (evaluate 2-3 times, take mean) is recommended for production but adds 2-3x cost. For v1.5, single-pass with CoT is sufficient given the per-cycle budget constraints. **Confidence: MEDIUM**

5. **Output format:** Structured JSON with CoT reasoning field + per-dimension integer scores (1-5 scale) + composite float. Parse with Pydantic for validation. **Confidence: HIGH**

**Implementation Architecture:**

```
Agent output (from SwarmState messages)
    + Agent soul definition (from soul_loader)
    + Rubric template (static, per-dimension)
    |
    v
PersonaScore Judge (single Gemini call with structured output)
    |
    v
Pydantic-validated PersonaScoreResult
    |
    v
Normalize to [0, 1] (score / 5.0 per dimension, weighted average for composite)
    |
    v
Feed into KAMI as new "persona" dimension (replacing or supplementing Accuracy)
```

**Integration with existing KAMI:**

- Add `persona` key to `KAMIDimensions` (or repurpose `accuracy` since it is frozen at 0.5)
- Add `epsilon` weight to `DEFAULT_WEIGHTS` for the persona dimension
- PersonaScore signal feeds into `merit_updater_node` via EMA, same as Recovery/Consensus/Fidelity
- The judge call happens as a new graph node (`persona_scorer`) after fan-in but before `merit_updater`

**Cost estimate:** One additional Gemini call per agent per cycle. At ~500 input tokens (soul excerpt + output excerpt + rubric) + ~200 output tokens (CoT + scores), ~$0.0001 per evaluation. 4 agents per cycle = ~$0.0004/cycle. Negligible.

**Dependencies:**
- Requires: Soul definitions (SOUL-01 through SOUL-06, all complete)
- Requires: Agent output in SwarmState messages (already present)
- Blocked by: Nothing -- all prerequisites exist
- Feeds into: KAMI-05 weight rebalancing (PersonaScore needs a weight allocation)

---

### 2. Token Cost Tracking (OBS-02)

**What it is:** Persist the `BudgetManager.summary()` dict into each cycle's snapshot so cost can be queried, compared across cycles, and aggregated over time.

**How Production LLM Systems Track Costs:**

The ecosystem offers tiered approaches. Langfuse and LangSmith provide full-stack observability with per-trace cost attribution. LiteLLM provides proxy-level spend tracking. **Confidence: HIGH**

For this project, the right approach is **internal tracking** (not external SaaS) because:
- BudgetManager already records input/output tokens and USD per session
- The data is already available via `usage_metadata` on LangChain AI messages
- CycleSnapshot already captures cycle artifacts -- adding cost is a schema extension

**What Needs to Change:**

| Component | Current State | Required Change |
|-----------|--------------|-----------------|
| `BudgetManager` | Tracks session totals, resets between cycles | Add `per_agent_usage` dict tracking tokens per soul_handle |
| `CycleSnapshot` | No cost field | Add `token_usage: Dict[str, Any]` field with per-agent and total breakdown |
| `CycleRunner` | Calls `budget.reset_session()` | Capture `budget.summary()` before reset, inject into snapshot |
| Replay CLI | No cost display | Add cost column to `list` table, cost section to `show` output |
| Analyst/Researcher nodes | Record usage to BudgetManager but don't tag by agent | Pass `soul_handle` to `record_usage()` for per-agent attribution |

**Per-agent attribution pattern:**

```python
# In analysts.py / researchers.py (already partially implemented):
if hasattr(last_msg, "usage_metadata") and last_msg.usage_metadata and budget:
    usage = last_msg.usage_metadata
    budget.record_usage(
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        agent=soul_handle,  # NEW: tag by agent
    )
```

**Complexity:** Low. The infrastructure is 80% built. Main work is:
1. Extend `BudgetManager` with per-agent counters (~20 lines)
2. Add cost field to `CycleSnapshot` Pydantic model (~5 lines)
3. Capture summary in `CycleRunner` before reset (~10 lines)
4. Display in replay CLI (~30 lines)

**Dependencies:**
- Requires: BudgetManager (SEC-02, complete)
- Requires: CycleSnapshot schema (CYCL-02, complete)
- Requires: Replay CLI (REPL-01 through REPL-06, complete)

---

### 3. ChromaDB Pruning + Obsidian Archiving (OBS-03)

**What it is:** A "Prune-to-Obsidian" workflow that exports old/low-relevance ChromaDB documents to Obsidian-compatible markdown files, then deletes them from the vector store to keep it lean.

**What a Healthy Vector DB Lifecycle Looks Like:**

Vector databases without pruning strategies exhibit two failure modes:
1. **Retrieval quality degradation** -- old, irrelevant vectors pollute search results
2. **Storage/performance bloat** -- HNSW index gets slower as collection grows

ChromaDB specifically:
- Supports metadata-based filtering for targeted deletion (`collection.delete(where={...})`)
- Has automatic WAL pruning since v0.5.5 (ChromaDB Cookbook)
- Has a maintenance CLI tool (chromadb-ops) for orphaned directory cleanup
- Does NOT have built-in TTL or age-based pruning -- this must be application-managed

**Confidence: HIGH** (verified via ChromaDB Cookbook and PyPI docs)

**Pruning Strategy:**

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Age | > 90 days since `ingested_at` | Trade/research context loses relevance beyond one quarter |
| Source type | `trade` documents older than 30 days | Trade decisions are already in PostgreSQL warehouse; vector copies are for short-term retrieval |
| Research staleness | `research` documents with `timestamp` > 60 days | Market research has shorter shelf life than trade records |
| External data | `external_data` older than 14 days | News/calendar data is highly perishable |

**Archive-to-Obsidian Workflow:**

```
1. Query ChromaDB for documents matching pruning criteria (age/source filters)
2. For each document:
   a. Reassemble chunks via MemoryService.get(document_id)
   b. Convert to Obsidian markdown:
      - YAML frontmatter (source, symbol, timestamp, document_id, content_hash)
      - Full text content
      - Tags (#archived, #trade/#research/#external-data)
   c. Write to quantum-swarm/Archives/{source}/{YYYY-MM}/{document_id}.md
3. Delete from ChromaDB via MemoryService.delete(document_id)
4. Run MemoryService.deduplicate() for orphan cleanup
5. Log archive event to audit.jsonl
```

**Existing Infrastructure:**
- `MemoryService` already has `get()`, `delete()`, `deduplicate()` methods
- `MemoryService` already has `AuditLog` integration
- Obsidian vault at `quantum-swarm/` already has symlinks and auto-generated indexes
- Metadata includes `ingested_at`, `source`, `timestamp` -- all needed for age filtering

**Complexity:** Medium. The MemoryService API covers most needs. New code:
1. Pruning criteria engine (configurable thresholds) -- ~50 lines
2. Obsidian markdown exporter -- ~40 lines
3. Archive orchestrator (query, export, delete, audit) -- ~60 lines
4. CLI subcommand or standalone script -- ~30 lines
5. Config block in `swarm_config.yaml` -- ~10 lines

**Dependencies:**
- Requires: MemoryService (complete, `src/memory/service.py`)
- Requires: ChromaDB package restored (ENV-01, not yet complete)
- Requires: Obsidian vault structure (complete, `quantum-swarm/`)
- Soft dependency: Token cost tracking (nice to include archive cost in cycle summary)

---

### 4. Gemini API Circuit Breaker (SEC-03)

**What it is:** A state machine wrapper around Gemini API calls that detects failure patterns and enters a soft-fail pause state instead of blind-retrying into a broken API.

**How Circuit Breakers Work for LLM APIs:**

The standard 3-state pattern (Portkey guide, PyBreaker):

```
CLOSED (normal operation)
    | failure_count >= threshold
    v
OPEN (all calls immediately return fallback)
    | timeout_duration expires
    v
HALF-OPEN (allow one probe call)
    | probe succeeds -> CLOSED
    | probe fails -> OPEN (reset timeout)
```

**Confidence: HIGH** (well-established pattern, multiple Python implementations)

**LLM-Specific Considerations:**

| Concern | Standard Circuit Breaker | LLM-Adapted Circuit Breaker |
|---------|------------------------|----------------------------|
| Failure detection | HTTP status codes | 429 (rate limit), 503 (overloaded), 500 (internal), timeout, empty response |
| Fallback behavior | Return cached response | Return degraded analysis with `"circuit_breaker": "open"` flag in SwarmState |
| Cost awareness | N/A | Open circuit prevents budget burn on retries |
| Per-model tracking | N/A | Track per-model if multiple models used (currently single model, but future-proof) |
| Retry backoff | Exponential | Exponential with jitter, respecting Gemini's `Retry-After` header |

**Implementation Design:**

```python
class GeminiCircuitBreaker:
    """3-state circuit breaker for Gemini API calls."""

    def __init__(
        self,
        failure_threshold: int = 3,      # failures before opening
        recovery_timeout: float = 60.0,  # seconds in OPEN before HALF-OPEN
        half_open_max: int = 1,          # probe calls in HALF-OPEN
    ): ...

    def call(self, fn, *args, **kwargs):
        """Execute fn() through circuit breaker logic."""
        if self.state == CircuitState.OPEN:
            if time_since_open < self.recovery_timeout:
                raise CircuitOpenError(...)
            self.state = CircuitState.HALF_OPEN

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except (RateLimitError, ServiceUnavailableError, TimeoutError) as e:
            self._on_failure(e)
            raise
```

**Integration Points:**

| Integration | How |
|-------------|-----|
| Analyst nodes (`analysts.py`) | Wrap LLM `invoke()` calls with circuit breaker |
| Researcher nodes (`researchers.py`) | Wrap LLM `invoke()` calls with circuit breaker |
| PersonaScore judge | Wrap judge LLM call (if circuit open, skip scoring, use previous PersonaScore) |
| BudgetManager | Circuit breaker prevents budget burn; complementary safety layer |
| SwarmState | Add `circuit_breaker_status: Optional[str]` for observability |
| Replay CLI | Display circuit breaker events in cycle show |

**What "soft-fail pause" means for this system:**
- When circuit is OPEN, agent nodes return a degraded response: `"[CIRCUIT_OPEN] {agent_name} analysis unavailable - Gemini API degraded"`
- The cycle continues with available agents (fan-in handles partial results)
- DecisionCard records the degradation
- KAMI does NOT penalize agents for circuit breaker pauses (not self-induced)

**Existing Python libraries:**
- `pybreaker` -- mature, well-maintained, supports listeners for logging. Use this rather than building from scratch.
- `circuitbreaker` -- simpler decorator-based API but less configurable.

**Recommendation:** Use `pybreaker` because it supports custom failure detection (needed to distinguish 429 from 500) and listener callbacks (needed for audit logging).

**Complexity:** Medium. Core circuit breaker logic is provided by pybreaker. Main work:
1. `GeminiCircuitBreaker` wrapper class with LLM-specific failure detection -- ~60 lines
2. Integration into analyst/researcher nodes -- ~20 lines per node (4 nodes)
3. Fallback response generation -- ~30 lines
4. Config in `swarm_config.yaml` -- ~10 lines
5. Audit event logging -- ~15 lines

**Dependencies:**
- Requires: New dependency `pybreaker` (pip install)
- Requires: Analyst/researcher node access (complete)
- Independent of other v1.5 features

---

### 5. KAMI Weight Rebalancing (KAMI-05)

**What it is:** Shift the Accuracy weight from 30% to 5-10% and redistribute to a new PersonaScore dimension and/or existing dimensions.

**Current Weights:**

| Dimension | Weight (alpha/beta/gamma/delta) | Status |
|-----------|-------------------------------|--------|
| Accuracy | 30% (alpha=0.30) | FROZEN at 0.5 -- no trade resolution pipeline updates it |
| Recovery | 35% (beta=0.35) | Active -- updated every cycle via EMA |
| Consensus | 25% (gamma=0.25) | Active -- updated every cycle via EMA |
| Fidelity | 10% (delta=0.10) | Active -- updated every cycle via EMA |

**Problem:** 30% of every agent's merit score is a constant 0.5. This means:
- Merit scores cluster artificially (0.15 of composite is always fixed)
- Active dimensions (Recovery, Consensus, Fidelity) have reduced influence on consensus weighting
- DebateSynthesizer merit weighting is less discriminating than intended

**Rebalancing Strategy:**

Two viable approaches depending on whether PersonaScore ships in the same phase:

**Option A: PersonaScore ships first (recommended)**

| Dimension | New Weight | Rationale |
|-----------|-----------|-----------|
| Accuracy | 5% (alpha=0.05) | Keep minimal -- will be activated when trade resolution pipeline exists |
| Recovery | 30% (beta=0.30) | Slightly reduced from 35% but still dominant -- self-correction is critical |
| Consensus | 25% (gamma=0.25) | Unchanged -- debate contribution matters |
| Fidelity | 15% (delta=0.15) | Increased -- soul adherence (structural) complements persona scoring |
| PersonaScore | 25% (epsilon=0.25) | New -- persona fidelity via LLM-as-Judge |

**Option B: PersonaScore not ready yet**

| Dimension | New Weight | Rationale |
|-----------|-----------|-----------|
| Accuracy | 5% (alpha=0.05) | Minimized while frozen |
| Recovery | 40% (beta=0.40) | Absorbs most of freed weight |
| Consensus | 30% (gamma=0.30) | Slightly increased |
| Fidelity | 25% (delta=0.25) | Significantly increased to compensate for missing PersonaScore |

**Best Practices for Weight Redistribution:**

- Weights should sum to 1.0 (enforced by existing `compute_merit()`)
- Changes should be config-driven (`swarm_config.yaml`) not code-driven
- Document rationale as a decision record (conventional commit `decision:`)
- Do NOT auto-optimize weights -- this encodes design intent, not statistical optima
- Monitor composite score distribution after rebalancing -- scores should spread more with Accuracy weight reduced

**Complexity:** Low. This is a config change + adding one key to `KAMIDimensions` if PersonaScore is included:

1. Update `swarm_config.yaml` kami section -- ~5 lines
2. Update `DEFAULT_WEIGHTS` in `kami.py` -- ~2 lines
3. If PersonaScore: add `persona` field to `KAMIDimensions` dataclass -- ~3 lines
4. If PersonaScore: add `epsilon` to `compute_merit()` formula -- ~2 lines
5. Update `_compute_kami_dimension_variance()` in `ars_auditor.py` to include persona dimension -- ~3 lines

**Dependencies:**
- Soft dependency on PersonaScore (Option A vs Option B)
- Independent of circuit breaker, token tracking, ChromaDB pruning

---

## Feature Dependencies

```
ENV-01 (Dep Fix) ────────────────────────────────────────> OBS-03 (ChromaDB Pruning)
                                                               needs chromadb working

SOUL-09 (PersonaScore) ──> KAMI-05 (Weight Rebalancing, Option A)
                           PersonaScore needs a weight allocation

OBS-02 (Token Tracking) ──> OBS-03 (Prune-to-Obsidian)
                             nice-to-have: include archive cost

SEC-03 (Circuit Breaker) ──> SOUL-09 (PersonaScore)
                              judge call should go through circuit breaker

BudgetManager (existing) ──> OBS-02 (Token Tracking)
                              extend, don't replace

MemoryService (existing) ──> OBS-03 (ChromaDB Pruning)
                              use existing API
```

**Critical path:** ENV-01 must come first (unblocks ChromaDB tests). Then PersonaScore + Circuit Breaker can parallelize. KAMI rebalancing should follow PersonaScore (Option A preferred).

## MVP Recommendation

**Phase ordering for v1.5:**

1. **ENV-01: Dependency Fix** -- unblock everything, restore CI green
   - Addresses: 13 broken tests, chromadb import failures
   - Complexity: Low
   - Prerequisite for: OBS-03

2. **SEC-03: Circuit Breaker** -- protect the system before adding more LLM calls
   - Addresses: Gemini API resilience
   - Complexity: Medium
   - Prerequisite for: PersonaScore judge calls should be protected

3. **SOUL-09: PersonaScore 5D** -- the marquee differentiator
   - Addresses: KAMI Accuracy gap, persona fidelity measurement
   - Complexity: High
   - Prerequisite for: KAMI-05 Option A

4. **KAMI-05: Weight Rebalancing** -- immediately benefits from PersonaScore
   - Addresses: 30% inert merit weight
   - Complexity: Low

5. **OBS-02: Token Cost Tracking** -- low effort, high observability value
   - Addresses: Cost visibility per cycle and per agent
   - Complexity: Low

6. **OBS-03: Prune-to-Obsidian** -- least urgent, most self-contained
   - Addresses: ChromaDB growth, historical archiving
   - Complexity: Medium

**Defer:**
- Multi-model fallback chains: wrong for this architecture (soul fidelity requires consistent model)
- Automated weight optimization: premature without 100+ cycles of PersonaScore data
- Real-time cost dashboard: use replay CLI queries until OBS-01 (WebSocket dashboard) in future milestone

## Sources

- [Langfuse: LLM-as-a-Judge Evaluation Guide](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)
- [Evidently AI: LLM-as-a-Judge Complete Guide](https://www.evidentlyai.com/llm-guide/llm-as-a-judge)
- [arXiv 2411.15594: A Survey on LLM-as-a-Judge](https://arxiv.org/abs/2411.15594)
- [Monte Carlo Data: LLM-as-Judge Best Practices](https://www.montecarlodata.com/blog-llm-as-judge/)
- [Portkey: Retries, Fallbacks, and Circuit Breakers in LLM Apps](https://portkey.ai/blog/retries-fallbacks-and-circuit-breakers-in-llm-apps/)
- [PyBreaker GitHub](https://github.com/danielfm/pybreaker)
- [ChromaDB Cookbook: Maintenance](https://cookbook.chromadb.dev/running/maintenance/)
- [chromadb-ops GitHub](https://github.com/amikos-tech/chromadb-ops)
- [Langfuse: Token and Cost Tracking](https://langfuse.com/docs/observability/features/token-and-cost-tracking)
- [LangSmith: Cost Tracking](https://docs.langchain.com/langsmith/cost-tracking)
- [LiteLLM: Spend Tracking](https://docs.litellm.ai/docs/proxy/cost_tracking)
