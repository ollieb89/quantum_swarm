"""
Level 1 Strategic Orchestrator

The central cognitive engine of the Financial Swarm.
Handles intent classification, task decomposition, and conflict resolution.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..core.cli_wrapper import OpenClawCLI, FileProtocol, AgentResponse

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Known intent types"""
    TRADE = "trade"
    ANALYSIS = "analysis"
    MACRO = "macro"
    RISK = "risk"
    UNKNOWN = "unknown"


class AgentSignal(Enum):
    """Trading signals from agents"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class AgentProposal:
    """Proposal from an L2 agent"""
    agent_id: str
    signal: AgentSignal
    confidence: float
    rationale: str
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "signal": self.signal.value,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "metadata": self.metadata
        }


@dataclass
class OrchestratorDecision:
    """Final decision from L1 Orchestrator"""
    task_id: str
    decision: str  # EXECUTE, HOLD, REJECT
    consensus_score: float
    rationale: str
    proposals: List[AgentProposal] = field(default_factory=list)
    risk_override: bool = False

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "decision": self.decision,
            "consensus_score": self.consensus_score,
            "rationale": self.rationale,
            "proposals": [p.to_dict() for p in self.proposals],
            "risk_override": self.risk_override
        }


class StrategicOrchestrator:
    """
    Level 1 Strategic Orchestrator

    Responsibilities:
    - Intent classification from user input
    - Task decomposition into subtasks
    - Delegation to L2 agents
    - Result aggregation and consensus
    - Conflict resolution
    - Risk enforcement
    """

    def __init__(
        self,
        cli: OpenClawCLI,
        protocol: FileProtocol,
        config: Dict
    ):
        self.cli = cli
        self.protocol = protocol
        self.config = config

        # Load thresholds
        thresholds = config.get("orchestrator", {}).get("thresholds", {})
        self.min_consensus = thresholds.get("min_consensus", 0.75)
        self.hard_risk_limit = thresholds.get("hard_risk_limit", 0.8)
        self.min_sample_size = thresholds.get("min_sample_size", 5)

        # Agent weights (from reliability profile)
        self.agent_weights = {
            "l2-macro-analyst": 0.4,
            "l2-quant-modeler": 0.6,
            "l2-risk-manager": 0.0  # Risk has veto power, not weighted
        }

    def process_intent(self, user_input: str) -> IntentType:
        """
        Classify user intent using pattern matching.

        This can be enhanced with actual NLP/LLM classification.
        """
        intent_patterns = self.config.get("orchestrator", {}).get(
            "intent_patterns", {}
        )

        user_lower = user_input.lower()

        for intent_name, patterns in intent_patterns.items():
            for pattern in patterns:
                if pattern in user_lower:
                    logger.info(f"Classified intent: {intent_name}")
                    return IntentType(intent_name)

        return IntentType.UNKNOWN

    def decompose_task(
        self,
        user_input: str,
        intent: IntentType
    ) -> Dict[str, Any]:
        """
        Decompose user input into actionable task.

        Returns task structure with target agents and objectives.
        """
        task_id = str(uuid.uuid4())[:8]

        task = {
            "task_id": task_id,
            "original_input": user_input,
            "intent": intent.value,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "subtasks": []
        }

        # Route to appropriate L2 agents based on intent
        routing = self.config.get("agents", {})

        if intent == IntentType.TRADE:
            task["subtasks"] = [
                {
                    "agent": "l2-macro-analyst",
                    "objective": "Analyze current macro environment and market sentiment"
                },
                {
                    "agent": "l2-quant-modeler",
                    "objective": "Generate trade proposal with technical analysis"
                },
                {
                    "agent": "l2-risk-manager",
                    "objective": "Validate proposal against risk limits"
                }
            ]
        elif intent == IntentType.MACRO:
            task["subtasks"] = [
                {
                    "agent": "l2-macro-analyst",
                    "objective": "Comprehensive macro environment analysis"
                }
            ]
        elif intent == IntentType.ANALYSIS:
            task["subtasks"] = [
                {
                    "agent": "l2-macro-analyst",
                    "objective": "Macro analysis"
                },
                {
                    "agent": "l2-quant-modeler",
                    "objective": "Technical analysis"
                }
            ]
        else:
            # Default: full analysis
            task["subtasks"] = [
                {
                    "agent": "l2-macro-analyst",
                    "objective": "General market analysis"
                }
            ]

        logger.info(f"Decomposed task {task_id} into {len(task['subtasks'])} subtasks")
        return task

    async def delegate_to_l2(
        self,
        task: Dict[str, Any],
        memory_context: str = ""
    ) -> List[AgentProposal]:
        """
        Delegate subtasks to L2 agents and collect proposals.
        """
        proposals = []

        # Read memory for context
        memory_context = self._load_memory()

        # Delegate each subtask
        for subtask in task["subtasks"]:
            agent_id = subtask["agent"]
            objective = subtask["objective"]

            # Build prompt with memory context
            prompt = self._build_l2_prompt(
                agent_id=agent_id,
                objective=objective,
                task_context=task["original_input"],
                memory=memory_context
            )

            # Execute agent
            logger.info(f"Delegating to {agent_id}: {objective}")

            response = self.cli.run_agent(
                message=prompt,
                agent_id=agent_id,
                thinking="medium"
            )

            if response.success:
                proposal = self._parse_agent_response(agent_id, response.data)
                if proposal:
                    proposals.append(proposal)
                    logger.info(
                        f"Received proposal from {agent_id}: "
                        f"signal={proposal.signal.value}, "
                        f"confidence={proposal.confidence}"
                    )
            else:
                logger.error(f"Agent {agent_id} failed: {response.error}")

        return proposals

    def resolve_conflicts(self, proposals: List[AgentProposal]) -> OrchestratorDecision:
        """
        Resolve conflicts between agent proposals.

        Applies:
        1. Hard risk constraint (veto power)
        2. Weighted consensus calculation
        3. Threshold validation
        """
        task_id = proposals[0].metadata.get("task_id", "unknown") if proposals else "unknown"

        # Check for risk override (highest priority)
        risk_proposal = next(
            (p for p in proposals if p.agent_id == "l2-risk-manager"),
            None
        )

        if risk_proposal:
            # Risk manager has detected high risk
            if risk_proposal.confidence > self.hard_risk_limit:
                return OrchestratorDecision(
                    task_id=task_id,
                    decision="REJECT",
                    consensus_score=0.0,
                    rationale=f"Hard risk constraint triggered. Risk score: {risk_proposal.confidence}",
                    proposals=proposals,
                    risk_override=True
                )

        # Calculate weighted consensus
        weighted_score = 0.0
        total_weight = 0.0

        for proposal in proposals:
            if proposal.agent_id == "l2-risk-manager":
                continue  # Skip risk in weighted average

            weight = self.agent_weights.get(proposal.agent_id, 0.5)
            weighted_score += proposal.confidence * weight
            total_weight += weight

        if total_weight > 0:
            consensus_score = weighted_score / total_weight
        else:
            consensus_score = 0.0

        # Apply decision logic
        if consensus_score >= self.min_consensus:
            decision = "EXECUTE"
            rationale = f"Consensus threshold met ({consensus_score:.2f} >= {self.min_consensus})"
        else:
            decision = "HOLD"
            rationale = f"Insufficient consensus ({consensus_score:.2f} < {self.min_consensus})"

        return OrchestratorDecision(
            task_id=task_id,
            decision=decision,
            consensus_score=consensus_score,
            rationale=rationale,
            proposals=proposals
        )

    def execute_decision(
        self,
        decision: OrchestratorDecision,
        memory_ref: str = ""
    ) -> Dict[str, Any]:
        """
        Execute the orchestrator's decision.
        """
        result = {
            "task_id": decision.task_id,
            "decision": decision.decision,
            "consensus_score": decision.consensus_score,
            "rationale": decision.rationale,
            "executed_at": datetime.utcnow().isoformat() + "Z"
        }

        # Create result file
        self.protocol.create_result(decision.task_id, result)

        # Send notification if critical
        if decision.decision == "REJECT" or decision.risk_override:
            self._send_alert(
                f"Trade {decision.decision}: {decision.rationale}",
                channel="telegram"
            )

        logger.info(f"Executed decision: {decision.decision} for task {decision.task_id}")
        return result

    def _build_l2_prompt(
        self,
        agent_id: str,
        objective: str,
        task_context: str,
        memory: str
    ) -> str:
        """Build prompt for L2 agent"""
        base_prompt = f"""
