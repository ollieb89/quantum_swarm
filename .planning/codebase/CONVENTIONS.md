# Coding Conventions

## Python (Swarm Core)
- **Naming:** `snake_case` for variables/functions, `PascalCase` for classes/dataclasses
- **Typing:** Explicit type hints required for public APIs and graph state
- **Logging:** Standard `logging` module with module-level loggers
- **Indentation:** 4 spaces (PEP 8)
- **Design:** State-driven logic via LangGraph nodes and edges

## TypeScript (Dexter Agent)
- **Naming:** `camelCase` for variables/functions, `PascalCase` for React/Ink components
- **Module System:** ESM (required by Bun)
- **Error Handling:** Result-pattern or structured error objects with Zod validation
- **Imports:** Relative paths with `.js` extensions for compiled output compatibility

## General
- **Configuration:** No hardcoded secrets; use `.env`
- **Documentation:** Use JSDoc/Docstrings for complex logic
- **Consistency:** Maintain language-specific idiomatic patterns even in a mixed-language repo
