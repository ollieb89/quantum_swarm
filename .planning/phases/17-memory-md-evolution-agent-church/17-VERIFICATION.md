---
phase: 17-memory-md-evolution-agent-church
verified: 2026-03-08T14:10:00Z
status: passed
score: 19/19 must-haves verified
re_verification: false
---

# Phase 17: MEMORY.md Evolution + Agent Church Verification Report

**Phase Goal:** Each agent maintains a capped structured self-reflection log after every task cycle, can propose edits to its own SOUL.md, and those proposals are reviewed by a standalone out-of-band Agent Church script before any soul file is mutated.

**Verified:** 2026-03-08T14:10:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | After a cycle where an agent produced output, its MEMORY.md gains exactly one new structured entry with all required labeled fields | VERIFIED | `_build_entry` produces `=== timestamp ===`, `[AGENT:]`, `[KAMI_DELTA:]`, `[MERIT_SCORE:]`, `[DRIFT_FLAGS:]`, `[THESIS_SUMMARY:]`; `test_memory_entry_written` PASSES |
| 2 | MEMORY.md is created on first write and never exceeds 50 entries — oldest are dropped when cap exceeded | VERIFIED | `_cap_entries` returns `entries[-50:]`; `test_memory_cap_enforced` PASSES (51st write → exactly 50 entries) |
| 3 | If an agent's canonical output field is None, no MEMORY entry is written (skip-on-no-output) | VERIFIED | `_process_agent` returns early when `value is None`; `test_skip_on_no_output` PASSES |
| 4 | `[KAMI_DELTA:]` is computed from diff between current merit score and previous MEMORY entry's `[MERIT_SCORE:]` — first entry uses 0.5 cold-start | VERIFIED | `kami_delta = current_composite - prev_score`; `_extract_prev_score` returns 0.5 on missing file; `test_kami_delta_computed` PASSES |
| 5 | `memory_writer_node` returns `{}` (silent, no SwarmState mutation) and continues on write failure without raising | VERIFIED | Node returns `{}`; each handle wrapped in `try/except Exception` with `logger.error`; `test_memory_writer_silent` and `test_memory_writer_nonblocking` PASS |
| 6 | SoulProposal is a Pydantic v2 BaseModel with all required fields and status enum validation | VERIFIED | `SoulProposal(BaseModel)` with `Literal["pending","approved","rejected","rate_limited"]`; `test_proposal_schema_valid` PASSES |
| 7 | A proposal JSON is written atomically (temp file + os.rename) to `data/soul_proposals/{proposal_id}.json` | VERIFIED | `write_proposal_atomic` uses `NamedTemporaryFile(delete=False)` + `os.rename`; `test_proposal_atomic_write` PASSES |
| 8 | KAMI delta trigger fires when `|delta| >= kami_delta_threshold` (0.05 default) | VERIFIED | `_check_triggers` checks `abs(kami_delta) >= threshold`; `test_trigger_kami_delta` PASSES |
| 9 | Drift streak trigger fires when last N consecutive entries all have non-empty `[DRIFT_FLAGS:]` | VERIFIED | `_extract_drift_flags` normalises "none" to ""; tail check requires `len(entries) >= streak_n`; `test_trigger_drift_streak` PASSES |
| 10 | Merit floor trigger fires when last K consecutive entries all have `[MERIT_SCORE:] <= merit_floor` | VERIFIED | `_extract_merit_score_from_entry` parses score; floor check with cold-start guard; `test_trigger_merit_floor` PASSES |
| 11 | When multiple triggers fire in same cycle, exactly one merged proposal is emitted with all trigger names in `proposal_reasons` | VERIFIED | `_check_triggers` returns all matched names; `write_proposal_atomic` called once with merged list; `test_merged_proposal` PASSES |
| 12 | After `rate_limit_rejection_k` rejections for same `(agent_id, target_section)` within window, proposals for that pair are suppressed | VERIFIED | `check_rate_limit` scans `*.json` for `status=="rejected"` within window; `test_rate_limit` PASSES |
| 13 | Running `python -m src.core.agent_church` processes all pending proposals in `data/soul_proposals/` | VERIFIED | `__main__` block calls `review_proposals()`; smoke test with empty dir returns `{'approved':0,'rejected':0,'skipped':0}` |
| 14 | An approved proposal has its target H2 section replaced in the agent's SOUL.md in-place | VERIFIED | `_apply_proposal` calls `_replace_h2_section` + `soul_path.write_text`; `test_church_approves` PASSES |
| 15 | After approval, `load_soul.cache_clear()` is called before `warmup_soul_cache()` (Phase 15 order) | VERIFIED | Lines 206-207 in `agent_church.py`; `test_church_cache_refresh` asserts call order PASSES |
| 16 | A proposal targeting a section not found in SOUL.md is rejected with a logged reason | VERIFIED | `_reject_proposal` called with `"Section not found in SOUL.md: ..."` on `ValueError`; `test_church_rejects_missing_section` PASSES |
| 17 | A proposal where `len(proposed_content) > 500` chars is rejected | VERIFIED | Char-limit check at line 295 in `agent_church.py`; `test_church_rejects_too_long` PASSES |
| 18 | A proposal where `agent_id` is not in `ALL_SOUL_HANDLES` raises `RequiresHumanApproval` — it does NOT silently pass or get auto-rejected | VERIFIED | `_is_l1_orchestrator` returns True; `raise RequiresHumanApproval(...)` is NOT caught inside `review_proposals`; `test_church_l1_raises` PASSES |
| 19 | `memory_writer_node` appears in the orchestrator graph between `merit_updater` and `trade_logger` | VERIFIED | `orchestrator.py` line 292: `add_node("memory_writer", ...)`, lines 349-350: `merit_updater→memory_writer`, `memory_writer→trade_logger`; `test_memory_writer_wired_between_merit_updater_and_trade_logger` PASSES |

