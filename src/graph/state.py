import operator
from typing import Annotated, List, TypedDict, Optional, Any

class SwarmState(TypedDict):
    """
    Global state for the Financial Swarm.
    Maintains task context, dialogue history, and analysis outputs.
    """
    # Unique task identifier
    task_id: str

    # Original user input or task description
    user_input: str

    # Classified intent (trade, analysis, macro, risk)
    intent: str

    # Full dialogue history (Annotated with operator.add for state merging)
    messages: Annotated[List[dict], operator.add]

    # Domain Analysis Outputs
    macro_report: Optional[dict]
    quant_proposal: Optional[dict]

    # Adversarial Debate (Phase 2 core)
    bullish_thesis: Optional[dict]
    bearish_thesis: Optional[dict]
    debate_resolution: Optional[dict]

    # Debate Synthesis (Plan 02-03)
    # 0.0 = fully bearish, 1.0 = fully bullish
    weighted_consensus_score: Optional[float]
    # Accumulates all debate messages with provenance (reducer: append)
    debate_history: Annotated[List[dict], operator.add]

    # Safety & Gating
    risk_approval: Optional[dict]
    consensus_score: float
    compliance_flags: List[str]
    # Risk Gating (Plan 02-04)
    risk_approved: Optional[bool]
    risk_notes: Optional[str]

    # Final Decision
    final_decision: Optional[dict]

    # Optional: External context (config, etc. - though usually passed in nodes)
    metadata: dict
