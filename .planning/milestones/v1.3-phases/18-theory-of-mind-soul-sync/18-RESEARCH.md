# Phase 18: Theory of Mind Soul-Sync — Research

**Researched:** 2026-03-08
**Domain:** LangGraph barrier node topology, frozen dataclass extension, H2 markdown section extraction, few-shot static content authoring
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Graph Topology**
- Barrier node position: `{bullish_researcher, bearish_researcher} → soul_sync_handshake_node → debate_synthesizer`
- Researchers run in parallel (fan-out topology preserved exactly)
- `soul_sync_handshake_node` is a join/barrier that fires after both researcher threads complete
- `soul_sync_handshake_node` makes zero LLM calls — pure lru_cache reads
- DebateSynthesizer is unchanged in Phase 18; still uses KAMI merit scores for weighting

**soul_sync_context SwarmState field**
- New field: `soul_sync_context: Optional[Dict[str, str]] = None`
- Plain field, no Annotated reducer (same pattern as `merit_scores`)
- Written once by `soul_sync_handshake_node`, never accumulated
- Content: `{"MOMENTUM": "<300-char summary>", "CASSANDRA": "<300-char summary>"}`
- Pre-declared in `AUDIT_EXCLUDED_FIELDS` (already present in audit_logger.py from Phase 17 prep)

**public_soul_summary() method on AgentSoul**
- Included sections (fixed order): `## Core Beliefs`, `## Voice`, `## Non-Goals`
- Excluded sections: `{"Drift Guard", "Core Wounds"}` — guard-only if absent (no-op, not error)
- Format: verbatim prose extraction, normalize whitespace, cap at ~300 characters
- Principle: peers see reasoning shape, not vulnerabilities or internal drift tripwires
- "Core Wounds" does not exist in any soul file in Phase 18 — exclusion guard is forward-compatible dormant logic

**AgentSoul — users field (USER.md)**
- `AgentSoul` grows a new field: `users: str` (default `""`)
- Loaded from `USER.md` in the agent's soul directory; graceful degradation — file absent = empty string, not error
- `warmup_soul_cache()` must still pass with missing USER.md
- `AgentSoul.system_prompt` property extended to include `users` content after AGENTS.md
- USER.md content flows into `system_prompt` (SwarmState field), already in `AUDIT_EXCLUDED_FIELDS`

**USER.md Empathetic Refutation Few-Shots**
- Format: fixed prose examples — no `{peer_summary}` or `{peer_handle}` runtime placeholders
- Static examples demonstrating refutation tone and style relative to opponent archetype
- Volume: 2–3 examples per researcher
  - Example themes: opponent makes strong evidence-backed argument; opponent argument is weak/unsupported; neutral/uncertain regime
- Tests: string assertions against static file content (same pattern as Phase 15 soul content fidelity tests)
- Only `bullish_researcher` and `bearish_researcher` require USER.md — other agents do not debate

### Claude's Discretion

- Exact prose content of USER.md few-shot examples for MOMENTUM and CASSANDRA
- Section extraction implementation detail (H2 heading parser, whitespace normaliser)
- Whether `soul_sync_handshake_node` is wrapped with `with_audit_logging` or is bare (no output — no audit record needed)
- `SwarmState` field order for `soul_sync_context` (after `merit_scores`)

### Deferred Ideas (OUT OF SCOPE)

- Dynamic peer soul injection into researcher system prompt at runtime (pre-researcher handshake)
- Richer soul_sync_context structure with metadata (sections_included, generated_at)
- Template-based USER.md with {peer_summary} interpolation
- Full researcher soul population (MOMENTUM/CASSANDRA HEXACO-6 profiles) — SOUL-08, v2+
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TOM-01 | `soul_sync_handshake_node` runs before DebateSynthesizer as a barrier node; reads peer soul summaries from lru_cache into `soul_sync_context` SwarmState field; preserves parallel researcher fan-out topology | LangGraph multi-source edge syntax confirmed; barrier wiring pattern verified in orchestrator; `soul_sync_context` already excluded from audit hash |
| TOM-02 | AgentSoul exposes `public_soul_summary()` method (excludes Drift Guard triggers and Core Wounds from peer view); researcher USER.md files contain Empathetic Refutation few-shot examples | H2 section parser pattern identified; frozen dataclass extension approach confirmed; USER.md loading pattern aligned with try/except FileNotFoundError convention |
</phase_requirements>

