---
phase: 07-self-improvement-loop
plan: "01"
subsystem: agents
tags: [gemini, langchain, memory, self-improvement, review-agent, rule-generator, institutional-memory]

# Dependency graph
requires:
  - phase: 06-stop-loss-enforcement
    provides: ATR stop_loss data persisted in trades table, enabling meaningful weekly review
  - phase: 09-structured-memory-registry
    provides: MemoryRegistry JSON store and MemoryRule pydantic model
provides:
  - Lazy-init PerformanceReviewAgent queries trades+audit_logs, generates LLM drift report
  - Lazy-init RuleGenerator converts drift reports into structured MemoryRule objects
  - SelfLearningPipeline orchestrates full review-to-rules pipeline with asyncio.run
  - _load_institutional_memory() reads both MemoryRegistry JSON and data/MEMORY.md
  - --review CLI flag in main.py triggers the /review pipeline
  - 4/4 self-improvement tests passing; 11/11 combined Phase 7+8+9 tests passing
affects:
  - phase: 10-rule-validation-harness
  - phase: 11-explainability-decision-cards

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy LLM singleton: module-level _llm = None + _get_llm() getter + property with setter on class"
    - "Dual-source memory loading: MemoryRegistry JSON (governed) + MEMORY.md (pipeline output)"
    - "SelfLearningPipeline: async run_review_async() + sync run_review() wrapper for main.py"

key-files:
  created:
    - src/agents/review_agent.py
    - src/agents/rule_generator.py
    - src/agents/self_learning.py
    - src/core/memory_registry.py
    - src/models/memory.py
    - tests/test_self_improvement.py
    - tests/test_portfolio_risk.py
    - tests/test_structured_memory.py
  modified:
    - src/graph/orchestrator.py
    - main.py
    - data/MEMORY.md

key-decisions:
  - "Lazy LLM init applied to PerformanceReviewAgent and RuleGenerator — ChatGoogleGenerativeAI must not be instantiated at import time without GOOGLE_API_KEY"
  - "_load_institutional_memory reads both MemoryRegistry (JSON) and data/MEMORY.md so pipeline-written rules are injected into agent prompts alongside formally governed rules"
  - "test_rule_generator_logic fixed to use valid JSON mock output and assert on MemoryRule objects (not plain strings) to match the actual generate_rules() return type"

patterns-established:
  - "Lazy LLM property pattern: _llm field + @property getter that calls _get_llm() singleton + @llm.setter for test injection"

requirements-completed: []

# Metrics
duration: 12min
completed: 2026-03-07
---

# Phase 7: Self-Improvement Loop Summary

**PerformanceReviewAgent + RuleGenerator pipeline with lazy LLM init, dual-source memory injection (MemoryRegistry + MEMORY.md), and --review CLI command wired to SelfLearningPipeline**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-07T20:38:56Z
- **Completed:** 2026-03-07T20:51:00Z
- **Tasks:** 5 (steps 1-5 from plan)
- **Files modified:** 11

## Accomplishments

- Fixed lazy LLM init in `PerformanceReviewAgent` and `RuleGenerator` — both now use a module-level `_get_llm()` singleton and a `@property`/`@llm.setter` pair, matching the project-wide pattern established in STATE.md
- Updated `_load_institutional_memory()` in the orchestrator to load from both the structured `MemoryRegistry` (JSON) and `data/MEMORY.md` flat-file, so rules produced by the `/review` pipeline flow into agent prompts
- Added `--review` CLI flag to `main.py`, providing a non-interactive entry point to the weekly self-improvement pipeline
- Fixed `test_rule_generator_logic` to supply valid JSON list mock output and assert on `MemoryRule` objects, aligning the test with the actual API
- 4/4 `test_self_improvement.py` tests now pass; 11/11 combined Phase 7+8+9 tests pass

## Task Commits

1. **Steps 1-5: Full Phase 7 implementation** - `9a214d6` (feat)

## Files Created/Modified

