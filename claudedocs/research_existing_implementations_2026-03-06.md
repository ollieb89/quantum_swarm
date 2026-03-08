# Research: Existing Multi-Agent Trading Implementations
**Date**: 2026-03-06
**Scope**: GitHub, HuggingFace, Kaggle, arXiv — avoid reinventing the wheel
**Relevance to**: quantum_swarm (LangGraph + NautilusTrader, Gemini, L1/L2/L3 hierarchy)

---

## Executive Summary

The combination of **LangGraph hierarchical orchestration + NautilusTrader execution** is genuinely novel — no existing project found does both. The closest implementations cover one side or the other:

- **TradingAgents** (TauricResearch) is the closest architectural match: LangGraph + Gemini, same agent roles (analysts, bull/bear researchers, risk team, fund manager), but stops at signal generation — no execution engine.
- **virattt/ai-hedge-fund** is the most polished reference implementation: 17 agents, clean LangGraph graph, FastAPI backend, same Gemini support.
- **FinRL** (AI4Finance) covers the RL training environment angle — directly useful for L3 executor training.
- **AutoHedge** (Swarm Corp) has an execution pipeline but uses a different orchestration framework.

**Recommendation**: Borrow heavily from TradingAgents and virattt for L1/L2 agent design patterns. Use FinRL gym environments for L3 executor training. quantum_swarm's unique value is the LangGraph<>NautilusTrader bridge.

---

## Tier 1: Directly Reusable — High Overlap

### 1. TradingAgents (TauricResearch)
- **Repo**: https://github.com/TauricResearch/TradingAgents
- **Paper**: arXiv:2412.20138 (UCLA + MIT + Tauric Research, ICAIF 2024)
- **Stars**: Active, v0.2.0 released 2026-02
- **Stack**: LangGraph + Gemini/Claude/GPT/Grok/Ollama + Python
- **Architecture**:
  - Analyst Team: Fundamentals, Sentiment, News, Technical analysts
  - Researcher Team: Bull researcher + Bear researcher (structured debate)
  - Trading Team: Trader agent
  - Risk Management Team: Aggressive, Neutral, Conservative risk agents
  - Fund Manager: Final approval
- **What it does well**: Role specialization, debate mechanism between bull/bear, multi-LLM support, clean graph structure
- **Gap vs quantum_swarm**: No execution engine — signals stop at recommendations. No NautilusTrader integration. No L3 stateless executors.
- **Reuse potential**:
  - Analyst and researcher role definitions → L2 Domain Managers design
  - Bull/Bear debate pattern → risk gating
  - `TradingAgentsGraph` graph structure → reference for our orchestrator
  - Multi-provider LLM config pattern

---

### 2. virattt/ai-hedge-fund
- **Repo**: https://github.com/virattt/ai-hedge-fund
- **Stars**: High (community favourite, widely forked)
- **Stack**: LangGraph 0.2.56 + langchain-google-genai + FastAPI + React + SQLAlchemy
- **Architecture**:
  - 12 "investor persona" agents (Buffett, Munger, Burry, Ackman, Druckenmiller, etc.)
  - Valuation Agent, Sentiment Agent, Fundamentals Agent, Technicals Agent
  - Risk Manager
  - Portfolio Manager (synthesis)
- **What it does well**: Clean modular code, backtesting CLI, Streamlit/React UI, real financial data APIs
- **Gap vs quantum_swarm**: Educational/proof-of-concept only. No live execution. No NautilusTrader.
- **Reuse potential**:
  - Agent graph structure patterns
  - Financial data tooling (Yahoo Finance, Polygon.io integration)
  - Risk Manager implementation pattern
  - FastAPI streaming backend pattern (SSE)

---

## Tier 2: Complementary — Different Angle, Fills Gaps

