# Phase 23: Full Persona Population - Research

**Researched:** 2026-03-09
**Domain:** Content authoring (SOUL.md, IDENTITY.md, AGENTS.md) + HEXACO-6 personality profiles + drift_guard YAML
**Confidence:** HIGH

## Summary

Phase 23 is a pure content authoring phase with zero code dependencies. Four skeleton agents (MOMENTUM/bullish_researcher, CASSANDRA/bearish_researcher, SIGMA/quant_modeler, GUARDIAN/risk_manager) must be expanded from ~150-word skeletons to ~450-550-word fully authored personas matching AXIOM/macro_analyst's depth. Additionally, all 5 agents (including AXIOM) need HEXACO-6 personality profile YAML blocks, and the 4 skeleton agents need drift_guard YAML blocks added to their SOUL.md files.

The existing infrastructure is fully mature: `soul_loader.py` loads all three files per agent, `drift_eval.py` parses YAML drift_guard blocks with strict validation (duplicate flag_ids, unknown types, invalid regex all raise ValueError), and `warmup_soul_cache()` validates all 5 agents load at graph creation time. The test suite (`test_persona_content.py`, `test_drift_eval.py`, `test_soul_loader.py`) provides coverage for structural validation. The only work is authoring content that conforms to established schemas.

**Primary recommendation:** Author all 4 agents in a single batch using AXIOM as the structural template, then add HEXACO-6 YAML blocks to all 5 agents, verify pairwise distances mathematically, and validate all drift_guard blocks parse without errors.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- All 4 agents match AXIOM's depth uniformly -- no lighter treatment for any agent
- SOUL.md: ~450-550 words with multi-paragraph Core Beliefs, detailed Voice section, explicit Non-Goals
- IDENTITY.md: ~220-280 words -- archetype, swarm role, comparative advantage, relation to peers
- AGENTS.md: ~300 words -- full JSON key specs, 5+ decision rules, detailed multi-step workflow
- Existing USER.md and MEMORY.md files left untouched (out of scope)
- Maximally distinct voices -- each agent immediately recognizable by register, cadence, reasoning structure, and vocabulary
- Not theatrical, but like different research desks in the same institution
- MOMENTUM: punchy, catalyst-focused, directional conviction
- CASSANDRA: forensic, skeptical, risk-anchored specificity
- SIGMA: mathematical, precise, statistics-lead
- GUARDIAN: procedural, firm, rule-driven, non-negotiable
- HEXACO-6 scores stored as yaml block in SOUL.md alongside drift_guard YAML
- Scale: 0.0 to 1.0 normalized floats
- Design approach: archetype-realistic first, then verify pairwise distance constraint
- Minimum pairwise Euclidean distance: >1.0 (recalibrated from >3.0; max possible sqrt(6) ~= 2.45, so >1.0 is ~41% of max)
- AXIOM also gets a HEXACO-6 block added to its SOUL.md (all 5 agents need profiles)
- Update ROADMAP.md success criterion #3 to reflect >1.0 threshold on normalized scale
- 2-3 drift_guard rules per agent, focused on primary and secondary failure modes
- Mix rule types per agent (keyword_ratio, keyword_any, regex) -- use whichever best fit the failure mode
- Keep AXIOM's existing 3 drift_guard rules unchanged -- treat as tested reference
- All rules must follow existing schema: drift_guard.version, drift_guard.rules[] with flag_id, type, and type-specific fields
- Rules must be parseable by parse_drift_guard_yaml() (fail-soft, but should not trigger warnings)
- Claude authors all 4 personas autonomously using AXIOM as template for structural depth
- Batch review: all 4 reviewed together at the end before committing
- No specific personality references or real-world investor inspirations -- full creative discretion
- Goal: institutional-grade archetypes with maximally distinct reasoning styles, not personality caricatures

### Claude's Discretion
- Exact HEXACO-6 score values for each agent (within archetype-realism and >1.0 distance constraints)
- Specific drift_guard keywords, patterns, and thresholds per agent
- Core Beliefs content for each agent
- AGENTS.md decision rule specifics and workflow step details
- Whether IDENTITY.md needs a failure-modes subsection

