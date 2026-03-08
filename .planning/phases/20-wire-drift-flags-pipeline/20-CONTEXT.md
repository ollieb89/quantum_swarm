# Phase 20: Wire Drift Flags Pipeline - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the hardcoded `[DRIFT_FLAGS:] none` in `memory_writer._build_entry()` with actual drift evaluation. Each agent's SOUL.md Drift Guard section contains machine-readable rules; `memory_writer` loads these via `soul_loader`, runs a deterministic evaluator against the agent's canonical output, and writes the resulting flag IDs to the MEMORY.md entry. This unblocks the DRIFT_STREAK evolution trigger (EVOL-02) and the ARS `drift_flag_frequency` metric (ARS-01). No LLM calls. No new dependencies.

</domain>

<decisions>
## Implementation Decisions

### Drift Evaluation Method
- **Structured Drift Guard**: each agent's `## Drift Guard` section in SOUL.md contains a fenced YAML block with machine-readable rules below the existing prose
- `soul_loader` parses the YAML block into `AgentSoul.drift_rules` (tuple of frozen `DriftRule` dataclasses) at load time with validation (fail-fast on malformed rules)
- `memory_writer` calls `load_soul(agent_id)` and evaluates `soul.drift_rules` against the canonical output — no file I/O, no LLM call
- **No LLM in control paths** — consistent with ARS and Agent Church design

### Rule Types (Three Supported)
- **`keyword_ratio`**: count matching terms / total tokens in canonical output; flag if ratio >= threshold
- **`keyword_any`**: flag if ANY term from the `include` list appears in the canonical output
- **`regex`**: flag if compiled pattern matches anywhere in the canonical output
- Rule type set is `{"keyword_ratio", "keyword_any", "regex"}` — extensible later without breaking existing rules

### SOUL.md Drift Guard Format
- Prose Drift Guard text remains for human context
- Machine-readable YAML fenced block added below prose within the same `## Drift Guard` H2 section
- Example structure:
  ```yaml
  drift_guard:
    version: 1
    rules:
      - flag_id: recency_bias
        type: keyword_ratio
        include: ["today", "latest", "just released", "this morning"]
        threshold: 0.08
      - flag_id: certainty_overreach
        type: regex
        pattern: "\\b(certainly|obviously|guaranteed)\\b"
      - flag_id: narrative_capture
        type: keyword_any
        include: ["consensus expects", "markets have priced in", "widely anticipated"]
  ```
- Preserves Agent Church H2-scoped editing — drift rules are part of the section replacement unit

### AgentSoul Schema Extension
- New frozen dataclass `DriftRule`: `flag_id: str`, `type: str`, `pattern: str | None`, `include: tuple[str, ...]`, `threshold: float | None`
- `AgentSoul` gets new field: `drift_rules: tuple[DriftRule, ...] = ()`
- Validation at load time: unique `flag_id` per agent, `type` in supported set, regex compiles, `keyword_ratio` requires `threshold`
- Agents with no YAML block get `drift_rules = ()` — empty tuple, not an error

### Flag Vocabulary & Semantics
- **Per-agent flag IDs defined in SOUL.md** — no global registry or enum
- Flag IDs are slug-like identifiers (lowercase, underscores): `recency_bias`, `catastrophism_without_evidence`, etc.
- Validated for uniqueness within each agent's rules at load time
- DRIFT_STREAK and ARS treat flags as **non-empty signal** — they count presence, not semantic categories
- Comma-separated serialization in MEMORY.md: `[DRIFT_FLAGS:] recency_bias,narrative_capture` or `[DRIFT_FLAGS:] none`
- Matches Phase 17 spec and existing ARS `_extract_drift_flags()` parser — zero migration

### Failure & Fallback Behavior
- **Three-state model**: `none` (clean evaluation, no drift) / `flag_ids` (drift detected) / `evaluation_failed` (broken rules)
- **No drift_guard YAML block** (skeleton agents with prose-only Drift Guard): write `[DRIFT_FLAGS:] none` — intentional absence, not failure
- **YAML present but malformed / regex won't compile / schema invalid**: write `[DRIFT_FLAGS:] evaluation_failed`
- ARS `drift_flag_frequency` treats `evaluation_failed` as non-empty (conservative safety posture)
- DRIFT_STREAK treats `evaluation_failed` as non-empty — persistent evaluator failures escalate
- `memory_writer` logs WARNING on evaluation_failed, does not halt cycle (non-blocking pattern)