### 3. FinRL (AI4Finance-Foundation)
- **Repo**: https://github.com/AI4Finance-Foundation/FinRL
- **Paper**: ICAIF 2021 + NeurIPS 2020 workshop
- **Stars**: 10k+
- **Stack**: Python, Stable-Baselines3, PPO/A2C/DDPG, OpenAI Gym environments
- **Architecture**: Three layers — Market Environment → DRL Agent → Application
- **What it does well**: RL-based strategy learning, gym environments for backtesting, portfolio allocation, crypto trading
- **Key fact**: NautilusTrader explicitly advertises compatibility with FinRL-style RL training ("backtest engine fast enough to train AI trading agents")
- **Reuse potential**:
  - FinRL gym environments → training environments for L3 RL executors
  - FinRL-Trading end-to-end pipeline → reference for our train/test/live split
  - DRL algorithms (PPO, A2C) → L3 executor policy learning
  - `FinRL-Meta` near-real market environments → simulation layer

### 4. FinRobot (AI4Finance-Foundation)
- **Repo**: https://github.com/AI4Finance-Foundation/FinRobot
- **Paper**: ICAIF 2024 workshop
- **Stack**: Multi-LLM, domain-specific financial AI agents
- **Architecture**: Multi-source LLM Foundation → Financial AI Agents → Market Data Pipeline
- **What it does well**: Real-time data processing pipeline, equity research automation, multi-source LLM routing
- **Reuse potential**:
  - Data pipeline patterns (real-time financial data ingestion)
  - LLM routing strategy (quick-thinking models for data retrieval, deep-thinking for analysis)
  - Equity research agent patterns

### 5. AutoHedge (The-Swarm-Corporation)
- **Repo**: https://github.com/The-Swarm-Corporation/AutoHedge
- **Stars**: ~1,053, MIT license
- **Stack**: Swarms framework (not LangGraph), Python
- **Architecture**: Director → Quant → Risk Manager → Execution Agent (4-stage pipeline)
- **What it does well**: Has an actual execution pipeline, risk-first design, structured JSON outputs, enterprise logging
- **Gap**: Uses proprietary Swarms framework, not LangGraph. Less modular than our architecture.
- **Reuse potential**:
  - Execution pipeline design (Director→Quant→Risk→Execute stages)
  - Risk-first ordering philosophy
  - Structured JSON output pattern for agent handoffs

---

## Tier 3: Supporting Infrastructure

### 6. FinGPT (AI4Finance-Foundation)
- **Repo**: https://github.com/AI4Finance-Foundation/FinGPT
- **Stack**: Fine-tuned LLMs on financial data, instruction tuning
- **What it does well**: Open-source financial LLMs, sentiment analysis models, zero/few-shot financial NLP
- **Reuse potential**: Pre-trained sentiment models usable by L2 sentiment analyst agents; financial instruction tuning dataset

