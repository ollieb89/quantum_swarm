# Stack Research — v1.4 Beta: Observable Swarm

**Domain:** Cycle persistence, cycle replay CLI, HEXACO-6 persona population, E2E pipeline hardening
**Researched:** 2026-03-08
**Confidence:** HIGH

---

## Verdict: Two New Dependencies, One Promotion

| Feature | Implementation | New Dep? |
|---------|---------------|----------|
| Per-cycle artifact persistence | `pathlib`, `json`, `shutil` (stdlib) + existing `psycopg` | None |
| Cycle replay CLI | `typer` + `rich` (both already installed as transitive deps) | **Promote to explicit** |
| HEXACO-6 persona profiles | Pure content authoring in SOUL.md files + `pydantic` validation | None |
| E2E pipeline hardening | Existing stack + `structlog` for structured logging | **New: structlog** |

**Net result:** Add `typer>=0.24.0` and `rich>=14.0.0` to `pyproject.toml` as explicit dependencies (already installed via langgraph transitive chain). Add `structlog>=24.0.0` as new dependency for structured logging in production runs.

---

## Recommended Stack

### New Explicit Dependencies

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| typer | `>=0.24.0` | Cycle replay CLI framework | Already installed (transitive via langgraph). Type-hint-driven CLI with zero boilerplate. Built on Click internally, so complex subcommands available if needed. Promotes to explicit dep to prevent accidental removal. |
| rich | `>=14.0.0` | Terminal formatting for replay CLI | Already installed (transitive). Tables, syntax highlighting, panels, progress bars -- all needed for step-through cycle replay display. |
| structlog | `>=24.0.0` | Structured JSON logging for E2E runs | stdlib `logging` produces unstructured text. Production market data runs need machine-parseable JSON logs with correlation IDs (task_id), timing, and error context. structlog wraps stdlib logging -- no migration needed, additive. |

### Core Technologies (Existing -- No Change)

| Technology | Current Version | v1.4 Role |
|------------|----------------|-----------|
| Python 3.12 | runtime | All features |
| LangGraph | 1.0.10 | Graph orchestration, checkpointing |
| psycopg | 3.3.3 | Cycle metadata persistence to PostgreSQL |
| pydantic | 2.12.5 | HEXACO-6 profile validation, cycle artifact schemas |
| pyyaml | 6.0.3 | Soul file YAML drift_guard blocks, config parsing |
| langgraph-checkpoint-postgres | 3.0.4 | Crash recovery for E2E pipeline runs |

### Supporting Stdlib Modules (Zero Install Cost)

| Module | Purpose | Specific Use |
|--------|---------|-------------|
| `pathlib.Path` | Cycle folder creation | `data/cycles/{cycle_number}/` numbered directories |
| `json` | Artifact serialization | Agent memos, debate transcripts, consensus snapshots as JSON |
| `shutil` | Cycle folder management | Atomic directory operations, archive old cycles |
| `os.replace` | Atomic file writes | Prevent partial-write corruption on cycle artifacts (existing pattern from MemoryRegistry) |
| `textwrap` | CLI output formatting | Wrap long thesis summaries in replay display |
| `itertools.count` | Cycle numbering | Monotonic cycle counter from last persisted cycle |

---

## Feature-by-Feature Stack Decisions

### 1. Per-Cycle Artifact Persistence

**Implementation:** Filesystem (numbered directories) + PostgreSQL metadata index.

**Why filesystem, not pure PostgreSQL:**
- Decision cards are already written to `data/audit.jsonl` (filesystem)
- MEMORY.md entries are already filesystem-based
- Numbered cycle folders (`data/cycles/0001/`, `data/cycles/0002/`) provide instant human browsability
- PostgreSQL stores the cycle metadata index (cycle_number, task_id, timestamp, outcome, artifact_paths) for queries

