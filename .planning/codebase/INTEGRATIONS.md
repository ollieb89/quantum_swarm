# Integrations

## LLM Providers
- **OpenAI:** Primary reasoning engine (when active)
- **Anthropic:** Preferred for research/caching (Claude Haiku/Sonnet)
- **Google:** Gemini 3 (Validated active for deep research)
- **Local:** Ollama (Mistral/Llama3 fallback)

## Financial Data
- **Financial Datasets API:** Direct access to fundamentals, SEC filings, and analyst targets
- **SEC EDGAR:** Integrated via Dexter's `read_filings` tool
- **Yahoo Finance:** Used for baseline market data and simulations

## External Tools
- **Exa Search:** Neural search integration for web discovery
- **Tavily:** Search fallback
- **Playwright:** Headless browser for interactive data extraction

## Internal Bridges
- **Python-to-Dexter CLI:** `src/agents/dexter/run-query.ts` bridge allowing Python orchestrator to delegate research to TS agent
