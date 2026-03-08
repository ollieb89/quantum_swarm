# Phase 17: MEMORY.md Evolution + Agent Church - Research

**Researched:** 2026-03-08
**Domain:** Agent self-reflection logging, soul proposal workflow, out-of-band review script
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**MEMORY.md Entry Format** — Fixed-field template, one entry per active agent per cycle:
```
=== 2026-03-08T12:34:56Z ===
[AGENT:] CASSANDRA
[KAMI_DELTA:] +0.04
[MERIT_SCORE:] 0.81
[DRIFT_FLAGS:] none
[THESIS_SUMMARY:] Inflation surprise risk remains underpriced; maintain hawkish bias.
```
- Entries appended (newest at bottom); file capped at 50 entries (oldest removed on overflow)
- `[DRIFT_FLAGS:]` = `none` or comma-separated flag names
- `[THESIS_SUMMARY:]` = deterministic first-sentence extract from canonical output field — NO extra LLM call
- Skip-on-no-output rule: if canonical output field is None/absent, skip MEMORY entry for that agent

**Per-agent canonical output field map:**
- AXIOM (macro_analyst) → `state["macro_report"]` — first sentence
- MOMENTUM (bullish_researcher) → `state["bullish_thesis"]` — first sentence
- CASSANDRA (bearish_researcher) → `state["bearish_thesis"]` — first sentence
- SIGMA (quant_modeler) → `state["quant_proposal"]` — first sentence
- GUARDIAN (risk_manager) → `state["risk_approval"]` reasoning field — first sentence

**Orchestrator Wiring** — New `memory_writer` node, graph position:
`merit_updater → memory_writer → trade_logger`
- Single node iterates all 5 soul handles
- Silent node: no SwarmState field added (no `memory_write_status`)
- Non-blocking: on write failure, log high-severity error and continue cycle

**SOUL.md Proposal Trigger** — Three triggers, OR logic (inside `memory_writer`):
1. KAMI delta threshold: `|KAMI_DELTA| >= kami_delta_threshold` (default 0.05)
2. Drift streak: last `drift_streak_n` consecutive entries have non-empty `[DRIFT_FLAGS:]`
3. Sustained merit decline: agent's `[MERIT_SCORE:]` <= `merit_floor` for last `merit_floor_k` entries
- One merged proposal per cycle when any trigger fires; `proposal_reasons` lists all matched triggers

**Config in `swarm_config.yaml`:**
```yaml
phase17:
  kami_delta_threshold: 0.05
  drift_streak_n: 3
  merit_floor: 0.40
  merit_floor_k: 3
  soul_autoapprove_max_chars: 500
  soul_autoapprove_allowed_ops:
    - section_patch
  rate_limit_rejection_k: 3
  rate_limit_window_days: 7
```

**Proposal JSON Schema** — Pydantic-validated, atomic write (temp + `os.rename()`):
```json
{
  "proposal_id": "cass_2026_03_08T124122Z",
  "agent_id": "CASSANDRA",
  "target_section": "## Core Beliefs",
  "proposed_content": "## Core Beliefs\n\nInflation regime shifts...",
  "proposal_reasons": ["KAMI_SPIKE", "DRIFT_STREAK"],
  "rationale": "Merit declined sharply; drift flags raised on 3 consecutive cycles.",
  "proposed_at": "2026-03-08T12:41:22Z",
  "status": "pending",
  "rejection_reason": null
}
```
Status values: `pending | approved | rejected | rate_limited`
`proposed_content` = full replacement text for target H2 section (no unified diff).

**Agent Church Review Policy:**
- Auto-approve: agent_id not L1 Orchestrator AND target_section exists in SOUL.md AND len(proposed_content) <= 500 AND operation is `section_patch`
- Auto-reject: target section missing, content exceeds char limit, multiple sections targeted, heading/structure modification, empty/malformed, OR proposer is L1 Orchestrator (raises `RequiresHumanApproval`)
- Post-approval: `load_soul.cache_clear()` + `warmup_soul_cache()`
- Rate-limiting: after `rate_limit_rejection_k` rejections for same `(agent_id, target_section)` within `rate_limit_window_days` — scan existing proposal JSONs (proposals double as rejection ledger)

**Reusable Assets:**
- `src/core/soul_loader.py` — `load_soul()`, `warmup_soul_cache()`, `SoulSecurityError`
- `src/graph/nodes/merit_updater.py` — template for `memory_writer`
- `src/core/kami.py` — `ALL_SOUL_HANDLES`, `RESEARCHER_HANDLE_MAP`
- `tests/core/conftest.py` — `clear_soul_caches` autouse fixture

