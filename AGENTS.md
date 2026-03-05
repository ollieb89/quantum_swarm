# Repository Guidelines

## Project Structure & Module Organization
The entrypoint is `main.py`, which wires the orchestrator, agents, executors, and self-learning pipeline. Core runtime logic lives in `src/`:
- `src/core/`: CLI and file-protocol wrappers (`cli_wrapper.py`)
- `src/orchestrator/`: L1 strategic orchestration
- `src/agents/`: L2/L3 trading and risk agents
- `src/skills/`: market-analysis and learning modules

Configuration is in `config/` (`swarm_config.yaml`, `agents.json`). Runtime artifacts and memory files go in `data/`. UI assets are in `dashboard/` and `dashboard/templates/`.

## Build, Test, and Development Commands
- `pip install -r requirements.txt`: install Python dependencies.
- `python main.py`: run interactive swarm mode.
- `python main.py --task "Analyze BTC and recommend a trade"`: run one task non-interactively.
- `python main.py --mode test`: execute built-in integration smoke checks.
- `python main.py --mode daemon`: run daemon mode.

Use Python 3.9+ and ensure `openclaw` CLI is installed if gateway-backed features are needed.

## Coding Style & Naming Conventions
Follow existing Python style:
- 4-space indentation; keep functions focused and small.
- `snake_case` for functions, methods, variables, and module names.
- `PascalCase` for classes and dataclasses.
- Add type hints on public methods and structured return values.
- Prefer module-level loggers (`logging.getLogger(__name__)`) and consistent error handling.

Keep configuration keys stable and descriptive (for example, `risk_limits.max_daily_loss`).

## Testing Guidelines
There is no dedicated `tests/` suite yet; baseline verification is `python main.py --mode test`. For new features, add targeted unit tests under `tests/` using `test_*.py` naming and isolate external dependencies (OpenClaw gateway, exchange APIs) with mocks/stubs where possible.

## Commit & Pull Request Guidelines
Use Conventional Commits:
- `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Example: `feat: add risk guard for max leverage breaches`

PRs should include:
- Clear summary of behavior changes
- Linked issue/task reference
- Commands run for verification
- Dashboard screenshot(s) when UI/templates change

## Security & Configuration Tips
Never commit secrets. Keep tokens (for example `OPENCLAW_API_TOKEN`) in environment variables, not in tracked config. Validate risk limits in `config/swarm_config.yaml` before enabling live trading paths.
