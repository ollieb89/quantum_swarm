# Phase 30: KAMI Weight Rebalance + Token Tracking - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Redistribute KAMI merit weights so Accuracy (currently 30% inert at 0.5) drops to ~8% and Fidelity (now fed by continuous PersonaScore) rises to ~32%. Simultaneously add per-agent per-cycle token usage tracking from BudgetManager through CycleSnapshot to the replay CLI. No new KAMI dimensions, no new CLI commands.

</domain>

<decisions>
## Implementation Decisions

### Weight Distribution
- Target: alpha (Accuracy) = 0.08, delta (Fidelity) = 0.32
- Remaining 60% split between beta (Recovery) and gamma (Consensus) — proportional scaling of current 0.35/0.25 ratio gives beta ~0.35, gamma ~0.25 (unchanged)
- Weights must still sum to 1.0
- Change is a constant update in `src/core/kami.py` DEFAULT_WEIGHTS

### EMA Absorption
- No score reset — existing merit scores continue with new weights applied at next composite calculation
- EMA naturally absorbs the weight change over subsequent cycles (scores will drift toward new equilibrium)
- No migration script needed — the composite is recalculated each cycle from individual dimension scores which are unchanged

### Token Tracking Architecture
- BudgetManager is the single authoritative source (REQUIREMENTS OBS-05)
- Extend BudgetManager.summary() to include per-agent breakdown, not just session aggregates
- Agent nodes already call `budget.record_usage()` with usage_metadata — need to tag calls with agent_id
- Per-agent tracking: `{agent_id: {input_tokens, output_tokens, usd_cost}}` dict added to BudgetManager

### CycleSnapshot Integration
- Add `token_usage: Optional[dict]` field to CycleSnapshot (excluded from audit hash, like persona_scores)
- CycleRunner populates from BudgetManager.per_agent_summary() after graph run completes
- Persisted to PostgreSQL cycle_snapshots and filesystem snapshot.json

### Replay CLI Display
- Show token usage as a summary line in cycle show view: "Tokens: 12,450 ($0.0032) | AXIOM: 3,200 | MOMENTUM: 2,800 | ..."
- No separate panel — compact inline format matching existing replay style

### Claude's Discretion
- Exact replay CLI formatting and column widths
- Whether to show tokens in the cycle list view (probably too noisy)
- BudgetManager internal data structure for per-agent tracking
- Test structure and naming

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BudgetManager` (`src/core/budget_manager.py`): Thread-safe token tracker with `record_usage()`, `summary()`, pricing lookup — extend for per-agent breakdown
- `CycleSnapshot` (`src/core/cycle_snapshot.py`): Pydantic model with `persona_scores` pattern to follow for `token_usage`
- `AUDIT_EXCLUDED_FIELDS` (`src/core/audit_logger.py`): Already excludes `persona_scores` — add `token_usage`
- Replay CLI handlers (`src/main.py`): `handle_show()` renders cycle step-through — add token line

### Established Patterns
- Agent nodes pass `budget` via graph state and call `budget.record_usage(input_tokens, output_tokens)` after LLM calls
- `usage_metadata` on LangChain AIMessage provides token counts (analysts.py:155, researchers.py:196)
- CycleRunner resets budget counters at cycle start (`budget.reset_session()`)

### Integration Points
- `src/core/kami.py:28` — DEFAULT_WEIGHTS dict (direct constant change)
- `src/core/budget_manager.py` — Add per-agent recording + per_agent_summary()
- `src/core/cycle_snapshot.py` — Add token_usage field
- `src/core/cycle_runner.py` — Populate token_usage from BudgetManager after graph run
- `src/core/audit_logger.py` — Add token_usage to AUDIT_EXCLUDED_FIELDS
- `src/main.py` — Render token data in handle_show()
- Agent nodes (`analysts.py`, `researchers.py`) — Pass agent_id to record_usage()

</code_context>

<specifics>
## Specific Ideas

No specific requirements — implementation follows success criteria and existing patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 30-kami-weight-rebalance-token-tracking*
*Context gathered: 2026-03-10*
