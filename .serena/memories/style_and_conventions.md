# Style and Conventions
- Language: Python 3.9+.
- Formatting/style: 4-space indentation, focused functions, `snake_case` for functions/variables/modules, `PascalCase` for classes.
- Prefer type hints on public methods and structured returns.
- Use module-level loggers (`logging.getLogger(__name__)`) and consistent error handling.
- Keep config keys stable/descriptive.
- Repo convention: prompt templates in `prompts/` should have both `.md` and `.toml`; SG command prompts in `commands/sg/`; add new prompts to `INDEX.md`.