**Artifact schema (Pydantic -- already installed):**
```python
class CycleArtifact(BaseModel):
    cycle_number: int
    task_id: str
    timestamp: datetime
    agent_memos: dict[str, dict]       # {handle: memo_content}
    debate_transcript: list[dict]       # Full debate_history from SwarmState
    consensus: dict                     # weighted_consensus_score + debate_resolution
    merit_scores: dict[str, dict]       # KAMI scores snapshot
    decision_card: Optional[dict]       # Full DecisionCard if trade executed
    execution_result: Optional[dict]    # OrderRouter result
    cycle_status: str                   # "executed" | "held" | "rejected" | "failed"
```

**File layout per cycle:**
```
data/cycles/0001/
    manifest.json          # CycleArtifact serialized (single source of truth)
    decision_card.json     # Extracted for standalone audit (duplicate of field in manifest)
    debate_transcript.json # Extracted for replay CLI readability
```

**No new library needed.** `pydantic.BaseModel.model_dump(mode="json")` + `json.dumps()` + `pathlib.Path.write_text()` covers all persistence. The `os.replace()` atomic write pattern from `MemoryRegistry` should be reused for manifest.json to prevent corruption.

**PostgreSQL index table:**
```sql
CREATE TABLE cycle_index (
    cycle_number INTEGER PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    cycle_status VARCHAR(32) NOT NULL,
    consensus_score REAL,
    artifact_path TEXT NOT NULL
);
```

Uses existing `psycopg` async pattern -- no new library.

**Confidence:** HIGH -- all components are proven patterns already in use.

---

### 2. Cycle Replay CLI

**Implementation:** `typer` CLI + `rich` terminal output.

**Why typer (not argparse or click directly):**
- Already installed (v0.24.1, transitive dependency)
- Type-hint-driven -- matches project's Pydantic/typing-heavy style
- Built on Click internally, so advanced features (chaining, groups) available
- Auto-generated --help with rich formatting
- Python 3.12 compatible (requires >=3.10)

**Why rich (not plain print or tabulate):**
- Already installed (v14.3.3, transitive dependency)
- `rich.table.Table` for merit score comparison across cycles
- `rich.panel.Panel` for agent memo display with borders
- `rich.syntax.Syntax` for JSON highlighting of decision cards
- `rich.console.Console.pager()` for long debate transcripts
- `rich.progress.Progress` for scanning cycle directories

**CLI structure:**
```
quantum-swarm replay list                    # List all cycles with summary
quantum-swarm replay show <cycle_number>     # Full cycle display
quantum-swarm replay step <cycle_number>     # Step-through navigation (n/p/q)
quantum-swarm replay compare <c1> <c2>       # Side-by-side merit/consensus diff
quantum-swarm replay merit-trend             # Merit score trend across cycles
```

**Step-through navigation:** Not a TUI (Textual would be overkill). Instead, use `rich.prompt.Prompt` for simple n(ext)/p(rev)/q(uit) navigation between cycle phases:
1. Agent Memos (macro_report, quant_proposal, bullish_thesis, bearish_thesis)
2. Soul-Sync Handshake context
3. Debate Transcript + Consensus
4. Risk Gate Decision
5. Execution Result + Decision Card
6. KAMI Merit Update

This is a sequential pager, not a reactive TUI. Much simpler to build and maintain.

**Do NOT use Textual:** Full TUI framework is unnecessary complexity for a replay viewer. The replay CLI is a diagnostic tool, not a dashboard. rich + typer covers the need completely.

**Confidence:** HIGH -- both libraries already installed and well-documented.

---

### 3. HEXACO-6 Personality Model for Diverse Personas

**Implementation:** Pure content authoring + Pydantic validation schema. No personality library needed.

**What HEXACO-6 is:** A six-factor personality model (Honesty-Humility, Emotionality, eXtraversion, Agreeableness, Conscientiousness, Openness). Each factor has 4 facets (24 facets total). It extends the Big Five with the Honesty-Humility dimension -- relevant for financial agents where trustworthiness and manipulation-resistance matter.

