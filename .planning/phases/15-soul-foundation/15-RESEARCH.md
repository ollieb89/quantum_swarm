# Phase 15: Soul Foundation - Research

**Researched:** 2026-03-08
**Domain:** Python dataclasses, functools.lru_cache, pathlib, LangGraph state typing, MiFID II audit exclusion, pytest fixtures
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Soul file format:** H1 file title, H2 canonical sections (IDENTITY.md: Identity / Archetype / Role in Swarm; SOUL.md: Core Beliefs / Drift Guard / Voice / Non-Goals; AGENTS.md: Output Contract / Decision Rules / Workflow), optional H3 substructure. No YAML frontmatter. Free-flowing prose within sections.
- **Macro analyst persona — AXIOM:** Seasoned institutional veteran, 30+ years pattern recognition, measured probabilistic language, sceptical of narrative without data, resists recency bias by default. Drift Guard primary trigger: recency bias / momentum chasing.
- **Skeleton personas (directional stubs, 2–4 sentences per section):**
  - bullish_researcher: Momentum-driven growth hunter — asymmetric upside, concentrated high-conviction positions, catalyst hunter.
  - bearish_researcher: Risk-first stress tester — every thesis has a fatal flaw; probes leverage, liquidity, valuation, tail risks.
  - quant_modeler: Systematic quantitative modeler — model-first, data-driven, sceptical without statistical backing, regime-conditional signal frameworks.
  - risk_manager: Institutional risk officer / guardian archetype — portfolio-level, enforces exposure limits and drawdown constraints as non-negotiable rules.
- **Test directory structure:** `tests/core/` mirrors `src/core/`. `tests/core/conftest.py` autouse fixture named `clear_soul_caches`, clears `load_soul.cache_clear()` only in Phase 15. Test files: `test_soul_loader.py` (unit), `test_persona_content.py` (content fidelity), `test_macro_analyst_soul.py` (integration).
- **SwarmState fields:** `active_persona: Optional[str]` and `system_prompt: Optional[str]` as plain TypedDict fields (no Annotated reducer).
- **Audit exclusion:** Add `AUDIT_EXCLUDED_FIELDS = {"system_prompt", "active_persona", "soul_sync_context"}` in `src/core/audit_logger.py`; strip fields before SHA-256 hashing in `_calculate_hash`.
- **Warmup call site:** `warmup_soul_cache()` called in `src/graph/orchestrator.py` at graph creation time (after `build_graph()`).
- **I/O pattern:** All soul file I/O uses synchronous `Path.read_text()` — `asyncio.run()` inside node functions is a known project-breaking pattern.
- **No new dependencies** — all features achievable with existing `pyproject.toml`.

### Claude's Discretion