**Integration Points:**
- Orchestrator line 344-345: insert `memory_writer` between `merit_updater` and `trade_logger`
- `src/core/souls/{agent_id}/MEMORY.md` — new file per agent (created on first write)
- `data/soul_proposals/` — new directory (created by `memory_writer` on first proposal)
- `config/swarm_config.yaml` — extend with `phase17:` block
- Agent Church: `python -m src.core.agent_church` — standalone script, not a LangGraph node

### Claude's Discretion

None specified — all decisions are locked.

### Deferred Ideas (OUT OF SCOPE)

- LLM-judged proposal review (semantic persona consistency) — Phase 18 Theory of Mind
- Fidelity dimension structural section checks in KAMI — Phase 18
- ARS drift metrics computed from MEMORY.md logs — Phase 19
- Public soul summaries for pre-debate handshake — Phase 18
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EVOL-01 | After each task cycle, each active agent appends a structured self-reflection entry to its `src/core/souls/{agent_id}/MEMORY.md` (capped at 50 entries; includes `[KAMI_DELTA:]` and `[MERIT_SCORE:]` machine-readable markers) | `memory_writer` node (async, mirrors `merit_updater` pattern); MEMORY.md created on first write; capping via entry-boundary parse + truncation |
| EVOL-02 | Agent can propose a SOUL.md diff stored as `data/soul_proposals/{agent_id}.json` (Pydantic-validated schema: agent_id, section, diff, rationale, proposed_at, status) | Proposal logic inside `memory_writer`; atomic write via `tempfile` + `os.rename()`; Pydantic v2 model for schema enforcement; `data/soul_proposals/` directory created by writer |
| EVOL-03 | Standalone `agent_church.py` script reviews proposals, applies approved diffs with `load_soul.cache_clear()` + `warmup_soul_cache()`, and raises `RequiresHumanApproval` for any L1 Orchestrator self-proposals | `src/core/agent_church.py` as `__main__` module; H2 section replacement via regex; custom exception class `RequiresHumanApproval`; no LLM calls; no LangGraph imports |
</phase_requirements>

---

## Summary

Phase 17 introduces two new subsystems: an in-graph `memory_writer` node that appends structured self-reflection entries to per-agent MEMORY.md files and emits soul-proposal JSON artifacts when drift/merit triggers fire, and a standalone `agent_church.py` script that reviews pending proposals out-of-band and applies or rejects them using structural heuristics only.

The implementation is entirely pure-Python with no new dependencies. All patterns — config-driven tunables, atomic file writes, `lru_cache` invalidation, non-blocking node failures, H2 section targeting — already exist in the Phase 15/16 codebase. The `memory_writer` node is deliberately silent (no SwarmState field), keeping the audit trail clean. Agent Church is a standalone script to avoid LangGraph coupling and to enforce the L1 self-approval conflict-of-interest boundary.

The primary implementation risks are: MEMORY.md parse correctness (entry-boundary detection for capping and streak counting), atomic write guarantees across OS temp-rename semantics, and ensuring `agent_church.py` respects the Import Layer Law (no upward imports from `src.core` to `src.graph`).

**Primary recommendation:** Build in three sequential plans — Plan 01: MEMORY.md writer + cap logic + config; Plan 02: soul proposal Pydantic schema + trigger logic + atomic emit; Plan 03: Agent Church script + H2 replacement + cache refresh + `RequiresHumanApproval` + tests.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 (installed) | SoulProposal schema validation | Already used throughout — DecisionCard, AuditLogEntry, all models |
| pathlib.Path | stdlib | File I/O for MEMORY.md, SOUL.md, proposals | All existing soul/audit file I/O uses Path |
| os.rename | stdlib | Atomic proposal write (temp + rename) | POSIX atomic on same filesystem; existing project pattern |
| datetime / timezone | stdlib | ISO 8601 UTC timestamps in entries and proposal IDs | Used in all existing audit artifacts |
| re | stdlib | Entry-boundary parsing (`=== timestamp ===`), H2 section replacement | No third-party parser needed for fixed-field format |
| yaml (pyyaml) | >=6.0.2 (installed) | Load `phase17:` block from swarm_config.yaml | Used in `merit_updater._load_kami_config()` — replicate pattern |
| tempfile | stdlib | Create temp file for atomic proposal write | Cross-platform safe; same-dir temp ensures rename atomicity |
| json | stdlib | Proposal file serialisation / deserialisation | Proposals are `.json` files on disk |
| logging | stdlib | High-severity error logging on write failures | Established project logging pattern |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| functools.lru_cache | stdlib | Soul cache used via `load_soul` and `warmup_soul_cache` | Agent Church clears and re-warms after approval |
| collections.defaultdict / Counter | stdlib | Rate-limit counting over proposal JSON files | Needed in Agent Church to count rejections per (agent_id, target_section) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `os.rename()` atomic write | `fcntl` file locking | Locking is complex, cross-platform unreliable; rename is simpler and sufficient since proposals are append-only artifacts |
| `re` for H2 section parsing | `markdown-it-py` or similar parser | Third-party parser is overkill; soul files use simple, stable H2 structure; regex on `## ` prefix is sufficient and zero-dependency |
| Pydantic v2 `BaseModel` | `dataclasses` + manual validation | Pydantic already the project standard for validated schemas; consistent with `DecisionCard` |