---

## Summary

Phase 18 adds Theory of Mind capability to the adversarial debate loop. Before the DebateSynthesizer runs, a new barrier node (`soul_sync_handshake_node`) inserts a curated peer-visible soul summary for each researcher into `SwarmState["soul_sync_context"]`. This context is consumed by Phase 19 (ARS Drift Auditor) downstream — the DebateSynthesizer itself is not changed in this phase. The entire handshake makes zero LLM calls, reads only from the in-process lru_cache, and is invisible to the MiFID II audit chain because `soul_sync_context` was pre-declared in `AUDIT_EXCLUDED_FIELDS` during Phase 17.

The phase has three implementation surfaces. First, `AgentSoul` gains a `public_soul_summary()` method (H2 section parser filtering to `Core Beliefs`, `Voice`, `Non-Goals`; capped at 300 chars) and a `users: str` field loaded from an optional `USER.md` file. Second, `soul_sync_handshake_node` is a new graph node wired as a LangGraph multi-predecessor barrier between the researcher fan-in and the debate synthesizer. Third, `USER.md` files are authored for MOMENTUM and CASSANDRA with 2–3 static Empathetic Refutation few-shot examples each.

All three surfaces are achievable with zero new dependencies. The code patterns are directly precedented by existing project infrastructure: frozen dataclass extension follows the `merit_scores` plain-field pattern; the barrier edge uses LangGraph's existing `add_edge(list, str)` syntax already used for `["bullish_researcher", "bearish_researcher"]`; the USER.md loading follows the same `try/except FileNotFoundError` graceful degradation as skeleton soul files in Phase 15.

**Primary recommendation:** Implement in three plans — (1) `AgentSoul` extension + `public_soul_summary()` + USER.md loading; (2) `soul_sync_handshake_node` + graph rewiring; (3) USER.md content authoring + test suite.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `dataclasses` (stdlib) | Python 3.12 | `AgentSoul` frozen dataclass extension | Already in use; frozen=True required for lru_cache hashability |
| `functools.lru_cache` (stdlib) | Python 3.12 | Soul caching across concurrent fan-out reads | Already in use; cache_clear() in conftest autouse fixture |
| `re` (stdlib) | Python 3.12 | H2 heading extraction for public_soul_summary() | Already used in memory_writer.py for MEMORY.md parsing |
| `pathlib.Path` (stdlib) | Python 3.12 | Synchronous file I/O for USER.md load | Project convention — all soul I/O is synchronous Path.read_text() |
| `langgraph.graph.StateGraph` | current | Barrier node wiring via `add_edge(list, str)` | Project graph framework |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typing.Optional`, `Dict` | Python 3.12 | SwarmState type annotation for `soul_sync_context` | New field follows `merit_scores` typing pattern |
| `logging` (stdlib) | Python 3.12 | Structured node logging in `soul_sync_handshake_node` | All nodes use module-level logger |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| H2 regex section parser | Third-party markdown parser (mistune, markdown-it-py) | No new dependency needed; H2 structure is controlled internal format; regex is sufficient and already precedented in the codebase |
| Static USER.md few-shots | Runtime `{peer_summary}` template interpolation | Deferred by decision; static is deterministic and statically testable without LLM mocking |

**Installation:** No new packages required. All functionality achievable with existing `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

Phase 18 adds the following files:

```
src/
├── core/
│   └── soul_loader.py              # AgentSoul: add users field + public_soul_summary()
├── graph/
│   ├── state.py                    # SwarmState: add soul_sync_context field
│   ├── orchestrator.py             # Wire soul_sync_handshake_node as barrier
│   └── nodes/
│       └── soul_sync_handshake.py  # New: barrier node (no LLM, lru_cache reads)
└── core/souls/
    ├── bullish_researcher/
    │   └── USER.md                 # New: MOMENTUM empathetic refutation few-shots
    └── bearish_researcher/
        └── USER.md                 # New: CASSANDRA empathetic refutation few-shots

tests/
└── core/
    └── test_soul_sync.py           # New: TOM-01, TOM-02 test suite
```

### Pattern 1: LangGraph Multi-Source Barrier Edge

**What:** LangGraph supports multi-predecessor edges via `add_edge(list[str], str)`. Both source nodes must produce outputs before the target fires. This is the barrier/join mechanism.

**When to use:** When a node must receive outputs from multiple parallel nodes before executing.

**Current wiring (to be changed):**
```python
# orchestrator.py — existing direct fan-in to debate_synthesizer
workflow.add_edge(["bullish_researcher", "bearish_researcher"], "debate_synthesizer")
```

**Phase 18 rewiring:**
```python
# orchestrator.py — insert soul_sync_handshake_node as barrier
workflow.add_edge(["bullish_researcher", "bearish_researcher"], "soul_sync_handshake_node")
workflow.add_edge("soul_sync_handshake_node", "debate_synthesizer")
```

The existing `["bullish_researcher", "bearish_researcher"]` multi-source edge is removed and replaced with the two lines above. Only these two `add_edge` calls change — all other graph topology is untouched.

### Pattern 2: Frozen Dataclass Field Extension

**What:** Adding `users: str = ""` to the `AgentSoul` frozen dataclass. The `frozen=True` constraint means all fields must remain hashable (str satisfies this). Default empty string provides backward-compatible graceful degradation.

**Existing pattern:**
```python
@dataclass(frozen=True)
class AgentSoul:
    agent_id: str
    identity: str
    soul: str
    agents: str
```

**Phase 18 extension:**
```python
@dataclass(frozen=True)
class AgentSoul:
    agent_id: str
    identity: str
    soul: str
    agents: str
    users: str = ""   # Contents of USER.md; empty string if file absent
```

Fields with defaults must appear after fields without defaults — `users: str = ""` placed last satisfies Python dataclass ordering rules.

### Pattern 3: public_soul_summary() — H2 Section Extraction

**What:** Parse `self.soul` (a markdown string with H2 sections) to extract only peer-visible sections, then truncate to ~300 characters.

**H2 section structure in SOUL.md files (from reading existing files):**
- `## Core Beliefs` — peer-visible (epistemology, reasoning shape)
- `## Drift Guard` — excluded (internal governance, vulnerability data)
- `## Voice` — peer-visible (communication archetype)
- `## Non-Goals` — peer-visible (explicit scope exclusions)

**Implementation approach:**
Split the soul text on `\n## ` boundaries. For each section, check if the heading is in the allowed set. Concatenate allowed sections. Normalize whitespace (collapse multiple newlines to single newline). Truncate to 300 characters at word boundary.

```python
_PEER_VISIBLE_SECTIONS = {"Core Beliefs", "Voice", "Non-Goals"}
_EXCLUDED_SECTIONS = {"Drift Guard", "Core Wounds"}  # Core Wounds: forward-compat guard

def public_soul_summary(self) -> str:
    """Return truncated peer-visible soul view excluding drift/wound sections."""
    import re
    # Split on H2 boundaries (## heading lines)
    parts = re.split(r'\n(?=## )', self.soul)
    allowed_parts = []
    for part in parts:
        # Extract heading name (## Heading Name\n...)
        match = re.match(r'^## (.+)', part.strip())
        if match:
            heading = match.group(1).strip()
            if heading in _PEER_VISIBLE_SECTIONS:
                allowed_parts.append(part.strip())
        else:
            # H1 title block before first H2 — skip
            pass
    text = " ".join(allowed_parts)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Cap at 300 characters at word boundary
    if len(text) > 300:
        text = text[:300].rsplit(' ', 1)[0]
    return text
```

