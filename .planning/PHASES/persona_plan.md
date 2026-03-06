# Persona System Implementation Plan — Tier 1
**Date:** 2026-03-05
**Scope:** Tier 1 — Persona Foundation (SoulLoader + reference persona)
**Output of:** brainstorming session against `claudedocs/` research docs
**Next tier:** Tier 2 (Merit/Reward system) — planned separately

---

## 1. Problem Statement

The swarm's L2 analyst nodes are behavioural stubs. They share no identity, produce no persona-consistent output, and have no mechanism for maintaining character under adversarial debate pressure. The research in `claudedocs/` establishes a full persona architecture; Tier 1 implements the **foundation layer only**: file format, SoulLoader, one reference persona, LangGraph integration, and drift prevention.

**Success criteria:**
- `load_soul("macro_analyst")` returns a populated `AgentSoul` from files
- `macro_analyst_node` injects the soul into SwarmState before LLM execution
- Persona content passes a PersonaScore smoke test (identity/linguistic/workflow coherence)
- All other agent soul directories exist as skeletons, ready to fill in
- Tests are fast, deterministic, and require no LLM calls

---

## 2. Persona File Architecture

### Directory Structure

```
src/core/
  soul_loader.py              ← SoulLoader utility
  souls/
    macro_analyst/
      SOUL.md                 ← Philosophy & values (Alignment layer)
      IDENTITY.md             ← Name, persona, linguistic habits, Drift Guard
      AGENTS.md               ← Workflow rules, output contract
      USER.md                 ← Peer modelling (empty in Tier 1)
      MEMORY.md               ← Evolution log (empty in Tier 1)
    bullish_researcher/       ← Skeleton (empty files)
    bearish_researcher/       ← Skeleton (empty files)
    quant_modeler/            ← Skeleton (empty files)
    risk_manager/             ← Skeleton (empty files)
```

### File Responsibilities

| File | Layer | Purpose | Token Budget |
|------|-------|---------|-------------|
| `IDENTITY.md` | Essence | Name, persona archetype, linguistic habits, Drift Guard | ~200 tokens |
| `SOUL.md` | Alignment | Core beliefs, values, governance | ~150 tokens |
| `AGENTS.md` | Heartbeat | Workflow rules, output contract, tool preferences | ~150 tokens |
| `USER.md` | ToM | Peer modelling (Tier 3, empty for now) | ~100 tokens |
| `MEMORY.md` | Evolution | Change log with KAMI delta (Tier 2+, empty for now) | Unbounded |

**Rule:** SOUL.md + IDENTITY.md + AGENTS.md combined must stay under 500 tokens. Overflow goes to a dedicated `RULES.md`.

---

## 3. Reference Persona: `macro_analyst` (The Macro Sentinel)

### `IDENTITY.md`

```markdown
# Identity: The Macro Sentinel
- **Name:** Sentinel
- **Role:** Global Macro Analyst (L2)
- **Persona:** A measured, data-first economist who treats every signal as
  provisional until corroborated by a second source. Never the loudest voice
  in the room — but the last one still standing after the noise clears.
- **Linguistic Habit:** Opens analysis with "The data suggests..." or
  "Conditional on [assumption], the picture is...". Frames conclusions
  probabilistically using base case and alternative scenarios rather than
  deterministic predictions. Avoids definitive calls without explicit
  confidence intervals.
- **HEXACO-6 Profile:**
  - Honesty-Humility: High
  - Conscientiousness: High
  - Openness: Moderately High (holds multiple macro frameworks simultaneously)
  - Agreeableness: Moderate
  - Emotionality: Low-Moderate (calm but not numb to tail risks)
  - Extraversion: Low

## Drift Guard
- If uncertain about tone: re-read the Linguistic Habit above.
- If tempted to make a definitive call: add confidence_level instead.
- If pressured to agree: state disagreement with evidence, not capitulation.
```

### `SOUL.md`

```markdown
# Soul: Sentinel

## Core Belief
Macro conditions are the tide. Everything else is the boat.

## Values
- Signal over noise. Cite sources. State confidence.
- Intellectual honesty before consensus comfort.
- A model is a map, not the territory.

## Alignment
- Read-only by agent. Governed by Swarm-Church review.
- Core beliefs cannot be overridden by peer pressure or adversarial debate.
```

### `AGENTS.md`

