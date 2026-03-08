---
phase: 16-kami-merit-index
verified: 2026-03-08T12:00:00Z
status: passed
score: 14/14 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 13/14
  gaps_closed:
    - "merit_scores values in SwarmState appear in MiFID II audit hash (round-trip SHA-256 deterministic with 4dp rounding)"
  gaps_remaining: []
  regressions: []
---

# Phase 16: KAMI Merit Index — Verification Report

**Phase Goal:** Agent reliability is measured by a multi-dimensional merit score that decays with time, persists across sessions, and replaces the character-length proxy in DebateSynthesizer consensus weighting
**Verified:** 2026-03-08T12:00:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (commit a31dad0)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | `compute_merit(dims, weights)` returns float in [0.1, 1.0] using α·accuracy + β·recovery + γ·consensus + δ·fidelity; INVALID_INPUT decreases Recovery | ✓ VERIFIED | `src/core/kami.py` compute_merit + _extract_recovery_signal; 23/23 kami unit tests pass |
| 2 | Cold start is 0.5; EMA via apply_ema(lam=0.9); bounds [0.1, 1.0]; weights from swarm_config.yaml sum to 1.0 | ✓ VERIFIED | kami.py constants confirmed; config/swarm_config.yaml kami: section with α+β+γ+δ=1.0 |
| 3 | merit_loader_node populates SwarmState["merit_scores"] from PostgreSQL at session start; cold-start defaults 0.5 | ✓ VERIFIED | `src/graph/nodes/merit_loader.py` wired as graph entry point; 4 tests pass |
| 4 | merit_loader_node is idempotent — non-None state returns without DB call | ✓ VERIFIED | Idempotency guard confirmed; test_merit_loader_idempotent passes |
| 5 | merit_updater_node applies EMA to Recovery, Consensus, Fidelity after each cycle; Accuracy unchanged in-cycle | ✓ VERIFIED | merit_updater.py EMA logic; test_merit_updater_accuracy_unchanged passes |
| 6 | merit_updater_node persists to DB before returning; DB failure returns {} | ✓ VERIFIED | _persist_merit called before return; test_merit_updater_db_fail_no_state_update passes |
| 7 | merit_loader is graph entry point; merit_updater is between decision_card_writer and trade_logger | ✓ VERIFIED | orchestrator.py set_entry_point("merit_loader"); decision_card_writer → merit_updater → trade_logger edge wired |
| 8 | initial_state includes merit_scores: None | ✓ VERIFIED | orchestrator.py initial_state confirmed |
| 9 | DebateSynthesizer reads merit_scores from SwarmState — no len(text) proxy | ✓ VERIFIED | debate.py: zero matches for len(bullish/bearish); merit_scores read from state; RESEARCHER_HANDLE_MAP used |
| 10 | Both sides zero or missing merit → weighted_consensus_score = 0.5 | ✓ VERIFIED | debate.py raw_score = 0.5 fallback; test_debate_synthesizer_neutral_fallback passes |
| 11 | Skeleton agent (fidelity=0.0 → composite near MERIT_FLOOR=0.1) cannot dominate consensus | ✓ VERIFIED | test_debate_synthesizer_skeleton_cannot_dominate passes |
| 12 | debate_history entries carry merit composite as "strength" field (not character length) | ✓ VERIFIED | debate.py uses bull_w / bear_w as strength; test_debate_synthesizer_strength_field_is_merit passes |
| 13 | merit_scores values in SwarmState appear in MiFID II audit hash (round-trip SHA-256 deterministic with 4dp rounding) | ✓ VERIFIED | test_merit_scores_in_audit_hash present (commit a31dad0); all 3 assertions pass — (a) merit_scores not in AUDIT_EXCLUDED_FIELDS, (b) different merit values produce different hashes, (c) 4dp rounding produces identical hashes for near-equal values |
| 14 | Thesis records stub directory exists at data/thesis_records/ | ✓ VERIFIED | data/thesis_records/.gitkeep and README.txt present |

