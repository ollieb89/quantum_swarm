---
phase: 10-rule-validation-harness
verified: 2026-03-08T06:00:00Z
status: human_needed
score: 11/11 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 10/11
  gaps_closed:
    - "MEM-06 formally registered in REQUIREMENTS.md — v1.3 section added with definition and traceability entry (Plan 10-04)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Run full self-improvement pipeline end-to-end"
    expected: "A proposed rule written by RuleGenerator transitions from proposed to either active or rejected in data/memory_registry.json; data/audit.jsonl contains one new event line with all required fields: rule_id, before_status, after_status, baseline_sharpe, treatment_sharpe, sharpe_delta, baseline_drawdown, treatment_drawdown, drawdown_delta, baseline_win_rate, treatment_win_rate, win_rate_delta"
    why_human: "Requires a live GOOGLE_API_KEY for RuleGenerator's LLM call, a live NautilusTrader backtest environment, and actual proposed rules flowing through the pipeline. Cannot be verified by static analysis or mocked tests."
---

# Phase 10: Rule Validation Harness — Verification Report

**Phase Goal:** Backtest or replay newly generated memory rules before promoting them to 'active'. Satisfies requirement MEM-06: proposed memory rules are automatically backtested before promotion; rules only transition to active if they pass a 2-of-3 metric evaluation harness (Sharpe ratio delta, max drawdown delta, win rate delta). Failing rules are moved to rejected. All promotion/rejection events are appended to `data/audit.jsonl` with full metric evidence.
**Verified:** 2026-03-08
**Status:** human_needed — all automated checks pass; one non-blocking live smoke test remains
**Re-verification:** Yes — gap closure after Plan 10-04 (documentation gap on MEM-06 in REQUIREMENTS.md)

---

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1   | 11 test methods exist in tests/test_rule_validator.py (9 unit + 2 integration) | VERIFIED | 349-line file; TestRuleValidator (9 methods), TestRuleValidatorIntegration (2 methods), all real assertions |
| 2   | MemoryRegistry.get_proposed_rules() exists and is importable | VERIFIED | Line 68 of src/core/memory_registry.py — one-line filter mirroring get_active_rules() |
| 3   | config/swarm_config.yaml contains validation_lookback_days: 90 and validation_min_trades: 10 | VERIFIED | Lines 169-170 under self_improvement section |
| 4   | RuleValidator class instantiates without error (no LLM, no GOOGLE_API_KEY) | VERIFIED | src/agents/rule_validator.py has no LLM dependency; pure data pipeline using yaml, asyncio, json |
| 5   | validate_proposed_rules() runs two backtester calls per proposed rule | VERIFIED | Lines 80-88 of rule_validator.py — two asyncio.run(asyncio.to_thread(...)) calls; test_two_backtest_calls_per_rule asserts mock_bt.call_count == 2 |
| 6   | Rules passing 2-of-3 metric improvement are promoted to active | VERIFIED | _passes_validation() at lines 137-147; test_pass_promotes_to_active confirms status == "active" |
| 7   | Rules failing 2-of-3 are moved to rejected | VERIFIED | Same _passes_validation() logic; test_fail_rejects_rule confirms status == "rejected" |
| 8   | Backtest errors leave rule proposed and do not raise | VERIFIED | try/except at lines 79-94 catches all exceptions, logs error, continues; test_backtest_error_leaves_proposed confirms count == 0 and status == "proposed" |
| 9   | Promotion/rejection events appended to audit.jsonl with required fields | VERIFIED | _write_audit() at lines 149-171 writes 14-field JSON lines; test_audit_event_on_promotion and test_audit_event_on_rejection confirm all required fields |
| 10  | RuleGenerator.persist_rules() auto-calls validate_proposed_rules() | VERIFIED | Lines 18, 118-121 of rule_generator.py — RuleValidator imported at top level, instantiated inline at end of persist_rules(), validator.registry shared |
| 11  | MEM-06 formally registered in REQUIREMENTS.md | VERIFIED | 3 occurrences in .planning/REQUIREMENTS.md: definition under v1.3 section (line 77), traceability entry mapping to Phase 10 Complete (line 149), footer timestamp update (line 158) |

**Score:** 11/11 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `tests/test_rule_validator.py` | 11 test methods across 2 classes | VERIFIED | 349 lines, 9 unit tests in TestRuleValidator + 2 integration tests in TestRuleValidatorIntegration; all real assertions, none stubs |
| `src/agents/rule_validator.py` | RuleValidator with validate_proposed_rules(), _passes_validation(), _write_audit() | VERIFIED | 172 lines, all three methods substantive and wired |
| `src/core/memory_registry.py` | get_proposed_rules() alongside get_active_rules() | VERIFIED | Line 68 — filters schema.rules by status == "proposed" |
| `config/swarm_config.yaml` | validation_lookback_days: 90 and validation_min_trades: 10 | VERIFIED | Lines 169-170 under self_improvement section |
| `src/agents/rule_generator.py` | persist_rules() wired to call RuleValidator | VERIFIED | Import at line 18; inline call at lines 119-121 |
| `.planning/REQUIREMENTS.md` | MEM-06 defined under v1.3, mapped to Phase 10 in Traceability | VERIFIED | Appears 3 times: definition, traceability entry, footer — all correct |