**Why HEXACO-6 (not Big Five or MBTI):**
- Honesty-Humility dimension directly maps to financial ethics (manipulation avoidance, fairness in analysis)
- Six orthogonal dimensions provide more personality space for 5 agents than Big Five's 5 dimensions
- Academic foundation with published scales (hexaco.org) -- not pop psychology
- Each agent can be profiled on all 6 dimensions with concrete behavioral predictions

**Implementation approach:**
1. Define a `HexacoProfile` Pydantic model with 6 float fields (1.0-5.0 scale matching HEXACO-PI-R)
2. Each agent's SOUL.md gains a `hexaco_profile:` YAML block alongside existing `drift_guard:`
3. The profile is loaded by `soul_loader.py` (extend `AgentSoul` with a `hexaco: HexacoProfile` field)
4. Profiles inform SOUL.md prose content (manual authoring, not generated)
5. Diversity validation: ensure all 5 agents span the HEXACO space (no two agents with identical high-H, high-C profiles)

**Proposed agent HEXACO profiles (authoring guide, not code):**

| Agent | H | E | X | A | C | O | Design Rationale |
|-------|---|---|---|---|---|---|-----------------|
| AXIOM (macro) | 4.5 | 2.0 | 2.5 | 3.0 | 4.5 | 4.0 | High honesty (no manipulation), low emotionality (stoic veteran), high conscientiousness (methodical) |
| MOMENTUM (bull) | 3.5 | 3.0 | 4.5 | 2.5 | 3.0 | 4.5 | High extraversion (bold, energetic), low agreeableness (willing to fight for thesis), high openness (creative) |
| CASSANDRA (bear) | 4.0 | 4.0 | 2.0 | 2.0 | 4.0 | 3.5 | High emotionality (anxiety-driven risk awareness), low extraversion (cautious), low agreeableness (contrarian) |
| SIGMA (quant) | 4.0 | 1.5 | 2.0 | 3.5 | 5.0 | 3.0 | Lowest emotionality (pure logic), highest conscientiousness (rigorous), moderate agreeableness (data-driven compromise) |
| GUARDIAN (risk) | 5.0 | 3.0 | 2.0 | 3.0 | 5.0 | 2.0 | Highest honesty (incorruptible gate), highest conscientiousness, lowest openness (conservative, rule-bound) |

**Pydantic schema (already installed):**
```python
class HexacoProfile(BaseModel):
    honesty_humility: float = Field(ge=1.0, le=5.0)
    emotionality: float = Field(ge=1.0, le=5.0)
    extraversion: float = Field(ge=1.0, le=5.0)
    agreeableness: float = Field(ge=1.0, le=5.0)
    conscientiousness: float = Field(ge=1.0, le=5.0)
    openness: float = Field(ge=1.0, le=5.0)
```

**Diversity validation (stdlib):** Euclidean distance between all agent profile pairs; flag if any pair distance < 1.5 (too similar). This is a build-time check, not runtime -- pure `math.sqrt` and `sum`, no numpy needed.

**No personality generation library.** The HEXACO profile is a structured metadata tag that guides human SOUL.md authoring. The LLM does not "run" the HEXACO model -- it receives the authored prose that was informed by the profile. This is intentional: personality is in the prose, not in a runtime trait engine.

**Confidence:** HIGH -- HEXACO-6 is well-documented, Pydantic validation is trivial, authoring is manual.

---

### 4. End-to-End Pipeline Hardening

**Implementation:** `structlog` (new) + existing `psycopg` + configuration hardening.

**Why structlog (not stdlib logging alone):**
- Production market data runs need JSON-structured logs for post-mortem analysis
- structlog wraps stdlib logging -- existing `logging.getLogger()` calls continue to work
- Adds contextual fields (task_id, cycle_number, agent_handle) to every log line without explicit passing
- Zero-migration: configure once at application entry point, all existing loggers gain structure
- Lightweight: pure Python, no C extensions, no heavy dependencies

**Why NOT alternatives:**