### Deferred Ideas (OUT OF SCOPE)
- HEXACO-6 automated diversity enforcement gate (runtime validation) -- noted in PROJECT.md, deferred
- PersonaScore 5D LLM-as-Judge fidelity evaluation pipeline (SOUL-09) -- future requirement
- Review and align AXIOM's drift_guard rules with new agent rules -- defer to post-population consistency pass
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PERS-01 | User can observe MOMENTUM (BullishResearcher) reasoning with distinct price/flow personality | AXIOM template structure; Voice differentiation guidelines; skeleton already has directional foundation |
| PERS-02 | User can observe CASSANDRA (BearishResearcher) reasoning with distinct tail-risk personality | AXIOM template structure; Voice differentiation guidelines; skeleton already has risk-first foundation |
| PERS-03 | User can observe SIGMA (QuantModeler) reasoning with distinct quantitative personality | AXIOM template structure; Voice differentiation guidelines; skeleton already has quantitative foundation |
| PERS-04 | User can observe GUARDIAN (RiskManager) reasoning with distinct risk-control personality | AXIOM template structure; Voice differentiation guidelines; skeleton already has constraint-enforcement foundation |
| PERS-05 | Each persona has HEXACO-6 diversity profile with minimum pairwise distance >1.0 | HEXACO-6 dimension definitions; distance calculation method; 0.0-1.0 scale constraints |
| PERS-06 | Each persona has functional YAML drift_guard block enabling ARS drift detection | drift_eval.py schema; parse_drift_guard_yaml() validation rules; AXIOM reference rules |
</phase_requirements>

## Standard Stack

This phase involves no new libraries or dependencies. All work is content authoring within existing file structures.

### Core
| Component | Location | Purpose | Why Standard |
|-----------|----------|---------|--------------|
| SOUL.md | `src/core/souls/{agent}/SOUL.md` | Core Beliefs, Drift Guard (prose + YAML), Voice, Non-Goals | Loaded by soul_loader.py, parsed by drift_eval.py |
| IDENTITY.md | `src/core/souls/{agent}/IDENTITY.md` | Identity, Archetype, Role in Swarm | Loaded by soul_loader.py, H1 extracted for active_persona |
| AGENTS.md | `src/core/souls/{agent}/AGENTS.md` | Output Contract, Decision Rules, Workflow | Loaded by soul_loader.py, defines agent behavior contract |

### Agent Directory Mapping
| Persona Name | Directory | Agent Role |
|-------------|-----------|------------|
| AXIOM | `src/core/souls/macro_analyst/` | L2 MacroAnalyst (fully authored reference) |
| MOMENTUM | `src/core/souls/bullish_researcher/` | L2 BullishResearcher (skeleton -> full) |
| CASSANDRA | `src/core/souls/bearish_researcher/` | L2 BearishResearcher (skeleton -> full) |
| SIGMA | `src/core/souls/quant_modeler/` | L2 QuantModeler (skeleton -> full) |
| GUARDIAN | `src/core/souls/risk_manager/` | L2 RiskManager (skeleton -> full) |

## Architecture Patterns

### AXIOM Reference Template (SOUL.md Structure)

The fully authored AXIOM SOUL.md establishes the structural pattern all 4 agents must match:

```markdown
# {PERSONA_NAME} -- Soul

## Core Beliefs
[Multi-paragraph. 3+ paragraphs establishing the agent's analytical philosophy,
 what it prioritizes, and WHY its lens matters. ~150-200 words.]

## Drift Guard
[1-2 paragraphs of prose describing primary and secondary drift triggers,
 explaining WHAT constitutes drift for this specific agent and WHY it matters.]

```yaml
drift_guard:
  version: 1
  rules:
    - flag_id: {primary_failure_mode}
      type: {keyword_ratio|keyword_any|regex}
      {type-specific fields}
    - flag_id: {secondary_failure_mode}
      type: {keyword_ratio|keyword_any|regex}
      {type-specific fields}
