"""
L2 Domain Managers - Macro Analyst, Quant Modeler, Risk Manager

Specialized agents for financial analysis and risk management.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MarketReport:
    """Market environment report from Macro Analyst"""
    phase: str  # Bullish/Neutral/Bearish
    risk_on: bool
    confidence: float
    vix_level: float
    sentiment: str
    outlook: str  # 1-5 day outlook
    indicators: Dict[str, Any]


@dataclass
class TradeProposal:
    """Trade proposal from Quant Modeler"""
    symbol: str
    direction: str  # LONG/SHORT
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    confidence: float
    indicators: Dict[str, Any]
    rationale: str


@dataclass
class RiskApproval:
    """Risk validation from Risk Manager"""
    approved: bool
    risk_score: float
    position_size: float
    stop_loss: float
    leverage: float
    modifications: Dict[str, Any]
    rationale: str


class MacroAnalyst:
    """
    L2 Macro Analyst

    Evaluates global market conditions, trend directions, and economic indicators.
    Focuses on inter-market correlations, sentiment analysis, and macroeconomic environment.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.agent_id = "l2-macro-analyst"

    def analyze(self, symbols: List[str] = None) -> MarketReport:
        """
        Perform macro analysis.

        In production, this would:
        1. Check global market hours (Tokyo/London/NY)
        2. Fetch economic calendar
        3. Analyze VIX and yields
        4. Generate sentiment score
        """
        logger.info(f"Running macro analysis for {symbols or ['global']}")

        # Simulated analysis
        report = MarketReport(
            phase="Bullish",
            risk_on=True,
            confidence=0.78,
            vix_level=14.5,
            sentiment="Risk-On",
            outlook="2-3 days",
            indicators={
                "vix": 14.5,
                "usd_index": 104.2,
                "10y_yield": 4.25,
                "gold": 2035.0,
                "btc": 67500.0
            }
        )

        logger.info(f"Macro analysis complete: {report.phase}, VIX: {report.vix_level}")
        return report

    def check_market_hours(self) -> Dict[str, bool]:
        """Check if major markets are open"""
        from datetime import datetime
        import pytz

        now = datetime.now(pytz.utc)

        # Simplified market hours (in UTC)
        markets = {
            "Tokyo": (0, 7),      # 00:00 - 07:00 UTC
            "London": (7, 16),    # 07:00 - 16:00 UTC
            "NY": (14, 21),       # 14:00 - 21:00 UTC
            "Sydney": (22, 24),   # 22:00 - 00:00 UTC
        }

        current_hour = now.hour

        status = {}
        for market, (open_hour, close_hour) in markets.items():
            if open_hour <= current_hour < close_hour:
                status[market] = True
            elif market == "Sydney" and (current_hour >= 22 or current_hour < 0):
                status[market] = True
            else:
                status[market] = False

        return status

    def get_economic_events(self) -> List[Dict]:
        """Get upcoming economic events"""
        # Placeholder - would integrate with economic calendar API
        return [
            {"event": "CPI", "date": "2026-03-12", "impact": "high"},
            {"event": "FOMC Minutes", "date": "2026-03-19", "impact": "high"},
            {"event": "NFP", "date": "2026-04-04", "impact": "high"},
        ]

    def to_json(self, report: MarketReport) -> Dict:
        """Convert report to JSON schema"""
        return {
            "signal": report.phase.lower(),
            "confidence": report.confidence,
            "risk_on": report.risk_on,
            "vix_level": report.vix_level,
            "sentiment": report.sentiment,
            "outlook": report.outlook,
            "indicators": report.indicators,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


class QuantModeler:
    """
    L2 Quant Modeler

    Processes time-series data, conducts factor analysis, and evaluates
    technical indicators to identify precise entry and exit signals.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.agent_id = "l2-quant-modeler"

    def analyze(
        self,
        symbol: str,
        timeframe: str = "1H"
    ) -> TradeProposal:
        """
        Perform technical analysis and generate trade proposal.

        In production, this would:
        1. Fetch price data
        2. Calculate technical indicators
        3. Identify patterns
        4. Generate entry/exit signals
        """
        logger.info(f"Running quant analysis for {symbol} on {timeframe}")

        # Simulated analysis
        proposal = TradeProposal(
            symbol=symbol,
            direction="LONG",
            entry_price=67500.0,
            stop_loss=66500.0,  # 1.5% below entry
            take_profit=69500.0,  # 3% above entry
            position_size=0.05,  # 5% of portfolio
            confidence=0.82,
            indicators={
                "rsi": 45.2,
                "macd": "bullish_crossover",
                "sma_20": 67200.0,
                "sma_50": 66800.0,
                "bb_upper": 68200.0,
                "bb_lower": 66800.0,
                "volume": "above_average"
            },
            rationale=f"RSI showing oversold conditions. Price resting on 50 SMA support."
        )

        logger.info(
            f"Trade proposal: {proposal.direction} {proposal.symbol} "
            f"@ {proposal.entry_price}, SL: {proposal.stop_loss}"
        )
        return proposal

    def calculate_indicators(self, prices: List[float]) -> Dict[str, float]:
        """Calculate technical indicators"""
        if not prices:
            return {}

        import statistics

        # Simple calculations (production would use TA-Lib or similar)
        sma_20 = statistics.mean(prices[-20:]) if len(prices) >= 20 else statistics.mean(prices)
        sma_50 = statistics.mean(prices[-50:]) if len(prices) >= 50 else sma_20

        # RSI calculation
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = statistics.mean(gains[-14:]) if len(gains) >= 14 else statistics.mean(gains)
        avg_loss = statistics.mean(losses[-14:]) if len(losses) >= 14 else statistics.mean(losses)

        rs = avg_gain / avg_loss if avg_loss != 0 else 100
        rsi = 100 - (100 / (1 + rs))

        return {
            "sma_20": sma_20,
            "sma_50": sma_50,
            "rsi": rsi,
            "momentum": prices[-1] - prices[-10] if len(prices) >= 10 else 0
        }

    def validate_stop_loss(self, proposal: TradeProposal) -> bool:
        """Validate stop-loss is present and reasonable"""
        if not proposal.stop_loss:
            return False

        entry = proposal.entry_price
        stop = proposal.stop_loss

        if proposal.direction == "LONG":
            loss_pct = (entry - stop) / entry
        else:
            loss_pct = (stop - entry) / entry

        # Stop loss should be between 0.5% and 5%
        return 0.005 <= loss_pct <= 0.05

    def to_json(self, proposal: TradeProposal) -> Dict:
        """Convert proposal to JSON schema"""
        return {
            "signal": proposal.direction.lower(),
            "confidence": proposal.confidence,
            "symbol": proposal.symbol,
            "entry_price": proposal.entry_price,
            "stop_loss": proposal.stop_loss,
            "take_profit": proposal.take_profit,
            "position_size": proposal.position_size,
            "indicators": proposal.indicators,
            "rationale": proposal.rationale,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


class RiskManager:
    """
    L2 Risk Manager

    Enforces strict operational discipline, portfolio limits, and trade safety.
    Validates all proposed strategies against internal limits and regulatory frameworks.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.agent_id = "l2-risk-manager"
        self.risk_limits = config.get("risk_limits", {})

    def validate(
        self,
        proposal: TradeProposal,
        portfolio: Optional[Dict] = None
    ) -> RiskApproval:
        """
        Validate trade proposal against risk limits.

        Checks:
        1. Position size limits
        2. Leverage limits
        3. Stop-loss presence
        4. Portfolio exposure
        5. VIX-based adjustments
        """
        logger.info(f"Validating trade proposal for {proposal.symbol}")

        modifications = {}
        risk_score = 0.0
        approved = True

        # Check position size
        max_position = self.risk_limits.get("max_position_size", 0.1)
        if proposal.position_size > max_position:
            modifications["position_size"] = max_position
            risk_score += 0.3
            logger.warning(f"Position size reduced: {proposal.position_size} -> {max_position}")

        # Check leverage
        max_leverage = self.risk_limits.get("max_leverage", 10.0)
        leverage = proposal.position_size * 10  # Simplified
        if leverage > max_leverage:
            modifications["leverage"] = max_leverage
            risk_score += 0.2
            logger.warning(f"Leverage capped at {max_leverage}")

        # Check stop-loss
        if not proposal.stop_loss:
            approved = False
            risk_score = 1.0
            modifications["error"] = "Stop-loss required"
            logger.error("Trade rejected: No stop-loss")

        # Check risk-reward ratio
        if approved and proposal.stop_loss and proposal.take_profit:
            if proposal.direction == "LONG":
                reward = proposal.take_profit - proposal.entry_price
                risk = proposal.entry_price - proposal.stop_loss
            else:
                reward = proposal.entry_price - proposal.take_profit
                risk = proposal.stop_loss - proposal.entry_price

            min_ratio = self.risk_limits.get("min_risk_reward", 1.5)
            if risk > 0 and reward / risk < min_ratio:
                modifications["take_profit"] = "adjusted for min risk-reward"
                risk_score += 0.2
                logger.warning("Take-profit adjusted for risk-reward ratio")

        # Check VIX
        vix = proposal.indicators.get("vix", 15)
        vix_thresholds = self.risk_limits.get("vix_thresholds", {})

        if vix >= vix_thresholds.get("critical", 40):
            approved = False
            risk_score = 1.0
            logger.error(f"Trade rejected: VIX critical ({vix})")
        elif vix >= vix_thresholds.get("high", 30):
            risk_score += 0.3
            logger.warning(f"VIX elevated ({vix})")

        # Final approval
        if risk_score >= self.risk_limits.get("max_drawdown", 0.15):
            approved = False
            logger.error("Trade rejected: Risk score exceeds limit")

        approval = RiskApproval(
            approved=approved,
            risk_score=min(risk_score, 1.0),
            position_size=modifications.get("position_size", proposal.position_size),
            stop_loss=proposal.stop_loss,
            leverage=modifications.get("leverage", leverage),
            modifications=modifications,
            rationale=f"{'Approved' if approved else 'Rejected'} with risk score {risk_score:.2f}"
        )

        logger.info(f"Risk validation: {'APPROVED' if approval.approved else 'REJECTED'}")
        return approval

    def calculate_position_size(
        self,
        account_equity: float,
        risk_per_trade: float,
        entry_price: float,
        stop_loss: float
    ) -> float:
        """Calculate safe position size based on risk parameters"""
        risk_amount = account_equity * risk_per_trade
        price_risk = abs(entry_price - stop_loss)

        if price_risk == 0:
            return 0

        position_size = risk_amount / price_risk
        return position_size

    def to_json(self, approval: RiskApproval) -> Dict:
        """Convert approval to JSON schema"""
        return {
            "approved": approval.approved,
            "confidence": 1.0 - approval.risk_score,
            "risk_score": approval.risk_score,
            "position_size": approval.position_size,
            "stop_loss": approval.stop_loss,
            "leverage": approval.leverage,
            "modifications": approval.modifications,
            "rationale": approval.rationale,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