Task: {objective}
Context: {task_context}

"""

        if memory:
            base_prompt += f"""
Relevant Historical Patterns (from MEMORY.md):
{memory}

"""

        # Add agent-specific instructions
        agent_config = self.config.get("agents", {}).get(agent_id, {})

        if "macro" in agent_id:
            base_prompt += """
You are the Macro Analyst. Analyze:
1. Global market conditions (VIX, yields)
2. Economic indicators
3. Market sentiment (Risk-On/Risk-Off)

Output format:
{{
  "signal": "bullish/bearish/neutral",
  "confidence": 0.0-1.0,
  "rationale": "your analysis",
  "metadata": {{"vix": X, "sentiment": "..."}}
}}
"""
        elif "quant" in agent_id:
            base_prompt += """
You are the Quant Modeler. Analyze:
1. Technical indicators (RSI, MACD, Moving Averages)
2. Price patterns
3. Entry/exit signals

Output format:
{{
  "signal": "strong_buy/buy/neutral/sell/strong_sell",
  "confidence": 0.0-1.0,
  "rationale": "your analysis",
  "metadata": {{"rsi": X, "trend": "..."}}
}}

IMPORTANT: Never suggest a trade without including stop-loss.
"""
        elif "risk" in agent_id:
            base_prompt += """