**Expected output shape (from CONTEXT.md example):**
`"CASSANDRA emphasizes regime shifts, inflation surprises, and structural fragility. Speaks in terse, caution-first language. Avoids consensus comfort, narrative smoothing, and overreliance on lagging indicators."`

### Pattern 4: USER.md Graceful Load

**What:** Attempt to read `USER.md` from the agent's soul directory. On `FileNotFoundError`, return empty string. Extend `system_prompt` property to append users content.

**Follows established pattern from Phase 15 skeleton soul handling:**
```python
# In load_soul():
try:
    users = (target / "USER.md").read_text(encoding="utf-8")
except FileNotFoundError:
    users = ""

return AgentSoul(
    agent_id=agent_id,
    identity=identity,
    soul=soul,
    agents=agents,
    users=users,
)

# system_prompt property extension:
@property
def system_prompt(self) -> str:
    parts = [self.identity, self.soul, self.agents]
    if self.users:
        parts.append(self.users)
    return "\n\n".join(parts)
```

### Pattern 5: soul_sync_handshake_node — Silent Barrier Node

**What:** A synchronous-compatible async node that reads lru_cache, builds the soul_sync_context dict, and returns it as the only SwarmState mutation. No LLM calls. Follows `memory_writer_node` template (non-blocking, pure function of in-memory state).

**Whether to wrap with `with_audit_logging`:** The node returns a non-empty dict (the soul_sync_context). Per project convention, nodes that mutate state are wrapped. However, soul_sync_context is excluded from the audit hash by AUDIT_EXCLUDED_FIELDS. Wrapping is safe — the soul_sync_context will appear in audit DB's `output_data` column JSON but will be stripped before SHA-256 hash computation. The recommended approach is to wrap it for consistency, since skipping audit wrapping would be an inconsistency requiring explanation in every future code review.

```python
# src/graph/nodes/soul_sync_handshake.py

from src.core.soul_loader import load_soul

_RESEARCHER_HANDLES = {
    "MOMENTUM": "bullish_researcher",
    "CASSANDRA": "bearish_researcher",
}

async def soul_sync_handshake_node(state: dict) -> dict:
    """Barrier node: read peer soul summaries from lru_cache → soul_sync_context.

    Runs after both researchers complete (LangGraph multi-source edge barrier).
    Zero LLM calls. Pure lru_cache reads. Non-blocking.
    """
    soul_sync_context = {}
    for handle, agent_id in _RESEARCHER_HANDLES.items():
        try:
            soul = load_soul(agent_id)
            soul_sync_context[handle] = soul.public_soul_summary()
        except Exception as e:
            logger.error("soul_sync_handshake: failed to load soul for %s: %s", agent_id, e)
            soul_sync_context[handle] = ""
    return {"soul_sync_context": soul_sync_context}
```

### Pattern 6: USER.md Few-Shot Content Structure

**What:** Static markdown prose file with 2–3 labeled empathetic refutation examples. No runtime placeholders. Content targets the opponent archetype's reasoning style.

**Recommended structure:**
```markdown
# MOMENTUM — User Context

## Empathetic Refutation Examples

### Example 1: Opponent makes a strong evidence-backed argument

[example prose showing how MOMENTUM acknowledges CASSANDRA's evidence
while pivoting to its own directional thesis]

### Example 2: Opponent argument is weak or unsupported

[example prose showing measured pushback without dismissiveness]

### Example 3: Neutral or uncertain regime

[example prose showing how MOMENTUM calibrates conviction when regime signals conflict]
```

CASSANDRA's USER.md follows the same structure but targets MOMENTUM's optimistic framing.

### Anti-Patterns to Avoid

