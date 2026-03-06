# Testing Standards

## Python
- **Runner:** `pytest`
- **Location:** `tests/` directory
- **Naming:** `test_*.py`
- **Patterns:**
  - Mocking external APIs (LLMs, Exchanges) is mandatory for baseline tests
  - Integration tests use the `--mode test` flag in `main.py`
  - Current configuration in `conftest.py` handles workspace root resolution

## TypeScript/Bun
- **Runner:** `bun test`
- **Location:** Co-located with source code (`*.test.ts`)
- **Framework:** Native Bun testing library (compatible with Jest syntax)
- **Evals:** Specialized evaluation runner in `src/evals/` using LangSmith for LLM-as-a-judge scoring

## Verification Flow
1.  **Unit Tests:** Verify individual agent tools and utilities
2.  **Smoke Checks:** Non-interactive query execution (`run-query.ts`)
3.  **Graph Simulation:** Running the LangGraph with simulated data fetchers
