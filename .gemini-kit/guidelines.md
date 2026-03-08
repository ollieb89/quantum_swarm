# Guidelines Context: Quantum Swarm

## Coding Standards
- **Python Style:** Adhere to PEP 8 with 4-space indentation.
- **Naming Conventions:**
  - `snake_case` for functions, methods, variables, and module names.
  - `PascalCase` for classes and dataclasses.
- **Logic:** Keep functions small, focused, and single-purpose.
- **Type Safety:** Provide type hints for all public methods and structured return values.
- **Logging:** Prefer module-level loggers (`logging.getLogger(__name__)`) over print statements.
- **Error Handling:** Use consistent error handling patterns and descriptive exception messages.

## Git & Development Workflow
- **Conventional Commits:** Use structured commit messages:
  - `feat:` for new features.
  - `fix:` for bug fixes.
  - `docs:` for documentation changes.
  - `refactor:` for code changes that neither fix a bug nor add a feature.
  - `test:` for adding or correcting tests.
  - `chore:` for updating build tasks, package manager configs, etc.
- **Pull Requests:** Every PR should include a clear summary, a reference to the task/issue, the commands used for verification, and screenshots if the dashboard UI was modified.

## Testing Guidelines
- **Verification:** Always run `python main.py --mode test` to ensure core integration remains intact.
- **Unit Testing:** Place new tests in the `tests/` directory following the `test_*.py` pattern.
- **Mocking:** Isolate external dependencies like OpenClaw gateways or exchange APIs using mocks or stubs.

## Documentation & Assets
- **Prompts:** When adding new LLM prompts, provide both `.md` and `.toml` files in the `prompts/` directory and update the `INDEX.md`.
- **UI:** Ensure any changes to dashboard templates are verified for responsiveness.