- **Runtime template placeholders in USER.md:** `{peer_summary}` interpolation is deferred. USER.md must be pure static text loadable by SoulLoader without any string formatting.
- **asyncio.run() inside soul_sync_handshake_node:** Project-breaking pattern (MEM-06 defect precedent). `load_soul()` is synchronous; no asyncio required.
- **Mutable default for `users` field:** Do not use `users: str = field(default="")` — `""` is an immutable default and `dataclass(frozen=True)` does not need `field()` for simple immutable defaults.
- **Reducer on soul_sync_context:** Do NOT add `Annotated[..., operator.add]`. The field is written once per cycle by one node; plain `Optional[Dict[str, str]]` with no reducer is correct (same as `merit_scores`).
- **Removing `["bullish_researcher", "bearish_researcher"]` edge without adding it back:** The barrier edge must be replaced with two new edges, not deleted. If only one `add_edge(list)` call is removed without the two replacements, both researchers will flow directly to debate_synthesizer (bypassing the handshake) and the handshake node will be unreachable.
- **Excluding soul_sync_context twice:** It is already in `AUDIT_EXCLUDED_FIELDS`. Do not add it again.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Peer soul visibility filtering | Custom JSON redaction layer, separate "public soul" file | `public_soul_summary()` method on AgentSoul + section parser | Single source of truth; lru_cache already holds the soul; no new I/O |
| Barrier synchronization between parallel nodes | Custom asyncio Event or Lock | LangGraph `add_edge(list, str)` built-in barrier | LangGraph guarantees both sources complete before target fires |
| Runtime peer summary injection into researcher prompts | Pre-researcher handshake node + dynamic prompt assembly | Static USER.md few-shots (deferred) | Locked decision; deferred to v2+ |
| Markdown section parser | Third-party markdown library | `re.split(r'\n(?=## )', text)` | Controlled internal format; stdlib regex sufficient; no new dependency |

**Key insight:** The lru_cache is already populated by `warmup_soul_cache()` at graph creation time. `soul_sync_handshake_node` reads from memory, not filesystem. The entire handshake is a dict construction from cached string data — it is essentially free in terms of I/O cost.

---

## Common Pitfalls

### Pitfall 1: Frozen Dataclass Field Ordering Break

**What goes wrong:** Adding `users: str` without a default before fields that have defaults (if any) — or forgetting that Python dataclass requires fields with defaults to come after fields without defaults.

**Why it happens:** `AgentSoul` currently has four fields, all required (no defaults). Adding `users: str = ""` with a default makes it the only field with a default. It must be placed last.

**How to avoid:** Add `users: str = ""` as the final field of the dataclass. Verify `AgentSoul("macro_analyst", "id", "soul", "agents")` still works (positional, without `users`) — it should, because `users` has a default.

**Warning signs:** `TypeError: non-default argument 'X' follows default argument` at import time.

### Pitfall 2: warmup_soul_cache() Fails When USER.md Absent

**What goes wrong:** If `load_soul()` raises `FileNotFoundError` for missing `USER.md` instead of using the `try/except` pattern, then `warmup_soul_cache()` fails at graph creation time.

**Why it happens:** Phase 15 used mandatory `read_text()` for IDENTITY.md, SOUL.md, AGENTS.md. USER.md is optional. If the same mandatory pattern is used, warmup fails for agents without USER.md (quant_modeler, risk_manager, macro_analyst).

**How to avoid:** Wrap USER.md read in `try/except FileNotFoundError: users = ""`. Test: `warmup_soul_cache()` must complete without error even with no USER.md files present.

**Warning signs:** Graph creation fails at startup with `FileNotFoundError: src/core/souls/quant_modeler/USER.md`.

### Pitfall 3: soul_sync_context Not Initialized in run_task_async

**What goes wrong:** `soul_sync_context` field is added to SwarmState but not initialized in the `initial_state` dict in `run_task_async()`. LangGraph may error or leave the field absent from state.

**Why it happens:** Every new SwarmState field added after Phase 15 requires a matching entry in `initial_state` in `LangGraphOrchestrator.run_task_async()`. Missing entries cause TypedDict validation issues.

**How to avoid:** Add `"soul_sync_context": None` to the `initial_state` dict in `orchestrator.py`'s `run_task_async()` alongside `"merit_scores": None`.

