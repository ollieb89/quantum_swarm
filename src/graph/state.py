import operator
from typing import Annotated, Dict, List, Literal, TypedDict, Optional, Any

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

    # Phase 1: Blackboard session ID (maps to data/inter_agent_comms/{session_id}/)
    blackboard_session: Optional[str]

    # Phase 1: Cumulative token usage tracked by BudgetManager
    total_tokens: Annotated[int, operator.add]

    # Phase 3: L3 Executor state fields
    # trade_history: Annotated reducer (operator.add) — always appends, trim at read time
    # Sliding window N=15 enforced in L2 agents: state["trade_history"][-15:]
    trade_history: Annotated[List[dict], operator.add]
    execution_mode: str                        # "paper" | "live"
    data_fetcher_result: Optional[dict]        # MarketData + SentimentData + EconomicData dicts
    knowledge_base_result: Optional[dict]      # Local KB context (sentiment_context + historical_stats)
    backtest_result: Optional[dict]            # NautilusTrader metrics dict
    execution_result: Optional[dict]           # OrderRouter fill dict

    # Phase 11: Decision Card (Explainability)
    decision_card_status: Optional[Literal["pending", "written", "failed"]]
    decision_card_error: Optional[str]
    decision_card_audit_ref: Optional[str]     # card_id on success

    # Phase 15: MBS Persona System — soul identity fields
    # IMPORTANT: These fields must NEVER enter state["messages"] (operator.add reducer
    # would cause unbounded accumulation and corrupt MiFID II audit trail).
    # They are excluded from AuditLogger hash input via AUDIT_EXCLUDED_FIELDS.
    system_prompt: Optional[str]    # Full soul content (IDENTITY + SOUL + AGENTS concatenated)
    active_persona: Optional[str]   # Agent handle from first H1 of IDENTITY.md (e.g. 'AXIOM')

    # Phase 16: KAMI Merit Index — earned dynamic merit scores keyed by soul handle.
    # Plain dict field (NO operator.add reducer) — merit_loader sets at session start,
    # merit_updater overwrites per cycle. Included in MiFID II audit hash (NOT excluded).
    # Canonicalize values with round(score, 4) before writing to prevent float jitter.
    merit_scores: Optional[Dict[str, Any]]

    # Phase 18: Theory of Mind Soul-Sync — peer soul summaries for ARS downstream.
    # Plain dict field (NO operator.add reducer) — written once by soul_sync_handshake_node.
    # Excluded from AuditLogger hash chain via AUDIT_EXCLUDED_FIELDS (pre-declared Phase 17).
    soul_sync_context: Optional[Dict[str, str]]
