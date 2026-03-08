"""
tests/test_mem06_gate_order.py — MEM-06 Gate Order Integration Tests.

Asserts that persist_rules() stores rules as 'proposed' and that
validate_proposed_rules() is the sole authority for promoting or rejecting rules.

MEM-06 correct gate order:
  1. persist_rules() calls registry.add_rule(rule)  → status = "proposed"
  2. persist_rules() calls validator.validate_proposed_rules()
  3. Validator runs 2-of-3 backtest harness on PROPOSED rules
  4. Validator calls update_status(rule.id, "active" | "rejected")

Bug in Phase 12 (MC-01 fix): persist_rules() called update_status("active")
BEFORE the validator, so by the time the validator ran, get_proposed_rules()
returned [] — the validator was a no-op, all rules were immediately active.

These 5 tests describe the CORRECT gate order and FAIL RED against the Phase 12
broken code. Plan 02 removes the premature update_status("active") call.

Run: .venv/bin/python3.12 -m pytest tests/test_mem06_gate_order.py -v
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.memory_registry import MemoryRegistry
from src.models.memory import MemoryRule
from src.agents.rule_generator import RuleGenerator
from src.agents.rule_validator import RuleValidator


# ---------------------------------------------------------------------------
# Shared mock backtest result constants
# ---------------------------------------------------------------------------

_BASELINE = {
    "sharpe_ratio": 1.0,
    "max_drawdown": -0.10,
    "win_rate": 0.50,
    "total_trades": 15,
}

_PASS = {
    "sharpe_ratio": 1.5,
    "max_drawdown": -0.05,
    "win_rate": 0.60,
    "total_trades": 15,
}

_FAIL = {
    "sharpe_ratio": 0.8,
    "max_drawdown": -0.15,
    "win_rate": 0.42,
    "total_trades": 15,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def isolated_rg(tmp_path) -> RuleGenerator:
    """
    Return a RuleGenerator with registry and memory_md_path redirected to tmp_path.
    Prevents any writes to the live data/ directory during tests.
    """
    rg = RuleGenerator()
    rg.registry = MemoryRegistry(str(tmp_path / "reg.json"))
    rg.memory_md_path = tmp_path / "MEMORY.md"
    return rg


@pytest.fixture()
def sample_rule() -> MemoryRule:
    """Return a minimal valid MemoryRule with status='proposed' (the default)."""
    return MemoryRule(
        title="AVOID: trading during high-VIX regimes",
        type="risk_adjustment",
        condition={"vix": ">30"},
        action={"reduce_position_size": 0.5},
        evidence={},
        status="proposed",
    )


def _patch_validator_audit(rg: RuleGenerator, audit_path: Path):
    """
    Return a context-manager that redirects RuleValidator.audit_path to audit_path.

    Uses the same patch.object(__init__) pattern as test_rule_validator.py
    TestRuleValidatorIntegration, so any RuleValidator instantiated inside
    rg.persist_rules() writes audit events to our tmp audit file.
    """
    original_init = RuleValidator.__init__

    def patched_init(self_v, **kwargs):
        original_init(self_v, **kwargs)
        self_v.audit_path = audit_path

    return patch.object(RuleValidator, "__init__", patched_init)


# ---------------------------------------------------------------------------
# Test 1: rule is stored as 'proposed' while the validator's backtests run
# ---------------------------------------------------------------------------


def test_rule_is_proposed_when_validator_backtests_run(isolated_rg, sample_rule, tmp_path):
    """
    MEM-06 RED: When validate_proposed_rules() fires its backtest calls, the rule
    must still be in 'proposed' state in the registry.

    CURRENT BROKEN PATH (Phase 12):
      persist_rules() calls update_status("active") immediately after add_rule().
      By the time the validator calls _run_nautilus_backtest(), get_proposed_rules()
      returns [] — so this recording mock observes zero proposed rules.

    EXPECTED CORRECT PATH (MEM-06):
      persist_rules() calls add_rule() only (leaves status="proposed").
      The validator's backtest loop iterates over the proposed rule — so
      get_proposed_rules() returns 1 rule when the backtest mock is called.
    """
    rg = isolated_rg
    audit_path = tmp_path / "audit.jsonl"

    observed_proposed: list[MemoryRule] = []

    def recording_backtest(instrument, metadata):
        # Called by validate_proposed_rules() — at this point the rule must still
        # be in 'proposed' state (not yet decided by the validator).
        observed_proposed.extend(rg.registry.get_proposed_rules())
        if not metadata:  # baseline call (empty metadata dict = baseline)
            return _BASELINE
        return _PASS

    with _patch_validator_audit(rg, audit_path):
        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=recording_backtest,
        ):
            rg.persist_rules([sample_rule])

    assert len(observed_proposed) > 0, (
        "MEM-06 RED: When validate_proposed_rules() runs its backtests, "
        "the rule must still be in 'proposed' state (observed_proposed must be non-empty). "
        "Currently persist_rules() calls update_status('active') BEFORE the validator, "
        "so by the time backtests run, get_proposed_rules() returns [] and "
        "observed_proposed is always empty."
    )


# ---------------------------------------------------------------------------
# Test 2: passing backtest → rule ends up 'active' via validator (not direct promotion)
# ---------------------------------------------------------------------------


def test_passing_backtest_promotes_to_active_via_validator(isolated_rg, sample_rule, tmp_path):
    """
    MEM-06 RED: A rule that passes the 2-of-3 backtest harness must be promoted to
    'active' by the VALIDATOR, not by an immediate update_status("active") call inside
    persist_rules().

    The outcome (rule is active) may look correct with the Phase 12 code, but the
    path is wrong: the validator never processed it. This test catches that by
    verifying the validator actually ran (Test 4) and that the outcome is 'active'.

    With the CORRECT gate order, the validator runs the backtests, sees improvement
    in all 3 metrics, and calls update_status(rule.id, "active").
    """
    rg = isolated_rg
    audit_path = tmp_path / "audit.jsonl"

    with _patch_validator_audit(rg, audit_path):
        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=[_BASELINE, _PASS],
        ):
            rg.persist_rules([sample_rule])

    updated = rg.registry.get_rule(sample_rule.id)
    assert updated is not None, "Rule must exist in registry after persist_rules()"
    assert updated.status == "active", (
        f"MEM-06: A rule passing the 2-of-3 harness must end up 'active'. "
        f"Got status='{updated.status}'. "
        "Validator is the sole promoter — rule status after persist_rules() + passing "
        "backtests must be 'active'."
    )


# ---------------------------------------------------------------------------
# Test 3: failing backtest → rule ends up 'rejected', never reaches 'active'
# ---------------------------------------------------------------------------


def test_failing_backtest_rejects_rule_and_never_promotes(isolated_rg, sample_rule, tmp_path):
    """
    MEM-06 RED: A rule that fails the 2-of-3 backtest harness must end up 'rejected'
    and must NEVER reach 'active'.

    CURRENT BROKEN PATH (Phase 12):
      persist_rules() calls update_status("active") immediately, then calls the validator.
      The validator's get_proposed_rules() returns [] (the rule is already 'active').
      The rule stays 'active' even when all backtest metrics are worse — a failing rule
      is never rejected because 'active -> rejected' is not a valid transition from this
      broken path (MemoryRegistry.VALID_TRANSITIONS does not include active → rejected
      via the validator's update_status call on an already-active rule).

    EXPECTED CORRECT PATH (MEM-06):
      add_rule() → status = "proposed"
      validator processes the proposed rule → treatment worse than baseline → rejected
      update_status(rule.id, "rejected") → status = "rejected"
    """
    rg = isolated_rg
    audit_path = tmp_path / "audit.jsonl"

    with _patch_validator_audit(rg, audit_path):
        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=[_BASELINE, _FAIL],
        ):
            rg.persist_rules([sample_rule])

    updated = rg.registry.get_rule(sample_rule.id)
    assert updated is not None, "Rule must exist in registry after persist_rules()"
    assert updated.status == "rejected", (
        f"MEM-06 RED: A rule failing the 2-of-3 harness must end up 'rejected'. "
        f"Got status='{updated.status}'. "
        "Currently Phase 12 promotes to 'active' before the validator runs, "
        "so a failing backtest cannot demote it — 'active -> rejected' is blocked "
        "by VALID_TRANSITIONS when the rule is already active."
    )


# ---------------------------------------------------------------------------
# Test 4: validator sees a non-empty proposed list (processes ≥ 1 rule)
# ---------------------------------------------------------------------------


def test_validator_processes_at_least_one_proposed_rule(isolated_rg, sample_rule, tmp_path):
    """
    MEM-06 RED: validate_proposed_rules() must be called with a non-empty proposed
    list and must return a processed count > 0.

    CURRENT BROKEN PATH (Phase 12):
      update_status("active") fires before the validator.
      validate_proposed_rules() calls get_proposed_rules() → returns [] → processed=0.

    EXPECTED CORRECT PATH (MEM-06):
      add_rule() leaves the rule as 'proposed'.
      validate_proposed_rules() calls get_proposed_rules() → returns [rule] → processed=1.
    """
    rg = isolated_rg
    audit_path = tmp_path / "audit.jsonl"

    original_validate = RuleValidator.validate_proposed_rules
    observed_counts: list[int] = []

    def recording_validate(self_v) -> int:
        count = original_validate(self_v)
        observed_counts.append(count)
        return count

    with _patch_validator_audit(rg, audit_path):
        with patch.object(RuleValidator, "validate_proposed_rules", recording_validate):
            with patch(
                "src.agents.rule_validator._run_nautilus_backtest",
                side_effect=[_BASELINE, _PASS],
            ):
                rg.persist_rules([sample_rule])

    assert len(observed_counts) > 0, (
        "MEM-06 RED: validate_proposed_rules() must have been called from persist_rules(). "
        "It was not recorded — check that persist_rules() actually calls the validator."
    )
    assert observed_counts[0] > 0, (
        f"MEM-06 RED: validate_proposed_rules() must process at least 1 rule. "
        f"Got processed={observed_counts[0]!r}. "
        "Currently persist_rules() promotes the rule to 'active' before calling the validator, "
        "so the validator finds [] proposed rules and returns 0."
    )


# ---------------------------------------------------------------------------
# Test 5: audit.jsonl receives one event line per processed rule
# ---------------------------------------------------------------------------


def test_audit_event_written_per_processed_rule(isolated_rg, sample_rule, tmp_path):
    """
    MEM-06 RED: One audit event must be written to audit.jsonl for each rule that
    the validator processes (promotes or rejects).

    CURRENT BROKEN PATH (Phase 12):
      The validator finds [] proposed rules → processes 0 rules → writes 0 audit events.
      audit.jsonl is empty after persist_rules().

    EXPECTED CORRECT PATH (MEM-06):
      The validator finds [rule] → runs backtests → writes 1 audit event line.
      The event has fields: timestamp, event, rule_id, before_status, after_status,
      plus 6 metric values and 3 deltas.
    """
    rg = isolated_rg
    audit_path = tmp_path / "audit.jsonl"

    with _patch_validator_audit(rg, audit_path):
        with patch(
            "src.agents.rule_validator._run_nautilus_backtest",
            side_effect=[_BASELINE, _PASS],
        ):
            rg.persist_rules([sample_rule])

    assert audit_path.exists(), (
        "MEM-06 RED: audit.jsonl must exist after persist_rules() runs the validator. "
        "Currently no audit events are written because the validator finds [] proposed rules."
    )

    lines = [ln.strip() for ln in audit_path.read_text().splitlines() if ln.strip()]
    assert len(lines) >= 1, (
        f"MEM-06 RED: audit.jsonl must contain at least 1 event line. "
        f"Found {len(lines)} line(s). "
        "Currently the validator finds [] proposed rules and writes no audit events "
        "because persist_rules() pre-promotes rules before the validator can see them."
    )

    event = json.loads(lines[0])
    assert event.get("event") == "rule_validation", (
        f"MEM-06: audit event 'event' field must be 'rule_validation'. "
        f"Got: {event.get('event')!r}"
    )
    assert event.get("rule_id") == sample_rule.id, (
        f"MEM-06: audit event must record the correct rule_id. "
        f"Expected '{sample_rule.id}', got '{event.get('rule_id')}'."
    )
    assert event.get("before_status") == "proposed", (
        f"MEM-06: audit before_status must be 'proposed'. "
        f"Got: {event.get('before_status')!r}. "
        "If before_status is not 'proposed', the rule was promoted before the validator ran."
    )