```

## Voice
[1-2 paragraphs describing register, sentence structure, vocabulary preferences,
 what makes this agent's output immediately recognizable. ~80-120 words.]

## Non-Goals
[2-3 paragraphs explicitly stating what this agent does NOT do,
 delegating to specific other agents. ~80-120 words.]
```

### AXIOM Reference Template (IDENTITY.md Structure)

```markdown
# {PERSONA_NAME}

## Identity
[1 paragraph establishing WHO this agent is. ~60-80 words.]

## Archetype
[1 paragraph establishing the professional archetype. ~60-80 words.]

## Role in Swarm
[1 paragraph establishing position in the swarm hierarchy and
 relationship to other agents. ~60-80 words.]
```

### AXIOM Reference Template (AGENTS.md Structure)

```markdown
# {PERSONA_NAME} -- Agents Contract

## Output Contract
[Explicit JSON keys with types. Every key listed with description.]

## Decision Rules
[Numbered list. 5+ rules. Each rule is a conditional constraint
 on output behavior. Rules reference specific output keys.]

## Workflow
[Numbered steps. 5+ steps. Sequential execution order from
 data gathering through to output construction.]
```

### HEXACO-6 YAML Block Format

The HEXACO-6 block is added to SOUL.md as a separate fenced YAML block (NOT inside the drift_guard block). Place it after the Non-Goals section:

```markdown
## Personality Profile

```yaml
hexaco_6:
  honesty_humility: 0.XX
  emotionality: 0.XX
  extraversion: 0.XX
  agreeableness: 0.XX
  conscientiousness: 0.XX
  openness: 0.XX
```
```

### HEXACO-6 Dimension Definitions for Financial Archetypes

| Dimension | Low (0.0) | High (1.0) | Relevance to Trading |
|-----------|-----------|------------|---------------------|
| Honesty-Humility | Self-promoting, overconfident | Modest, transparent about limitations | How openly agent admits uncertainty |
| Emotionality | Detached, stoic under stress | Reactive, anxiety-sensitive | Response to drawdowns and tail events |
| Extraversion | Reserved, independent analysis | Bold, assertive, conviction-forward | How forcefully agent advocates its view |
| Agreeableness | Confrontational, contrarian | Cooperative, consensus-seeking | Debate behavior in adversarial setting |
| Conscientiousness | Flexible, adaptive, loose process | Rigid, rule-bound, methodical | Process adherence vs. creative latitude |
| Openness | Conventional, precedent-bound | Unconventional, novel frameworks | Willingness to adopt new analytical approaches |

### Pairwise Distance Calculation

Euclidean distance in 6D space between agents A and B:

```
d(A, B) = sqrt(sum((A_i - B_i)^2 for i in 1..6))
```

With 5 agents, there are C(5,2) = 10 pairwise distances. ALL 10 must exceed 1.0.

Maximum possible distance on [0.0, 1.0]^6 scale: sqrt(6) = 2.449

Minimum required: >1.0 (~41% of max)

Design strategy: Start with archetype-realistic profiles, compute all 10 distances, adjust outlier dimensions if any pair falls below 1.0. The constraint is achievable because the 5 agents have fundamentally different cognitive orientations.

### Anti-Patterns to Avoid

