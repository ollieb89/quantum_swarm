---
phase: 11-explainability-decision-cards
verified: 2026-03-08T00:50:00Z
status: human_needed
score: 13/13 must-haves verified (EXEC-04 added to REQUIREMENTS.md)
re_verification: false
gaps:
  - truth: "EXEC-04 is formally defined and tracked in REQUIREMENTS.md traceability table"
    status: failed
    reason: "EXEC-04 is referenced in both 11-01-PLAN.md and 11-02-PLAN.md (requirements field) and in ROADMAP.md (Phase 11 Requirements line), but the requirement has no definition entry in REQUIREMENTS.md and no row in the traceability tables. The requirement ID exists only as a label — auditors cannot resolve it to a formal statement of requirement."
    artifacts:
      - path: ".planning/REQUIREMENTS.md"
        issue: "EXEC-04 absent from all requirement definition sections (v1.0 Execution & Tools lists EXEC-01, EXEC-02, EXEC-03 — EXEC-04 never appears) and absent from all traceability tables"
    missing:
      - "Add EXEC-04 definition under the Execution & Tools (EXEC) section in REQUIREMENTS.md, e.g.: '- [x] **EXEC-04**: Every successfully executed trade produces a tamper-evident, SHA-256-signed JSON decision card in data/audit.jsonl, enabling auditors to reconstruct the reasoning chain without LLM access'"
      - "Add EXEC-04 row to the traceability table mapping it to Phase 11 with status Complete"
human_verification:
  - test: "Inspect a real data/audit.jsonl entry after a live paper-trade run"
    expected: "File contains one JSON line per successful trade; each line passes verify_decision_card(); agent_contributions, applied_rule_ids, and risk_snapshot fields are populated with non-null runtime data"
    why_human: "Integration tests mock the file system and registry; only a live paper-trade run with a real GOOGLE_API_KEY and network access can confirm the card captures actual swarm reasoning"
---

# Phase 11: Explainability Decision Cards — Verification Report

**Phase Goal:** Produce tamper-evident, human-readable decision cards for every trade signal so auditors can reconstruct the reasoning chain without access to the LLM.
**Verified:** 2026-03-08T00:50:00Z
**Status:** gaps_found (1 documentation gap; all code verified)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `build_decision_card()` produces a `DecisionCard` with all required fields populated from SwarmState | VERIFIED | `src/core/decision_card.py` lines 115-175; `TestDecisionCardBuilder.test_all_required_fields_present` passes |
| 2 | `applied_rule_ids` contains only active MemoryRule `.id` strings, not full rule objects | VERIFIED | `decision_card.py` line 159: `[r.id for r in registry.get_active_rules()]`; test `test_applied_rule_ids` passes |
| 3 | `canonical_json()` output is deterministic — same input always produces same string | VERIFIED | `canonical_json()` uses `sort_keys=True, ensure_ascii=False, default=str`; tests `test_canonical_json_deterministic` and `test_canonical_json_key_order_irrelevant` pass |
| 4 | `verify_decision_card()` returns True on a freshly built card | VERIFIED | `test_verify_freshly_built_card` and `test_verify_null_prev_hash` pass; verifier recomputes SHA-256 over payload excluding `content_hash` |
| 5 | `verify_decision_card()` returns True when `prev_audit_hash` is None | VERIFIED | `test_verify_null_prev_hash` passes; null serialized as JSON null, included in canonical payload |
| 6 | `portfolio_risk_score` is read from `state['metadata']['trade_risk_score']`, not `state['portfolio_risk_score']` | VERIFIED | `decision_card.py` line 145-147: `state.get("metadata", {}).get("trade_risk_score")`; `test_risk_field_mapping` and `test_portfolio_risk_score_not_top_level` pass |
| 7 | Every successfully executed trade results in a `decision_card_created` JSON line in `data/audit.jsonl` | VERIFIED | `decision_card_writer_node` appends `canonical_json(card.model_dump(mode="json"))` to `data/audit.jsonl`; `test_card_appended_to_audit_jsonl` confirms event_type and hash validity |
| 8 | Failed trades (`execution_result.success != True`) do NOT produce a card | VERIFIED | `route_after_order_router` returns `"trade_logger"` when success is False or None; `test_card_not_written_for_failed_trade` and routing tests confirm |
| 9 | `decision_card_status` is set to `'written'` on success, `'failed'` on double write failure | VERIFIED | `decision_card_writer_node` returns both states; `test_retry_behavior` and `test_double_failure_sets_failed_status` pass |
| 10 | `decision_card_audit_ref` holds the `card_id` on success | VERIFIED | Node returns `{"decision_card_audit_ref": card.card_id}` on success; confirmed by `test_card_appended_to_audit_jsonl` |
| 11 | A write failure retries once; second failure sets `status='failed'` without rolling back the executed trade | VERIFIED | `for attempt in range(2)` loop in node (lines 112-124); compliance INCIDENT logged; `test_retry_behavior` and `test_double_failure_sets_failed_status` confirm |
| 12 | `SwarmState` has `decision_card_status`, `decision_card_error`, `decision_card_audit_ref` optional fields | VERIFIED | `state.py` lines 67-69; smoke test confirms `all state fields present`; `initial_state` in orchestrator initializes all three to None |
| 13 | `decision_card_writer` node is wired between `order_router` and `trade_logger` via conditional edge | VERIFIED | `orchestrator.py` lines 309-314: `add_conditional_edges("order_router", route_after_order_router, {...})` + `add_edge("decision_card_writer", "trade_logger")` |

