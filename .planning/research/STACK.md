# Stack Research — MBS Persona System (v1.3)

**Domain:** Multi-Agent Persona Architecture (SoulLoader, KAMI, Theory of Mind, ARS)
**Researched:** 2026-03-08
**Confidence:** HIGH

---

## Verdict: No New Dependencies Required

All four MBS persona system features are achievable with Python stdlib and the libraries already installed in `pyproject.toml`. This is the core finding and the primary architectural decision.

| Feature | Implementation | New Dep? |
|---------|---------------|----------|
| SoulLoader + lru_cache | `pathlib.Path`, `functools.lru_cache`, `dataclasses` | None |
| KAMI Merit Index + EMA decay | `numpy` (already installed), pure arithmetic | None |
| Theory of Mind Soul-Sync | String slicing on loaded `AgentSoul` objects | None |
| ARS Drift Auditor | `re`, `datetime`, `pathlib`, `json` (all stdlib) | None |
| KAMI persistence to PostgreSQL | `psycopg` (already installed, async) | None |
| Per-agent MEMORY.md evolution log | `pathlib.Path.write_text()` (stdlib) | None |
| Agent Church approval gate | LangGraph conditional edge (already installed) | None |

---

## Recommended Stack

### Core Technologies (Existing — No Change)

| Technology | Version in pyproject.toml | Role in MBS System |
|------------|--------------------------|-------------------|
| Python 3.12 | `>=3.12` (runtime) | EMA arithmetic, dataclasses, functools |
| LangGraph | `>=0.2.0` | Graph nodes for Soul-Sync, Church gate, ARS auditor |
| langchain-google-genai | `>=2.0.0` | LLM calls inside nodes that use injected soul prompts |
| numpy | `>=1.24` | EMA decay calculation for KAMI (already in stack) |
| psycopg | `>=3.3.3` | KAMI score persistence to PostgreSQL |
| pyyaml | `>=6.0.2` | Optional: SOUL.md frontmatter parsing if metadata section added |

### Supporting Stdlib Modules (Zero Install Cost)

| Module | Purpose | Specific Use |
|--------|---------|-------------|
| `functools.lru_cache` | Persona file caching | `@lru_cache(maxsize=None)` on `load_soul()` — cache is frozen because soul files are immutable at runtime |
| `pathlib.Path` | File I/O for soul dirs | Read SOUL.md, IDENTITY.md, AGENTS.md; write MEMORY.md evolution entries |
| `dataclasses.dataclass(frozen=True)` | Immutable soul container | `AgentSoul` dataclass — frozen ensures lru_cache hashability |
| `re` | Drift pattern matching | ARS auditor parses MEMORY.md evolution log entries for sentiment/topic drift |
| `datetime` / `timezone` | Timestamping | KAMI score timestamps, MEMORY.md log entries, ARS audit windows |
| `json` | Structured persistence | KAMI score snapshots in state; ARS report output |
| `math` | EMA formula | `math.exp(-λ * t)` for time-decay weight (alternative to numpy for scalar EMA) |
| `collections.deque` | Sliding ARS window | Fixed-length window over MEMORY.md log entries for drift scoring |
| `difflib.unified_diff` | SOUL.md diff generation | Agent Church approval gate — shows proposed SOUL.md change as readable diff |

---

## Feature-by-Feature Implementation Notes

### 1. SoulLoader + lru_cache (SOUL-01 through SOUL-07)

**Implementation:** Pure stdlib. No new libraries.

```python
from pathlib import Path
from functools import lru_cache
from dataclasses import dataclass
```

`lru_cache` on `load_soul(agent_id: str)` works because:
- `AgentSoul` is a `frozen=True` dataclass (hashable)
- The cache key is a single string (`agent_id`)
- Soul files are read-only at runtime — no cache invalidation needed
- `warmup_soul_cache()` iterates `souls/` at graph creation, populating the cache during `create_orchestrator_graph()`

Path-traversal guard is pure Python string checking (no `os.path.realpath` needed given the simple `"/" in agent_id or ".." in agent_id` check).

**Confidence:** HIGH — plan already contains the complete implementation (`persona_plan.md` §4).

---

### 2. KAMI Merit Index + EMA Decay (KAMI-01 through KAMI-04)

**Implementation:** numpy (already installed) or pure Python `math` — either works. numpy is preferred because it's already a dependency and handles vectorised score history naturally.

