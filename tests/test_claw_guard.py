"""
tests.test_claw_guard — Tests for ClawGuard security rule engine.

Each test verifies one rule: passes when state is compliant, blocks when not.
"""

import pytest
from src.security.claw_guard import ClawGuard, claw_guard_node


CONFIG = {
    "security": {
        "min_consensus": 0.75,
        "paper_trade_only": True,
    }
}

CONFIG_LIVE_ALLOWED = {
    "security": {
        "min_consensus": 0.75,
        "paper_trade_only": False,
    }
}


# --- require_risk_approval ---

def test_require_risk_approval_passes():
    guard = ClawGuard(CONFIG)
    state = {"risk_approved": True, "weighted_consensus_score": 0.8,
             "messages": [], "execution_mode": "paper"}
    approved, violations = guard.check(state)
    assert approved is True
    assert violations == []


def test_require_risk_approval_blocks_when_false():
    guard = ClawGuard(CONFIG)
    state = {"risk_approved": False, "weighted_consensus_score": 0.8,
             "messages": [], "execution_mode": "paper"}
    approved, violations = guard.check(state)
    assert approved is False
    assert any("risk_approved" in v for v in violations)


def test_require_risk_approval_blocks_when_none():
    guard = ClawGuard(CONFIG)
    state = {"risk_approved": None, "weighted_consensus_score": 0.8,
             "messages": [], "execution_mode": "paper"}
    approved, violations = guard.check(state)
    assert approved is False


# --- require_consensus_threshold ---

def test_consensus_threshold_passes_above_min():
    guard = ClawGuard(CONFIG)
    state = {"risk_approved": True, "weighted_consensus_score": 0.8,
             "messages": [], "execution_mode": "paper"}
    approved, violations = guard.check(state)
    assert approved is True


def test_consensus_threshold_blocks_below_min():
    guard = ClawGuard(CONFIG)
    state = {"risk_approved": True, "weighted_consensus_score": 0.5,
             "messages": [], "execution_mode": "paper"}
    approved, violations = guard.check(state)
    assert approved is False
    assert any("consensus" in v for v in violations)


def test_consensus_threshold_blocks_when_none():
    guard = ClawGuard(CONFIG)
    state = {"risk_approved": True, "weighted_consensus_score": None,
             "messages": [], "execution_mode": "paper"}
    approved, violations = guard.check(state)
    assert approved is False


# --- no_credential_in_messages ---

def test_no_credential_passes_clean_messages():
    guard = ClawGuard(CONFIG)
    state = {"risk_approved": True, "weighted_consensus_score": 0.8,
             "messages": [{"role": "user", "content": "buy BTC"}],
             "execution_mode": "paper"}
    approved, violations = guard.check(state)
    assert approved is True


def test_no_credential_blocks_api_key_in_messages():
    guard = ClawGuard(CONFIG)
    state = {"risk_approved": True, "weighted_consensus_score": 0.8,
             "messages": [{"role": "user", "content": "sk-abc123def456ghi789jkl012mno345p"}],
             "execution_mode": "paper"}
    approved, violations = guard.check(state)
    assert approved is False
    assert any("credential" in v for v in violations)


def test_no_credential_blocks_password_pattern():
    guard = ClawGuard(CONFIG)
    state = {"risk_approved": True, "weighted_consensus_score": 0.8,
             "messages": [{"role": "assistant", "content": "password=hunter2"}],
             "execution_mode": "paper"}
    approved, violations = guard.check(state)
    assert approved is False


# --- paper_trade_only ---

def test_paper_trade_only_passes_paper_mode():
    guard = ClawGuard(CONFIG)
    state = {"risk_approved": True, "weighted_consensus_score": 0.8,
             "messages": [], "execution_mode": "paper"}
    approved, violations = guard.check(state)
    assert approved is True


def test_paper_trade_only_blocks_live_mode():
    guard = ClawGuard(CONFIG)
    state = {"risk_approved": True, "weighted_consensus_score": 0.8,
             "messages": [], "execution_mode": "live"}
    approved, violations = guard.check(state)
    assert approved is False
    assert any("live" in v or "paper_trade_only" in v for v in violations)


def test_paper_trade_only_allows_live_when_disabled():
    guard = ClawGuard(CONFIG_LIVE_ALLOWED)
    state = {"risk_approved": True, "weighted_consensus_score": 0.8,
             "messages": [], "execution_mode": "live"}
    approved, violations = guard.check(state)
    assert approved is True


# --- claw_guard_node integration ---

def test_claw_guard_node_sets_compliance_flags_on_block():
    state = {"risk_approved": False, "weighted_consensus_score": 0.8,
             "messages": [], "execution_mode": "paper", "compliance_flags": []}
    result = claw_guard_node(state, config=CONFIG)
    assert result["risk_approved"] is False  # blocked — propagate block signal
    assert len(result["compliance_flags"]) > 0


def test_claw_guard_node_passes_clean_state():
    state = {"risk_approved": True, "weighted_consensus_score": 0.8,
             "messages": [], "execution_mode": "paper", "compliance_flags": []}
    result = claw_guard_node(state, config=CONFIG)
    assert result["risk_approved"] is True
    assert result["compliance_flags"] == []
