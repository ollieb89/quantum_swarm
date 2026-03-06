import logging
from typing import Dict, Any, List, Optional
from src.graph.state import SwarmState

logger = logging.getLogger(__name__)

class InstitutionalGuard:
    """
    Final institutional safety layer that enforces global risk limits and compliance.
    Runs after the domain RiskManager but before the OrderRouter (Execution).
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.risk_limits = config.get("risk_limits", {})
        
        # Institutional-specific limits (can be expanded in config/swarm_config.yaml)
        self.max_leverage = self.risk_limits.get("max_leverage", 10.0)
        self.restricted_assets = self.risk_limits.get("restricted_assets", [])
        self.hard_equity_stop = self.risk_limits.get("hard_equity_stop", None) # portfolio-wide kill switch

    def check_compliance(self, state: SwarmState) -> Dict[str, Any]:
        """
        Performs non-negotiable institutional compliance checks.
        Returns a dictionary with 'approved' status and any 'violation' notes.
        """
        task_id = state.get("task_id", "unknown")
        proposal = state.get("quant_proposal", {})
        symbol = proposal.get("symbol", "unknown")
        
        # 1. Restricted Asset Check
        if symbol in self.restricted_assets:
            logger.warning("Institutional violation: %s is on the restricted list.", symbol)
            return {
                "approved": False,
                "violation": f"Asset {symbol} is restricted for institutional compliance."
            }
            
        # 2. Position/Leverage Check
        # Extract proposed leverage from the quant/risk reports if available
        # Defaulting to 1.0 if not explicitly requested
        requested_leverage = proposal.get("leverage", 1.0)
        if requested_leverage > self.max_leverage:
            logger.warning("Institutional violation: Requested leverage %.2f exceeds limit %.2f.", requested_leverage, self.max_leverage)
            return {
                "approved": False,
                "violation": f"Requested leverage {requested_leverage} exceeds institutional limit {self.max_leverage}."
            }
            
        # 3. Hard Equity Stop (Placeholder for real-time portfolio value check)
        # In a real system, this would fetch current account balances via OrderRouter or a dedicated service.
        # For Phase 4, we use a placeholder or assume equity is sufficient unless explicitly reported otherwise.
        if self.hard_equity_stop:
            # mock equity check logic
            current_equity = 1000000.0 # This would be live data
            if current_equity < self.hard_equity_stop:
                logger.critical("Institutional violation: Total equity below hard stop threshold!")
                return {
                    "approved": False,
                    "violation": "Kill-switch activated: Total portfolio equity below hard stop threshold."
                }
                
        return {"approved": True, "violation": None}

def institutional_guard_node(state: SwarmState, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for the InstitutionalGuard.
    """
    guard = InstitutionalGuard(config)
    result = guard.check_compliance(state)
    
    compliance_flags = list(state.get("compliance_flags", []))
    if not result["approved"]:
        compliance_flags.append(f"INSTITUTIONAL_VIOLATION: {result['violation']}")
        # We override risk_approved to False if institutional guard blocks it
        return {
            "risk_approved": False,
            "risk_notes": (state.get("risk_notes") or "") + f" | Institutional Guard Block: {result['violation']}",
            "compliance_flags": compliance_flags
        }
    
    compliance_flags.append("INSTITUTIONAL_APPROVED")
    return {
        "compliance_flags": compliance_flags
    }
