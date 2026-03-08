# Research: Phase 5 - Quant Alpha Intelligence

## 1. Objectives
- Centralize technical indicator calculations (RSI, MACD, Bollinger Bands) into a single skill.
- Expose the skill as a tool for L2 agents (MacroAnalyst, QuantModeler).
- Ensure strict compliance with the interface requirements in `05-CONTEXT.md`.

## 2. Technical Findings

### 2.1 Current Infrastructure
- **Skill Registry**: `src/skills/registry.py` handles discovery of skills with `SKILL_INTENT` and `handle()`.
- **Existing Indicators**: `src/skills/market_analysis.py` contains a `TechnicalIndicators` class with basic SMA, EMA, RSI, MACD, BB, and ATR implementations.
- **Agent Tools**: `src/tools/analyst_tools.py` defines tools using the `@tool` decorator for LangGraph ReAct agents.
- **Orchestrator**: `src/graph/orchestrator.py` and `src/graph/nodes/l1.py` handle intent classification and routing.

### 2.2 Integration Strategy
- **New Skill**: Create `src/skills/quant_alpha_intelligence.py` to house the centralized logic. This will be more robust than the existing `TechnicalIndicators` in `market_analysis.py`.
- **Tool Exposure**: Add a `calculate_indicators` tool in `src/tools/analyst_tools.py` that delegates to the new skill.
- **Agent Updates**: Add the `calculate_indicators` tool to `MacroAnalyst` and `QuantModeler` in `src/graph/agents/analysts.py`.
- **Prompting**: Update agent system prompts to include the `calculate_indicators` tool contract.

### 2.3 Requirements Compliance (from 05-CONTEXT.md)
- **Safe Ranges**: Implement 2-250 period validation.
- **Multi-Instance**: Support requesting multiple RSI periods in one call.
- **Output**: Nested JSON with metadata (timestamp, series_length, indicator_params).
- **Precision**: 8 decimal places for all values.
- **Errors**: Structured errors (e.g., `INSUFFICIENT_DATA`) for invalid inputs.

## 3. Implementation Details

### 3.1 Indicator Specifications
- **RSI**: Relative Strength Index (Standard Wilde's / EMA based).
- **MACD**: Moving Average Convergence Divergence (Fast, Slow, Signal).
- **Bollinger Bands**: SMA + N*Stdev.
- **ATR**: Average True Range (High, Low, Close series). *Added for Phase 6 dependency.*

### 3.2 Tool Schema
```python
@tool
def calculate_indicators(series: Dict[str, List[float]], indicators: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate technical indicators for provided price series.
    series: {"close": [...], "high": [...], "low": [...]}
    indicators: [{"name": "rsi", "params": {"period": 14}}, ...]
    """
```

## 4. Risks & Mitigations
- **Data Quality**: Agents might provide malformed series. Mitigation: Strict validation in the skill.
- **Performance**: Large series or too many indicators could slow down agents. Mitigation: Enforce "safe range" and max series length.
- **Duplication**: Ensure `market_analysis.py` indicators are eventually deprecated or refactored to use the new centralized skill.
