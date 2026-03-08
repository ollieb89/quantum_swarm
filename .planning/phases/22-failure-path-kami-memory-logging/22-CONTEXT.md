# Phase 22: Failure Path KAMI + Memory Logging - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

When `order_router_node` returns a failure (`execution_result.success != True`), the execution path must still flow through `decision_card_writer -> merit_updater -> memory_writer -> trade_logger` so that KAMI scoring captures failure signals and MEMORY.md records the cycle. Currently `route_after_order_router` sends failures directly to `trade_logger`, bypassing merit and memory — this is gap INT-03.

</domain>

<decisions>
## Implementation Decisions

### Failure Routing Strategy
- **Remove the conditional routing entirely.** Replace `route_after_order_router` conditional branch with a direct edge: `order_router -> decision_card_writer`. All outcomes traverse the same chain.
- **Policy belongs in nodes, not routing.** Each downstream node becomes outcome-aware: it inspects `execution_result.success` and varies behavior accordingly, rather than the graph topology encoding success/failure logic.
- **Graph topology after Phase 22:**
  ```
  order_router -> decision_card_writer -> merit_updater -> memory_writer -> trade_logger
  ```
  Single path for all outcomes. No branching.

### Decision Card for Failures
- **Full failure card** — same card structure as success but with failure reason, attempted instrument, and decision context. Complete MiFID audit trail.
- **Normal audit_ref** — failure cards are first-class audit events. Same hash-chain treatment as success cards. No separate audit stream or prefix.

### Recovery Penalty Signal
- **Only self-induced failures penalise Recovery.** External/infrastructure failures (exchange down, network timeout, venue unavailable) do NOT touch KAMI Recovery.
- **Add `failure_cause` to `execution_result`** — `order_router` classifies the failure cause. `merit_updater` consumes the classification. No error-string parsing.
- **Failure cause taxonomy:**
  - Self-induced: `INVALID_ORDER`, `BAD_PARAMETERS`, `RISK_RULE_VIOLATION`, `INSUFFICIENT_FUNDS_FROM_SIZING`, `UNSUPPORTED_INSTRUMENT`
  - External: `EXCHANGE_DOWN`, `BROKER_API_ERROR`, `NETWORK_TIMEOUT`, `VENUE_UNAVAILABLE`
  - Unknown: neutral/no penalty (fail-open for unclassified causes)
- **Standard Phase 16 Recovery failure value** — no graded penalties. Use the existing canonical failure signal (`0` for error invocation). EMA handles decay naturally.

### MEMORY.md Failure Entries
- **Keep skip-on-no-output rule** — failure changes entry content, not entry eligibility. Only agents with non-None canonical output get entries, consistent with Phase 17.
- **Add `[CYCLE_STATUS:]` field** — new machine-readable marker with values: `success | failed | external_failure`. Placed between `[DRIFT_FLAGS:]` and `[THESIS_SUMMARY:]`.
- **Extract THESIS_SUMMARY normally** — the agent's thesis is valid forensic data regardless of downstream execution failure. CYCLE_STATUS tells the outcome story.
- **Updated MEMORY.md entry format:**
  ```text
  === 2026-03-08T12:34:56Z ===
  [AGENT:] CASSANDRA
  [KAMI_DELTA:] -0.03
  [MERIT_SCORE:] 0.78
  [DRIFT_FLAGS:] none
  [CYCLE_STATUS:] failed
  [THESIS_SUMMARY:] Inflation surprise risk remains underpriced; maintain hawkish bias.
  ```

### Claude's Discretion
- Exact `failure_cause` classification logic inside `order_router_node` (how to map exceptions/errors to the taxonomy)
- Whether `route_after_order_router` function is deleted or kept as dead code with a deprecation comment
- How `decision_card_writer` detects failure (reads `execution_result.success` vs a dedicated state field)
- `[CYCLE_STATUS:]` value for cycles that were aborted before reaching order_router (if applicable)
- Test structure and mocking approach for failure path scenarios

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/graph/orchestrator.py:81-86` — `route_after_order_router()` is the conditional branch to remove. Replace with direct edge at line 347-351.
- `src/graph/orchestrator.py:106` — `decision_card_writer_node()` already handles `decision_card_status: "failed"` for write errors. Extend to handle execution failures.
- `src/graph/nodes/merit_updater.py:76-79` — already has "aborted cycles (no execution_result) are skipped" guard. Extend to handle `execution_result.success == False`.
- `src/graph/nodes/memory_writer.py:271` — `_build_entry()` builds the entry template. Add `[CYCLE_STATUS:]` line here.
- `src/graph/nodes/memory_writer.py:433` — `_write_agent_memory()` checks canonical output. No change needed for skip-on-no-output.

### Established Patterns
- **Non-blocking node failure:** log error, continue cycle (Phase 11 `decision_card_writer` pattern)
- **outcome-aware nodes:** `merit_updater` already reads `execution_result` dict — extend with `failure_cause` field
- **Machine-readable MEMORY fields:** `[FIELD:] value` format with deterministic parsing (Phase 17 locked)
- **Config-driven tunables:** failure cause taxonomy could live in `swarm_config.yaml` but simpler as constants

### Integration Points
- `src/graph/orchestrator.py` — remove `route_after_order_router` conditional, replace with direct edge
- `src/graph/agents/l3/order_router.py` — add `failure_cause` classification to `execution_result` dict
- `src/graph/nodes/merit_updater.py` — handle `execution_result.success == False` with failure_cause-based Recovery signal
- `src/graph/nodes/memory_writer.py:_build_entry()` — add `[CYCLE_STATUS:]` field
- `src/graph/orchestrator.py:decision_card_writer_node()` — handle failure cards with full structure

</code_context>

<specifics>
## Specific Ideas

- "Every router outcome should traverse the same post-router chain; node behavior varies by outcome, not by topology."
- "KAMI should learn from agent-caused failure, not platform-caused failure."
- "Thesis says what the agent thought. Cycle status says what happened to the cycle."
- "Failure changes the content of qualifying MEMORY entries, not which agents qualify for them."
- "If all branches converge immediately and behavior is outcome-aware downstream, remove the branch."
- Recovery penalty uses the existing Phase 16 canonical failure value (resolve 0 vs -1 naming consistently with existing code)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 22-failure-path-kami-memory-logging*
*Context gathered: 2026-03-08*