- quant_modeler and risk_manager SOUL.md section content (persona seeds established, full prose at Claude's discretion)
- AXIOM's `## Voice` section wording (measured, probabilistic, institutional tone)
- AXIOM's `## Non-Goals` section content
- Exact path-traversal guard implementation in SoulLoader
- SystemMessage injection approach (prepend SystemMessage before agent invocation — synchronous)
- Test assertion depth within each test file

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SOUL-01 | System loads agent soul from filesystem with path-traversal guard and `lru_cache` for consistency across node invocations | SoulLoader architecture: `@lru_cache` on `load_soul(agent_id: str)`, `frozen=True` dataclass for hashability, `Path.resolve()` + prefix check for traversal guard |
| SOUL-02 | `macro_analyst` has fully-populated IDENTITY.md, SOUL.md, and AGENTS.md | AXIOM persona locked by user — three files, standard H2 sections, free-flowing prose |
| SOUL-03 | Four skeleton soul dirs exist with minimum viable content so `warmup_soul_cache()` completes | One dir per skeleton agent, each needing three files with populated H2 sections (2–4 sentences) |
| SOUL-04 | SwarmState carries `active_persona` and `system_prompt` as dedicated non-reducer fields | Add two `Optional[str]` fields to `SwarmState` TypedDict; confirmed by existing `macro_report`, `risk_approved` pattern |
| SOUL-05 | All five L2 nodes inject agent soul into `system_prompt` before LLM execution; fields excluded from audit | MacroAnalyst + QuantModeler in analysts.py, BullishResearcher + BearishResearcher in researchers.py, plus quant_modeler (same file as macro) — audit exclusion via `AUDIT_EXCLUDED_FIELDS` strip |
| SOUL-06 | Autouse fixture calls `load_soul.cache_clear()` before and after every test | `tests/core/conftest.py`, fixture `clear_soul_caches`, yield pattern, scoped to soul tests |
| SOUL-07 | Deterministic test suite — zero LLM calls; string assertions against static files | Three test files in `tests/core/`; mock agents already established in existing test patterns |
</phase_requirements>

---

## Summary

Phase 15 is a pure Python infrastructure phase with no new dependencies. The work divides into three tracks: (1) a new `src/core/soul_loader.py` module implementing `AgentSoul` frozen dataclass + `lru_cache`-decorated `load_soul()` function with path-traversal guard; (2) soul file content authored into `src/core/souls/{agent_id}/` for all five L2 agents; and (3) integration wiring — two new `SwarmState` fields, audit field exclusion, injection into all five L2 node functions, and warmup call in the orchestrator.

The critical cross-cutting concern is MiFID II audit chain integrity. The `AuditLogger._calculate_hash()` method currently serialises its input and output dictionaries with no field exclusion. Any soul content that enters `input_data` or `output_data` will be permanently hashed into the chain. The fix is to strip `AUDIT_EXCLUDED_FIELDS` before serialisation — this must happen inside `_calculate_hash` (or the caller that builds the payload), not at the database insertion point, because the hash is calculated from the pre-serialisation dicts.

The test strategy is entirely deterministic: all tests read static soul files from the filesystem and assert string presence. No LLM calls are made because the soul injection happens before agent invocation and the tests exercise `SoulLoader` and state mutation independently from the agent's LLM sub-graph. The autouse `clear_soul_caches` fixture is the sole mechanism preventing cached souls from bleeding between tests — it must clear the `lru_cache` on `load_soul` both before (isolation guarantee) and after (cleanup guarantee) each test.

**Primary recommendation:** Implement in wave order — SoulLoader + AgentSoul dataclass first (foundation), then soul files (content), then SwarmState + audit wiring (integration), then node injection (wiring), then test suite (validation). Each wave has clear, verifiable exit criteria.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `functools.lru_cache` | stdlib | Cache `load_soul()` return value per `agent_id` string key | `AgentSoul` is frozen (hashable), lru_cache requires hashable args; zero overhead after warm-up |
| `dataclasses.dataclass(frozen=True)` | stdlib | `AgentSoul` immutable value object | Frozen = hashable = safe as lru_cache return; prevents accidental mutation across concurrent fan-out |
| `pathlib.Path` | stdlib | File I/O for soul files | Already used throughout project; `Path.read_text()` is the project-established synchronous I/O pattern |
| `typing.TypedDict` | stdlib | `SwarmState` field additions | `SwarmState` is already a TypedDict; new fields follow the identical pattern of existing `Optional[str]` fields |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langchain_core.messages.SystemMessage` | existing dep | Inject soul content as LLM system prompt | Prepend to message list passed to each L2 agent's LLM invocation |
| `pytest` | >=9.0.2 (dev dep) | Test runner for all soul tests | Project standard; already in pyproject.toml |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@lru_cache` on module-level function | Class-based cache with `__init__` | lru_cache is simpler, `.cache_clear()` built-in (required by SOUL-06 fixture), no state management needed |
| `Path.resolve()` prefix check for traversal guard | `os.path.realpath()` + startswith | `Path.resolve()` is idiomatic pathlib; equivalent behaviour; `os.path` is lower-level and less readable |
| Plain `Optional[str]` SwarmState fields | `Annotated[Optional[str], some_reducer]` | Plain fields overwrite on each update (correct for soul injection — one soul per session); `operator.add` reducer would accumulate unboundedly (wrong) |

**Installation:** No new packages required. All dependencies exist in the project's `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

```
src/
└── core/
    ├── soul_loader.py          # SoulLoader class + load_soul() + warmup_soul_cache() + AgentSoul
    └── souls/
        ├── macro_analyst/
        │   ├── IDENTITY.md     # Identity / Archetype / Role in Swarm
        │   ├── SOUL.md         # Core Beliefs / Drift Guard / Voice / Non-Goals
        │   └── AGENTS.md       # Output Contract / Decision Rules / Workflow
        ├── bullish_researcher/
        │   ├── IDENTITY.md
        │   ├── SOUL.md
        │   └── AGENTS.md
        ├── bearish_researcher/
        │   ├── IDENTITY.md
        │   ├── SOUL.md
        │   └── AGENTS.md
        ├── quant_modeler/
        │   ├── IDENTITY.md
        │   ├── SOUL.md
        │   └── AGENTS.md
        └── risk_manager/
            ├── IDENTITY.md
            ├── SOUL.md
            └── AGENTS.md

tests/
└── core/
    ├── conftest.py             # clear_soul_caches autouse fixture
    ├── test_soul_loader.py     # SoulLoader unit tests
    ├── test_persona_content.py # Content fidelity tests against static files
    └── test_macro_analyst_soul.py  # Integration: node injects soul into state
```

### Pattern 1: AgentSoul Frozen Dataclass

**What:** Immutable value object holding all parsed soul file content, returned by `load_soul()` and cached via `lru_cache`.

**When to use:** Any code that needs to access agent identity. Always go through `load_soul()` — never read soul files directly from outside `soul_loader.py`.

**Example:**
```python
# src/core/soul_loader.py
from __future__ import annotations
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

SOULS_DIR = Path(__file__).parent / "souls"
SOUL_FILES = ("IDENTITY.md", "SOUL.md", "AGENTS.md")

@dataclass(frozen=True)
class AgentSoul:
    """Immutable identity snapshot for one L2 agent."""
    agent_id: str
    identity: str       # Contents of IDENTITY.md
    soul: str           # Contents of SOUL.md
    agents: str         # Contents of AGENTS.md

    @property
    def system_prompt(self) -> str:
        """Concatenated soul content for LLM system prompt injection."""
        return f"{self.identity}\n\n{self.soul}\n\n{self.agents}"

    @property
    def active_persona(self) -> str:
        """Agent handle extracted from IDENTITY.md first line."""
        # First H1 line of IDENTITY.md, e.g., "# AXIOM"
        first_line = self.identity.splitlines()[0].lstrip("# ").strip()
        return first_line
```

### Pattern 2: Path-Traversal Guard + lru_cache

**What:** Validate the `agent_id` string resolves to a subdirectory of `SOULS_DIR` before any filesystem access.

**When to use:** Inside `load_soul()` — before any `Path.read_text()` call.

**Example:**
```python
@lru_cache(maxsize=None)
def load_soul(agent_id: str) -> AgentSoul:
    """Load and cache an agent's soul from the filesystem."""
    # Path-traversal guard: resolve and verify prefix
    target = (SOULS_DIR / agent_id).resolve()
    if not str(target).startswith(str(SOULS_DIR.resolve())):
        raise ValueError(f"Invalid agent_id — path traversal detected: {agent_id!r}")

    if not target.is_dir():
        raise FileNotFoundError(f"No soul directory for agent: {agent_id!r}")

    identity = (target / "IDENTITY.md").read_text(encoding="utf-8")
    soul = (target / "SOUL.md").read_text(encoding="utf-8")
    agents = (target / "AGENTS.md").read_text(encoding="utf-8")

    return AgentSoul(
        agent_id=agent_id,
        identity=identity,
        soul=soul,
        agents=agents,
    )
```

### Pattern 3: warmup_soul_cache()

**What:** Eagerly loads all five soul directories at graph creation time to fail fast (missing files surface at startup, not during a live run).

**When to use:** Called once in `src/graph/orchestrator.py` after `build_graph()`.

**Example:**
```python
_KNOWN_AGENTS = (
    "macro_analyst",
    "bullish_researcher",
    "bearish_researcher",
    "quant_modeler",
    "risk_manager",
)

def warmup_soul_cache() -> None:
    """Pre-load all agent souls into lru_cache. Raises on missing/malformed files."""
    for agent_id in _KNOWN_AGENTS:
        load_soul(agent_id)
```

### Pattern 4: SwarmState Field Addition

**What:** Two plain `Optional[str]` fields added to `SwarmState` TypedDict — no `Annotated` reducer annotation, consistent with existing non-accumulating fields.

**When to use:** Add these alongside the existing `macro_report`, `risk_approved`, etc. pattern.

**Example:**
```python
# src/graph/state.py (additions only)
# Phase 15: Soul Foundation
system_prompt: Optional[str]    # Active soul content injected by L2 node (audit-excluded)
active_persona: Optional[str]   # Agent handle string, e.g., "AXIOM" (audit-excluded)
```

### Pattern 5: Soul Injection in Node Functions

**What:** Each L2 node calls `load_soul(agent_id)` at the top of its node function, writes fields to state, then injects the soul into the LLM call as a SystemMessage.

**When to use:** MacroAnalyst, QuantModeler (analysts.py), BullishResearcher, BearishResearcher (researchers.py). For Phase 15 the soul is returned in state; actual LLM injection via SystemMessage prepend is also wired here.

**Example:**
```python
# src/graph/agents/analysts.py — MacroAnalyst node (modified)
from langchain_core.messages import SystemMessage
from src.core.soul_loader import load_soul

def MacroAnalyst(state: SwarmState, budget=None) -> dict:
    soul = load_soul("macro_analyst")
    # ... existing query construction ...
    messages_for_agent = [SystemMessage(content=soul.system_prompt)] + existing_messages + [HumanMessage(content=query)]
    result = _get_macro_agent().invoke({"messages": messages_for_agent})
    # ... existing result extraction ...
    return {
        "messages": [response],
        "total_tokens": tokens_to_add,
        "macro_report": {"text": content},
        "system_prompt": soul.system_prompt,
        "active_persona": soul.active_persona,
    }
```

### Pattern 6: Audit Field Exclusion

**What:** Strip `AUDIT_EXCLUDED_FIELDS` from the data dict before SHA-256 hashing in `AuditLogger._calculate_hash()`. The exclusion must happen before hash computation — stripping only at DB insertion would still corrupt the chain because the hash would differ from what was computed.

**When to use:** Modify `AuditLogger._calculate_hash()` to remove excluded fields from `input_data` and `output_data` before the `json.dumps` call.

**Example:**
```python
# src/core/audit_logger.py (additions)
AUDIT_EXCLUDED_FIELDS: frozenset[str] = frozenset({
    "system_prompt",
    "active_persona",
    "soul_sync_context",   # Phase 18 pre-declared
})

def _strip_excluded(data: dict) -> dict:
    """Return a copy of data with AUDIT_EXCLUDED_FIELDS removed."""
    return {k: v for k, v in data.items() if k not in AUDIT_EXCLUDED_FIELDS}

def _calculate_hash(self, entry: dict, prev_hash) -> str:
    # Strip soul fields before hashing
    clean_entry = {
        **entry,
        "input_data": self._strip_excluded(entry["input_data"]),
        "output_data": self._strip_excluded(entry["output_data"]),
    }
    data_string = json.dumps({
        "task_id": clean_entry["task_id"],
        "timestamp": clean_entry["timestamp"].isoformat(),
        "node_id": clean_entry["node_id"],
        "input_data": clean_entry["input_data"],
        "output_data": clean_entry["output_data"],
    }, sort_keys=True, default=str)
    # ... rest unchanged ...
```

### Pattern 7: autouse Cache-Clear Fixture

**What:** `clear_soul_caches` autouse fixture in `tests/core/conftest.py` calls `load_soul.cache_clear()` before and after every test via yield pattern.

**When to use:** Scope this conftest to `tests/core/` only — it must not affect the 244 existing tests in `tests/`.

**Example:**
```python
# tests/core/conftest.py
import pytest
from src.core.soul_loader import load_soul

@pytest.fixture(autouse=True)
def clear_soul_caches():
    """Clear lru_cache on load_soul before and after every test."""
    load_soul.cache_clear()
    yield
    load_soul.cache_clear()
```

### Anti-Patterns to Avoid

- **Putting system_prompt into state["messages"]:** The `operator.add` reducer accumulates without bound; soul content grows with every cycle and corrupts the MiFID II audit trail by entering hash-chained records.
- **Reading soul files directly in node functions:** Bypasses the lru_cache and re-reads from disk on every invocation. Always use `load_soul(agent_id)`.
- **Using asyncio.run() inside node functions for I/O:** This is a known project-breaking pattern (MiFID II defect). All soul I/O is synchronous `Path.read_text()`.
- **Lazy initialisation pattern for SoulLoader:** The lazy LLM init pattern (`_llm = None; def _get_llm(): ...`) exists to defer API key validation. SoulLoader has no API key requirement — file I/O is safe at import time and should not be lazily deferred.
- **Module-level global conftest.py fixture scope:** Placing `clear_soul_caches` in the root `conftest.py` would apply it to all 244 existing tests, which don't use `load_soul`. Keep it in `tests/core/conftest.py`.
- **YAML frontmatter in soul files:** Phase 15 explicitly defers version/weight metadata. Any YAML parser introduced now creates coupling that ARS (Phase 19) must later work around.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cache invalidation | Custom TTL cache, dict-based singleton | `functools.lru_cache` | Built-in `.cache_clear()` is the exact method SOUL-06 fixture needs; thread-safe in CPython for read-dominant workloads |
| Path safety | Regex-based agent_id validation | `Path.resolve()` + prefix check | `resolve()` follows symlinks and collapses `..` — regex cannot handle all traversal variants |
| Immutable value objects | Custom `__eq__`/`__hash__`/`__setattr__` | `@dataclass(frozen=True)` | Same pattern as `GraphDecision` already in project; frozen guarantees hashability required by lru_cache |
| Test isolation | `importlib.reload()`, module teardown | `lru_cache.cache_clear()` | Simpler, faster, no import side-effects; the established project pattern (seen in test_analysts.py reset_analyst_singletons) |

**Key insight:** This entire phase is achievable with Python stdlib + existing project patterns. The temptation to introduce a YAML/TOML configuration layer for soul files adds parser complexity and defeats the H2-section prose format chosen for human maintainability and machine parseability (regex-based ARS in Phase 19).

---

## Common Pitfalls

### Pitfall 1: Soul Content in Hash Chain
**What goes wrong:** `system_prompt` or `active_persona` enters `input_data` or `output_data` in `AuditLogger.log_transition()`, and `_calculate_hash()` includes it. Any subsequent verification with `verify_chain()` will reflect this content — audit records are immutable, so once written they cannot be corrected.
**Why it happens:** Node functions return `{"system_prompt": ..., "active_persona": ..., ...}` as partial state updates. If the orchestrator passes the full updated state as `output_data` to `log_transition`, soul fields are present.
**How to avoid:** Add `AUDIT_EXCLUDED_FIELDS` stripping in `_calculate_hash()` and/or strip at the `log_transition` call site before building `entry_payload`. Stripping in `_calculate_hash` is safer — it applies regardless of how `log_transition` is called.
**Warning signs:** `verify_chain()` returns `True` initially but fails after `load_soul.cache_clear()` when soul content changes between sessions.

### Pitfall 2: lru_cache Miss on Mutable Default Return
**What goes wrong:** `AgentSoul` dataclass declared without `frozen=True` raises `TypeError: unhashable type` when `lru_cache` attempts to cache the return value.
**Why it happens:** `lru_cache` requires the return value to be hashable when used as a cache entry; only `frozen=True` dataclasses are hashable by default.
**How to avoid:** Always declare `@dataclass(frozen=True)` for `AgentSoul`. Verify with `hash(load_soul("macro_analyst"))` in a test.
**Warning signs:** `TypeError: unhashable type: 'AgentSoul'` on first call to `load_soul()`.

### Pitfall 3: Cache Leak Between Tests
**What goes wrong:** Test A loads a soul, test B calls `load_soul.cache_clear()` in its fixture teardown, but test C (which ran after A, before B's teardown) still sees A's cached soul.
**Why it happens:** lru_cache is process-global. Without clearing before each test, the first test to call `load_soul()` poisons the cache for all subsequent tests in the same process.
**How to avoid:** The `clear_soul_caches` autouse fixture clears cache BEFORE yield (pre-test isolation) AND after yield (post-test cleanup). Both are required.
**Warning signs:** Flaky tests that pass in isolation but fail when run after a test that modified soul file content or mocked `load_soul`.

### Pitfall 4: Path Traversal Returns Wrong Error Type
**What goes wrong:** Path traversal guard raises `FileNotFoundError` instead of `ValueError`, allowing callers to catch `FileNotFoundError` and proceed silently.
**Why it happens:** Developer uses `target.is_dir()` check only, which also returns False for traversal paths — the error type leaks information about the guard mechanism.
**How to avoid:** The guard must raise `ValueError` specifically for traversal attempts (before any filesystem stat call), and `FileNotFoundError` only for legitimately missing directories. Per SOUL-01 success criteria.
**Warning signs:** Test `test_path_traversal_raises_valueerror` fails with `FileNotFoundError` instead.

### Pitfall 5: System Prompt in messages[] Accumulator
**What goes wrong:** Developer passes `SystemMessage(content=soul.system_prompt)` to the agent and also writes `system_prompt` to `state["messages"]`. The `operator.add` reducer appends it on every cycle; by cycle 10 there are 10 copies of the soul in the messages list.
**Why it happens:** Confusion between state management (soul fields go to dedicated SwarmState keys) and LLM context management (SystemMessage goes into the agent's local message list, not state["messages"]).
**How to avoid:** Soul content touches state only through `state["system_prompt"]` and `state["active_persona"]`. The SystemMessage is constructed locally inside the node function and passed directly to the agent invocation — never written to `state["messages"]`.
**Warning signs:** `state["messages"]` grows by more than one AIMessage per node invocation.

### Pitfall 6: warmup_soul_cache() Raising at Import Time
**What goes wrong:** `warmup_soul_cache()` is called at module import level rather than inside `create_orchestrator_graph()`, causing test collection to fail if soul directories don't exist.
**Why it happens:** Misreading the instruction "at graph creation time" as "at module load time".
**How to avoid:** Call `warmup_soul_cache()` inside `create_orchestrator_graph()` (or `build_graph()`), not at module level. Tests that mock `load_soul` won't be affected.
**Warning signs:** `pytest --collect-only` fails with `FileNotFoundError` before any test runs.

---

## Code Examples

Verified patterns from existing codebase:

### Frozen Dataclass Pattern (from src/graph/models.py)
```python
# Direct template for AgentSoul
@dataclass(frozen=True)
class GraphDecision:
    task_id: str
    decision: str
    consensus_score: float = 0.0
    rationale: str = ""
    proposals: list[Any] = field(default_factory=list)
```

### Autouse Singleton Reset (from tests/test_analysts.py:26)
```python
@pytest.fixture(autouse=True)
def reset_analyst_singletons():
    analysts_mod._macro_agent = None
    analysts_mod._quant_agent = None
    yield
    analysts_mod._macro_agent = None
    analysts_mod._quant_agent = None
```
The `clear_soul_caches` fixture follows this exact yield-sandwich pattern; replace module-level None assignment with `load_soul.cache_clear()`.

### Optional[str] SwarmState Fields (from src/graph/state.py)
```python
# Pattern for plain non-accumulating state fields:
macro_report: Optional[dict]     # overwrites each update — no reducer
risk_approved: Optional[bool]    # overwrites each update — no reducer
risk_notes: Optional[str]        # overwrites each update — no reducer
# New fields follow identically:
system_prompt: Optional[str]     # overwrites each update — no reducer
active_persona: Optional[str]    # overwrites each update — no reducer
```

### Audit Logger Hash Structure (from src/core/audit_logger.py:66)
```python
data_string = json.dumps({
    "task_id": entry["task_id"],
    "timestamp": entry["timestamp"].isoformat(),
    "node_id": entry["node_id"],
    "input_data": entry["input_data"],   # <-- strip AUDIT_EXCLUDED_FIELDS before this
    "output_data": entry["output_data"], # <-- strip AUDIT_EXCLUDED_FIELDS before this
}, sort_keys=True, default=str)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded system prompt string in `create_react_agent(prompt=...)` | File-backed soul loaded from `src/core/souls/{agent_id}/` at runtime | Phase 15 | Persona is editable without code changes; diff-stable for Phase 17 Agent Church |
| Agent identity not tracked in SwarmState | `active_persona` field in SwarmState | Phase 15 | Phase 18 Soul-Sync can read peer identities from state without re-loading files |

**Deprecated/outdated:**
- Hardcoded `prompt=` string in `create_react_agent()` for MacroAnalyst and QuantModeler — Phase 15 replaces these with soul-injected SystemMessage; the `prompt=` kwarg becomes either empty or minimal post-injection.

---

## Open Questions

1. **Partial soul injection for four skeleton agents**
   - What we know: Skeletons have minimum viable content (2–4 sentences per section per the locked decisions)
   - What's unclear: Whether `warmup_soul_cache()` validates minimum content or just that files exist and are non-empty
   - Recommendation: Validate files exist and are non-empty (non-zero byte); content richness validation deferred to Phase 19 ARS

2. **SystemMessage position in agent invocation**
   - What we know: "Prepend SystemMessage before agent invocation" (Claude's discretion). The existing invocation passes `[HumanMessage(content=content)]` to sub-graph. The `create_react_agent(prompt=...)` kwarg is also a system prompt.
   - What's unclear: Whether the new SystemMessage from soul should replace the `prompt=` kwarg in `create_react_agent()` or be prepended alongside it in the messages list.
   - Recommendation: Prepend as SystemMessage to the messages list in the node function. Leave the existing `prompt=` kwarg as-is for Phase 15 (migration to soul-only prompt is a Phase 17 concern). Two system prompts stacking is valid for LangChain/Gemini — the soul SystemMessage takes precedence by position.

3. **SwarmState initialisation in existing tests**
   - What we know: Many tests use `_make_state()` helpers that build minimal SwarmState dicts. Adding `system_prompt` and `active_persona` as new TypedDict fields means existing state helpers may be missing these keys.
   - What's unclear: Whether TypedDict enforcement causes test failures when these keys are absent.
   - Recommendation: TypedDict is not enforced at runtime — missing optional fields return `None` from `.get()`. Existing tests will not break. The `_make_state()` helpers in new `tests/core/` test files should explicitly include the new fields.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/core/ -x -q` |
| Full suite command | `.venv/bin/python3.12 -m pytest -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SOUL-01 | `load_soul("macro_analyst")` returns populated `AgentSoul`; traversal raises `ValueError` | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_loader.py -x` | Wave 0 |
| SOUL-02 | IDENTITY.md, SOUL.md, AGENTS.md all contain expected H2 sections for macro_analyst | content fidelity | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py::test_axiom_identity -x` | Wave 0 |
| SOUL-03 | `warmup_soul_cache()` completes without error with all five soul dirs present | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_loader.py::test_warmup_completes -x` | Wave 0 |
| SOUL-04 | `system_prompt` and `active_persona` are valid SwarmState keys with `Optional[str]` type | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_loader.py::test_swarmstate_fields -x` | Wave 0 |
| SOUL-05 | `macro_analyst_node` writes both fields to state before LLM invocation; fields absent from audit hash input | integration | `.venv/bin/python3.12 -m pytest tests/core/test_macro_analyst_soul.py -x` | Wave 0 |
| SOUL-06 | `load_soul.cache_clear()` called before and after every test; no cache bleed between tests | unit | `.venv/bin/python3.12 -m pytest tests/core/ -x -q` (all pass in any order) | Wave 0 |
| SOUL-07 | All soul tests pass with zero LLM calls (agents mocked, only string assertions) | integration | `.venv/bin/python3.12 -m pytest tests/core/ -x -q` | Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python3.12 -m pytest tests/core/ -x -q`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/core/__init__.py` — make `tests/core/` a package for proper pytest collection
- [ ] `tests/core/conftest.py` — `clear_soul_caches` autouse fixture
- [ ] `tests/core/test_soul_loader.py` — SOUL-01, SOUL-03, SOUL-04, SOUL-06 unit tests
- [ ] `tests/core/test_persona_content.py` — SOUL-02 content fidelity tests
- [ ] `tests/core/test_macro_analyst_soul.py` — SOUL-05, SOUL-07 integration tests
- [ ] `src/core/souls/macro_analyst/IDENTITY.md` — AXIOM identity (required by all soul tests)
- [ ] `src/core/souls/macro_analyst/SOUL.md` — AXIOM soul (required by all soul tests)
- [ ] `src/core/souls/macro_analyst/AGENTS.md` — AXIOM agents (required by all soul tests)
- [ ] Four skeleton soul directories with minimum viable content (required by SOUL-03)

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `src/graph/models.py`, `src/graph/state.py`, `src/core/audit_logger.py`, `src/graph/agents/analysts.py`, `src/graph/agents/researchers.py`, `src/graph/orchestrator.py`
- Direct codebase inspection — `tests/test_analysts.py`, `tests/test_mem03_integration.py`, `conftest.py`
- `.planning/phases/15-soul-foundation/15-CONTEXT.md` — locked user decisions
- `.planning/REQUIREMENTS.md` — SOUL-01 through SOUL-07 requirement text
- `.planning/STATE.md` — v1.3 accumulated context and critical patterns
- Python stdlib docs — `functools.lru_cache`, `dataclasses.dataclass(frozen=True)`, `pathlib.Path.resolve()`

### Secondary (MEDIUM confidence)
- `pyproject.toml` — confirmed no new dependencies needed; pytest 9.0.2 + pytest-asyncio available
- `.planning/config.json` — `nyquist_validation` key absent → validation architecture section required

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are Python stdlib, already used in project
- Architecture: HIGH — patterns verified directly from existing codebase files
- Pitfalls: HIGH — derived from CONTEXT.md code insights + STATE.md accumulated context + direct audit_logger.py inspection
- Soul file content: MEDIUM — persona characterisation locked by user decisions; exact prose at Claude's discretion

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable stdlib + LangGraph patterns; soul content is static)