- `src/agents/review_agent.py` - PerformanceReviewAgent with lazy LLM init; queries trades+audit_logs, generates LLM drift report
- `src/agents/rule_generator.py` - RuleGenerator with lazy LLM init; converts drift reports to MemoryRule objects and persists them via MemoryRegistry
- `src/agents/self_learning.py` - SelfLearningPipeline orchestrating review-to-rules pipeline (async + sync wrapper)
- `src/core/memory_registry.py` - MemoryRegistry managing lifecycle of MemoryRule objects in JSON store
- `src/models/memory.py` - MemoryRule and MemoryRegistrySchema pydantic models
- `src/graph/orchestrator.py` - `_load_institutional_memory()` updated to read both MemoryRegistry and data/MEMORY.md
- `main.py` - `--review` CLI flag added, wired to `swarm.run_weekly_review()`
- `tests/test_self_improvement.py` - All 4 tests fixed and passing
- `data/MEMORY.md` - Committed (initial content from earlier work)

## Decisions Made

- **Lazy LLM property pattern:** Used `@property`/`@setter` on the class rather than a bare attribute so tests can inject `generator.llm = mock_llm` without triggering Google API key validation at construction time. This matches the project-wide pattern documented in STATE.md.
- **Dual-source memory loading:** `_load_institutional_memory()` reads both the JSON registry (formally governed, status-filtered) and `data/MEMORY.md` (written by the pipeline). This allows immediately useful rule injection without requiring a governance review cycle for every auto-generated rule.
- **Test fix (rule_generator):** The original test expected plain string output from `generate_rules()`, which was never the correct interface — the implementation returns `List[MemoryRule]`. Fixed the test to supply valid JSON and assert on structured fields.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Lazy LLM init missing in PerformanceReviewAgent and RuleGenerator**
- **Found during:** Step 2/3 (review_agent.py, rule_generator.py)
- **Issue:** Both classes instantiated `ChatGoogleGenerativeAI` at `__init__` time, causing `ValidationError` in test environments without `GOOGLE_API_KEY`
- **Fix:** Applied lazy-init pattern: module-level `_llm = None`, `_get_llm()` getter, `@property`/`@setter` on the class
- **Files modified:** `src/agents/review_agent.py`, `src/agents/rule_generator.py`
- **Verification:** `test_review_agent_data_fetch` and `test_rule_generator_logic` both pass without API key
- **Committed in:** `9a214d6`

**2. [Rule 1 - Bug] test_rule_generator_logic used wrong mock output format and wrong assertion type**
- **Found during:** Step 5 (verification)
- **Issue:** Test mocked LLM to return plain text (`"PREFER: ...\nAVOID: ..."`) and asserted `rules[0].startswith("PREFER:")` — neither matches the `generate_rules()` API which expects JSON in → returns `List[MemoryRule]` out
- **Fix:** Updated mock to return valid JSON list of rule dicts; assertions updated to check `rules[0].title` and `rules[0].type`
- **Files modified:** `tests/test_self_improvement.py`
- **Verification:** `test_rule_generator_logic` passes
- **Committed in:** `9a214d6`

---

**Total deviations:** 2 auto-fixed (2 bugs in existing code)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

None beyond the two auto-fixed bugs above.

## Next Phase Readiness

- Phase 7 complete: self-improvement loop is end-to-end wired
- `--review` CLI and interactive `review` command both invoke `SelfLearningPipeline`
- Requires live PostgreSQL + Google API key for real `/review` run; all tests mock both
- Phase 8 (Portfolio Risk Governance) and Phase 9 (Structured Memory Registry) tests already passing (included in this commit as they were untracked)

## Self-Check: PASSED

- FOUND: src/agents/review_agent.py
- FOUND: src/agents/rule_generator.py
- FOUND: src/graph/orchestrator.py
- FOUND: .planning/phases/07-self-improvement-loop/07-01-SUMMARY.md
- FOUND: commit 9a214d6

---
*Phase: 07-self-improvement-loop*
*Completed: 2026-03-07*