**Score:** 19/19 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/graph/nodes/memory_writer.py` | LangGraph node: `memory_writer_node`, helpers, config loader | VERIFIED | 482 lines; exports `memory_writer_node`, `HANDLE_TO_AGENT_ID`, all documented helpers |
| `src/core/soul_errors.py` | `RequiresHumanApproval(SoulError)` added to hierarchy | VERIFIED | Present at line 20; existing hierarchy untouched |
| `config/swarm_config.yaml` | `phase17:` block with all 8 tunables | VERIFIED | Block at line 262; all 8 keys present with correct defaults |
| `tests/core/test_memory_writer.py` | 6 unit tests covering EVOL-01 behaviours | VERIFIED | 6/6 tests PASS |
| `src/core/soul_proposal.py` | `SoulProposal` model, atomic write helpers, rate-limit | VERIFIED | Pydantic v2 model; `write_proposal_atomic`, `check_rate_limit`, `build_proposal_id` present |
| `tests/core/test_soul_proposal.py` | 7 unit tests covering EVOL-02 behaviours | VERIFIED | 7/7 tests PASS |
| `src/core/agent_church.py` | Standalone review script; `review_proposals()`, guards, H2 replacement | VERIFIED | `__main__` block present; all documented helpers implemented |
| `tests/core/test_agent_church.py` | 5 unit tests covering EVOL-03 behaviours | VERIFIED | 5/5 tests PASS |
| `tests/core/test_import_boundaries.py` | Two new assertions: `test_agent_church_imports_cleanly`, `test_soul_proposal_imports_cleanly` | VERIFIED | Both present and PASS; also `test_agent_church_does_not_import_graph`, `test_soul_proposal_does_not_import_graph` present |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `memory_writer_node` | `src/core/souls/{agent_id}/MEMORY.md` | `Path.parent.mkdir` + `write_text` | WIRED | `_write_memory_entry` at line 254 creates parent dir and writes; path: `souls_dir / agent_id / "MEMORY.md"` |
| `memory_writer_node` | `state['merit_scores']` | reads `composite` key + `_extract_prev_score` from MEMORY.md | WIRED | `_process_agent` line 399-409; delta computed from persisted score vs current composite |
| `memory_writer._process_agent` | `src/core/soul_proposal.write_proposal_atomic` | `from src.core.soul_proposal import write_proposal_atomic` | WIRED | Import at line 47; called at line 447 after trigger check |
| `soul_proposal.check_rate_limit` | `data/soul_proposals/*.json` | `proposals_dir.glob("*.json")` + `status=="rejected"` | WIRED | Lines 140-160 in `soul_proposal.py`; scans JSON ledger within time window |
| `agent_church._apply_proposal` | `src/core/souls/{agent_id}/SOUL.md` | `soul_path.read_text` + `_replace_h2_section` + `soul_path.write_text` | WIRED | Lines 189-199 in `agent_church.py`; full read-modify-write cycle |
| `agent_church._apply_proposal` | `soul_loader.load_soul` + `warmup_soul_cache` | `load_soul.cache_clear()` then `warmup_soul_cache()` | WIRED | Lines 206-207; Phase 15 order enforced |
| `src/graph/orchestrator.py` | `memory_writer_node` | `add_node("memory_writer")` + edge chain | WIRED | Lines 292, 349-350; import at line 38 |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| EVOL-01 | 17-01 | Per-agent MEMORY.md structured self-reflection log, capped at 50 entries, with `[KAMI_DELTA:]` and `[MERIT_SCORE:]` markers | SATISFIED | `memory_writer_node` writes structured entries; 6/6 tests pass; cap enforced |
| EVOL-02 | 17-02 | Agent can propose a SOUL.md diff stored as Pydantic-validated `SoulProposal` JSON; three triggers (KAMI_SPIKE, DRIFT_STREAK, MERIT_FLOOR); rate-limit guard | SATISFIED | `soul_proposal.py` + `_check_triggers` in `memory_writer.py`; 7/7 tests pass; atomic write confirmed |
| EVOL-03 | 17-03 | Standalone `agent_church.py` script reviews proposals with structural heuristics, applies approved diffs with cache invalidation, raises `RequiresHumanApproval` for L1 self-proposals | SATISFIED | `agent_church.py` fully functional; `python -m src.core.agent_church` runs; 5/5 tests pass |

No orphaned requirements found — all three EVOL IDs claimed in plans and marked complete in REQUIREMENTS.md.

---

## Anti-Patterns Found

None. Scanned `memory_writer.py`, `soul_proposal.py`, `agent_church.py`, `orchestrator.py` for stubs, empty implementations, placeholder returns, and TODO markers. No blockers or warnings found.

- `memory_writer_node` returns `{}` unconditionally — correct (documented silent node contract, not a stub)
- `proposed_content` sentinel `"[PENDING — Agent Church will draft content based on MEMORY.md context]"` is intentional per plan design (memory_writer does not draft soul content)
- No `console.log`, `return null`, `return {}` stub patterns in implementation logic

---

## Human Verification Required

### 1. Real-cycle MEMORY.md population

**Test:** Run the full swarm graph against a live market signal and inspect `src/core/souls/macro_analyst/MEMORY.md` after execution.
**Expected:** A new `=== ISO8601Z ===` entry appears with all six labeled fields populated from the actual cycle output.
**Why human:** Cannot verify live LangGraph execution or Gemini API response content programmatically in this context.

### 2. Agent Church applied SOUL.md mutation end-to-end

**Test:** Place a valid pending SoulProposal JSON targeting `## Core Beliefs` in `data/soul_proposals/`, then run `python -m src.core.agent_church`. Inspect the target agent's SOUL.md before and after.
**Expected:** The `## Core Beliefs` section content is replaced by `proposed_content`; proposal JSON shows `status: approved`.
**Why human:** Real SOUL.md files would need to exist for the test agent with the target section; confirming actual file mutation requires manual inspection.

---

## Test Suite Health

| Scope | Count | Result |
|-------|-------|--------|
| Phase 17 tests (`test_memory_writer.py`, `test_soul_proposal.py`, `test_agent_church.py`) | 18 | 18 PASS |
| Import boundary tests (`test_import_boundaries.py`) | 14 | 14 PASS |
| Graph wiring test (`test_memory_writer_wired_...`) | 1 | 1 PASS |
| Full suite | 363 | 362 PASS, 1 FAIL (pre-existing PostgreSQL failure `test_trade_warehouse_persistence` — unrelated to Phase 17) |

---

## Gaps Summary

No gaps. All 19 must-have truths are satisfied by substantive, wired implementations. All 3 requirement IDs (EVOL-01, EVOL-02, EVOL-03) are satisfied. The Import Layer Law is enforced for all new `src.core.*` modules. The orchestrator graph wiring is confirmed by both code inspection and a dedicated passing test.

The single failing test (`test_trade_warehouse_persistence`) is the pre-existing PostgreSQL failure documented since Phase 16 and is unrelated to Phase 17 work.

---

_Verified: 2026-03-08T14:10:00Z_
_Verifier: Claude (gsd-verifier)_
