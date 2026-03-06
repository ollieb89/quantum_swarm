# Technology Stack

## Backend (Swarm Orchestration)
- **Language:** Python 3.12+
- **Core Framework:** [LangGraph](https://github.com/langchain-ai/langgraph) (Agent orchestration and state management)
- **LLM Integration:** [LangChain](https://github.com/langchain-ai/langchain)
- **Data/Trading:** [Nautilus Trader](https://nautilustrader.io/) (Planned/PoC), `ccxt` (Crypto exchanges), `yfinance` (Simulated data)
- **State/Persistence:** MemorySaver (LangGraph), JSON-based file protocol for cross-agent comms

## Specialized Agent (Dexter)
- **Runtime:** [Bun](https://bun.sh/)
- **Language:** TypeScript (Strict mode)
- **UI:** [Ink](https://github.com/vadimdemedes/ink) (React-based CLI)
- **LLM Integration:** LangChain (JS/TS)
- **Validation:** [Zod](https://zod.dev/)
- **Automation:** [Playwright](https://playwright.dev/) (Web browsing/scraping)

## Infrastructure & Tooling
- **Environment:** `.env` for API key management
- **Dependency Management:** `pip` (Python), `bun install` (TS)
- **Version Control:** Git
- **Communication:** File-based inbox/outbox system (`data/inbox`, `data/outbox`)
