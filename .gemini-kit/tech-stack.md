# Tech Stack Context: Quantum Swarm

## Languages
- **Python:** Version 3.9 or higher is required for the core agentic logic.
- **HTML/CSS/JS:** Used for the OpenClaw Financial Swarm Dashboard.

## Core Frameworks
- **OpenClaw:** The central AI agent runtime and message router for hierarchical orchestration.
- **Flask / Flask-SocketIO:** Provides the web dashboard and real-time communication between the swarm and the UI.

## Key Libraries & Tools
- **Data & Math:** `pandas`, `numpy`, `pytz`.
- **Financial Analysis:** `ccxt`, `yfinance`, `ta-lib`.
- **Configuration:** `pyyaml`.
- **Infrastructure:** `systemd` (used for the Obsidian tracking automation timer), `npm` (for OpenClaw CLI).

## Storage & Data Protocol
- **File-Based Memory:** Uses a "Filesystem-as-Context" model with `.md`, `.json`, and `.yaml` files.
- **JSON:** Used for trade logging (`trades.json`), agent definitions (`agents.json`), and inter-agent communication messages.
- **Markdown:** Used for persistent memory (`MEMORY.md`), system-wide rules (`AGENTS.md`), and Obsidian project tracking.
- **YAML:** Centralized configuration (`swarm_config.yaml`).

## Integration
- **OpenClaw Gateway:** Deterministic message routing and skill management.
- **Obsidian:** Automated project tracking and status updates via specialized scripts.