---

## Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| tests/test_rule_validator.py | src/agents/rule_validator.RuleValidator | import at line 16 | WIRED | `from src.agents.rule_validator import RuleValidator` confirmed |
| tests/test_rule_validator.py | src/core/memory_registry.get_proposed_rules | used in integration tests via fresh_reg.get_proposed_rules() | WIRED | Line 297 of test file |
| src/agents/rule_validator.py | src/graph/agents/l3/backtester._run_nautilus_backtest | top-level import at line 18 | WIRED | `from src.graph.agents.l3.backtester import _run_nautilus_backtest` — enables mock patch at correct path |
| src/agents/rule_validator.py | src/core/memory_registry.MemoryRegistry | self.registry.update_status() call | WIRED | Line 111 of rule_validator.py |
| src/agents/rule_validator.py | data/audit.jsonl | _write_audit() opens in "a" mode | WIRED | Line 170: `with open(self.audit_path, "a") as f:` |
| src/agents/rule_generator.persist_rules() | src/agents/rule_validator.RuleValidator.validate_proposed_rules() | inline call at end of persist_rules() | WIRED | Lines 119-121 of rule_generator.py confirmed |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
| ----------- | ------------ | ----------- | ------ | -------- |
| MEM-06 | 10-01-PLAN, 10-02-PLAN, 10-03-PLAN | Proposed memory rules auto-backtested before promotion via 2-of-3 metric harness; all events appended to audit.jsonl | SATISFIED | Implementation in rule_validator.py; wiring in rule_generator.py; 30/30 tests green; formally defined in REQUIREMENTS.md v1.3 section mapped to Phase 10 Complete |

**Coverage:** 1 requirement declared, 1 satisfied, 0 orphaned.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| None | — | — | — | No anti-patterns found in phase 10 artifacts |

Scan covered: `src/agents/rule_validator.py`, `src/agents/rule_generator.py` (wiring section only), `tests/test_rule_validator.py`. No TODO, FIXME, placeholder comments, stub returns, or empty handlers found.

---

## Test Suite Results (Verified Live)

```
30 passed, 2 warnings in 5.93s

tests/test_rule_validator.py       11/11  PASS
tests/test_structured_memory.py    14/14  PASS  (no regressions)
tests/test_self_improvement.py      5/5   PASS  (no regressions from persist_rules wiring)
```

---

## Human Verification Required

### 1. End-to-end self-improvement pipeline smoke run

**Test:** With a valid `GOOGLE_API_KEY` set, trigger the self-improvement loop so that `RuleGenerator.persist_rules()` is called with at least one proposed rule. Observe `data/memory_registry.json` and `data/audit.jsonl` after the run.
**Expected:** The rule transitions from `proposed` to either `active` or `rejected` in the registry JSON. `data/audit.jsonl` contains one new event line with all required fields: `rule_id`, `before_status`, `after_status`, `baseline_sharpe`, `treatment_sharpe`, `sharpe_delta`, `baseline_drawdown`, `treatment_drawdown`, `drawdown_delta`, `baseline_win_rate`, `treatment_win_rate`, `win_rate_delta`.
**Why human:** Requires a live Google API key for RuleGenerator's LLM call, a live NautilusTrader backtest environment, and actual proposed rules flowing through the pipeline. Cannot be verified by static analysis or mocked tests.

---

## Re-verification Summary

**Gap from previous verification (10/11): CLOSED**

The single failing truth from the initial verification — "MEM-06 formally registered in REQUIREMENTS.md" — has been resolved by Plan 10-04. The plan added:
- A new `## v1.3 Requirements` section with MEM-06's full formal definition (2-of-3 metric harness, audit.jsonl, status transitions)
- A `### v1.3 Requirements` subsection in the Traceability table mapping MEM-06 to Phase 10 with status Complete
- A footer timestamp update to 2026-03-08

Verified by `grep -c "MEM-06" .planning/REQUIREMENTS.md` returning 3 (definition, traceability row, footer).

**No regressions.** All 30 tests that passed in the initial verification continue to pass.

**All automated must-haves: 11/11 verified.** Status advances to `human_needed` — only the live smoke test (requiring a real API key and NautilusTrader environment) remains outstanding. This is a non-blocking quality gate; the automated test suite at 30/30 provides strong confidence in correctness.

---

_Verified: 2026-03-08_
_Verifier: Claude (gsd-verifier)_
