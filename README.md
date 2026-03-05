# Quantum Swarm

Multi-Agent Trading System with OpenClaw Integration

## Requirements

```
# Core
Python >= 3.9

# Configuration
pyyaml >= 6.0

# Web Dashboard (optional, for embedded server)
flask >= 2.0
flask-socketio >= 5.0

# Date handling
pytz >= 2023.3

# Optional: For live trading
ccxt >= 4.0
yfinance >= 0.2

# Optional: For technical analysis
ta-lib  # Requires system installation
numpy >= 1.24
pandas >= 2.0
```

## Installation

```bash
# Clone and install
cd quantum-swarm
pip install -r requirements.txt

# Install OpenClaw CLI (if not already installed)
npm install -g openclaw@latest

# Configure
cp config/swarm_config.yaml.example config/swarm_config.yaml
# Edit swarm_config.yaml with your settings
```

## Quick Start

```bash
# Run in interactive mode
python main.py

# Run a specific task
python main.py --task "Analyze BTC and recommend a trade"

# Run tests
python main.py --mode test

# Run as daemon
python main.py --mode daemon
```

## Project Structure

```
quantum-swarm/
├── config/               # Configuration files
│   ├── swarm_config.yaml
│   └── agents.json
├── data/                 # Data directory
│   ├── inbox/           # Incoming tasks
│   ├── outbox/          # Completed results
│   ├── inter_agent_comms/  # Agent communication
│   ├── logs/            # Execution logs
│   └── MEMORY.md        # Learned rules
├── src/
│   ├── core/            # Core utilities
│   │   └── cli_wrapper.py
│   ├── orchestrator/    # L1 Orchestrator
│   │   └── strategic_l1.py
│   ├── agents/          # L2/L3 Agents
│   │   ├── __init__.py
│   │   └── l3_executor.py
│   └── skills/          # Skills modules
│       ├── market_analysis.py
│       └── crypto_learning.py
├── dashboard/           # Web Dashboard
│   └── templates/
│       └── index.html
├── main.py              # Entry point
├── requirements.txt
└── README.md
```

## Usage

### Interactive Mode

```bash
$ python main.py
> analyze BTC
> trade ETH
> review
> status
> quit
```

### Configuration

Edit `config/swarm_config.yaml`:

```yaml
openclaw:
  gateway_url: "http://127.0.0.1:18789"
  api_token: "${OPENCLAW_API_TOKEN}"

risk_limits:
  max_position_size: 0.10
  max_leverage: 10.0
  max_daily_loss: 0.05
```

## OpenClaw CLI Commands

This project integrates with OpenClaw CLI:

```bash
# Check gateway status
openclaw health

# List agents
openclaw agents list

# Add cron job
openclaw cron add --name "macro_scan" --message "Analyze markets" --at "0 */4 * * *"

# Send message
openclaw message send --target "alerts" --message "Trade executed"
```

## Obsidian Tracking Automation

Use the built-in updater and a user-level `systemd` timer:

```bash
chmod +x scripts/run_obsidian_tracking_update.sh scripts/install_obsidian_tracking_timer.sh
scripts/install_obsidian_tracking_timer.sh --install
scripts/install_obsidian_tracking_timer.sh --status
```

Manual run + logs:

```bash
systemctl --user start quantum-swarm-tracking.service
journalctl --user -u quantum-swarm-tracking.service --no-pager -n 100
```

If you need the timer to run while logged out, enable linger once:

```bash
sudo loginctl enable-linger "$USER"
```

Reference: `docs/obsidian-tracking-automation.md`

## Features

- **L1 Strategic Orchestrator**: Intent classification, task decomposition, conflict resolution
- **L2 Domain Managers**: Macro Analyst, Quant Modeler, Risk Manager
- **L3 Executors**: Data Fetcher, Backtester, Order Router
- **Self-Improvement Framework**: Trade logging, analysis, rule generation
- **File-Based Protocol**: Inbox/outbox communication
- **Web Dashboard**: Real-time monitoring and controls

## License

MIT