**Installation:** No new packages required. All dependencies already in `.venv`.

---

## Architecture Patterns

### Recommended Project Structure

```
src/
├── core/
│   ├── agent_church.py      # NEW — standalone review script (__main__)
│   ├── soul_proposal.py     # NEW — SoulProposal Pydantic model + helpers
│   ├── soul_loader.py       # EXISTING — load_soul, warmup_soul_cache
│   ├── soul_errors.py       # EXISTING — extend with RequiresHumanApproval
│   └── souls/
│       └── {agent_id}/
│           └── MEMORY.md    # NEW per agent — created on first write
src/
├── graph/
│   └── nodes/
│       └── memory_writer.py # NEW — LangGraph node
data/
└── soul_proposals/          # NEW directory — created on first proposal
config/
└── swarm_config.yaml        # EXTEND — add phase17: block
tests/
└── core/
    ├── test_memory_writer.py    # NEW
    ├── test_soul_proposal.py    # NEW
    └── test_agent_church.py     # NEW
```

### Pattern 1: memory_writer Node (mirrors merit_updater)

**What:** Async LangGraph node that iterates `ALL_SOUL_HANDLES`, checks canonical output field, writes MEMORY entry if non-None, evaluates proposal triggers, emits proposal JSON if any trigger fires.

**When to use:** Placed between `merit_updater` and `trade_logger` in orchestrator graph. Runs every cycle after merit is settled.

**Example:**
```python
# src/graph/nodes/memory_writer.py
import logging
from pathlib import Path
from src.core.kami import ALL_SOUL_HANDLES
from src.graph.state import SwarmState

logger = logging.getLogger(__name__)

_CANONICAL_FIELD_MAP = {
    "AXIOM": "macro_report",
    "MOMENTUM": "bullish_thesis",
    "CASSANDRA": "bearish_thesis",
    "SIGMA": "quant_proposal",
    "GUARDIAN": "risk_approval",
}

async def memory_writer_node(state: SwarmState) -> dict:
    """Write per-agent MEMORY.md entries and emit soul proposals on trigger.

    Silent node: returns empty dict (no SwarmState field changes).
    Non-blocking: logs error and continues on any write failure.
    """
    for handle in ALL_SOUL_HANDLES:
        try:
            _process_agent(handle, state)
        except Exception as e:
            logger.error("memory_writer: unhandled error for %s: %s", handle, e)
    return {}  # Silent — no state mutation
```

### Pattern 2: Entry-Boundary MEMORY.md Parse

**What:** Parse MEMORY.md by splitting on `=== ... ===` separator lines to get discrete entries. Used for capping at 50 and for streak detection.

**When to use:** After appending a new entry; before emitting a proposal (streak/floor checks).

**Example:**
```python
import re

_ENTRY_SEP = re.compile(r"^=== .+ ===$", re.MULTILINE)

def _parse_entries(content: str) -> list[str]:
    """Split MEMORY.md content into a list of entry blocks.

    Each block includes the === header line. Empty content → [].
    """
    if not content.strip():
        return []
    # Split on separator, keep the separators by using a capture group
    parts = _ENTRY_SEP.split(content)
    headers = _ENTRY_SEP.findall(content)
    # Reconstruct: [header + body, ...]
    entries = []
    for i, header in enumerate(headers):
        body = parts[i + 1] if i + 1 < len(parts) else ""
        entries.append(header + "\n" + body.lstrip("\n"))
    return entries

def _cap_entries(entries: list[str], max_entries: int = 50) -> list[str]:
    """Remove oldest entries (front of list) to enforce cap."""
    if len(entries) > max_entries:
        return entries[len(entries) - max_entries:]
    return entries
```

### Pattern 3: Atomic Proposal Write

**What:** Write proposal JSON to a temp file in the same directory, then `os.rename()`. POSIX rename is atomic on same-filesystem writes.

**When to use:** Every time a proposal is emitted from `memory_writer`.

