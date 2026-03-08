# Phase 17 — Soul Infrastructure Hardening: Required Regression Tests

**Created:** 2026-03-08
**Context:** Identified after Phase 15 (Soul Foundation) completion.

These tests must exist and pass before Phase 17 is considered complete. They guard
against the failure modes most likely to appear once souls gain derived helpers,
richer injection paths, and tighter audit coupling.

---

## Must-Ship Regression Pack (8 tests)

| # | Test name | Guards against |
|---|-----------|----------------|
| 1 | `test_summary_updates_after_soul_file_change` | Derived cache (e.g. `get_soul_summary()`) serving stale content after raw soul file changes |
| 2 | `test_repeated_calls_are_order_independent` | Cache interaction between raw and derived helpers producing different results depending on call order |
| 3 | `test_decision_card_hash_is_deterministic` | Same inputs + same soul producing different audit hashes across runs |
| 4 | `test_excluded_runtime_fields_do_not_change_hash` | Runtime-only fields (timestamps, cache hits) leaking into SHA-256 audit chain |
| 5 | `test_verify_decision_card_does_not_mutate_input` | Verifier silently modifying the card dict it is checking (breaks audit replay) |
| 6 | `test_unknown_soul_id_raises` | Silent fallback to a generic or empty soul when an unregistered ID is requested |
| 7 | `test_bullish_researcher_receives_bullish_soul` | Agent construction injecting the wrong soul due to a registry mismatch |
| 8 | `test_skeleton_soul_blocked_in_production` | Placeholder skeleton personas (MOMENTUM/CASSANDRA/SIGMA/GUARDIAN) being used for live inference before they are fully authored |

---

## Suggested Test Module Layout

```
tests/core/
  test_soul_cache.py        # Tests 1, 2 — cache desync and ordering
  test_soul_validation.py   # Tests 6, 7, 8 — unknown IDs, registry parity, skeleton gate
  test_soul_audit.py        # Tests 3, 4, 5 — audit hash determinism and verifier purity
```

---

## Phase 17 Readiness Gate

Phase 17 is safe to mark complete only when all of the following are true:

- [ ] No cache-related order dependence (tests 1, 2 pass)
- [ ] No audit hash drift across reruns (tests 3, 4, 5 pass)
- [ ] No silent persona fallback (test 6, 7 pass)
- [ ] No placeholder soul in production paths (test 8 pass)
- [ ] Startup fails fast if any required soul is missing

---

## Additional Checklists (consult during Phase 17 planning)

### Cache desync
- Every cached soul helper has an explicit invalidation strategy
- `conftest.py` clears all cached helpers introduced in this phase
- Warmup covers the same helper set that production depends on

### Audit determinism
- Same input + same soul → same decision-card hash
- `AUDIT_EXCLUDED_FIELDS` updated if new runtime-only soul fields are introduced
- Verifier recomputes and compares — never mutates

### Persona bleed-through
- Unknown soul IDs raise `SoulNotFoundError` (typed — in place since Phase 15 cleanup)
- `AGENT_SOUL_MAP` (when introduced) must match `ALL_REQUIRED_SOULS` / `_KNOWN_AGENTS`
- Skeleton souls blocked from production unless override flag is set

### Orchestrator injection
- Warmup registry matches injection registry
- `bootstrap_orchestrator()` fails fast if any required soul is missing
- No agent class bypasses `load_soul()` with a direct path join

---

## Exception Types (in place since Phase 15 cleanup commit)

```python
from src.core.soul_errors import (
    SoulError,           # base
    SoulNotFoundError,   # missing soul directory
    SoulValidationError, # schema / content failure
    SoulSecurityError,   # path traversal
)
```

Use these in Phase 17 tests — do not assert on `ValueError` or `FileNotFoundError`.
