# Research: Phase 9 - Structured Memory Registry

## 1. Objectives
- Implement `MemoryRegistry` class to manage `data/memory_registry.json`.
- Define Pydantic models for `MemoryRule` with strict validation.
- Update `RuleGenerator` to output structured JSON rules.
- Update `LangGraphOrchestrator` to inject only `active` rules.

## 2. Technical Findings

### 2.1 Data Models
- **MemoryRule**:
    - `id`: UUID or human-readable ID (e.g., `mem_001`).
    - `status`: Enum (`proposed`, `active`, `deprecated`, `rejected`).
    - `type`: Enum (`risk_adjustment`, `strategy_preference`, `market_regime`).
    - `condition`: Dict describing when the rule applies.
    - `action`: Dict describing what to do.
    - `evidence`: Dict containing sample size, confidence, etc.

### 2.2 RuleGenerator Update
- Current prompt asks for markdown bullets.
- New prompt must ask for a JSON object matching the `MemoryRule` schema.
- Needs to generate `proposed` status by default.

### 2.3 Persistence Logic
- `MemoryRegistry.add_rule()`: Adds a new rule with `proposed` status.
- `MemoryRegistry.get_active_rules()`: Returns list of rules where `status == "active"`.
- `MemoryRegistry.update_status()`: Handles lifecycle transitions.

## 3. Implementation Strategy
1. **Models**: Create `src/models/memory.py` with Pydantic definitions.
2. **Registry**: Create `src/core/memory_registry.py` for file I/O and logic.
3. **Generator**: Update `src/agents/rule_generator.py` to use the registry.
4. **Orchestrator**: Update `src/graph/orchestrator.py` to use `MemoryRegistry`.

## 4. Risks & Mitigations
- **JSON Corruption**: Manual edits or concurrent writes could corrupt the file. Mitigation: Use atomic writes and validation on load.
- **Prompt Injection**: LLM might generate malformed JSON. Mitigation: Use Pydantic output parsers or robust try/catch blocks.
