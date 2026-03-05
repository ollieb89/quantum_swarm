# LangGraph Migration Cleanup Design

**Date:** 2026-03-05
**Scope:** Production-ready cleanup (Critical + Important issues)
**Goal:** Make the LangGraph migration safe to ship and safe to build on

## Context

Phase 1 migrated orchestration from a custom `StrategicOrchestrator` to a LangGraph
StateGraph-based `LangGraphOrchestrator`. A code review identified 12 issues across
3 severity levels. This design addresses all Critical (3) and Important (5) issues.
Suggestions (4) are tracked as Phase 2 backlog.

## Approach: Graph-Owned Types (Option A)

Consumer analysis confirmed only one downstream call site (`main.py:105` via
`.to_dict()`). No tests, CLI handlers, API code, or notebooks import
`OrchestratorDecision`. This makes it safe to define a new, minimal type owned by
the graph module and drop the legacy dependency entirely.

---

## Fixes (Critical)

### Fix 1: Decouple from legacy module

**Problem:** `src/graph/orchestrator.py:169` imports `OrchestratorDecision`,
`AgentProposal`, `AgentSignal` from `src.orchestrator.strategic_l1`. `AgentProposal`
and `AgentSignal` are unused.

**Solution:** Create `src/graph/models.py` with a minimal frozen dataclass:

```python
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass(frozen=True)
class GraphDecision:
    task_id: str
    decision: str
    consensus_score: float = 0.0
    rationale: str = ""
    proposals: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
```

Update `orchestrator.py` to import `GraphDecision` from `.models`.

### Fix 2: Remove dead import in main.py

**Problem:** `main.py:18` imports `StrategicOrchestrator` which is unused.

**Solution:** Delete the import line.

### Fix 3: SwarmState missing defaults

**Problem:** `run_task` creates initial state without `intent`, `consensus_score`,
`compliance_flags`, etc. `route_by_intent` will `KeyError` on `state["intent"]`.

**Solution:** Add defaults to `initial_state` in `run_task` for all fields that
downstream nodes or routing logic access. Keep `SwarmState` TypedDict strict
(no `total=False`) so missing fields are caught during development.

```python
initial_state = {
    "task_id": task_id,
    "user_input": user_input,
    "intent": "unknown",
    "messages": [],
    "macro_report": None,
    "quant_proposal": None,
    "bullish_thesis": None,
    "bearish_thesis": None,
    "debate_resolution": None,
    "risk_approval": None,
    "consensus_score": 0.0,
    "compliance_flags": [],
    "final_decision": None,
    "metadata": {"created_at": datetime.now(timezone.utc).isoformat()},
}
```

---

## Fixes (Important)

### Fix 4: Deprecated `datetime.utcnow()`

**File:** `src/graph/orchestrator.py:151`
**Change:** `datetime.utcnow()` -> `datetime.now(timezone.utc)`, add `timezone` import.

### Fix 5: Config via `functools.partial`

**File:** `src/graph/orchestrator.py:103-108`
**Change:** Replace lambda closures with `functools.partial` for all 6 `add_node` calls.
Avoids shadowing LangGraph's `RunnableConfig` and makes binding explicit.

```python
from functools import partial
workflow.add_node("classify_intent", partial(classify_intent, config=config))
```

### Fix 6: POC module-level graph construction

**File:** `src/poc/langgraph_orchestrator_poc.py`
**Change:** Wrap graph construction (lines 125-160) in `def build_graph():`, call from
`if __name__ == "__main__":`.

### Fix 7: Commented-out code in main.py

**File:** `main.py:48-52`
**Change:** Delete the commented-out `StrategicOrchestrator` instantiation block.
Old code is preserved in `plans_archive/`.

### Fix 8: Legacy backup as importable .py

**File:** `src/orchestrator/strategic_l1_legacy.py`
**Change:** Move to `plans_archive/strategic_l1_legacy.py`. Keeps it outside `src/`
so linters, test discovery, and package scanners ignore it. Retains `.py` extension
for syntax highlighting when referenced.

---

## Phase 2 Backlog (Suggestions)

| # | Title | Acceptance Criteria |
|---|-------|-------------------|
| 9 | Node error handling | Decorator preserves node signature and returns updated state; error recorded under `state['errors']` list with node name + exception + traceback summary |
| 10 | Remove `python >= 3.9` from requirements.txt | Move to `pyproject.toml` `requires-python`, remove invalid line from requirements.txt |
| 11 | Add `src/poc/__init__.py` | Empty init file so POC modules are importable for test harnesses |
| 12 | POC/production state type divergence | POC `messages: List[str]` -> `List[dict]` matching production `SwarmState`; dict schema matches production (keys + types); mypy/pyright passes for both |

---

## Change Summary

| Fix | File(s) | Change |
|-----|---------|--------|
| 1 | New `src/graph/models.py` | `GraphDecision` frozen dataclass with `asdict()`-based `to_dict()` |
| 2 | `main.py` | Remove dead `StrategicOrchestrator` import |
| 3 | `src/graph/orchestrator.py` | Add all defaults to `initial_state` dict in `run_task` |
| 4 | `src/graph/orchestrator.py` | `datetime.now(timezone.utc)` + import |
| 5 | `src/graph/orchestrator.py` | `functools.partial` replacing lambda closures |
| 6 | `src/poc/langgraph_orchestrator_poc.py` | Wrap graph construction in function |
| 7 | `main.py` | Delete commented-out orchestrator block |
| 8 | `src/orchestrator/strategic_l1_legacy.py` | Move to `plans_archive/` |

**8 changes, 5 files touched, 1 new file, 1 file moved.**
