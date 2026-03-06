# Implementation Plan: Phase 1 - Foundation & Orchestration (L1)

**Project:** Quantum Swarm
**Phase:** 1
**Date:** 2026-03-06
**Status:** In Progress

---

## Context

The LangGraph `StateGraph` orchestrator and L3 executor nodes have been built (previous sprint — see `plans_archive/`).
Phase 1 now focuses on three remaining foundational deliverables that complete the L1 layer:

1. Orchestration Consolidation & Blackboard Implementation
2. Security Guardrails (ClawGuard)
3. Skill Discovery & Deterministic Bypass

---

## Deliverable 1 — Orchestration Consolidation & Blackboard Implementation

### Goal
Retire the legacy `src/orchestrator/strategic_l1.py` and implement a filesystem blackboard so agents communicate via structured files rather than in-process calls.

### Approach
- **Why blackboard:** `communication: filesystem_blackboard` is the authoritative architecture decision. It decouples agents for independent deployment and audit.
- **Why retire legacy:** `src/graph/orchestrator.py` supersedes `src/orchestrator/strategic_l1.py`. Keeping both creates ambiguity.

### Steps
- [x] Archive `src/orchestrator/strategic_l1.py` → `plans_archive/legacy/strategic_l1.py` and delete original
- [x] Create `src/blackboard/` module:
  - `src/blackboard/__init__.py`
  - `src/blackboard/board.py` — `Blackboard` class: read/write typed JSON slots under `data/blackboard/`
- [x] Update `src/graph/orchestrator.py` nodes to write outputs to blackboard slots alongside `SwarmState` (risk_approval, final_decision via src/graph/nodes/l1.py)
- [x] Create `tests/test_blackboard.py` — verify read/write/slot isolation + wiring (9/9 passing)

### Files
| Action | Path |
|--------|------|
| Archive + delete | `src/orchestrator/strategic_l1.py` |
| Create | `src/blackboard/board.py` |
| Create | `src/blackboard/schema.py` |
| Modify | `src/graph/orchestrator.py` |
| Create | `tests/test_blackboard.py` |

---

## Deliverable 2 — Security Guardrails (ClawGuard)

### Goal
Intercept agent outputs before execution to enforce hard safety rules: no unapproved live orders, no credential leakage, no consensus bypass.

### Approach
- Implement as a LangGraph node inserted before `order_router_node`
- Rules are declarative (config-driven) so they can be audited without code changes

### Steps
- [x] Create `src/security/` module:
  - `src/security/__init__.py`
  - `src/security/claw_guard.py` — `ClawGuard` class with rule engine
- [x] Rules to implement:
  - `require_risk_approval` — block if `risk_approved != True`
  - `require_consensus_threshold` — block if `weighted_consensus_score < config.min_consensus`
  - `no_credential_in_messages` — scan `messages` for credential patterns (regex)
  - `paper_trade_only` — force `dry_run=True` unless explicitly unlocked in config
- [x] Wire `claw_guard_node` into the graph between `risk_manager_node` and `order_router_node`
- [x] Create `tests/test_claw_guard.py` — test each rule passes/blocks correctly (14/14 passing)

### Files
| Action | Path |
|--------|------|
| Create | `src/security/claw_guard.py` |
| Modify | `src/graph/orchestrator.py` (wire node) |
| Modify | `config/` (add `min_consensus`, `paper_trade_only` keys) |
| Create | `tests/test_claw_guard.py` |

---

## Deliverable 3 — Skill Discovery & Deterministic Bypass

### Goal
Allow the orchestrator to discover available skills at startup and route deterministic intents (e.g. "show portfolio") directly to handler functions, bypassing the LLM graph entirely.

### Approach
- Skills live in `src/skills/` (already partially populated)
- A registry scans for skills at startup and maps intent → handler
- Deterministic bypass: if intent matches a registered skill, call it directly and return; skip graph invocation

### Steps
- [x] Create `src/skills/registry.py` — `SkillRegistry` class:
  - `discover()` — scans `src/skills/` for modules exposing `SKILL_INTENT` and `handle(state)`
  - `route(intent, state)` — returns handler result or `None` if no match
- [x] Add `SKILL_INTENT` + `handle()` to existing skill files (`market_analysis.py`, `crypto_learning.py`)
- [x] Update `classify_intent` node in `src/graph/orchestrator.py` to check registry before graph routing
- [x] Create `tests/test_skill_registry.py` — verify discovery, routing, and bypass (8/8 passing)

### Files
| Action | Path |
|--------|------|
| Create | `src/skills/registry.py` |
| Modify | `src/skills/market_analysis.py` |
| Modify | `src/skills/crypto_learning.py` |
| Modify | `src/graph/orchestrator.py` |
| Create | `tests/test_skill_registry.py` |

---

## Rollback Plan

1. All changes are additive except the `strategic_l1.py` archive — which is preserved in `plans_archive/legacy/`
2. To revert ClawGuard: remove `claw_guard_node` from graph edges in `orchestrator.py`
3. To revert Skill Discovery: remove registry call from `classify_intent`

---

## Security Checklist

- [ ] ClawGuard `no_credential_in_messages` rule covers API keys, passwords, tokens
- [ ] Blackboard slot files are written to `data/blackboard/` (gitignored) not committed
- [ ] `paper_trade_only` defaults to `True` in config — live trading requires explicit opt-in
- [ ] Skill handlers receive a copy of state, cannot mutate graph state directly

---

## Completion Criteria

- [x] `src/orchestrator/strategic_l1.py` removed from active codebase
- [x] Blackboard reads/writes verified by `tests/test_blackboard.py`
- [x] ClawGuard blocks a simulated unapproved order in `tests/test_claw_guard.py`
- [x] Skill registry discovers and routes at least 2 skills in `tests/test_skill_registry.py`
- [x] All existing tests still pass (49/49)