- **Personality caricature:** Making agents sound like fictional characters rather than institutional professionals. Each should read like a different research desk, not a different character in a novel.
- **Voice convergence:** Using similar sentence structures, vocabulary, and reasoning patterns across agents. If you can swap two agents' outputs and nobody notices, the voices are not distinct enough.
- **Drift guard overlap:** Using the same keywords or patterns across multiple agents' drift_guard rules. Each agent's failure modes are unique to its archetype.
- **HEXACO score clustering:** Assigning similar profiles to agents with different archetypes. The profiles should reflect genuinely different cognitive orientations.
- **Orphaned output keys:** AGENTS.md defining JSON output keys that the existing agent code does not produce or consume. Check the skeleton AGENTS.md for the established output contract keys.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML drift_guard validation | Manual parsing/checking | `parse_drift_guard_yaml()` in drift_eval.py | Already handles all edge cases: duplicate flag_ids, unknown types, invalid regex, missing required fields |
| Soul loading validation | Manual file-existence checks | `warmup_soul_cache()` | Loads all 5 agents, surfaces any missing files or parse errors at startup |
| Pairwise distance calculation | Complex matrix code | Simple Python script with math.sqrt and itertools.combinations | 10 pairs, 6 dimensions, straightforward arithmetic |
| Active persona extraction | Manual H1 parsing | `AgentSoul.active_persona` property | Already extracts first H1 from IDENTITY.md |

## Common Pitfalls

### Pitfall 1: Drift Guard YAML Indentation
**What goes wrong:** YAML indentation errors in fenced code blocks cause parse_drift_guard_yaml() to raise ValueError, which soul_loader catches and logs a warning -- silently disabling drift detection for that agent.
**Why it happens:** YAML is whitespace-sensitive and the block is embedded inside markdown fencing.
**How to avoid:** Use exactly the same indentation as AXIOM's existing YAML block. Test each SOUL.md through parse_drift_guard_yaml() before committing.
**Warning signs:** `warmup_soul_cache()` succeeds but `drift_rules` tuple is empty for an agent that should have rules.

### Pitfall 2: Regex Escaping in YAML
**What goes wrong:** Regex patterns with backslashes (like `\b`) need careful quoting in YAML. Double-quoted strings interpret `\b` as backspace; single-quoted or unquoted strings pass them through literally.
**Why it happens:** YAML string escaping rules differ from regex escaping rules.
**How to avoid:** Use double-quoted strings with doubled backslashes (`"\\b"`) as AXIOM does, or verify the regex compiles correctly via `re.compile()`.
**Warning signs:** drift_eval.py raises ValueError on invalid regex pattern.

### Pitfall 3: HEXACO-6 Distance Constraint Failure
**What goes wrong:** Designing archetype-realistic profiles first and then discovering that two agents are too close in HEXACO space (distance < 1.0).
**Why it happens:** Agents with adjacent functions (e.g., CASSANDRA and GUARDIAN both care about risk) may have similar profiles.
**How to avoid:** Design all 5 profiles simultaneously, compute all 10 pairwise distances before finalizing any individual profile. Adjust dimensions where agents share traits but differ in expression (e.g., CASSANDRA has high Emotionality for anxiety-driven vigilance; GUARDIAN has low Emotionality for stoic rule enforcement).
**Warning signs:** Any pairwise distance below 1.0 after profile assignment.

### Pitfall 4: Keyword Ratio Threshold Calibration
**What goes wrong:** Setting keyword_ratio thresholds too low causes false positives on normal agent output; too high makes the rule inert.
**Why it happens:** The ratio is computed as matching_tokens / total_tokens, where tokens are whitespace-split words. Multi-word phrases in the include list won't match via keyword_ratio (it does single-token matching).
**How to avoid:** Use keyword_ratio for single-word recency/certainty markers. Use keyword_any for multi-word phrases. Use regex for pattern matching. AXIOM's 0.08 threshold is a reasonable baseline.
**Warning signs:** keyword_ratio include list contains multi-word strings (these will never match since tokens are single words).

### Pitfall 5: Missing H1 in IDENTITY.md
**What goes wrong:** `active_persona` property falls back to agent_id (e.g., "bullish_researcher") instead of persona name (e.g., "MOMENTUM").
**Why it happens:** First line of IDENTITY.md is not `# PERSONA_NAME`.
**How to avoid:** First line of every IDENTITY.md must be `# {PERSONA_NAME}` (e.g., `# MOMENTUM`).
**Warning signs:** Soul-sync handshake uses directory name instead of persona name.