**Example:**
```python
import json
import os
import tempfile
from pathlib import Path

PROPOSALS_DIR = Path("data/soul_proposals")

def _write_proposal_atomic(proposal_dict: dict, filename: str) -> None:
    """Write proposal JSON atomically using temp-file + rename."""
    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    target = PROPOSALS_DIR / filename
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=PROPOSALS_DIR,
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    ) as f:
        json.dump(proposal_dict, f, indent=2, ensure_ascii=False)
        tmp_path = f.name
    os.rename(tmp_path, target)
```

### Pattern 4: H2 Section Replacement in Agent Church

**What:** Locate a named H2 section in SOUL.md content, replace everything from that H2 to the next H2 (exclusive) with `proposed_content`.

**When to use:** In `agent_church.py` when applying an approved proposal.

**Example:**
```python
import re

def _replace_h2_section(soul_content: str, target_section: str, new_content: str) -> str:
    """Replace a single H2 section body in SOUL.md.

    Finds `target_section` (must be an exact H2 header match).
    Replaces from that H2 up to (but not including) the next H2 or EOF.
    Raises ValueError if target_section not found.
    """
    # Normalize: ensure proposed_content ends with double newline
    replacement = new_content.rstrip("\n") + "\n\n"

    # Match the target section and everything until next H2 or end
    pattern = re.compile(
        r"(^" + re.escape(target_section) + r"\n)(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    if not pattern.search(soul_content):
        raise ValueError(f"Section not found in SOUL.md: {target_section!r}")

    return pattern.sub(replacement, soul_content, count=1)
```

### Pattern 5: Config Loading (replicate merit_updater pattern)

**What:** Lazy-load `phase17:` block from `swarm_config.yaml` into a module-level dict. Used in `memory_writer` for trigger thresholds.

**Example:**
```python
_P17_CONFIG: dict = {}

def _load_p17_config() -> dict:
    global _P17_CONFIG
    if not _P17_CONFIG:
        config_path = Path(__file__).parents[3] / "config" / "swarm_config.yaml"
        try:
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
            _P17_CONFIG = cfg.get("phase17", {})
        except Exception as e:
            logger.warning("memory_writer: could not load swarm_config.yaml: %s", e)
            _P17_CONFIG = {}
    return _P17_CONFIG
```

### Anti-Patterns to Avoid

- **Returning a state field from memory_writer:** The node is intentionally silent. Adding `memory_write_status` to SwarmState violates the locked decision and creates audit trail noise.
- **LLM call for THESIS_SUMMARY:** The summary must be a deterministic first-sentence extract, not an LLM-authored one. No extra API call.
- **Global cycle count for streak detection:** Streak = N consecutive *written* entries for that agent (parsed from MEMORY.md tail), not global cycle count. An agent that produced no output has no entry, so the streak resets correctly by construction.
- **Calling warmup_soul_cache() inside memory_writer node:** Only Agent Church calls this (post-approval, out-of-band). In-node soul cache refresh would race with concurrent fan-out reads.
- **Importing src.graph.* from src.core.agent_church:** Agent Church lives in `src.core` and must not import orchestrator or agents — Import Layer Law. It reads soul files directly via `Path`, not via the graph runtime.
- **Auto-approving L1 Orchestrator proposals:** The review policy raises `RequiresHumanApproval` — this must propagate to the caller, not be caught silently.
- **One proposal file per agent (overwriting):** Proposals accumulate as the rejection ledger. Files are named by `proposal_id`, not `agent_id`. Do not overwrite previous proposals.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Validated proposal schema | Custom dict + ad-hoc type checks | Pydantic v2 `BaseModel` | Field-level validation, `.model_dump()`, `.model_validate()` already the project standard |
| Atomic file write | `open()` + write directly | `tempfile.NamedTemporaryFile` + `os.rename()` | Direct write leaves partial files on crash; rename is POSIX-atomic on same filesystem |
| Entry boundary detection | Raw line grep | Regex split on `=== ... ===` separator | Grep misidentifies partial matches in THESIS_SUMMARY lines; entry boundary is unambiguous |
| Rate-limit persistence | Separate SQLite or counter file | Scan existing `data/soul_proposals/*.json` | Proposals are the rejection ledger; no separate surface needed (locked decision) |
| Soul file H2 section parsing | Full Markdown AST parser | `re.compile` with `MULTILINE | DOTALL` | Soul files have a stable, simple H2 structure; AST parser is an unnecessary dependency |

**Key insight:** Every problem in this phase is a file I/O + string manipulation problem. The project's existing patterns cover 100% of it — no new library needed.

---

## Common Pitfalls

### Pitfall 1: MEMORY.md Created as Directory

