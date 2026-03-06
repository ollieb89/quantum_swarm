import pytest
from src.security.institutional_guard import InstitutionalGuard, institutional_guard_node

def test_institutional_guard_restricted_asset():
    config = {
        "risk_limits": {
            "restricted_assets": ["XRP/USDT", "DOGE/USDT"]
        }
    }
    guard = InstitutionalGuard(config)
    
    # Test restricted asset
    state = {"quant_proposal": {"symbol": "XRP/USDT"}}
    result = guard.check_compliance(state)
    assert result["approved"] is False
    assert "restricted" in result["violation"]
    
    # Test allowed asset
    state = {"quant_proposal": {"symbol": "BTC/USDT"}}
    result = guard.check_compliance(state)
    assert result["approved"] is True

def test_institutional_guard_leverage():
    config = {
        "risk_limits": {
            "max_leverage": 5.0
        }
    }
    guard = InstitutionalGuard(config)
    
    # Test leverage breach
    state = {"quant_proposal": {"symbol": "BTC/USDT", "leverage": 10.0}}
    result = guard.check_compliance(state)
    assert result["approved"] is False
    assert "leverage" in result["violation"]
    
    # Test acceptable leverage
    state = {"quant_proposal": {"symbol": "BTC/USDT", "leverage": 3.0}}
    result = guard.check_compliance(state)
    assert result["approved"] is True

def test_institutional_guard_node_logic():
    config = {
        "risk_limits": {
            "restricted_assets": ["BAD/USDT"]
        }
    }
    
    # Test violation updates state correctly
    state = {
        "quant_proposal": {"symbol": "BAD/USDT"},
        "compliance_flags": ["PRE_EXISTING"],
        "risk_notes": "All good so far"
    }
    
    update = institutional_guard_node(state, config)
    
    assert update["risk_approved"] is False
    assert "INSTITUTIONAL_VIOLATION" in update["compliance_flags"][1]
    assert "Institutional Guard Block" in update["risk_notes"]
    
    # Test approval updates state correctly
    state = {
        "quant_proposal": {"symbol": "GOOD/USDT"},
        "compliance_flags": []
    }
    update = institutional_guard_node(state, config)
    assert "INSTITUTIONAL_APPROVED" in update["compliance_flags"]
    assert "risk_approved" not in update # Should not override if approved
