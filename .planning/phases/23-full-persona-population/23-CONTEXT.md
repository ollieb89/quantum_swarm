# Phase 23: Full Persona Population - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Populate all 4 skeleton agents (MOMENTUM, CASSANDRA, SIGMA, GUARDIAN) with fully authored HEXACO-6 diverse personalities and YAML drift_guard blocks. AXIOM is the fully authored reference — skeletons must match its depth. This is a content authoring phase with zero code dependencies. Existing USER.md and MEMORY.md files are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Persona depth & file structure
- All 4 agents match AXIOM's depth uniformly — no lighter treatment for any agent
- SOUL.md: ~450-550 words with multi-paragraph Core Beliefs, detailed Voice section, explicit Non-Goals
- IDENTITY.md: ~220-280 words — archetype, swarm role, comparative advantage, relation to peers
- AGENTS.md: ~300 words — full JSON key specs, 5+ decision rules, detailed multi-step workflow
- Existing USER.md and MEMORY.md files left untouched (out of scope)

### Voice differentiation
- Maximally distinct voices — each agent immediately recognizable by register, cadence, reasoning structure, and vocabulary
- Not theatrical, but like different research desks in the same institution
- MOMENTUM: punchy, catalyst-focused, directional conviction
- CASSANDRA: forensic, skeptical, risk-anchored specificity
- SIGMA: mathematical, precise, statistics-lead
- GUARDIAN: procedural, firm, rule-driven, non-negotiable

### HEXACO-6 profiles
- Scores stored as ```yaml hexaco_6: ... ``` block in SOUL.md alongside drift_guard YAML
- Scale: 0.0 to 1.0 normalized floats (matches existing score conventions)
- Design approach: archetype-realistic first, then verify pairwise distance constraint
- Minimum pairwise Euclidean distance: >1.0 (recalibrated from >3.0 which was impossible on 0.0-1.0 scale; max possible distance is sqrt(6) ~= 2.45, so >1.0 is ~41% of max)
- AXIOM also gets a HEXACO-6 block added to its SOUL.md (all 5 agents need profiles for pairwise distance calculation)
- Update ROADMAP.md success criterion #3 to reflect >1.0 threshold on normalized scale

### Drift guard rules
- 2-3 rules per agent, focused on each archetype's primary and secondary failure modes
- Mix rule types per agent (keyword_ratio, keyword_any, regex) — use whichever types best fit the failure mode
- Keep AXIOM's existing 3 drift_guard rules unchanged — treat as tested reference
- All rules must follow existing schema: drift_guard.version, drift_guard.rules[] with flag_id, type, and type-specific fields
- Rules must be parseable by parse_drift_guard_yaml() (fail-soft, but should not trigger warnings)

### Content authoring approach
- Claude authors all 4 personas autonomously using AXIOM as template for structural depth
- Batch review: all 4 reviewed together at the end before committing
- No specific personality references or real-world investor inspirations — full creative discretion
- Goal: institutional-grade archetypes with maximally distinct reasoning styles, not personality caricatures

### Claude's Discretion
- Exact HEXACO-6 score values for each agent (within archetype-realism and >1.0 distance constraints)
- Specific drift_guard keywords, patterns, and thresholds per agent
- Core Beliefs content for each agent
- AGENTS.md decision rule specifics and workflow step details
- Whether IDENTITY.md needs a failure-modes subsection

</decisions>

<specifics>
## Specific Ideas

- Agents should feel like authentic research desk voices, not fictional characters
- The swarm should produce natural disagreements from distinct cognitive frames — each agent interprets the same market signal differently
- Cognitive orthogonality is the goal: distinct analytical lenses, distinct debate behaviors, distinct evidence preferences

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/core/soul_loader.py`: AgentSoul frozen dataclass, load_soul() with lru_cache — reads IDENTITY.md, SOUL.md, AGENTS.md per agent
- `src/core/drift_eval.py`: parse_drift_guard_yaml() parses YAML drift_guard blocks from SOUL.md text, supports keyword_ratio, keyword_any, regex rule types
- `src/core/souls/macro_analyst/SOUL.md`: AXIOM is the fully authored reference (~500 words, 3 drift_guard rules with YAML block)
- Skeleton SOUL.md files exist for all 4 agents (~150 words each, prose only, no YAML)
- Skeleton IDENTITY.md files exist (~150 words each)
- Skeleton AGENTS.md files exist (~100 words each)

### Established Patterns
- drift_guard YAML block format: version 1, rules list with flag_id, type, and type-specific fields (include/threshold for keyword_ratio, include for keyword_any, pattern for regex)
- Soul loader is fail-soft on drift_guard parse errors (logs warning, continues)
- AUDIT_EXCLUDED_FIELDS prevents soul content from entering MiFID II hash chain
- warmup_soul_cache() called at graph creation to validate all souls load

### Integration Points
- warmup_soul_cache() will validate all 5 agents load without errors after population
- ARS drift auditor will use new drift_guard rules for per-agent drift detection
- Soul-Sync handshake exchanges truncated soul summaries before debate (richer souls = richer summaries)
- DebateSynthesizer uses KAMI merit-weighted consensus — distinct voices strengthen merit differentiation

</code_context>

<deferred>
## Deferred Ideas

- HEXACO-6 automated diversity enforcement gate (runtime validation) — noted in PROJECT.md out-of-scope, deferred
- PersonaScore 5D LLM-as-Judge fidelity evaluation pipeline (SOUL-09) — future requirement
- Review and align AXIOM's drift_guard rules with new agent rules — defer to post-population consistency pass

</deferred>

---

*Phase: 23-full-persona-population*
*Context gathered: 2026-03-09*