**What goes wrong:** `Path("src/core/souls/AXIOM/MEMORY.md").mkdir(parents=True)` creates `MEMORY.md` as a directory.
**Why it happens:** Copy-paste from the `mkdir(parents=True, exist_ok=True)` pattern used for `data/soul_proposals/`.
**How to avoid:** Only call `mkdir()` on the *parent* directory. Write content with `path.write_text()` or `open(path, "a")`. On first write, check `if not path.exists(): path.write_text("")` to initialise.
**Warning signs:** `IsADirectoryError` on first MEMORY write.

### Pitfall 2: Streak Count Uses Global Cycles Not Written Entries

**What goes wrong:** Tracking `N consecutive swarm cycles` instead of `N consecutive written entries` for an agent. An agent that produced no output in several cycles would incorrectly appear to have a `drift_streak_n`-entry streak.
**Why it happens:** Misreading the spec — "consecutive" refers to entries in the MEMORY.md file, not global clock ticks.
**How to avoid:** Always parse MEMORY.md tail *after* appending the current entry. Count entries from the bottom; stop counting when an entry is found without `[DRIFT_FLAGS:]` non-empty.
**Warning signs:** Proposals firing for agents with no recent outputs.

### Pitfall 3: os.rename() Across Filesystems

**What goes wrong:** `os.rename(tmp, target)` raises `OSError: [Errno 18] Invalid cross-device link` when `tmp` is on `/tmp` and target is on a different mount.
**Why it happens:** `tempfile.NamedTemporaryFile` defaults to the OS temp directory, which may be a different filesystem.
**How to avoid:** Always pass `dir=PROPOSALS_DIR` to `NamedTemporaryFile` so the temp file is on the same filesystem as the target.
**Warning signs:** `OSError: [Errno 18]` on the `os.rename()` call.

### Pitfall 4: Proposal ID Collision

**What goes wrong:** Two proposals for the same agent in rapid succession get the same `proposal_id` (e.g., if timestamp resolution is seconds and two cycles run within 1 second).
**Why it happens:** Timestamp-only proposal IDs have 1-second granularity.
**How to avoid:** Use `datetime.utcnow().strftime("%Y%m%dT%H%M%S") + uuid.uuid4().hex[:6]` to guarantee uniqueness, or use milliseconds: `strftime("%Y%m%dT%H%M%S%f")[:19]`.
**Warning signs:** `FileExistsError` on `os.rename()` (unlikely on Linux but possible on fast test runs).

### Pitfall 5: H2 Regex Matches the Wrong Section

**What goes wrong:** `_replace_h2_section` replaces the wrong section when `target_section` is a substring of another H2 (e.g., `## Core` matching `## Core Beliefs`).
**Why it happens:** Partial `re.escape` match without anchoring to the full line.
**How to avoid:** Use `re.compile(r"^" + re.escape(target_section) + r"\n", re.MULTILINE)` — the `^` anchor plus `\n` after the heading ensures exact line match.
**Warning signs:** Wrong section content replaced; content post-replacement fails `load_soul()` parse expectations.

### Pitfall 6: `warmup_soul_cache()` Called Before `load_soul.cache_clear()` in Agent Church

**What goes wrong:** Warm-up loads stale soul into cache; the mutated SOUL.md is not reflected.
**Why it happens:** Swapped call order.
**How to avoid:** Always `cache_clear()` first, then `warmup_soul_cache()`. These two calls are always paired in this order (established Phase 15 pattern).
**Warning signs:** Agent continues with pre-mutation soul after a successful Agent Church run.

### Pitfall 7: agent_church.py Imports src.graph.*

**What goes wrong:** `from src.graph.state import SwarmState` or similar in `agent_church.py` violates Import Layer Law.
**Why it happens:** Agent Church is in `src.core`; developers may reach for SwarmState for type hints.
**How to avoid:** Agent Church operates on raw JSON dicts and `Path` objects only. It never imports from `src.graph.*`. Use plain `dict` instead of `SwarmState` for any type hints needed.
**Warning signs:** `test_import_boundaries.py` would fail if Agent Church is added to `TestCoreLeafImports`.

---

## Code Examples

Verified patterns from existing codebase:

### Loading config (from merit_updater.py)
```python
# Source: src/graph/nodes/merit_updater.py
_KAMI_CONFIG: Dict = {}

def _load_kami_config() -> Dict:
    global _KAMI_CONFIG
    if not _KAMI_CONFIG:
        config_path = Path(__file__).parents[3] / "config" / "swarm_config.yaml"
        try:
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
            _KAMI_CONFIG = cfg.get("kami", {})
        except Exception as e:
            logger.warning("merit_updater: could not load swarm_config.yaml: %s", e)
            _KAMI_CONFIG = {}
    return _KAMI_CONFIG
```