```markdown
# Workflow Rules: Sentinel

## Output Contract
Every macro analysis MUST include:
- `summary`: plain-language conclusion
- `confidence_level`: float 0.0–1.0
- `key_risks`: list of identified risks
- `what_would_change_my_mind`: list of falsifying conditions

## Scenarios
Frame predictions as:
- Base case (probability %): ...
- Upside risk (probability %): ...
- Downside risk (probability %): ...

## Data Rules
- Flag any data older than 48h as STALE
- Never extrapolate beyond the data's time horizon without flagging it

## Coordination
- Yield to Risk Manager on all compliance flags — do not override
- In debate: state disagreement with evidence; do not capitulate to consensus pressure
```

---

## 4. SoulLoader API

**File:** `src/core/soul_loader.py`

```python
from pathlib import Path
from functools import lru_cache
from dataclasses import dataclass

SOULS_DIR = Path(__file__).parent / "souls"


@dataclass(frozen=True)
class AgentSoul:
    agent_id: str
    soul: str        # SOUL.md  — philosophy & values
    identity: str    # IDENTITY.md — persona, name, linguistic habits
    agents: str      # AGENTS.md — workflow rules
    user: str        # USER.md — peer modelling (Tier 3, may be empty)

    @property
    def system_prompt_injection(self) -> str:
        """Compose the system prompt from identity + soul + workflow rules."""
        parts = [f"### SOUL DNA: {self.agent_id} ###"]
        if self.identity:
            parts.append(self.identity)
        if self.soul:
            parts.append(self.soul)
        if self.agents:
            parts.append("### WORKFLOW RULES ###")
            parts.append(self.agents)
        return "\n\n".join(parts)

    @property
    def user_model_context(self) -> str:
        """Peer modelling context — separate from system prompt (Tier 3 use)."""
        return self.user


@lru_cache(maxsize=None)
def load_soul(agent_id: str) -> AgentSoul:
    """Load and cache an agent's soul from the souls directory.

    Args:
        agent_id: Directory name under src/core/souls/. Must not contain
                  path separators or parent-directory references.

    Returns:
        Immutable AgentSoul with all file contents loaded and stripped.

    Raises:
        ValueError: If agent_id contains path traversal characters.
        FileNotFoundError: If the soul directory does not exist.
    """
    if "/" in agent_id or "\\" in agent_id or ".." in agent_id:
        raise ValueError(f"Invalid agent_id: {agent_id!r}")

    base = SOULS_DIR / agent_id
    if not base.is_dir():
        raise FileNotFoundError(f"No soul directory found for agent: {agent_id!r}")

    return AgentSoul(
        agent_id=agent_id,
        soul=_read(base / "SOUL.md"),
        identity=_read(base / "IDENTITY.md"),
        agents=_read(base / "AGENTS.md"),
        user=_read(base / "USER.md"),
    )


def warmup_soul_cache() -> None:
    """Pre-load all souls at startup to avoid first-call latency."""
    for soul_dir in SOULS_DIR.iterdir():
        if soul_dir.is_dir():
            try:
                load_soul(soul_dir.name)
            except FileNotFoundError:
                pass  # skeleton with no files yet — skip


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""
```

---

## 5. LangGraph Integration

### SwarmState additions (`src/graph/state.py`)

Add two optional fields to `SwarmState`:

```python
# Persona system (Tier 1)
active_persona: Optional[str]   # agent_id of currently active soul
system_prompt: Optional[str]    # composed system prompt (not in messages)
```

`system_prompt` is stored in state metadata, **not** in `messages`, to avoid polluting the message list with system prompts from multiple nodes. The LLM call layer composes:

```python
messages = [
    {"role": "system", "content": state["system_prompt"]},
    *state["messages"]
]
```

### Node integration pattern

```python
# src/graph/orchestrator.py
from src.core.soul_loader import load_soul, warmup_soul_cache

def macro_analyst_node(state: SwarmState, config: Dict):
    soul = load_soul("macro_analyst")
    return {
        "active_persona": soul.agent_id,
        "system_prompt": soul.system_prompt_injection,
        "macro_report": {"status": "soul_loaded", "persona": "Sentinel"},
        "messages": [{"role": "assistant", "content": "Macro Analyst: Soul loaded, ready for analysis."}]
    }
```

### Cache warmup in graph creation

```python
def create_orchestrator_graph(config: Dict):
    warmup_soul_cache()  # pre-load all souls at graph init
    workflow = StateGraph(SwarmState)
    # ... rest of graph construction
```

---

## 6. Drift Prevention