### Pitfall 6: Prose-Only Drift Guard Section (No YAML Block)
**What goes wrong:** The skeleton SOUL.md files have a `## Drift Guard` section with prose but no fenced YAML block. parse_drift_guard_yaml() returns empty tuple -- no drift rules active.
**Why it happens:** Skeletons were intentionally created as prose-only placeholders in Phase 15.
**How to avoid:** Every populated SOUL.md must have BOTH the prose description AND the fenced `yaml` block within the Drift Guard section.

## Code Examples

### Drift Guard YAML Reference (from AXIOM SOUL.md -- source of truth)

```yaml
drift_guard:
  version: 1
  rules:
    - flag_id: recency_bias
      type: keyword_ratio
      include: ["today", "latest", "just released", "this morning", "last week", "recent data", "past month"]
      threshold: 0.08
    - flag_id: narrative_capture
      type: keyword_any
      include: ["consensus expects", "markets have priced in", "widely anticipated", "priced into", "market consensus"]
    - flag_id: certainty_overreach
      type: regex
      pattern: "\\b(certainly|obviously|guaranteed|inevitably|without doubt)\\b"
```

### Validation Script (for pairwise HEXACO-6 distances)

```python
import math
from itertools import combinations

profiles = {
    "AXIOM":     [H, E, X, A, C, O],  # fill with actual values
    "MOMENTUM":  [H, E, X, A, C, O],
    "CASSANDRA": [H, E, X, A, C, O],
    "SIGMA":     [H, E, X, A, C, O],
    "GUARDIAN":  [H, E, X, A, C, O],
}

for (a, va), (b, vb) in combinations(profiles.items(), 2):
    d = math.sqrt(sum((x - y) ** 2 for x, y in zip(va, vb)))
    status = "OK" if d > 1.0 else "FAIL"
    print(f"{a} <-> {b}: {d:.3f} [{status}]")
```

### Validating Drift Guard Parse (post-authoring check)

```python
from src.core.drift_eval import parse_drift_guard_yaml
from pathlib import Path

for agent in ["bullish_researcher", "bearish_researcher", "quant_modeler", "risk_manager"]:
    soul_text = (Path("src/core/souls") / agent / "SOUL.md").read_text()
    rules = parse_drift_guard_yaml(soul_text)
    print(f"{agent}: {len(rules)} rules parsed")
    for r in rules:
        print(f"  - {r.flag_id} ({r.type})")
```

### Validating warmup_soul_cache (final gate)

```python
from src.core.soul_loader import load_soul, warmup_soul_cache, _KNOWN_AGENTS

warmup_soul_cache()
for agent_id in _KNOWN_AGENTS:
    soul = load_soul(agent_id)
    print(f"{soul.active_persona}: identity={len(soul.identity)}c, soul={len(soul.soul)}c, agents={len(soul.agents)}c, drift_rules={len(soul.drift_rules)}")
```

## Existing Content Inventory

### Files to MODIFY (expand from skeleton to full)

| File | Current Size | Target Size | Key Changes |
|------|-------------|-------------|-------------|
| `src/core/souls/bullish_researcher/SOUL.md` | ~150 words | ~450-550 words | Multi-paragraph Core Beliefs, drift_guard YAML block, detailed Voice, explicit Non-Goals |
| `src/core/souls/bullish_researcher/IDENTITY.md` | ~150 words | ~220-280 words | Deeper archetype, comparative advantage, peer relations |
| `src/core/souls/bullish_researcher/AGENTS.md` | ~100 words | ~300 words | Full JSON key specs, 5+ decision rules, detailed workflow |
| `src/core/souls/bearish_researcher/SOUL.md` | ~150 words | ~450-550 words | Same expansion pattern |
| `src/core/souls/bearish_researcher/IDENTITY.md` | ~150 words | ~220-280 words | Same expansion pattern |
| `src/core/souls/bearish_researcher/AGENTS.md` | ~100 words | ~300 words | Same expansion pattern |
| `src/core/souls/quant_modeler/SOUL.md` | ~150 words | ~450-550 words | Same expansion pattern |
| `src/core/souls/quant_modeler/IDENTITY.md` | ~150 words | ~220-280 words | Same expansion pattern |
| `src/core/souls/quant_modeler/AGENTS.md` | ~100 words | ~300 words | Same expansion pattern |
| `src/core/souls/risk_manager/SOUL.md` | ~150 words | ~450-550 words | Same expansion pattern |
| `src/core/souls/risk_manager/IDENTITY.md` | ~150 words | ~220-280 words | Same expansion pattern |
| `src/core/souls/risk_manager/AGENTS.md` | ~100 words | ~300 words | Same expansion pattern |