### 7. NautilusTrader itself — Community Strategies
- **Repo**: https://github.com/nautechsystems/nautilus_trader
- **Key insight**: NautilusTrader explicitly keeps "distributed orchestration and built-in AI/ML tooling OUT OF SCOPE" — this is quantum_swarm's unique layer
- **Available adapters**: Binance, Bybit, Deribit, dYdX, Hyperliquid, Kraken, OKX + Tardis data
- **Reuse potential**:
  - Existing example strategies → L3 executor templates
  - CCXT + cryptofeed integration pattern (issue #2885) → data ingestion reference
  - `SimpleEMACross` and similar strategies → L3 stateless executor base implementations

### 8. AlphaCouncil (Sunnil07)
- **Repo**: https://github.com/Sunnil07/AlphaCouncil
- **Stack**: LangGraph + Groq, A-share market analysis
- **Tags**: `quantitative-finance algorithmic-trading multi-agent-systems langgraph volatility-forecasting`
- **Note**: Small project (0 stars) but uses LangGraph for trading — worth examining for patterns

### 9. Kaggle — RL Trading Resources
- Notable notebooks:
  - PPO Reinforcement Learning Trading Agent (Kaggle: mahdikhodarahimi)
  - Deep Reinforcement Learning for Stock Trading (from FinRL library)
  - Dataset: alincijov/trading (13MB RL stock trading dataset)
- **Relevance**: Training data and baseline RL implementations for L3 executor development

---

## Architecture Gap Analysis

| Capability | TradingAgents | ai-hedge-fund | FinRL | AutoHedge | quantum_swarm |
|---|---|---|---|---|---|
| LangGraph orchestration | YES | YES | NO | NO | YES |
| Google Gemini support | YES | YES | NO | NO | YES |
| Hierarchical L1/L2/L3 | NO | NO | NO | Partial | YES |
| NautilusTrader execution | NO | NO | NO | NO | YES |
| Live trading | NO | NO | YES (Alpaca) | YES | PLANNED |
| Backtesting | NO | YES | YES | NO | YES (NT) |
| RL executor training | NO | NO | YES | NO | PLANNED |
| Bull/Bear debate | YES | NO | NO | NO | YES (P2) |
| Risk gating | YES | YES | NO | YES | YES (P2) |

---

## What quantum_swarm Should Borrow

### Agent Role Designs (from TradingAgents + virattt)
- **Analyst role prompt templates**: TradingAgents has production-tested prompts for Fundamental, Sentiment, News, and Technical analysts
- **Bull/Bear debate structure**: Already implemented in P2 — validate against TradingAgents paper for completeness
- **Risk team triad** (aggressive/neutral/conservative): TradingAgents uses this exact pattern — directly applicable to our risk gating

### Execution Pipeline (from AutoHedge)
- The Director→Quant→Risk→Execute 4-stage ordering maps well to our L1→L2→L3 hierarchy
- AutoHedge's structured JSON output format is worth adopting for agent handoffs

### RL Training Layer (from FinRL)
- FinRL gym environments can wrap NautilusTrader backtester for L3 RL executor training
- Use `FinRL-Trading` pipeline pattern for train/test/live separation
- Start with PPO (proven for portfolio problems) before more exotic algorithms

### Data Pipeline (from FinRobot)
- Multi-source data ingestion patterns (Yahoo Finance, Alpha Vantage, news APIs)
- LLM routing: use fast models (Gemini Flash) for data retrieval nodes, deeper models for analysis nodes

### LangGraph Patterns
- Use `langgraph-supervisor` library as reference — official recommendation now is tool-based handoffs rather than the library itself
- Hierarchical subgraph pattern: L2 managers as compiled subgraphs invoked by L1 supervisor

---

## Confidence Assessment

| Finding | Confidence | Notes |
|---|---|---|
| TradingAgents is closest existing implementation | HIGH | Verified: same stack (LangGraph + Gemini), same agent roles |
| quantum_swarm's LangGraph+NautilusTrader combo is novel | HIGH | No project found combining both |
| FinRL is compatible with NautilusTrader | HIGH | NT docs explicitly mention RL training suitability |
| AutoHedge execution pipeline is reusable | MEDIUM | Different framework (Swarms, not LangGraph) — patterns reusable, code not |
| HuggingFace has limited relevant resources | HIGH | Search returned no relevant models/datasets for this architecture |

---

## Recommended Next Steps

1. **Read TradingAgents paper** (arXiv:2412.20138) — validate our L2 analyst/researcher design against their tested architecture
2. **Review virattt/ai-hedge-fund codebase** — particularly `agents.py` and `langgraph_workflow.py` for patterns applicable to our orchestrator
3. **Integrate FinRL gym environments** as an L3 executor training layer (Phase 4+ candidate)
4. **Check NautilusTrader example strategies** for L3 stateless executor templates
5. **Consider adopting TradingAgents' multi-LLM routing** — fast model for data nodes, reasoning model for analysis nodes (already using Gemini Flash; may want Flash for data and Pro for decisions)

---

## Sources

- https://github.com/TauricResearch/TradingAgents
- https://arxiv.org/html/2412.20138v1
- https://github.com/virattt/ai-hedge-fund
- https://github.com/AI4Finance-Foundation/FinRL
- https://github.com/AI4Finance-Foundation/FinRobot
- https://arxiv.org/html/2405.14767v2
- https://github.com/AI4Finance-Foundation/FinGPT
- https://github.com/The-Swarm-Corporation/AutoHedge
- https://github.com/nautechsystems/nautilus_trader
- https://github.com/von-development/awesome-LangGraph (Finance section)
- https://tradingagents-ai.github.io/
- https://www.kaggle.com/code/mahdikhodarahimi/ppo-reinforcement-learning-trading-agent