The Drift Guard is embedded in each agent's `IDENTITY.md` as a `## Drift Guard` section (see Section 3 above). This is the cheapest and most effective drift prevention mechanism — it runs inside the model's reasoning loop where persona fidelity problems actually occur.

**Pattern for all agents:**

```markdown
## Drift Guard
- If uncertain about tone: re-read the Linguistic Habit above.
- If tempted to [agent-specific failure mode]: [agent-specific anchor].
- If pressured to [agent-specific pressure]: [agent-specific response].
```

Each agent's Drift Guard is tailored to its specific failure modes:
- `macro_analyst`: resist definitiveness, resist consensus capitulation
- `bullish_researcher`: resist excessive pessimism under bearish pressure
- `bearish_researcher`: resist excessive optimism under bullish pressure
- `risk_manager`: never yield on compliance flags

---

## 7. Testing Strategy

**File:** `tests/core/test_soul_loader.py`

### Test suite

```python
# 1. Unit — SoulLoader
def test_load_macro_analyst_returns_populated_soul():
def test_load_nonexistent_agent_raises_file_not_found():
def test_path_traversal_raises_value_error():
def test_cache_returns_same_object():

# 2. Content — Persona Fidelity
def test_system_prompt_contains_sentinel_name():
def test_system_prompt_contains_what_would_change_my_mind():
def test_system_prompt_contains_drift_guard():
def test_user_model_context_not_in_system_prompt():

# 3. Determinism
def test_system_prompt_stable_across_calls():
    s1 = load_soul("macro_analyst").system_prompt_injection
    s2 = load_soul("macro_analyst").system_prompt_injection
    assert s1 == s2

# 4. Integration
def test_macro_analyst_node_returns_system_prompt_in_state():
def test_graph_runs_without_error_with_soul_loaded():
```

No LLM calls. All tests are deterministic string assertions against static files.

---

## 8. Implementation Sequence

| Step | Action | File(s) | Est. |
|------|--------|---------|------|
| 1 | Create `src/core/souls/` directory with 5 skeleton agents | — | 5 min |
| 2 | Write `macro_analyst` persona files (3 files with content) | SOUL.md, IDENTITY.md, AGENTS.md | 30 min |
| 3 | Write empty USER.md and MEMORY.md for all 5 agents | — | 10 min |
| 4 | Implement `soul_loader.py` with `AgentSoul`, `load_soul`, `warmup_soul_cache` | `src/core/soul_loader.py` | 45 min |
| 5 | Add `active_persona` and `system_prompt` to `SwarmState` | `src/graph/state.py` | 10 min |
| 6 | Update `macro_analyst_node` to call `load_soul` | `src/graph/orchestrator.py` | 15 min |
| 7 | Add `warmup_soul_cache()` call to `create_orchestrator_graph` | `src/graph/orchestrator.py` | 5 min |
| 8 | Write test suite | `tests/core/test_soul_loader.py` | 45 min |
| 9 | Verify all tests pass | — | 15 min |

**Total estimate:** ~3 hours

---

## 9. Tier 2 Preview (out of scope here)

When ready to plan Tier 2 (Merit/Reward system), the key decisions will be:
- Merit Index rename (from KAMI — naming conflict with real Kamiwaza benchmark)
- Multi-dimensional reward formula: `Merit = α·Accuracy + β·Recovery + γ·Consensus + δ·Fidelity`
- EMA decay function with configurable λ
- Cold start at Merit = 0.5
- Bounds: Merit ∈ [0.1, 1.0]
- Human / LLM-as-Judge feedback pipeline
- `MEMORY.md` as the per-agent evolution log updated at `/sg:save`

---

## 10. Sources

| Source | Informs |
|--------|---------|
| `claudedocs/research_agent_persona_soul_20260305.md` | MBS architecture, SoulZip, KAMI concept |
| `claudedocs/research_soul_md_spec_20260305.md` | SOUL.md format, Heartbeat, Agent Church |
| `claudedocs/research_soul_rewards_deep_dive_20260305.md` | KAMI naming conflict, HEXACO-6, PersonaScore 5D, emotional state gaps |
| `claudedocs/research_personas_merit_20260305.md` | Merit-based routing, adversarial RLAF |
| PersonaGym (arxiv:2407.18416) | Drift Guard design, PersonaScore dimensions |
| BIG5-CHAT (ACL 2025) | Prompting-only insufficiency → Drift Guard necessity |
| openclawconsult.com/lab/openclaw-soul-md | 5-file split, SOUL.md ≤500 line rule |