| Alternative | Rejected Because |
|-------------|-----------------|
| `python-json-logger` | Less flexible binding model; structlog's processors are more powerful |
| `loguru` | Replaces stdlib logging entirely -- too invasive for 30,600 LOC codebase |
| `stdlib logging` (as-is) | Unstructured text is not parseable for production incident analysis |

**Hardening additions (no new deps):**

| Area | What | Library |
|------|------|---------|
| Retry with backoff | Wrap `data_fetcher_node` for transient API failures (yfinance, ccxt) | stdlib `time.sleep` + manual exponential backoff (3 retries, 1s/2s/4s) |
| Circuit breaker | Track consecutive failures per external API; skip after N failures | stdlib `collections.defaultdict` + counter logic |
| Timeout enforcement | Wrap LLM calls with configurable timeout | `asyncio.wait_for()` (stdlib) |
| Graceful degradation | If data_fetcher fails, populate partial state and continue to consensus | Existing LangGraph conditional edges |
| Cycle numbering | Monotonic counter from PostgreSQL `cycle_index` sequence | `psycopg` (existing) |

**Production configuration (no new deps):**
```yaml
# config/swarm_config.yaml additions
pipeline:
  max_retries: 3
  retry_backoff_base: 1.0
  llm_timeout_seconds: 60
  circuit_breaker_threshold: 5
  circuit_breaker_reset_seconds: 300
```

**Confidence:** HIGH for structlog integration. MEDIUM for circuit breaker (pattern is clear but needs careful testing with real market data APIs).

---

## Installation

```bash
# Promote transitive deps to explicit (already installed, no download)
# Add new dependency
uv add typer rich structlog
```

**Changes to pyproject.toml:**
```toml
dependencies = [
    # ... existing ...
    # v1.4: Observable Swarm
    "typer>=0.24.0",
    "rich>=14.0.0",
    "structlog>=24.0.0",
]
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| CLI framework | typer | argparse | Verbose, no auto-complete, no rich integration |
| CLI framework | typer | click (direct) | More boilerplate; typer wraps click with type hints |
| Terminal output | rich | tabulate | No panels, no syntax highlighting, no pager |
| TUI framework | rich (panels) | textual | Full TUI is overkill for replay; textual adds async complexity |
| Structured logging | structlog | loguru | loguru replaces stdlib logging entirely; too invasive |
| Structured logging | structlog | python-json-logger | Less flexible processor pipeline |
| Personality model | HEXACO-6 | Big Five (OCEAN) | Missing Honesty-Humility; only 5 dimensions for 5 agents |
| Personality model | HEXACO-6 | MBTI | Not empirically validated; 16 types are categorical not continuous |
| Cycle persistence | Filesystem + PG index | Pure PostgreSQL JSONB | Loses human-browsable artifact files; JSONB querying is slower for large blobs |
| Cycle persistence | Filesystem + PG index | SQLite per cycle | Adds second DB engine; PostgreSQL already handles metadata well |
| Retry logic | Manual backoff | tenacity library | One more dependency for 15 lines of retry code; not justified |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|------------|
| textual (TUI framework) | Async TUI framework for a sequential replay tool is architectural overkill; adds 2MB+ dep | rich panels + typer prompts for step-through |
| tenacity (retry library) | 15 lines of manual backoff code does not justify a new dependency | `for attempt in range(max_retries): time.sleep(backoff)` |
| loguru | Replaces stdlib logging; 30,600 LOC codebase uses `logging.getLogger()` everywhere | structlog (wraps stdlib, non-invasive) |
| SQLAlchemy / Alembic | Project uses raw psycopg3 throughout; ORM adds complexity without value at this scale | Raw `CREATE TABLE` + `psycopg.execute()` |
| pandas for cycle analysis | Already installed but importing pandas for simple merit trend display is wasteful | List comprehensions + rich.table |
| Any HEXACO personality library | HEXACO profiles are static metadata tags, not runtime simulations | Pydantic model + manual SOUL.md authoring |
| sentence-transformers for replay search | Full-text search over cycles is not a v1.4 requirement | grep-style filtering by cycle_status or consensus_score range |

---

## SwarmState Extensions Required

```python
# To add to src/graph/state.py for v1.4
cycle_number: Optional[int]              # Monotonic cycle counter from PostgreSQL sequence
cycle_artifact_path: Optional[str]       # Path to data/cycles/{number}/ for current run
```

Minimal additions. The cycle artifact writer node reads existing state fields (macro_report, quant_proposal, bullish_thesis, bearish_thesis, debate_history, weighted_consensus_score, merit_scores, decision_card_audit_ref, execution_result) and persists them to the cycle folder. No new data flows through state.

---

## PostgreSQL Schema Extensions

```sql
-- Cycle index table (new)
CREATE TABLE cycle_index (
    cycle_number SERIAL PRIMARY KEY,
    task_id VARCHAR(64) NOT NULL UNIQUE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    cycle_status VARCHAR(32) NOT NULL DEFAULT 'running',
    consensus_score REAL,
    artifact_path TEXT NOT NULL,
    CONSTRAINT valid_status CHECK (cycle_status IN ('running', 'executed', 'held', 'rejected', 'failed'))
);

