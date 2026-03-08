---
phase: 11-explainability-decision-cards
plan: "01"
subsystem: audit
tags: [pydantic, sha256, decision-card, audit, hashing, tdd]

# Dependency graph
requires:
  - phase: 09-structured-memory-registry
    provides: MemoryRegistry.get_active_rules() returning List[MemoryRule] with .id fields
  - phase: 08-portfolio-risk-governance
    provides: state["metadata"]["trade_risk_score"] — portfolio risk score field location
provides:
  - DecisionCard Pydantic model (AgentContributions, RiskSnapshot sub-models)
  - build_decision_card(state, registry, prev_audit_hash) builder function
  - canonical_json() deterministic serializer
  - verify_decision_card() SHA-256 integrity verifier
  - _compute_hash() internal helper
affects:
  - 11-02 (decision_card_writer LangGraph node will call build_decision_card)
  - any phase that reads data/audit.jsonl

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure Python service with no import-time side effects — no LLM, no I/O, no async at module level"
    - "Pydantic v2 model with nested sub-models (AgentContributions, RiskSnapshot)"
    - "content_hash excluded from its own payload before SHA-256 — avoids circular dependency"
    - "canonical_json: sort_keys=True, ensure_ascii=False, default=str — same pattern as audit_logger.py"
    - "build_decision_card() computes hash after model_dump(mode='json') so datetimes are ISO strings in payload"

key-files:
  created:
    - src/core/decision_card.py
    - tests/test_decision_card.py
  modified: []

key-decisions:
  - "portfolio_risk_score sourced from state.get('metadata', {}).get('trade_risk_score') — not a top-level SwarmState field (Phase 8 pattern)"
  - "content_hash excluded from its own hash payload — circular inclusion would make the hash unverifiable"
  - "prev_audit_hash=None is an explicit tested case, not a silent omission — null included as JSON null in payload"
  - "model_dump(mode='json') used before hashing so datetime fields become ISO strings consistently"

patterns-established:
  - "DecisionCard TDD: RED (14 failing tests) -> GREEN (implementation) -> verified clean with no refactor needed"
  - "verify_decision_card() is a pure function — never mutates card_dict, only reads and recomputes"

requirements-completed: [EXEC-04]

# Metrics
duration: 2min
completed: 2026-03-08
---

# Phase 11 Plan 01: DecisionCard Model, Builder, Canonical JSON, and Verifier Summary

**SHA-256 self-verifying DecisionCard Pydantic model with deterministic canonical JSON serializer, SwarmState builder, and immutable hash verifier — 14/14 TDD tests passing**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-08T00:27:10Z
- **Completed:** 2026-03-08T00:28:49Z
- **Tasks:** 1 (TDD: RED + GREEN, no refactor needed)
- **Files modified:** 2

## Accomplishments

- `DecisionCard` Pydantic v2 model with `AgentContributions` and `RiskSnapshot` sub-models — all fields per spec
- `build_decision_card(state, registry, prev_audit_hash)` correctly sources `portfolio_risk_score` from `state.get("metadata", {}).get("trade_risk_score")` and extracts rule IDs via `registry.get_active_rules()`
- `canonical_json()` is deterministic: sort_keys=True, ensure_ascii=False, default=str — key insertion order is irrelevant
- `verify_decision_card()` recomputes SHA-256 from payload (excluding `content_hash`) and returns True/False without mutating the dict
- `prev_audit_hash=None` is an explicit tested case — null is serialized as JSON null and included in the hash payload
- 14 unit tests in `TestDecisionCardBuilder` and `TestHashing` — all passing

## Task Commits

1. **RED: Failing tests** - `47a1e93` (test)
2. **GREEN: Implementation** - `50afc84` (feat)

**Plan metadata:** committed with final docs commit

## Files Created/Modified

- `src/core/decision_card.py` — DecisionCard model, AgentContributions, RiskSnapshot, build_decision_card, canonical_json, _compute_hash, verify_decision_card
- `tests/test_decision_card.py` — 14 unit tests across TestDecisionCardBuilder and TestHashing

## Decisions Made

- `content_hash` excluded from its own SHA-256 payload (avoids circular dependency; verifier recomputes over the same exclusion)
- `model_dump(mode="json")` called before hashing so datetime fields serialize to ISO strings consistently across environments
- `prev_audit_hash=None` is an explicit tested edge case, not a silent omission — JSON null is written into the payload and included in the hash
- `portfolio_risk_score` sourced via `state.get("metadata", {}).get("trade_risk_score")` — follows Phase 8 pattern; no top-level SwarmState field of that name exists

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `src/core/decision_card.py` fully tested and exported; ready for Plan 02 to wire `decision_card_writer` LangGraph node
- `build_decision_card()` accepts optional `registry` and `prev_audit_hash` — Plan 02 will pass live instances
- No blockers

---
*Phase: 11-explainability-decision-cards*
*Completed: 2026-03-08*