### Soul cache invalidation pattern (from soul_loader.py / Phase 15)
```python
# Source: src/core/soul_loader.py
from src.core.soul_loader import load_soul, warmup_soul_cache

# Agent Church post-approval refresh — always this order:
load_soul.cache_clear()
warmup_soul_cache()
```

### Non-blocking node failure pattern (from decision_card_writer_node)
```python
# Source: src/graph/orchestrator.py — decision_card_writer_node
try:
    _do_thing()
except Exception as e:
    logger.error("memory_writer: write failed for %s: %s", handle, e)
    # Continue — do not re-raise; MEMORY is forensic, not trade-critical
```

### Pydantic v2 model (from decision_card.py — same pattern for SoulProposal)
```python
# Source: src/core/decision_card.py
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Literal, Optional

class SoulProposal(BaseModel):
    proposal_id: str
    agent_id: str
    target_section: str
    proposed_content: str
    proposal_reasons: list[str]
    rationale: str
    proposed_at: datetime
    status: Literal["pending", "approved", "rejected", "rate_limited"]
    rejection_reason: Optional[str] = None
```

### Thesis extract (first sentence from a state dict field)
```python
def _extract_thesis_summary(value: object, max_chars: int = 200) -> str:
    """Return first sentence from a state field value.

    Handles: dict (looks for 'content', 'reasoning', 'summary' keys),
    str (uses directly). Returns empty string if not extractable.
    Truncates to max_chars with ellipsis.
    """
    text = ""
    if isinstance(value, dict):
        for key in ("content", "reasoning", "summary", "thesis"):
            if isinstance(value.get(key), str):
                text = value[key]
                break
    elif isinstance(value, str):
        text = value

    if not text:
        return ""

    # First sentence: split on ". " or "\n" — take the first fragment
    for delimiter in (". ", ".\n", "\n"):
        if delimiter in text:
            text = text.split(delimiter)[0] + "."
            break

    if len(text) > max_chars:
        text = text[:max_chars - 3] + "..."
    return text
```