**Warning signs:** KeyError or TypedDict validation warnings during test runs that invoke the full graph.

### Pitfall 4: public_soul_summary() Returns Empty String

**What goes wrong:** The H2 section parser fails to match any sections, returning an empty summary. This silently degrades the soul_sync_context to empty strings.

**Why it happens:** SOUL.md files for the skeleton agents (MOMENTUM, CASSANDRA) use the same H2 structure as AXIOM, but whitespace or encoding differences could cause regex mismatches. Specifically, if the section split regex requires `\n## ` but the file uses Windows line endings (`\r\n##`), the split fails.

**How to avoid:** Normalize line endings with `.replace('\r\n', '\n')` before parsing. Add a test asserting `public_soul_summary()` returns a non-empty string for both bullish_researcher and bearish_researcher.

**Warning signs:** `soul_sync_context` contains `{"MOMENTUM": "", "CASSANDRA": ""}` in test assertions.

### Pitfall 5: Graph Topology Breaks Existing Fan-in Edge

**What goes wrong:** Removing the `["bullish_researcher", "bearish_researcher"]` → `debate_synthesizer` edge without properly replacing it causes the graph to fail compilation or route incorrectly.

**Why it happens:** LangGraph's StateGraph raises errors if nodes have no outgoing edges (unreachable) or if expected predecessors of a node are missing.

**How to avoid:** Delete the single `add_edge(["bullish_researcher", "bearish_researcher"], "debate_synthesizer")` line and replace with exactly two lines:
```python
workflow.add_edge(["bullish_researcher", "bearish_researcher"], "soul_sync_handshake_node")
workflow.add_edge("soul_sync_handshake_node", "debate_synthesizer")
```
Register `soul_sync_handshake_node` as a node before adding edges. Run `build_graph()` smoke test.

**Warning signs:** `langgraph.errors.InvalidUpdateError` or `NodeNotFoundError` at graph compilation.

### Pitfall 6: lru_cache Hashability Broken by users Field Type

**What goes wrong:** If `users` is given a mutable default (e.g., `users: list = field(default_factory=list)`) the frozen dataclass cannot be hashed.

**Why it happens:** `lru_cache` requires all arguments to be hashable. `frozen=True` provides `__hash__` based on all fields. Mutable fields break this.

**How to avoid:** `users: str = ""` — string is immutable and hashable. This is the only acceptable type for the new field given the frozen constraint.

**Warning signs:** `TypeError: unhashable type` when `load_soul()` tries to cache an `AgentSoul` instance.

---

## Code Examples

Verified patterns from existing project source:

### Existing LangGraph Multi-Source Barrier (from orchestrator.py line 316)
```python
# Source: src/graph/orchestrator.py
workflow.add_edge(["bullish_researcher", "bearish_researcher"], "debate_synthesizer")
```
Phase 18 replaces this single call with:
```python
workflow.add_edge(["bullish_researcher", "bearish_researcher"], "soul_sync_handshake_node")
workflow.add_edge("soul_sync_handshake_node", "debate_synthesizer")
```

### Existing Frozen Dataclass Pattern (from soul_loader.py)
```python
# Source: src/core/soul_loader.py
@dataclass(frozen=True)
class AgentSoul:
    agent_id: str
    identity: str
    soul: str
    agents: str
```

### Existing Optional File Load Pattern (from memory_writer.py)
```python
# Source: src/graph/nodes/memory_writer.py
if memory_path.exists():
    existing_content = memory_path.read_text()
```
Phase 18 uses `try/except FileNotFoundError` instead (more idiomatic):
```python
try:
    users = (target / "USER.md").read_text(encoding="utf-8")
except FileNotFoundError:
    users = ""
```

### Existing Plain SwarmState Field Pattern (from state.py)
```python
# Source: src/graph/state.py
# Phase 16: KAMI Merit Index
merit_scores: Optional[Dict[str, Any]]
```
Phase 18 follows this exactly:
```python
# Phase 18: Theory of Mind Soul-Sync
soul_sync_context: Optional[Dict[str, str]]
```