You are the Risk Manager. Validate:
1. Position sizing
2. Stop-loss placement
3. Leverage limits
4. Portfolio exposure

Output format:
{{
  "approved": true/false,
  "confidence": 0.0-1.0,
  "risk_score": 0.0-1.0,
  "rationale": "your analysis",
  "modifications": {{}}
}}

IMPORTANT: If any risk parameter is breached, output "approved": false.
"""

        return base_prompt

    def _parse_agent_response(
        self,
        agent_id: str,
        response_data: Any
    ) -> Optional[AgentProposal]:
        """Parse L2 agent response into structured proposal"""
        try:
            if isinstance(response_data, dict):
                data = response_data
            elif isinstance(response_data, str):
                # Try to parse JSON from text
                data = json.loads(response_data)
            else:
                return None

            # Extract signal
            signal_str = data.get("signal", data.get("approved", "neutral"))

            if isinstance(signal_str, bool):
                signal = AgentSignal.BUY if signal_str else AgentSignal.SELL
            else:
                try:
                    signal = AgentSignal(signal_str)
                except ValueError:
                    signal = AgentSignal.NEUTRAL

            return AgentProposal(
                agent_id=agent_id,
                signal=signal,
                confidence=float(data.get("confidence", data.get("risk_score", 0.5))),
                rationale=data.get("rationale", ""),
                metadata=data.get("metadata", data.get("modifications", {}))
            )

        except Exception as e:
            logger.error(f"Failed to parse response from {agent_id}: {e}")
            return None

    def _load_memory(self) -> str:
        """Load MEMORY.md for context"""
        memory_path = self.config.get("self_improvement", {}).get(
            "memory_file", "data/MEMORY.md"
        )

        try:
            with open(memory_path, "r") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    def _send_alert(self, message: str, channel: str = "telegram") -> None:
        """Send alert notification"""
        try:
            self.cli.send_message(
                target="alerts",
                message=message,
                channel=channel
            )
        except Exception as e:
            logger.warning(f"Failed to send alert: {e}")

    async def run_task(self, user_input: str) -> OrchestratorDecision:
        """
        Main entry point: Process user intent through full swarm flow.
        """
        # Step 1: Classify intent
        intent = self.process_intent(user_input)
        logger.info(f"Intent classified: {intent.value}")

        # Step 2: Decompose into task
        task = self.decompose_task(user_input, intent)

        # Step 3: Create task file
        self.protocol.create_task(
            task_id=task["task_id"],
            task_type=intent.value,
            payload=task
        )

        # Step 4: Delegate to L2 agents
        proposals = await self.delegate_to_l2(task)

        # Step 5: Resolve conflicts
        decision = self.resolve_conflicts(proposals)

        # Step 6: Execute decision
        self.execute_decision(decision)

        return decision
