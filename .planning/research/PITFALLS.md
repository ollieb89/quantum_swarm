# Domain Pitfalls

**Domain:** Quantitative Finance / Multi-Agent Systems (MAS)
**Researched:** 2025-03-05
**Overall Confidence:** HIGH (Verified against EU/Finanstilsynet enforcement actions and MAS literature)

## Critical Pitfalls

### Pitfall 1: Synchronized Feedback Loops (Flash Crash Trigger)
**What goes wrong:** Multiple autonomous agents (L3) respond to the same market signal or each other's trades, creating a recursive selling/buying spiral.
**Why it happens:** "Mechanical herding" where agents converge on the same "optimal" strategy (e.g., momentum) or react to the price impact of fellow agents.
**Consequences:** Rapid portfolio liquidation, massive slippage, and systemic market instability.
**Prevention:** Implement "myopic" constraints (short-term volume limits), instrument-level circuit breakers, and adversarial agent testing to detect correlation.
**Detection:** Real-time monitoring of trade correlation across swarms; spikes in internal trade volume without external news.

### Pitfall 2: Short Selling Regulation (SSR) Compliance Breach
**What goes wrong:** L3 agents execute short sales without a valid "locate" or an "absolutely enforceable claim" to the shares, violating EU SSR (specifically Finanstilsynet focus).
**Why it happens:** Failure to account for T+2 settlement cycles or delays in share capital registration; assuming liquidity exists because it was there "recently."
**Consequences:** Heavy fines (e.g., NOK 3.5m fine for ATG Netherlands in 2025) and regulatory suspension.
**Prevention:** Hard-code a mandatory "Locate Verification" step in the execution pipeline; implement a settlement delay buffer in the risk model.
**Detection:** Pre-trade checks flagging any sell order where share ownership is not explicitly verified in the custodian ledger.

### Pitfall 3: "Black-Box" Explainability Gap (MiFID II Art. 17)
**What goes wrong:** The system makes a series of trades that the compliance officer or regulator (Finanstilsynet) cannot understand or audit after the fact.
**Why it happens:** Use of complex neural networks (LLMs/RL) for decision-making without an "explainability layer" or immutable audit trail of the prompt-response chain.
**Consequences:** Violation of MiFID II requirements for "understandable" and "governed" algorithms; inability to defend against market abuse accusations.
**Prevention:** Implement an "Inspector" agent that logs the *rationale* for every strategic shift; store immutable logs of the full agent state at the time of trade.
**Detection:** Periodic "Audit Stress Tests" where a human attempts to reconstruct the logic of a trade using only the logs.

## Moderate Pitfalls

### Pitfall 1: Reward Hacking & Algorithmic Collusion
**What goes wrong:** Agents find "shortcuts" to maximize rewards (e.g., volume, short-term Sharpe) that actually harm long-term portfolio health or violate ethics.
**Prevention:** Multi-objective reward functions; use of adversarial agents (L2) to "stress" the strategies of the executors.

### Pitfall 2: Non-Stationarity (Regime Shift Failure)
**What goes wrong:** Agents trained on low-volatility data fail catastrophically during a "Black Swan" event or sudden interest rate hike.
**Prevention:** Dynamic regime detection (L2) that triggers a "Safe Mode" (reduced position sizes) when market volatility exceeds historical bounds.

### Pitfall 3: State Drift & Context Corruption
**What goes wrong:** Strategic intent from L1 is lost or corrupted as it passes through L2 (Managers) to L3 (Executors) due to "lossy" summarization.
**Prevention:** Mandatory schema validation between agent layers; L1-to-L3 "Consistency Checks" before execution.

## Minor Pitfalls

### Pitfall 1: Internal Wash Trading
**What goes wrong:** Two different swarms/agents accidentally trade against each other (buying and selling the same instrument), creating useless costs and regulatory red flags.
**Prevention:** Global order book monitoring that blocks orders that would cross internally.

### Pitfall 2: Communication Latency
**What goes wrong:** Hierarchical overhead (L1 -> L2 -> L3) makes the trade "stale" by the time it reaches the market.
**Prevention:** Asynchronous parallel processing for non-critical analysis; direct "Emergency Path" for risk-based liquidations.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **L1: Strategic Orchestration** | Explainability Gap | Build the "Audit Log" and "Inspector" role from day one. |
| **L2: Domain Managers** | State Drift | Use strictly typed JSON schemas for all inter-agent communication. |
| **L3: Autonomous Execution** | SSR Compliance | Integrate a hard "Locate" check before any order is sent to the router. |
| **Risk Gating (All)** | Feedback Loops | Implement instrument-level kill switches that trigger on volume/volatility anomalies. |

## Sources

- **Finanstilsynet (Norway):** Enforcement action against Algorithmic Trading Group (ATG) Netherlands (2025) regarding SSR violations.
- **Danish FSA (Finanstilsynet):** Thematic study on recordkeeping and market abuse detection (2025).
- **ESMA:** MiFID II Article 17 - Regulatory Technical Standards on Algorithmic Trading.
- **Academic Research:** "Flash Crashes and Algorithmic Feedback Loops" (various, 2010-2024).
- **Industry Reports:** Galileo.ai and Medium post-mortems on multi-agent system state corruption.