### Existing Silent Node Pattern (from memory_writer.py)
```python
# Source: src/graph/nodes/memory_writer.py
async def memory_writer_node(state: dict) -> dict:
    for handle in ALL_SOUL_HANDLES:
        try:
            _process_agent(handle, state)
        except Exception as e:
            logger.error("memory_writer: unhandled error for %s: %s", handle, e)
    return {}
```
`soul_sync_handshake_node` differs in that it returns a non-empty dict (the soul_sync_context), but otherwise follows the same error-handling shell.

### Existing AUDIT_EXCLUDED_FIELDS Pre-Declaration (from audit_logger.py)
```python
# Source: src/core/audit_logger.py
AUDIT_EXCLUDED_FIELDS: frozenset[str] = frozenset({
    "system_prompt",
    "active_persona",
    "soul_sync_context",   # Pre-declared in Phase 17 for Phase 18
})
```
No changes needed to audit_logger.py in Phase 18.

### Existing system_prompt Property (from soul_loader.py)
```python
# Source: src/core/soul_loader.py
@property
def system_prompt(self) -> str:
    return f"{self.identity}\n\n{self.soul}\n\n{self.agents}"
```
Phase 18 extension:
```python
@property
def system_prompt(self) -> str:
    parts = [self.identity, self.soul, self.agents]
    if self.users:
        parts.append(self.users)
    return "\n\n".join(parts)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Direct `["bullish_researcher", "bearish_researcher"] → debate_synthesizer` edge | `["bullish_researcher", "bearish_researcher"] → soul_sync_handshake_node → debate_synthesizer` | Phase 18 | Barrier node inserted; DebateSynthesizer topology unchanged |
| `AgentSoul` has 4 fields (identity, soul, agents, agent_id) | `AgentSoul` has 5 fields (+users) | Phase 18 | USER.md optional content included in system_prompt |
| `soul_sync_context` pre-declared in AUDIT_EXCLUDED_FIELDS but no SwarmState field | `soul_sync_context: Optional[Dict[str, str]]` added to SwarmState | Phase 18 | ARS Phase 19 can read peer soul summaries from state |

---

## Open Questions

1. **Should soul_sync_handshake_node be wrapped with with_audit_logging?**
   - What we know: The node returns `{"soul_sync_context": {...}}`. `soul_sync_context` is in AUDIT_EXCLUDED_FIELDS, so it is stripped before hash computation. Wrapping is safe.
   - What's unclear: Whether the audit DB entry for this node provides forensic value or just noise.
   - Recommendation: Wrap with `with_audit_logging` for topology consistency. The audit record will show the node ran (useful for debugging) without leaking soul content into the hash chain. This is Claude's discretion per CONTEXT.md.

2. **H2 parser edge case: soul file with no H2 sections?**
   - What we know: All current SOUL.md files (AXIOM, MOMENTUM, CASSANDRA) have H2 sections. The pattern is consistent.
   - What's unclear: Whether a future skeleton soul with only an H1 title and no H2 sections would cause `public_soul_summary()` to return empty.
   - Recommendation: Add a fallback: if no matching H2 sections found, return the first 300 characters of `self.soul` as a degraded summary. Log a warning. This prevents silent empty strings.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (Python 3.12) |
| Config file | none — pytest.ini absent; uses default discovery |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py -x -q` |
| Full suite command | `.venv/bin/python3.12 -m pytest tests/core/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOM-01 | `soul_sync_context` field exists in SwarmState | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestSwarmStateSoulSync -x` | ❌ Wave 0 |
| TOM-01 | `soul_sync_handshake_node` returns dict with MOMENTUM and CASSANDRA keys | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestSoulSyncHandshakeNode -x` | ❌ Wave 0 |
| TOM-01 | Barrier node wiring does not disrupt fan-out topology (build_graph smoke test) | smoke | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestGraphTopology -x` | ❌ Wave 0 |
| TOM-01 | `soul_sync_handshake_node` makes zero LLM calls | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestNoLLMCalls -x` | ❌ Wave 0 |
| TOM-02 | `public_soul_summary()` returns non-empty string for MOMENTUM | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestPublicSoulSummary::test_momentum_summary_non_empty -x` | ❌ Wave 0 |
| TOM-02 | `public_soul_summary()` returns non-empty string for CASSANDRA | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestPublicSoulSummary::test_cassandra_summary_non_empty -x` | ❌ Wave 0 |
| TOM-02 | `public_soul_summary()` excludes Drift Guard content | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestPublicSoulSummary::test_drift_guard_excluded -x` | ❌ Wave 0 |
| TOM-02 | `public_soul_summary()` output is <= 300 characters | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestPublicSoulSummary::test_summary_length -x` | ❌ Wave 0 |
| TOM-02 | `AgentSoul.users` field exists and defaults to empty string | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestAgentSoulUsers -x` | ❌ Wave 0 |
| TOM-02 | USER.md content is included in system_prompt when present | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestAgentSoulUsers::test_users_in_system_prompt -x` | ❌ Wave 0 |
| TOM-02 | `warmup_soul_cache()` completes without error (no USER.md for non-researchers) | smoke | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestWarmupWithUsers -x` | ❌ Wave 0 |
| TOM-02 | USER.md files exist for bullish_researcher and bearish_researcher | content | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestUserMdContent -x` | ❌ Wave 0 |
| TOM-02 | USER.md files contain empathetic refutation examples | content | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestUserMdContent::test_user_md_has_examples -x` | ❌ Wave 0 |
| TOM-01/02 | `AgentSoul` remains hashable after adding `users` field | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py::TestAgentSoulHashability -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python3.12 -m pytest tests/core/test_soul_sync.py -x -q`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest tests/core/ -q`
- **Phase gate:** Full suite (`tests/core/`) green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/core/test_soul_sync.py` — covers TOM-01, TOM-02 (all rows above)
- [ ] `src/graph/nodes/soul_sync_handshake.py` — new node module
- [ ] `src/core/souls/bullish_researcher/USER.md` — new content file
- [ ] `src/core/souls/bearish_researcher/USER.md` — new content file

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `src/core/soul_loader.py` — AgentSoul frozen dataclass, lru_cache, system_prompt property, warmup_soul_cache
- Direct code inspection: `src/graph/orchestrator.py` — existing barrier edge at line 316, with_audit_logging wrapper, run_task_async initial_state dict
- Direct code inspection: `src/graph/state.py` — SwarmState TypedDict, merit_scores plain field pattern
- Direct code inspection: `src/core/audit_logger.py` — AUDIT_EXCLUDED_FIELDS frozenset, soul_sync_context pre-declaration
- Direct code inspection: `src/graph/nodes/memory_writer.py` — silent node pattern, synchronous I/O, try/except error handling
- Direct code inspection: `src/core/souls/*/SOUL.md` — confirmed H2 section structure (Core Beliefs, Drift Guard, Voice, Non-Goals)
- Direct code inspection: `.planning/phases/18-theory-of-mind-soul-sync/18-CONTEXT.md` — all locked decisions and implementation specifics

### Secondary (MEDIUM confidence)
- LangGraph `add_edge(list, str)` multi-source barrier: confirmed by existing usage in orchestrator.py line 316 — same syntax, same version, project already uses this pattern

### Tertiary (LOW confidence)
- None — all claims in this research document are verified against project source code at HIGH confidence

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies; all stdlib and langgraph already in use
- Architecture patterns: HIGH — all patterns are verbatim extensions of existing project code, verified by direct inspection
- Pitfalls: HIGH — derived from direct code reading of the exact files being modified and established project decisions
- Test infrastructure: HIGH — pytest confirmed working (74 tests collected in tests/core/); test patterns verified against existing soul tests

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable domain — no external dependencies being introduced)
