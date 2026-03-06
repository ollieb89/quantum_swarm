# Phase 5: Quant Alpha Intelligence - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Register a single `quant-alpha-intelligence` skill that any agent in the swarm can call to compute RSI, MACD, Bollinger Bands, and ATR — eliminating duplicate implementations. Phase 5 delivers the skill module and its registration. QuantModeler integration is in scope. Stop-loss logic that consumes ATR is Phase 6.

</domain>

<decisions>
## Implementation Decisions

### Module architecture
- Create a new standalone `src/skills/quant_alpha.py` with `SKILL_INTENT = "quant-alpha-intelligence"`
- Do NOT wrap or import from `market_analysis.py` — fully self-contained
- Remove `TechnicalIndicators` class from `market_analysis.py` (it is only used internally there); update `generate_market_report()` in `market_analysis.py` to import from `quant_alpha` instead
- `market_analysis.py` retains all its other classes (MarketHours, PatternRecognition, MarketEnvironment, etc.) unchanged

### Indicator accuracy — MACD
- Implement proper EMA-of-MACD-line signal line (9-period EMA of the MACD line, NOT simplified)
- Histogram = MACD line - signal line (will be non-zero)
- Minimum data required: raise `ValueError` with clear message if fewer prices than needed (e.g. `"Need at least 50 prices for reliable MACD"`)
- Output dict: `{macd: float, signal: float, histogram: float, trend: "bullish"|"bearish"}`

### Indicator accuracy — RSI, Bollinger Bands
- RSI: raise `ValueError` if fewer than `period + 1` prices (no silent fallback to 50.0)
- Bollinger Bands: raise `ValueError` if fewer than `period` prices

### ATR — included in Phase 5
- ATR is included in Phase 5 (not deferred to Phase 6)
- Input: `{highs: List[float], lows: List[float], closes: List[float], period: int = 14}`
- Output: `{atr: float, period: int, suggested_stop_distance: float}` where `suggested_stop_distance = 1.5 * atr`
- ATR uses full True Range formula: TR = max(high-low, |high-prev_close|, |low-prev_close|)
- Raise `ValueError` if fewer than `period + 1` candles

### Skill registry integration
- `quant_alpha.py` exposes `SKILL_INTENT = "quant-alpha-intelligence"` and `handle(state: dict) -> dict`
- `handle()` reads `state["prices"]` for close-price indicators and `state["ohlcv"]` for ATR
- Add `"quant-alpha-intelligence"` to `quant_modeler.skills` list in `config/swarm_config.yaml`
- SkillRegistry.discover() auto-discovers via the module scan (no manual registration needed)

### QuantModeler tool interface
- Add a new `@tool`-decorated function `compute_indicators(prices: list[float], indicators: list[str]) -> dict` in `src/tools/analyst_tools.py`
- This tool is added to QuantModeler's `tools=[]` list alongside `fetch_market_data` and `run_backtest`
- The tool internally calls `quant_alpha` functions directly (not via skill registry routing)
- For ATR, a separate `@tool` `compute_atr(highs: list[float], lows: list[float], closes: list[float]) -> dict`

### Claude's Discretion
- Exact EMA seeding strategy (first value as seed vs Wilder's smoothing)
- Whether to expose `sma()` and `ema()` as public functions in quant_alpha.py
- Internal helper structure within quant_alpha.py
- Docstring depth and parameter validation detail

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/skills/market_analysis.py` → `TechnicalIndicators`: Has working RSI, Bollinger Bands, ATR, EMA, SMA implementations (good reference). MACD signal line is broken (simplified). Will be removed from this file and superseded by quant_alpha.py.
- `src/skills/registry.py` → `SkillRegistry`: Auto-discovers `SKILL_INTENT + handle()` from all modules in `src/skills/`. No changes needed.
- `src/tools/analyst_tools.py` → `fetch_market_data`, `run_backtest`: Pattern to follow for new `@tool` functions (LangChain `@tool` decorator, plain dict return).

### Established Patterns
- Skill registry: module exports `SKILL_INTENT: str` + `handle(state: dict) -> dict`. Scanned at startup.
- QuantModeler tools: `@tool`-decorated functions passed in `tools=[]` to `create_react_agent()`. Returns plain dicts the LLM reasons over.
- Lazy LLM init: required for all module-level LLM instances (no LLM needed for quant_alpha — pure math).
- Error handling: `ValueError` with clear messages (not silent fallbacks).

### Integration Points
- `src/graph/agents/analysts.py` → `QuantModeler` node: add new tools to its `tools=[]` list
- `src/skills/market_analysis.py` → `generate_market_report()`: update to call `quant_alpha` functions after `TechnicalIndicators` is removed
- `config/swarm_config.yaml` → `agents.quant_modeler.skills`: add `"quant-alpha-intelligence"`

</code_context>

<specifics>
## Specific Ideas

- ATR `suggested_stop_distance = 1.5 * atr` — multiplier explicitly decided (1.5x)
- Raise `ValueError` (not silent fallback) for all insufficient-data cases
- MACD must produce non-zero histograms — test against reference values is explicit in success criteria

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-quant-alpha-intelligence*
*Context gathered: 2026-03-06*