### ALL_SOUL_HANDLES — canonical list (from kami.py)
```python
# Source: src/core/kami.py
ALL_SOUL_HANDLES = ["AXIOM", "MOMENTUM", "CASSANDRA", "SIGMA", "GUARDIAN"]

# Handle → agent_id mapping needed for MEMORY.md path resolution:
HANDLE_TO_AGENT_ID = {
    "AXIOM": "macro_analyst",
    "MOMENTUM": "bullish_researcher",
    "CASSANDRA": "bearish_researcher",
    "SIGMA": "quant_modeler",
    "GUARDIAN": "risk_manager",
}
# Note: RESEARCHER_HANDLE_MAP in kami.py is the inverse (agent_id → handle).
# Phase 17 needs the forward direction — define HANDLE_TO_AGENT_ID in memory_writer
# or extend kami.py (keeping Import Layer Law: kami.py is already core-safe).
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Global `data/MEMORY.md` for all agents | Per-agent `src/core/souls/{agent_id}/MEMORY.md` | Phase 17 (this phase) | Enables per-agent drift detection; Phase 19 ARS reads individual agent logs |
| Single MEMORY.md with max_memory_entries=100 (swarm_config) | Structured per-agent MEMORY.md capped at 50 entries | Phase 17 | Old config key (`self_improvement.memory_file`) remains but is unrelated — do not confuse with new per-agent files |
| No soul mutation path | Proposal workflow + Agent Church | Phase 17 | Agents can influence their own soul content within guarded structural constraints |

**Deprecated/outdated:**
- `self_improvement.memory_file: "data/MEMORY.md"` in `swarm_config.yaml`: This is the old global memory file from the self-improvement subsystem. Phase 17 MEMORY.md files are entirely separate; do not modify or reference the old path.

---

## Open Questions

1. **HANDLE_TO_AGENT_ID mapping**
   - What we know: `RESEARCHER_HANDLE_MAP` in `kami.py` maps two agent_id values to handles (not all five). `soul_loader.py` uses agent_id (lowercase directory name) not handle (uppercase).
   - What's unclear: Does `memory_writer` iterate by handle and need to resolve to agent_id for the MEMORY.md path, or iterate by agent_id?
   - Recommendation: Define `HANDLE_TO_AGENT_ID = {handle: agent_id, ...}` in `memory_writer.py` (or extend `kami.py`) to resolve `AXIOM → macro_analyst` etc. for `Path` construction. Keep it close to `ALL_SOUL_HANDLES`.

2. **KAMI_DELTA computation source**
   - What we know: `[KAMI_DELTA:]` in MEMORY entry = change in composite merit score this cycle. `merit_updater_node` computes new composite but does not return the delta — it returns the full updated `merit_scores` dict.
   - What's unclear: Should `memory_writer` compute delta as `new_composite - old_composite` from `state["merit_scores"]` (pre-update value) vs. post-update value?
   - Recommendation: `memory_writer` receives state *after* `merit_updater` has run. The pre-update composite is no longer directly in state. `memory_writer` should read the *current* `merit_scores` from state (post-update) and compare to the *previous cycle's* MEMORY entry's `[MERIT_SCORE:]` line — parse the last MEMORY entry for that agent to get `prev_score`, then `delta = current_score - prev_score`. On first entry, delta = 0.

3. **RequiresHumanApproval exception placement**
   - What we know: The exception must be raised (not silently caught) when L1 Orchestrator self-proposes.
   - What's unclear: What constitutes "L1 Orchestrator" as an `agent_id`? No L1 soul handle exists in `ALL_SOUL_HANDLES`.
   - Recommendation: L1 Orchestrator proposal is a defensive guard — `agent_id not in ALL_SOUL_HANDLES` or `agent_id == "orchestrator"` should trigger it. In practice no current code path creates such a proposal, but the guard must exist as specified by EVOL-03.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (installed in .venv) |
| Config file | pytest.ini or pyproject.toml (existing) |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/core/test_memory_writer.py tests/core/test_soul_proposal.py tests/core/test_agent_church.py -x -q` |
| Full suite command | `.venv/bin/python3.12 -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVOL-01 | MEMORY.md created on first write with correct format | unit | `.venv/bin/python3.12 -m pytest tests/core/test_memory_writer.py::test_memory_entry_written -x` | ❌ Wave 0 |
| EVOL-01 | MEMORY.md capped at 50 entries (oldest removed) | unit | `.venv/bin/python3.12 -m pytest tests/core/test_memory_writer.py::test_memory_cap_enforced -x` | ❌ Wave 0 |
| EVOL-01 | Skip-on-no-output: no entry written when canonical field is None | unit | `.venv/bin/python3.12 -m pytest tests/core/test_memory_writer.py::test_skip_on_no_output -x` | ❌ Wave 0 |
| EVOL-01 | KAMI_DELTA computed correctly from previous MEMORY entry | unit | `.venv/bin/python3.12 -m pytest tests/core/test_memory_writer.py::test_kami_delta_computed -x` | ❌ Wave 0 |
| EVOL-01 | memory_writer returns {} (silent node) | unit | `.venv/bin/python3.12 -m pytest tests/core/test_memory_writer.py::test_memory_writer_silent -x` | ❌ Wave 0 |
| EVOL-01 | memory_writer continues on write failure (non-blocking) | unit | `.venv/bin/python3.12 -m pytest tests/core/test_memory_writer.py::test_memory_writer_nonblocking -x` | ❌ Wave 0 |
| EVOL-02 | SoulProposal model validates all required fields | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_proposal.py::test_proposal_schema_valid -x` | ❌ Wave 0 |
| EVOL-02 | Proposal written atomically (temp + rename) | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_proposal.py::test_proposal_atomic_write -x` | ❌ Wave 0 |
| EVOL-02 | KAMI_DELTA trigger fires when delta >= threshold | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_proposal.py::test_trigger_kami_delta -x` | ❌ Wave 0 |
| EVOL-02 | Drift streak trigger fires after N consecutive flagged entries | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_proposal.py::test_trigger_drift_streak -x` | ❌ Wave 0 |
| EVOL-02 | Merit floor trigger fires after K entries <= floor | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_proposal.py::test_trigger_merit_floor -x` | ❌ Wave 0 |
| EVOL-02 | One merged proposal emitted (not separate) when multiple triggers fire | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_proposal.py::test_merged_proposal -x` | ❌ Wave 0 |
| EVOL-02 | Rate limiting: proposal suppressed after K rejections in window | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_proposal.py::test_rate_limit -x` | ❌ Wave 0 |
| EVOL-03 | Agent Church approves valid proposal, mutates SOUL.md, clears cache | unit | `.venv/bin/python3.12 -m pytest tests/core/test_agent_church.py::test_church_approves -x` | ❌ Wave 0 |
| EVOL-03 | Agent Church rejects proposal with missing target_section | unit | `.venv/bin/python3.12 -m pytest tests/core/test_agent_church.py::test_church_rejects_missing_section -x` | ❌ Wave 0 |
| EVOL-03 | Agent Church rejects proposal exceeding char limit | unit | `.venv/bin/python3.12 -m pytest tests/core/test_agent_church.py::test_church_rejects_too_long -x` | ❌ Wave 0 |
| EVOL-03 | Agent Church raises RequiresHumanApproval for L1 orchestrator proposal | unit | `.venv/bin/python3.12 -m pytest tests/core/test_agent_church.py::test_church_l1_raises -x` | ❌ Wave 0 |
| EVOL-03 | load_soul.cache_clear() + warmup_soul_cache() called after approval | unit | `.venv/bin/python3.12 -m pytest tests/core/test_agent_church.py::test_church_cache_refresh -x` | ❌ Wave 0 |
| All | agent_church imports cleanly (Import Layer Law) | smoke | `.venv/bin/python3.12 -m pytest tests/core/test_import_boundaries.py -x` | ✅ (needs new assertion) |
| All | memory_writer_node in orchestrator graph between merit_updater → trade_logger | integration | `.venv/bin/python3.12 -m pytest tests/test_graph_wiring.py -x` | ✅ (needs new assertion) |