**Score:** 14/14 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/core/kami.py` | KAMIDimensions, compute_merit, apply_ema, signal helpers | ✓ VERIFIED (wired) | Exports all required symbols; imported by merit_updater.py and debate.py |
| `config/swarm_config.yaml` | kami: config section | ✓ VERIFIED | weights α=0.30, β=0.35, γ=0.25, δ=0.10; sum=1.0 |
| `src/core/persistence.py` | agent_merit_scores table DDL | ✓ VERIFIED | CREATE TABLE IF NOT EXISTS agent_merit_scores with soul_handle PK, composite, dimensions JSONB, updated_at, evolution_suspended |
| `src/graph/state.py` | merit_scores field in SwarmState | ✓ VERIFIED | Plain Optional[Dict[str, Any]], no Annotated reducer |
| `src/graph/nodes/merit_loader.py` | merit_loader_node async function | ✓ VERIFIED (wired) | Imported in orchestrator.py; wired as entry point |
| `src/graph/nodes/merit_updater.py` | merit_updater_node async function | ✓ VERIFIED (wired) | Imported in orchestrator.py; wired between decision_card_writer and trade_logger |
| `src/graph/debate.py` | DebateSynthesizer using KAMI merit scores | ✓ VERIFIED | merit_scores read from state; RESEARCHER_HANDLE_MAP from kami imported; len() proxy absent |
| `tests/test_kami.py` | Unit tests for compute_merit, apply_ema, bounds | ✓ VERIFIED | 23 tests; all pass |
| `tests/core/test_merit_loader.py` | Integration tests | ✓ VERIFIED | 4 tests; all pass |
| `tests/core/test_merit_updater.py` | Integration tests | ✓ VERIFIED | 5 tests; all pass |
| `tests/test_audit_chain.py` | test_merit_scores_in_audit_hash | ✓ VERIFIED | Added in commit a31dad0; 3/3 tests in file pass including gap-closure test |
| `data/thesis_records/.gitkeep` | Directory stub for deferred Accuracy path | ✓ VERIFIED | .gitkeep and README.txt present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/graph/orchestrator.py` | `src/graph/nodes/merit_loader.py` | workflow.set_entry_point("merit_loader"); add_edge to classify_intent | ✓ WIRED | Confirmed |
| `src/graph/orchestrator.py` | `src/graph/nodes/merit_updater.py` | decision_card_writer → merit_updater → trade_logger | ✓ WIRED | Confirmed |
| `src/graph/nodes/merit_updater.py` | `src/core/kami.py` | from src.core.kami import apply_ema, compute_merit, KAMIDimensions | ✓ WIRED | Confirmed |
| `src/graph/nodes/merit_loader.py` | agent_merit_scores | SELECT soul_handle, composite, dimensions FROM agent_merit_scores | ✓ WIRED | Confirmed |
| `src/graph/debate.py` | SwarmState["merit_scores"] | merit_scores = state.get("merit_scores") or {}; RESEARCHER_HANDLE_MAP lookup | ✓ WIRED | Confirmed |
| `src/graph/debate.py` | `src/core/kami.py` | from src.core.kami import RESEARCHER_HANDLE_MAP, DEFAULT_MERIT | ✓ WIRED | Confirmed |
| `tests/test_audit_chain.py` | `src/core/audit_logger.py` | AUDIT_EXCLUDED_FIELDS check + _strip_excluded + SHA-256 hash | ✓ WIRED | Gap closed; test_merit_scores_in_audit_hash present and passing |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| KAMI-01 | 16-01-PLAN.md, 16-03-PLAN.md | Multi-dimensional formula (α·Accuracy + β·Recovery + γ·Consensus + δ·Fidelity) with configurable weights in swarm_config.yaml | ✓ SATISFIED | compute_merit() in kami.py; config/swarm_config.yaml kami: section; 23 unit tests green |
| KAMI-02 | 16-01-PLAN.md | EMA decay (λ=0.9), cold start 0.5, bounds [0.1, 1.0]; INVALID_INPUT penalises Recovery | ✓ SATISFIED | apply_ema(), _extract_recovery_signal() in kami.py; all related tests pass |
| KAMI-03 | 16-02-PLAN.md | merit_scores field in SwarmState; loaded from agent_merit_scores PostgreSQL at session start; persisted after each cycle | ✓ SATISFIED | merit_loader_node + merit_updater_node wired; 9 integration tests green; agent_merit_scores DDL in persistence.py |
| KAMI-04 | 16-03-PLAN.md | DebateSynthesizer uses KAMI merit scores; skeleton agents (empty IDENTITY.md) receive weight near MERIT_FLOOR | ✓ SATISFIED | debate.py rewired; len() proxy removed; 4 debate tests pass including skeleton_cannot_dominate |

All four KAMI requirements satisfied. No orphaned requirements found.

### Anti-Patterns Found

No blocker anti-patterns. No len(text) proxy residue in debate.py. No upward imports in kami.py.

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `src/core/kami.py` | Comment referencing src.graph (documentation only, not an actual import) | Info | No violation; informational comment only |

### Human Verification Required

None. All automated checks are sufficient for this phase.

### Regression Check

The pre-existing `tests/test_persistence.py::test_trade_warehouse_persistence` failure (`column "position_size" does not exist` — PostgreSQL schema mismatch) is unchanged from previous verification. It predates Phase 16 and is unrelated to the gap fix. No new failures introduced.

Full suite: 339/340 passing (1 pre-existing failure, same as initial verification).

### Gaps Summary

No gaps remain. The single gap from initial verification — the missing `test_merit_scores_in_audit_hash` in `tests/test_audit_chain.py` — was added in commit `a31dad0` and all three contractual assertions pass cleanly. All 14 must-haves are now verified.

---

_Verified: 2026-03-08T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification after: commit a31dad0 (test(16-03): add test_merit_scores_in_audit_hash)_