EMA formula:
```
KAMI_new = λ * score_new + (1 - λ) * KAMI_old
```

Bounds enforcement: `max(0.1, min(1.0, KAMI_new))`
Cold start: initialise to `0.5` when no prior score exists in SwarmState.

Multi-dimensional formula from PROJECT.md:
```
Merit = α·Accuracy + β·Recovery + γ·Consensus + δ·Fidelity
```

All four components are scalar floats derived from existing SwarmState fields:
- Accuracy: derived from `backtest_result` Sharpe ratio (already computed by RuleValidator)
- Recovery: boolean success after tool failure (observable from `messages` list)
- Consensus: peer agreement signal from `weighted_consensus_score` (already in SwarmState)
- Fidelity: PersonaScore proxy — keyword match rate against `AgentSoul.identity` content

**No new library needed.** `numpy.clip` and scalar arithmetic cover all cases.

**KAMI persistence (KAMI-04):** Add a `kami_scores: dict[str, float]` field to SwarmState and mirror to PostgreSQL via the existing `psycopg` async connection in `src/core/db.py`. A new `kami_scores` table with `(agent_id, score, timestamp)` is the minimal schema — no ORM, just raw psycopg INSERT.

**Confidence:** HIGH — EMA and bounds are standard numpy/math, no exotic libraries.

---

### 3. Theory of Mind Soul-Sync Handshake (TOM-01, TOM-02)

**Implementation:** Pure string operations on loaded `AgentSoul` objects. No new libraries.

Soul-Sync works by truncating `AgentSoul.system_prompt_injection` to a token budget before debate:
- Budget: ~200 tokens per peer summary (per persona_plan.md §2 file budgets)
- Truncation: `summary = soul.system_prompt_injection[:800]` (characters, ≈200 tokens at 4 chars/token average)

This summary is injected into the `user` role of the debate messages before BullishResearcher/BearishResearcher nodes execute — a pure state mutation, no extra library.

Empathetic Refutation (TOM-02) is a prompt engineering change in the researcher system prompt, not a code library. The Drift Guard pattern from `IDENTITY.md` already handles this: each agent's Drift Guard section instructs it to address peer persona logic rather than flat-reject.

**Confidence:** HIGH — zero-library feature; implementation is in prompt content and message ordering.

---

### 4. ARS Drift Auditor (ARS-01, ARS-02)

**Implementation:** `re`, `pathlib`, `datetime`, `collections.deque` — all stdlib. No new libraries.

ARS drift score algorithm:
1. Read all agents' `MEMORY.md` files via `pathlib.Path`
2. Parse timestamped self-reflection entries with `re` (consistent format enforced by EVOL-01)
3. Compute semantic drift proxy: cosine similarity of word-frequency vectors across rolling N-entry windows
4. Flag if drift score exceeds threshold (configurable, default 0.35)

For semantic similarity without a vector library: use `collections.Counter` over word frequencies + manual dot-product. This is sufficient for the ARS audit use case — the signal being detected (topic/sentiment drift in agent writing) is coarse enough that full embedding models are not needed and would add unnecessary dependency weight.

If higher-fidelity drift detection is needed in future: `sentence-transformers` is already in `pyproject.toml` (`>=5.2.3`) and could be used without a new install. Hold this option for v2.0.

**Alert mechanism:** Log to `data/audit.jsonl` (existing audit pipeline) and set a flag in SwarmState. No external alerting library needed for v1.3 scope.

**Confidence:** HIGH — ARS drift is an internal metric over text files; stdlib Counter-based cosine is proven sufficient.

---

## Installation

No changes to `pyproject.toml` are required. All capabilities exist in the current installed environment.

```bash
# Nothing to install — all features use:
# - stdlib: functools, pathlib, dataclasses, re, datetime, json, math, collections, difflib
# - Already in pyproject.toml: numpy>=1.24, psycopg>=3.3.3, langgraph>=0.2.0, pyyaml>=6.0.2
```

---

## Alternatives Considered