### Sampling Rate

- **Per task commit:** `.venv/bin/python3.12 -m pytest tests/core/test_memory_writer.py tests/core/test_soul_proposal.py tests/core/test_agent_church.py -x -q`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/core/test_memory_writer.py` — covers EVOL-01 (6 tests)
- [ ] `tests/core/test_soul_proposal.py` — covers EVOL-02 (7 tests)
- [ ] `tests/core/test_agent_church.py` — covers EVOL-03 (5 tests)
- [ ] `src/core/soul_proposal.py` — SoulProposal Pydantic model (needed before tests)
- [ ] `src/core/agent_church.py` — standalone review script (needed before tests)
- [ ] `src/graph/nodes/memory_writer.py` — LangGraph node (needed before tests)
- [ ] `RequiresHumanApproval` exception — define in `src/core/soul_errors.py` (extend existing hierarchy)
- [ ] Update `tests/core/test_import_boundaries.py::TestCoreLeafImports` — add `test_agent_church_imports_cleanly` and `test_soul_proposal_imports_cleanly`

No new framework installation required — pytest already present in `.venv`.

---

## Sources

### Primary (HIGH confidence)

- `src/core/soul_loader.py` — confirmed `load_soul()` / `warmup_soul_cache()` / `AgentSoul` / `_KNOWN_AGENTS`
- `src/core/kami.py` — confirmed `ALL_SOUL_HANDLES`, `RESEARCHER_HANDLE_MAP`, import layer law comment
- `src/graph/nodes/merit_updater.py` — confirmed config-loading pattern, async node structure, non-blocking fail pattern
- `src/graph/orchestrator.py` lines 344-345 — confirmed current edge: `decision_card_writer → merit_updater → trade_logger`
- `src/graph/state.py` — confirmed `SwarmState` fields: `macro_report`, `bullish_thesis`, `bearish_thesis`, `quant_proposal`, `risk_approval`, `merit_scores`, `active_persona`
- `src/core/soul_errors.py` — confirmed exception hierarchy: `SoulError > SoulNotFoundError | SoulValidationError | SoulSecurityError`
- `src/core/decision_card.py` — confirmed Pydantic v2 `BaseModel` pattern used in project
- `tests/core/conftest.py` — confirmed `clear_soul_caches` autouse fixture with `load_soul.cache_clear()`
- `tests/core/test_import_boundaries.py` — confirmed Import Layer Law enforcement + `TestCoreLeafImports` pattern
- `config/swarm_config.yaml` — confirmed existing `kami:` block structure; `phase17:` block does not yet exist
- `.planning/config.json` — confirmed `nyquist_validation` key absent (treated as enabled)
- `src/core/souls/macro_analyst/SOUL.md` — confirmed H2 section format: `## Core Beliefs`, `## Drift Guard`, `## Voice`, `## Non-Goals`

### Secondary (MEDIUM confidence)

- Python stdlib `os.rename()` + `tempfile.NamedTemporaryFile(dir=...)` — POSIX atomic write pattern; cross-filesystem limitation verified by engineering knowledge; `dir=` parameter is the standard fix documented in Python docs
- Pydantic v2.12.5 `BaseModel` — confirmed installed version; `model_dump()`, `model_validate()` API verified from existing usage in codebase

### Tertiary (LOW confidence)

- None. All research findings are grounded in direct codebase inspection.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all libraries already in use in codebase
- Architecture patterns: HIGH — patterns replicated directly from Phase 15/16 code; entry-boundary parse is self-contained stdlib regex
- Pitfalls: HIGH — identified from direct code reading (os.rename cross-device, H2 regex anchoring) and established project decisions (Import Layer Law, non-blocking pattern)

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable domain — no external API dependencies)
