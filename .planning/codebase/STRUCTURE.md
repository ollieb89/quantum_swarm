# Codebase Structure

**Analysis Date:** 2025-03-05

## Directory Layout

```
quantum_swarm/
├── src/                    # Primary source code (Python)
│   ├── agents/             # Agent implementations (Executors & Dexter TS)
│   │   ├── dexter/         # TypeScript-based Dexter agent
│   │   └── l3_executor.py  # Base Level 3 executors
│   ├── core/               # Core framework utilities
│   ├── graph/              # LangGraph orchestration
│   │   ├── agents/         # LangGraph specific agent nodes (L2/L3)
│   │   │   └── l3/         # L3 LangGraph nodes (e.g., DataFetcher)
│   │   ├── orchestrator.py # Graph compilation and logic
│   │   └── state.py        # Centralized SwarmState
│   ├── models/             # Shared data models (Pydantic)
│   ├── orchestrator/       # Strategic L1 orchestrator
│   ├── skills/             # Agent skills and tools
│   └── tools/              # Integration bridges and API clients
├── tests/                  # Comprehensive test suite
├── dashboard/              # Monitoring dashboard (HTML/JS)
├── data/                   # Persistence layer (logs, memory, inbox/outbox)
├── docs/                   # Design, research, and phase reports
├── scripts/                # Automation and tracking scripts
├── .planning/              # Phase-based planning and state tracking
└── main.py                 # System entry point
```

## Directory Purposes

**src/graph/:**
- Purpose: Management of the swarm's state and workflow using LangGraph.
- Contains: Node definitions, conditional routing logic, and state management.
- Key files: `src/graph/orchestrator.py`, `src/graph/state.py`.

**src/agents/dexter/:**
- Purpose: TypeScript fundamental analysis agent.
- Contains: Fundamental research logic, market news integration, and report generation.
- Key files: `src/agents/dexter/src/index.tsx`.

**src/tools/:**
- Purpose: Infrastructure for external service integration.
- Contains: Clients for market data (yfinance, CCXT), and bridges for external agents (Dexter).
- Key files: `src/tools/dexter_bridge.py`, `src/tools/data_sources/`.

**src/models/:**
- Purpose: Definitions of structured data used throughout the swarm.
- Contains: Pydantic models for market data, sentiment, and agent outputs.
- Key files: `src/models/data_models.py`.

## Key File Locations

**Entry Points:**
- `main.py`: Primary CLI entry point.
- `src/orchestrator/strategic_l1.py`: Strategic L1 Orchestrator logic.
- `src/graph/orchestrator.py`: LangGraph operational entry point.

**Configuration:**
- `config/swarm_config.yaml`: Central system configuration.
- `config/agents.json`: Agent-specific parameters and reliability profiles.

**Core Logic:**
- `src/graph/debate.py`: Logic for weighing evidence and synthesizing consensus.
- `src/graph/agents/analysts.py`: Reasoning logic for L2 Domain Managers.
- `src/graph/agents/researchers.py`: Adversarial research logic.

**Testing:**
- `tests/`: Root of the test suite, categorized by component (e.g., `test_dexter_bridge.py`).

## Naming Conventions

**Files:**
- snake_case for Python files: `l3_executor.py`.
- kebab-case for TypeScript files/dirs: `run-query.ts`.

**Directories:**
- snake_case for Python packages: `data_sources/`.
- kebab-case for general directories: `plans-archive/`.

## Where to Add New Code

**New Agent (L2/L3):**
- Implementation: `src/graph/agents/` or `src/agents/`.
- Integration: Register as a node in `src/graph/orchestrator.py`.

**New Technical Skill/Tool:**
- Shared helper: `src/tools/` or `src/skills/`.

**New Data Source:**
- Client: `src/tools/data_sources/`.
- Integration: Update `src/graph/agents/l3/data_fetcher.py`.

## Special Directories

**data/inter_agent_comms/:**
- Purpose: Persistence for asynchronous communication between agents.
- Generated: Yes.
- Committed: No (managed by protocol).

**.planning/codebase/:**
- Purpose: Architectural and structural mapping documents (like this one).
- Committed: Yes.

---

*Structure analysis: 2025-03-05*
