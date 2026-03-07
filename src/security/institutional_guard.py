import logging
import json
from typing import Dict, Any, List, Optional
from src.graph.state import SwarmState
from src.core.db import get_pool

logger = logging.getLogger(__name__)

class InstitutionalGuard:
    """
    Final institutional safety layer that enforces global risk limits and compliance.
    Runs after the domain RiskManager but before the OrderRouter (Execution).
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.risk_limits = config.get("risk_limits", {})
        
        # Institutional-specific limits
        self.max_leverage = self.risk_limits.get("max_leverage", 10.0)
        self.restricted_assets = self.risk_limits.get("restricted_assets", [])
        self.hard_equity_stop = self.risk_limits.get("hard_equity_stop", None)
        
        # Portfolio-level limits (Phase 8)
        self.starting_capital = self.risk_limits.get("starting_capital", 1000000.0)
        self.max_notional_exposure = self.risk_limits.get("max_notional_exposure", 500000.0)
        self.max_concentration = self.risk_limits.get("max_asset_concentration_pct", 0.20)
        self.max_concurrent = self.risk_limits.get("max_concurrent_trades", 10)

    async def _get_open_positions(self) -> List[Dict[str, Any]]:
        """Fetch all open positions from PostgreSQL."""
        pool = get_pool()
        open_trades = []
        query = "SELECT symbol, position_size, entry_price FROM trades WHERE exit_time IS NULL;"
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query)
                    rows = await cur.fetchall()
                    for row in rows:
                        open_trades.append({
                            "symbol": row[0],
                            "quantity": float(row[1]),   # position_size from DB, called "quantity" internally
                            "price": float(row[2])       # entry_price from DB, called "price" internally
                        })
        except Exception as e:
            logger.error("Failed to fetch open positions: %s", e)
        return open_trades

    def calculate_risk_score(self, proposal: Dict[str, Any], current_heat: float) -> float:
        """
        Compute a normalized pre-trade risk score (0.0 to 1.0).
        0.0 = Safest, 1.0 = Highest Risk.
        """
        entry = proposal.get("entry_price")
        stop = proposal.get("stop_loss")
        confidence = proposal.get("confidence", 0.5)
        
        if not entry or not stop:
            return 1.0 # Maximum risk if protection missing
            
        # 1. Stop distance impact (normalized to 10% move)
        stop_dist_pct = abs(entry - stop) / entry
        dist_score = min(stop_dist_pct / 0.1, 1.0)
        
        # 2. Confidence inversion (low confidence = higher risk)
        conf_score = 1.0 - confidence
        
        # 3. Portfolio heat impact
        heat_score = current_heat # already 0.0 to 1.0
        
        # Weighted average
        total_score = (dist_score * 0.4) + (conf_score * 0.3) + (heat_score * 0.3)
        return round(min(total_score, 1.0), 4)

    async def check_compliance(self, state: SwarmState) -> Dict[str, Any]:
        """
        Performs non-negotiable institutional compliance checks including portfolio limits.
        """
        proposal = state.get("quant_proposal", {})
        symbol = proposal.get("symbol", "unknown")
        entry_price = float(proposal.get("entry_price", 0.0))
        quantity = float(proposal.get("quantity", 0.0))
        new_notional = entry_price * quantity
        
        # 1. Restricted Asset Check
        if symbol in self.restricted_assets:
            return {"approved": False, "violation": f"Asset {symbol} is restricted."}
            
        # 2. Portfolio-level checks
        open_positions = await self._get_open_positions()
        
        # Count check
        if len(open_positions) >= self.max_concurrent:
            return {"approved": False, "violation": f"Max concurrent trades ({self.max_concurrent}) reached."}
            
        # Total Exposure check
        current_total_notional = sum(p["quantity"] * p["price"] for p in open_positions)
        if (current_total_notional + new_notional) > self.max_notional_exposure:
            return {
                "approved": False, 
                "violation": f"Order exceeds max notional exposure. Current: {current_total_notional:.2f}, New: {new_notional:.2f}, Max: {self.max_notional_exposure:.2f}"
            }
            
        # Asset Concentration check
        asset_notional = sum(p["quantity"] * p["price"] for p in open_positions if p["symbol"] == symbol)
        if (asset_notional + new_notional) / self.starting_capital > self.max_concentration:
            return {
                "approved": False, 
                "violation": f"Concentration limit for {symbol} exceeded ({self.max_concentration*100}%)."
            }

        # 3. Risk Scoring
        current_heat = current_total_notional / self.max_notional_exposure
        risk_score = self.calculate_risk_score(proposal, current_heat)
        
        return {
            "approved": True, 
            "violation": None,
            "risk_score": risk_score,
            "portfolio_heat": current_heat
        }

async def institutional_guard_node(state: SwarmState, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for the InstitutionalGuard.
    """
    guard = InstitutionalGuard(config)
    result = await guard.check_compliance(state)
    
    compliance_flags = list(state.get("compliance_flags", []))
    if not result["approved"]:
        compliance_flags.append(f"INSTITUTIONAL_VIOLATION: {result['violation']}")
        return {
            "risk_approved": False,
            "risk_notes": (state.get("risk_notes") or "") + f" | Institutional Guard Block: {result['violation']}",
            "compliance_flags": compliance_flags
        }
    
    compliance_flags.append("INSTITUTIONAL_APPROVED")
    return {
        "compliance_flags": compliance_flags,
        "metadata": {
            **state.get("metadata", {}),
            "trade_risk_score": result.get("risk_score"),
            "portfolio_heat": result.get("portfolio_heat")
        }
    }