| Feature | Considered | Rejected Because |
|---------|-----------|-----------------|
| KAMI EMA | `scipy.stats.exponential_smoothing` | Already have numpy; scipy adds no value for a single EMA formula |
| ARS drift | `sentence-transformers` embeddings | Already in pyproject.toml but adds 200-500ms latency per audit run; Counter-cosine is sufficient for v1.3 coarse detection |
| ARS drift | `chromadb` vector store | Already broken in env (known issue); not appropriate for file-level drift detection |
| Soul-Sync truncation | tiktoken for exact token counting | Would add a new dep; 4 chars/token approximation is safe at 200-token budget |
| SOUL.md parsing | `markdown-it-py` | pyyaml (already installed) handles any frontmatter; plain string reads handle body |
| KAMI persistence | SQLAlchemy ORM | Project uses raw psycopg3 async throughout; introducing ORM contradicts existing pattern |
| Agent Church diffs | `pygit2` or `gitpython` | `difflib.unified_diff` (stdlib) produces readable diffs; no git operation needed |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|------------|
| `sentence-transformers` for ARS (v1.3) | GPU/CPU overhead not justified for coarse drift scoring at v1.3 scale; adds 30s+ cold start | `collections.Counter` cosine similarity on MEMORY.md word frequencies |
| `asyncio.run()` inside node functions | Known project pitfall — breaks async event loop; caused MEM-06 defect | `ThreadPoolExecutor` for sync file I/O in async contexts, or use synchronous `Path.read_text()` directly (soul files are small, sync read is fine) |
| Module-level `AgentSoul` instantiation | LLM lazy-init pattern applies here too — `warmup_soul_cache()` should only be called at graph creation time, not at import | Use `warmup_soul_cache()` inside `create_orchestrator_graph()`, not at module level |
| `MEMORY.md` as SQLite/JSON store | Defeats the RLAF self-reflection narrative: agents write prose reasoning, not structured records | Append-only markdown with timestamped H2 sections; ARS auditor parses the prose |
| Pydantic for `AgentSoul` | `lru_cache` requires hashable arguments/returns; Pydantic models are not hashable by default | `dataclasses.dataclass(frozen=True)` — immutable, hashable, zero-dep, IDE-friendly |

---

## SwarmState Extensions Required

These are state schema changes, not library additions:

```python
# To add to src/graph/state.py for v1.3
active_persona: Optional[str]         # SOUL-04: agent_id of active soul
system_prompt: Optional[str]          # SOUL-04: composed soul injection (not in messages)
kami_scores: Optional[dict]           # KAMI-04: {agent_id: float} merit index scores
soul_sync_summaries: Optional[dict]   # TOM-01: {agent_id: str} truncated soul for debate
ars_flags: Optional[list]             # ARS-02: list of agent_ids with drift flag set
```

None of these require new types beyond what `typing` stdlib provides.

---

## Version Compatibility

| Package | Installed Constraint | MBS Usage | Known Issues |
|---------|---------------------|-----------|-------------|
| numpy | `>=1.24` | EMA arithmetic, `np.clip()` | None — scalar ops are stable across all numpy versions |
| psycopg | `>=3.3.3` | KAMI score INSERT | Async-only pattern — use `await conn.execute()`, not sync psycopg2 API |
| langgraph | `>=0.2.0` | ARS + Church conditional edges | `workflow.branches` (conditional) + `workflow.edges` (direct) — check both when inspecting graph topology |
| pyyaml | `>=6.0.2` | Optional SOUL.md frontmatter | Only needed if SOUL.md gains structured YAML front matter; not required for Tier 1 |

---

## Sources

- `persona_plan.md` (project file, 2026-03-05) — SoulLoader API design, file format, lru_cache pattern. HIGH confidence.
- `docs/SOT_PERSONA_REWARD_SYSTEM.md` (project file, 2026-03-05) — KAMI formula, ARS audit specification, Agent Church governance. HIGH confidence.
- `pyproject.toml` (project file, current) — Verified installed dependency set. HIGH confidence.
- `src/graph/state.py` (project file, current) — SwarmState TypedDict shape, existing fields. HIGH confidence.
- `src/graph/debate.py` (project file, current) — DebateSynthesizer integration point for KAMI weighting. HIGH confidence.
- Python 3.12 docs — `functools.lru_cache`, `dataclasses`, `pathlib`, `difflib`. HIGH confidence (stdlib).
- numpy docs — `np.clip()`, scalar EMA arithmetic. HIGH confidence.

---
*Stack research for: Quantum Swarm v1.3 MBS Persona System*
*Researched: 2026-03-08*
