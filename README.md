# Quantum Swarm

Multi-Agent Trading System with LangGraph Orchestration & OpenClaw Integration.

## Requirements

- **Python**: >= 3.12 (managed via `uv`)
- **System Dependencies**: `ta-lib` (required for technical analysis)

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd quantum-swarm

# Install dependencies using uv
uv sync

# Configure environment
cp .env.example .env
# Set your GOOGLE_API_KEY and other credentials
```

## Quick Start

```bash
# Run in interactive mode
uv run python main.py

# Run a specific task
uv run python main.py --task "Analyze BTC and recommend a trade"

# Run the Phase 2 test suite
uv run python -m pytest tests/test_analysts.py tests/test_researchers.py tests/test_adversarial_debate.py -v
```

## Architecture: LangGraph Swarm

The system uses a 3-layer hierarchical orchestration model built on **LangGraph**:

1.  **L1 (Strategic Orchestrator)**: Intent classification and routing.
2.  **L2 (Cognitive Analysis)**: Parallel adversarial debate (MacroAnalyst, QuantModeler -> Bullish/Bearish Researchers).
3.  **L3 (Execution Engine)**: Risk-gated execution pipeline (Data Fetcher, Backtester, Order Router).

### Project Structure

```
quantum-swarm/
├── src/
│   ├── graph/           # Core LangGraph orchestration
│   │   ├── agents/      # L2 analysis agents
│   │   ├── nodes/       # Reusable graph nodes
│   │   └── debate.py    # Consensus & debate logic
│   ├── core/            # System utilities
│   ├── security/        # ClawGuard & safety protocols
│   ├── tools/           # Market data & execution tools
│   └── blackboard/      # Shared persistent state
├── tests/               # 60+ unit & integration tests
├── .planning/           # Roadmap & Project State (YAML-backed)
├── config/              # Agent & Swarm configurations
├── data/                # Market data (DuckDB) & logs
└── dashboard/           # Real-time HTML dashboard
```

## Features

- **Adversarial Debate**: Researcher agents (Bullish vs. Bearish) battle to reach a weighted consensus score before execution.
- **Risk Gating**: Trades only proceed if the debate consensus exceeds the 0.6 threshold.
- **ClawGuard**: Hard security layer to prevent credential leaks and verify risk approvals.
- **Verification Wrapper**: Budget-enforced tool calls with automatic deduplication caching.
- **OpenClaw Integration**: Unified gateway for order routing and health monitoring.

## License

MIT