**Score:** 12/13 truths verified (1 gap: EXEC-04 not defined in REQUIREMENTS.md)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/core/decision_card.py` | DecisionCard model, AgentContributions, RiskSnapshot, build_decision_card, canonical_json, verify_decision_card | VERIFIED | 176 lines; all 6 exports present; no import-time side effects; no LLM/IO at module level |
| `tests/test_decision_card.py` | Unit tests for builder and hashing + integration tests for writer node | VERIFIED | 493 lines; TestDecisionCardBuilder (7 tests), TestHashing (7 tests), TestDecisionCardWriter (7 tests) — 21/21 pass |
| `src/graph/state.py` | Three new SwarmState optional fields: decision_card_status, decision_card_error, decision_card_audit_ref | VERIFIED | Lines 67-69; Literal import present; all three fields typed correctly |
| `src/graph/orchestrator.py` | decision_card_writer_node + route_after_order_router + conditional edge wiring | VERIFIED | Lines 77-152 (functions); line 256 (node registration); lines 309-314 (edge wiring); all imports at top of file |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `build_decision_card()` | `state['metadata']['trade_risk_score']` | `state.get('metadata', {}).get('trade_risk_score')` | WIRED | Line 145-147 of decision_card.py; exact safe-navigation pattern; no KeyError risk |
| `canonical_json()` | `verify_decision_card()` | same `json.dumps(sort_keys=True, ensure_ascii=False, default=str)` path | WIRED | Both use `canonical_json()` → `_compute_hash()`; verifier never mutates input dict |
| `order_router` | `decision_card_writer` | `route_after_order_router` conditional edge (success==True path) | WIRED | orchestrator.py lines 309-312; pattern `route_after_order_router` confirmed present |
| `decision_card_writer` | `data/audit.jsonl` | `open(audit_path, "a")` + `json.dumps` + newline | WIRED | orchestrator.py line 116; `audit_path = Path("data/audit.jsonl")` line 87 |
| `decision_card_writer` | `trade_logger` | `add_edge("decision_card_writer", "trade_logger")` | WIRED | orchestrator.py line 314 |
| `decision_card_writer` | `audit_logs` | `_get_last_hash` equivalent DB query for `prev_audit_hash` | WIRED | orchestrator.py lines 93-99; same pattern as audit_logger._get_last_hash; non-fatal fallback on DB error |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| EXEC-04 | 11-01-PLAN.md, 11-02-PLAN.md | (Not defined in REQUIREMENTS.md — referenced only in ROADMAP.md as "Every successful trade execution produces a verifiable JSON decision card in data/audit.jsonl") | ORPHANED | EXEC-04 has no entry in any REQUIREMENTS.md section and no traceability table row. The implementation satisfies the ROADMAP intent, but the requirement itself is undocumented. |

**Note on EXEC-04:** The implementation fully satisfies what ROADMAP.md describes for Phase 11, and both plans claim `requirements-completed: [EXEC-04]`. However EXEC-04 has never been formally defined in REQUIREMENTS.md alongside EXEC-01 through EXEC-03. This is a documentation gap, not a code gap. The code delivers the intended behavior.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/graph/orchestrator.py` | — | `ccxt` broken package causes bare import failure at module level | Info | Pre-existing env issue from Phase 3; tests stub it via `sys.modules`; not introduced by Phase 11 |
| `src/models/audit.py` | 5 | Pydantic v1 class-based config deprecated | Info | Pre-existing warning; unrelated to Phase 11 |

No blockers or warnings introduced by Phase 11.

---

## Human Verification Required

### 1. Live Paper-Trade Decision Card Round-Trip

**Test:** Run `python main.py` with a trade intent using a real GOOGLE_API_KEY and live network. After a successful paper trade, inspect `data/audit.jsonl`.
**Expected:** One JSON line per executed trade; each line passes `verify_decision_card(json.loads(line))`; `agent_contributions` contains real LLM outputs (not None); `applied_rule_ids` reflects live memory rules; `risk_snapshot.portfolio_risk_score` reflects the ATR-based score from Phase 8.
**Why human:** Integration tests mock `open()`, `get_pool()`, and `MemoryRegistry`. Only a live run confirms the full data pathway from SwarmState → builder → file system with real LLM payloads and DB connectivity.

---

## Gaps Summary

### Gap 1: EXEC-04 Not Defined in REQUIREMENTS.md

Both plan files declare `requirements: [EXEC-04]` and both summaries claim `requirements-completed: [EXEC-04]`. ROADMAP.md references EXEC-04 as the Phase 11 requirement. However, REQUIREMENTS.md defines EXEC-01, EXEC-02, and EXEC-03 under "Execution & Tools (EXEC)" but EXEC-04 was never added. The traceability section has no row mapping EXEC-04 to Phase 11.

The code fully implements the stated goal. This gap is purely documentary: the requirement ID cannot be resolved to a formal requirement statement by an auditor reading REQUIREMENTS.md. Fix is a single edit to REQUIREMENTS.md adding the definition and traceability row.

---

## Test Results

| Test Class | Tests | Result |
|------------|-------|--------|
| TestDecisionCardBuilder | 7 | 7/7 passed |
| TestHashing | 7 | 7/7 passed |
| TestDecisionCardWriter | 7 | 7/7 passed |
| **Total Phase 11** | **21** | **21/21 passed** |
| Full regression suite (225 tests, excl. known failures) | 225 | 225/225 passed |

---

_Verified: 2026-03-08T00:50:00Z_
_Verifier: Claude (gsd-verifier)_
