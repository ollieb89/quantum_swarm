# Phase 5: Quant Alpha Intelligence - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Centralized technical indicator skill available to any agent in the swarm. Provides RSI, MACD, Bollinger Bands, and ATR through a single registered `calculate_indicators` tool, eliminating duplicate implementations. Does NOT fetch its own data — callers provide the raw series. Timeframe interpretation and data sourcing belong to the calling agent.

</domain>

<decisions>
## Implementation Decisions

### Indicator coverage
- RSI, MACD, Bollinger Bands, and ATR are all formally in Phase 5 scope
- ATR is included here (not deferred to Phase 6) because Phase 6 stop-loss calculation depends on it
- Bollinger Bands always returns `bandwidth` as part of its output — not optional
- `quant_alpha_intelligence.py` is the permanent home for all technical indicators; any future indicator (Stochastic, VWAP, etc.) is added here, not in a new file or phase

### Tool schema & multi-instance
- Tool accepts: `series: {close: [...], high: [...], low: [...]}` + `indicators: [{name, params}, ...]`
- Multiple entries with the same indicator name but different params are valid and return separate labeled results
- Result keys follow `{name}_{period}` convention: `rsi_14`, `rsi_28`, `macd_12_26_9`, `bb_20`
- `full_series: true` flag is part of the public contract — agents can request the full calculated series (not just latest value) for trend analysis
- ATR requires `high` and `low` series in addition to `close`; agents always provide full OHLC when requesting ATR; tool validates and returns `INVALID_INPUT` if high/low missing

### Error handling
- Agents see structured error dicts only — no exceptions propagate through the tool boundary
- Error format: `{"error": {"code": "INSUFFICIENT_DATA", "message": "RSI(14) requires at least 15 data points; received 9."}}`
- Two formal error codes: `INSUFFICIENT_DATA` (series too short), `INVALID_INPUT` (bad params, missing required series, invalid values)
- Batch requests return partial results: each indicator fails or succeeds independently; a failure in one does not cancel others

### Agent integration
- `calculate_indicators` is added explicitly per agent — only MacroAnalyst and QuantModeler currently have it; future agents opt in via code change
- System prompt contract includes one example call per indicator so agents can reason without needing to infer the schema
- RSI always returns a machine-readable `state` field alongside the raw value: `overbought` (>70), `oversold` (<30), `neutral` (30–70)
- No generic confidence score; only indicator-native interpretation fields (RSI state is standard, not novel)

### Safe ranges & precision
- All period parameters validated in range 2–250; requests outside this range return `INVALID_INPUT`
- All numeric output rounded to 8 decimal places for downstream risk calculation precision

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/skills/quant_alpha_intelligence.py`: `TechnicalIndicators` class (RSI via Wilder's EMA smoothing, MACD via EMA, BB with bandwidth, ATR)
- `src/skills/quant_alpha_intelligence.py`: `handle(state)` function for skill registry dispatch
- `src/tools/analyst_tools.py`: `calculate_indicators` @tool wrapping `TechnicalIndicators`; module-level singleton `_indicators = TechnicalIndicators()`
- `src/skills/registry.py`: skill discovery via `SKILL_INTENT` attribute

### Established Patterns
- `@tool` decorator (langchain_core.tools) — consistent with all other analyst tools
- Skill registered via `SKILL_INTENT = "quant-alpha-intelligence"` — L1 progressive disclosure picks it up automatically
- Pure Python math, no LLM dependency — no lazy init needed here
- `TechnicalIndicators` is stateless — safe as module-level singleton

### Integration Points
- `src/graph/agents/analysts.py`: MacroAnalyst and QuantModeler tool lists — where new agents would be added
- `src/skills/registry.py`: auto-discovers the skill on import via `SKILL_INTENT`
- Phase 6 (`src/graph/agents/l3/order_router.py`): calls `calculate_indicators` with ATR request for stop-loss calculation

</code_context>

<specifics>
## Specific Ideas

- "All new indicators go into `quant_alpha_intelligence.py`" — single authoritative home, no splitting across files
- ATR added proactively for Phase 6 dependency rather than having Phase 6 add it mid-flight
- RSI state annotation (`overbought`/`oversold`/`neutral`) kept minimal and indicator-native — no invented confidence scores

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-quant-alpha-intelligence*
*Context gathered: 2026-03-07*