CREATE INDEX idx_cycle_status ON cycle_index(cycle_status);
CREATE INDEX idx_cycle_started ON cycle_index(started_at);
```

Uses existing `psycopg` async pool from `src/core/db.py`. The `SERIAL` type provides monotonic cycle numbering without application-level coordination.

---

## Integration Points

| New Component | Integrates With | How |
|---------------|----------------|-----|
| Cycle artifact writer (new node) | orchestrator.py | New node after `memory_writer`, before `trade_logger` in graph edge chain |
| Cycle number allocator | db.py `get_pool()` | INSERT INTO cycle_index RETURNING cycle_number at graph entry |
| Replay CLI | data/cycles/ filesystem | Reads manifest.json files; no graph dependency |
| HEXACO profiles | soul_loader.py | Extend `AgentSoul` dataclass with `hexaco: Optional[HexacoProfile]` |
| structlog | orchestrator.py entry | Configure at `create_orchestrator_graph()` -- all downstream loggers gain structure |

---

## Version Compatibility

| Package | Version | Python 3.12 | Notes |
|---------|---------|-------------|-------|
| typer | 0.24.1 (installed) | Yes (>=3.10) | Pin `>=0.24.0` to stay on current major |
| rich | 14.3.3 (installed) | Yes | Pin `>=14.0.0` for Panel/Table API stability |
| structlog | latest (new) | Yes | Pure Python, no binary deps |
| pydantic | 2.12.5 (installed) | Yes | Already used for DecisionCard; reuse for CycleArtifact + HexacoProfile |
| psycopg | 3.3.3 (installed) | Yes | Async pool pattern unchanged |

---

## Sources

- [HEXACO-PI-R Scale Descriptions](https://hexaco.org/scaledescriptions) -- Official HEXACO factor/facet definitions. HIGH confidence.
- [Rich PyPI](https://pypi.org/project/rich/) -- v14.3.3 confirmed current. HIGH confidence.
- [Typer PyPI](https://pypi.org/project/typer/) -- v0.24.1 confirmed current. HIGH confidence.
- pyproject.toml (project file, current) -- Verified installed dependency set. HIGH confidence.
- `uv pip list` (local env) -- Confirmed rich 14.3.3, typer 0.24.1, pydantic 2.12.5 already installed. HIGH confidence.
- src/core/decision_card.py, src/graph/nodes/memory_writer.py (project files) -- Existing persistence patterns. HIGH confidence.
- src/graph/orchestrator.py (project file) -- Graph edge topology for integration point planning. HIGH confidence.

---
*Stack research for: Quantum Swarm v1.4 Beta: Observable Swarm*
*Researched: 2026-03-08*