### Evaluation Scope & Inputs
- Drift rules evaluate against the **full per-agent canonical output field** (same source as THESIS_SUMMARY, pre-truncation)
- Canonical output field map (from Phase 17): AXIOM→macro_report, MOMENTUM→bullish_thesis, CASSANDRA→bearish_thesis, SIGMA→quant_proposal, GUARDIAN→risk_approval
- **Case-insensitive matching** for `keyword_ratio` and `keyword_any` (lowercase text before matching)
- `regex` rules run against **original text** (can use `(?i)` flag explicitly if needed)
- No historical window or trend detection — single-output evaluation per cycle

### Claude's Discretion
- Exact drift rule content for each of the 5 agents' SOUL.md Drift Guard YAML blocks
- `DriftRule` dataclass field ordering and any additional validation helpers
- Tokenization approach for `keyword_ratio` (simple whitespace split vs more sophisticated)
- How `_build_entry()` signature changes to accept drift flags (parameter vs computed internally)
- Test structure and organization for the drift evaluator

</decisions>

<specifics>
## Specific Ideas

- The evaluator is ~40 lines: tokenize, run keyword_any, run regex, run keyword_ratio, emit list of flag_ids
- AXIOM is the only fully-authored soul — it should get real drift rules first; skeleton agents get rules when they're fully authored
- AXIOM's Drift Guard prose already describes two triggers: "recency bias" (reliance on last 3-6 months of data) and "narrative capture" (retelling financial press consensus) — convert these to structured rules
- `evaluation_failed` sentinel must be distinct from any valid flag_id — enforce this at validation time
- The existing `_extract_drift_flags()` in memory_writer (line 310) already parses the comma-separated format — reuse it

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/core/soul_loader.py` — `load_soul()` with `@lru_cache`, `AgentSoul` frozen dataclass, YAML parsing already needed
- `src/graph/nodes/memory_writer.py:270` — `_build_entry()` hardcodes `[DRIFT_FLAGS:] none` — the exact line to replace
- `src/graph/nodes/memory_writer.py:310` — `_extract_drift_flags()` already parses comma-separated drift flags for DRIFT_STREAK trigger
- `src/core/ars_auditor.py:160` — `_compute_drift_flag_frequency()` already counts non-empty drift flags — just needs real data
- `src/core/souls/macro_analyst/SOUL.md:11` — AXIOM's existing prose Drift Guard section to receive YAML block

### Established Patterns
- **Frozen dataclass + lru_cache**: AgentSoul is frozen for hashability and concurrent read safety
- **Non-blocking node failure**: log error and continue cycle (Phase 11 decision_card_writer pattern)
- **Config-driven tunables**: drift thresholds live in SOUL.md per-agent, not swarm_config.yaml
- **Comma-separated field values**: established in Phase 17 MEMORY.md format

### Integration Points
- `src/core/soul_loader.py` — extend `_parse_soul()` to extract YAML fenced block from `## Drift Guard`, add `drift_rules` field to `AgentSoul`
- `src/graph/nodes/memory_writer.py:_build_entry()` — accept drift_flags parameter or compute internally
- `src/core/souls/macro_analyst/SOUL.md` — add YAML block to `## Drift Guard` section
- 4 skeleton SOUL.md files — optionally add YAML blocks (or leave prose-only for now)

</code_context>

<deferred>
## Deferred Ideas

- Drift rules for skeleton agents (MOMENTUM, CASSANDRA, SIGMA, GUARDIAN) — author when their SOUL.md files are fully populated
- `keyword_absent` rule type (detect missing expected vocabulary) — add only if a real use case emerges
- Historical trend detection in drift evaluation (last N entries) — single-output evaluation is sufficient for v1.3
- Cross-agent drift correlation (e.g., all agents drifting in same direction) — future ARS enhancement
- Adaptive thresholds based on market regime — future phase

</deferred>

---

*Phase: 20-wire-drift-flags-pipeline*
*Context gathered: 2026-03-08*
