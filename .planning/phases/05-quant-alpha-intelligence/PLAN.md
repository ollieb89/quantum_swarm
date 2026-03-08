# Plan: Phase 5 - Quant Alpha Intelligence

Implementation plan for the centralized technical indicator skill.

## 1. Goal
Provide a unified `calculate_indicators` tool that all agents can use to compute RSI, MACD, and Bollinger Bands with strict interface requirements.

## 2. Implementation Steps

### Step 1: Implement the QuantAlphaIntelligence Skill
- **File**: `src/skills/quant_alpha_intelligence.py`
- **Actions**:
    - Define `SKILL_INTENT = "quant-alpha-intelligence"`
    - Implement `TechnicalIndicators` class with:
        - `rsi(prices, period)`
        - `macd(prices, fast, slow, signal)`
        - `bollinger_bands(prices, period, std_dev)`
        - `atr(highs, lows, closes, period)`
    - Implement `handle(state)` function that:
        - Parses `indicator_requests` from state.
        - Validates "safe ranges" (2-250).
        - Returns nested JSON with metadata and precision.
        - Handles `INSUFFICIENT_DATA` and `INVALID_INPUT` errors.
- **Dependencies**: None.

### Step 2: Register the Tool
- **File**: `src/tools/analyst_tools.py`
- **Actions**:
    - Import the `TechnicalIndicators` logic from `src.skills.quant_alpha_intelligence`.
    - Create a `@tool` decorated function `calculate_indicators`.
    - Ensure it accepts a `series` dict and `indicators` list.
- **Dependencies**: Step 1.

### Step 3: Update Agents
- **File**: `src/graph/agents/analysts.py`
- **Actions**:
    - Add `calculate_indicators` to the tool list for `MacroAnalyst` and `QuantModeler`.
    - Update system prompts for both agents to include the new tool's usage and schema.
- **Dependencies**: Step 2.

### Step 4: Verification
- **File**: `tests/test_quant_alpha_intelligence.py`
- **Actions**:
    - Test `TechnicalIndicators` class directly with known data.
    - Test `calculate_indicators` tool with various input scenarios (valid, empty, too short).
    - Test `SkillRegistry` discovery of the new skill.
    - Run a smoke test on the graph to ensure agents can "see" the tool.

## 3. Success Criteria
1. Calling `calculate_indicators` with a price series returns RSI, MACD, and BB values.
2. Skill is discoverable by L1 orchestrator.
3. QuantModeler can invoke the tool and receive structured output.
4. Unit tests pass with 80%+ coverage for indicator logic.

## 4. Rollback Plan
- Revert changes to `src/graph/agents/analysts.py` and `src/tools/analyst_tools.py`.
- Delete `src/skills/quant_alpha_intelligence.py` and `tests/test_quant_alpha_intelligence.py`.