### Files to ADD content to (existing, append HEXACO-6 block)

| File | Change |
|------|--------|
| `src/core/souls/macro_analyst/SOUL.md` | Add `## Personality Profile` section with hexaco_6 YAML block (AXIOM's existing drift_guard rules unchanged) |

### Files NOT touched (out of scope)

| File | Reason |
|------|--------|
| `src/core/souls/bullish_researcher/USER.md` | Existing -- out of scope per CONTEXT.md |
| `src/core/souls/bearish_researcher/USER.md` | Existing -- out of scope per CONTEXT.md |
| `src/core/souls/quant_modeler/MEMORY.md` | Existing -- out of scope per CONTEXT.md |

### Files to UPDATE (non-soul)

| File | Change |
|------|--------|
| `.planning/ROADMAP.md` | Update Phase 23 success criterion #3: change ">3.0" to ">1.0 on normalized 0.0-1.0 scale" |
| `.planning/REQUIREMENTS.md` | Update PERS-05: change ">3.0" to ">1.0 on normalized 0.0-1.0 scale" |

## Drift Guard Design Guidance

### Per-Agent Failure Modes (for drift_guard rule design)

| Agent | Primary Failure Mode | Secondary Failure Mode | Suggested Rule Types |
|-------|---------------------|----------------------|---------------------|
| MOMENTUM | Thesis recycling (stale catalyst, no refresh) | Unbounded optimism (no risk acknowledgment) | keyword_ratio for recency words; keyword_any for blind optimism phrases |
| CASSANDRA | Catastrophism without evidence (unfounded doom) | Reflexive contrarianism (opposing for opposition's sake) | keyword_any for doom language; regex for certainty in negative predictions |
| SIGMA | Data mining without regime conditioning (overfit signals) | False precision (excessive decimal places, spurious accuracy) | keyword_ratio for overfit indicators; regex for false precision patterns |
| GUARDIAN | Threshold erosion under social pressure (loosening limits) | Scope creep into thesis evaluation (judging trade quality, not risk) | keyword_any for hedging/exception language; keyword_any for thesis-evaluation vocabulary |

## State of the Art

| Aspect | Current State | After Phase 23 |
|--------|--------------|----------------|
| AXIOM soul | Fully authored (~500 words, 3 drift rules) | Unchanged + HEXACO-6 block added |
| MOMENTUM soul | Skeleton (~150 words, no YAML) | Fully authored (~500 words, 2-3 drift rules, HEXACO-6) |
| CASSANDRA soul | Skeleton (~150 words, no YAML) | Fully authored (~500 words, 2-3 drift rules, HEXACO-6) |
| SIGMA soul | Skeleton (~150 words, no YAML) | Fully authored (~500 words, 2-3 drift rules, HEXACO-6) |
| GUARDIAN soul | Skeleton (~150 words, no YAML) | Fully authored (~500 words, 2-3 drift rules, HEXACO-6) |
| HEXACO-6 profiles | None | All 5 agents, pairwise distance >1.0 |
| ARS drift detection | Active for AXIOM only | Active for all 5 agents |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via `.venv/bin/python3.12 -m pytest`) |
| Config file | None (default discovery) |
| Quick run command | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py tests/core/test_drift_eval.py tests/core/test_soul_loader.py -x -q` |
| Full suite command | `.venv/bin/python3.12 -m pytest tests/core/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERS-01 | MOMENTUM has distinct personality sections | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py -x -q` | Partial (AXIOM-only tests exist; MOMENTUM tests needed) |
| PERS-02 | CASSANDRA has distinct personality sections | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py -x -q` | Partial |
| PERS-03 | SIGMA has distinct personality sections | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py -x -q` | Partial |
| PERS-04 | GUARDIAN has distinct personality sections | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py -x -q` | Partial |
| PERS-05 | HEXACO-6 pairwise distance >1.0 | unit | `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py -x -q` | No |
| PERS-06 | drift_guard YAML parses for all agents | unit | `.venv/bin/python3.12 -m pytest tests/core/test_soul_loader.py -x -q` | Partial (AXIOM drift parse tested; other agents need coverage) |

### Sampling Rate
- **Per task commit:** `.venv/bin/python3.12 -m pytest tests/core/test_persona_content.py tests/core/test_soul_loader.py -x -q`
- **Per wave merge:** `.venv/bin/python3.12 -m pytest tests/core/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/core/test_persona_content.py` -- extend with per-agent structural tests (MOMENTUM, CASSANDRA, SIGMA, GUARDIAN matching AXIOM's section structure)
- [ ] `tests/core/test_persona_content.py` -- add HEXACO-6 pairwise distance validation test
- [ ] `tests/core/test_persona_content.py` -- add drift_guard rule count and parseability tests for all 5 agents

## Open Questions

1. **HEXACO-6 block placement in SOUL.md**
   - What we know: The CONTEXT.md says "alongside drift_guard YAML" but drift_guard is inside `## Drift Guard` section
   - What's unclear: Whether to add a new `## Personality Profile` H2 section or embed within an existing section
   - Recommendation: Add new `## Personality Profile` section after `## Non-Goals` to keep it cleanly separated from drift_guard. This does not affect soul_loader (it reads the full file text) or drift_eval (it only searches for `## Drift Guard` section). The `public_soul_summary()` method filters for `_PEER_VISIBLE_SECTIONS` = {"Core Beliefs", "Voice", "Non-Goals"}, so a new section will be automatically excluded from peer summaries (correct behavior -- personality profile is internal metadata).

2. **ROADMAP.md and REQUIREMENTS.md threshold update**
   - What we know: CONTEXT.md says to update the >3.0 threshold to >1.0
   - Recommendation: Include this as a task in the plan -- update both files before or alongside content authoring

## Sources

### Primary (HIGH confidence)
- `src/core/soul_loader.py` -- AgentSoul dataclass, load_soul(), warmup_soul_cache(), _KNOWN_AGENTS, _PEER_VISIBLE_SECTIONS
- `src/core/drift_eval.py` -- DriftRule dataclass, parse_drift_guard_yaml() validation logic, evaluate_drift() matching logic, SUPPORTED_TYPES
- `src/core/souls/macro_analyst/SOUL.md` -- AXIOM fully authored reference (~500 words, 3 drift_guard rules)
- `src/core/souls/macro_analyst/IDENTITY.md` -- AXIOM identity reference (~220 words)
- `src/core/souls/macro_analyst/AGENTS.md` -- AXIOM agents contract reference (~300 words)
- `src/core/souls/{bullish,bearish,quant,risk}/` -- all skeleton files read directly
- `tests/core/test_persona_content.py` -- existing structural tests for AXIOM
- `tests/core/test_drift_eval.py` -- comprehensive drift rule parsing and evaluation tests

### Secondary (MEDIUM confidence)
- HEXACO-6 personality model dimensions -- based on established psychometric model (Ashton & Lee, 2004); dimension interpretations adapted for financial archetypes

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all infrastructure exists, no new code needed
- Architecture: HIGH -- AXIOM template fully establishes the pattern; skeletons already follow directory structure
- Pitfalls: HIGH -- drift_eval.py source code directly reveals all validation constraints
- HEXACO-6 design: MEDIUM -- dimension interpretations for financial archetypes are creative judgment, not established practice

**Research date:** 2026-03-09
**Valid until:** 2026-04-09 (stable -- content authoring phase, no dependency churn)
