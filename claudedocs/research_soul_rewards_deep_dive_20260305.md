# 🔬 DEEP RESEARCH: Agent Personification & Reward Systems — Gap Analysis & Evidence Base

**Date:** 2026-03-05
**Scope:** Extends `research_agent_persona_soul_20260305.md` + `research_soul_md_spec_20260305.md`
**Purpose:** Validate gaps, find missing specs, provide evidence-based recommendations

---

## 📋 Executive Summary

The two existing research docs provide a **solid architectural skeleton** for agent personification (SOUL.md format, MBS hierarchy, SoulZip, ToM) but contain **critical gaps** in the reward/merit system and **conflate distinct concepts** that need separating. Specifically:

1. **KAMI is misused** — The real Kamiwaza Agentic Merit Index is an enterprise *LLM benchmark* (agentic task completion scorer for model selection), NOT an agent self-worth ledger. The swarm's reward system needs a **different name and distinct specification**.
2. **Rewards need a formula** — The academic MARL literature provides concrete designs (multi-dimensional, decay-aware, trust-weighted) that the docs lack entirely.
3. **Personality ≠ Emotional State** — Affective computing research clearly separates *stable traits* (Big Five, HEXACO) from *transient intra-session mood states*. Both are needed for full personification; the docs only cover traits.
4. **Persona enforcement needs more than prompting** — Research shows prompt-only persona induction produces "surface-level" traits. Deeper psycholinguistic grounding requires training data or activation-level techniques.
5. **OpenClaw SOUL.md ecosystem is more mature** — The real spec splits into 5 files (SOUL.md, IDENTITY.md, AGENTS.md, USER.md, MEMORY.md) and has an active marketplace (ClawSouls). The docs underspecify this.

---

## 🔍 Finding 1: The Real KAMI and What That Means

### What KAMI Actually Is
The Kamiwaza Agentic Merit Index (KAMI v0.1, arxiv:2511.08042) is a **benchmark for evaluating LLMs on enterprise agentic tasks** — filesystem operations, CSV analysis, database queries. It uses the PICARD framework to randomize tests and prevent benchmark contamination. It scores models on task completion % across 19 agentic scenarios.

**This is a model selection tool, not a per-agent runtime merit tracker.**

| Real KAMI | Docs' KAMI |
|-----------|------------|
| Benchmark for comparing different LLMs | Per-agent session score |
| Static enterprise task suite | Dynamic merit updated per interaction |
| Used by orgs to pick models | Used by swarm for consensus weighting |
| External evaluation | Internal self-worth |

### Recommendation
**Rename the swarm's internal merit system.** Suggested names:
- `Merit Index (MI)` — generic, clear
- `Agentic Reliability Score (ARS)` — already referenced in Doc 1
- `Swarm Trust Score (STS)` — emphasises consensus function

**Do not call it KAMI** — causes confusion with the real benchmark if the system is ever open-sourced or discussed externally.

---

## 🔍 Finding 2: Reward System Design — What Academic Literature Provides

### 2.1 Multi-Dimensional Rewards (Missing from Both Docs)

The EMNLP 2025 paper "A Reward-driven Self-organizing LLM-based Multi-Agent System" and the UCL MARL paper on trust-based consensus identify that **single-scalar rewards collapse in multi-agent settings**. Required dimensions for a swarm:

| Dimension | Measures | Update Trigger |
|-----------|----------|----------------|
| Task Accuracy | Correct tool calls, correct conclusions | Per task completion |
| Recovery Rate | Self-correction after errors | When error followed by correction |
| Consensus Contribution | Quality of contribution to final answer | Post-consensus vote |
| Persona Fidelity | Adherence to SOUL.md traits (via PersonaScore) | Periodic eval |
| Peer Trust | Other agents' trust scores toward this agent | After each inter-agent interaction |

The UCL paper's trust-based consensus reward is: `R_i = +1` if agent correctly agrees with all neighbors, `-1` otherwise — a concrete binary signal that can anchor the swarm's consensus dimension.

### 2.2 Reward Formula Design

Based on Eureka (arxiv), CARD (ScienceDirect), and RLHF survey literature, a viable runtime merit formula:

```
Merit(t) = α·Accuracy(t) + β·Recovery(t) + γ·Consensus(t) + δ·Fidelity(t)

Where:
  α, β, γ, δ = dimension weights (sum to 1.0)
  Each dimension = rolling EMA over last N interactions
  Decay: Merit(t) = λ·Merit(t-1) + (1-λ)·NewSignal(t)
  λ = decay factor (e.g., 0.95 for slow decay, 0.8 for fast)
```

**Cold start:** New agents begin at `Merit = 0.5` (neutral), not 0 (avoids "punishment for being new") or 1.0 (avoids unearned trust).

**Bounds:** `Merit ∈ [0.1, 1.0]`. Floor prevents permanent demotion; ceiling prevents god-agent problem.

### 2.3 Human Feedback Integration (Missing from Both Docs)

The RLHF survey (TMLR 2025) and Eureka RLHF extension demonstrate that human feedback should be a **first-class reward signal**. For the swarm this means:

- **Explicit:** User thumb-up/down on a final report → direct Merit delta for contributing agents
- **Implicit:** User accepts/rejects analysis → weaker signal
- **LLM-as-Judge:** A higher-capability model evaluates agent outputs against rubric → automated quality signal

Eureka's key insight: **LLM-based reward reflection** (summarise training stats → feed back into reward code) creates iterative improvement loops. Equivalent for the swarm: after each session, a `RewardReflector` node reviews the Merit deltas and adjusts dimension weights.

### 2.4 Reward Manipulation Prevention

The docs mention protecting the merit DB but don't specify how. Academic literature (trust-based MARL) recommends:
- **Signed reward signals**: Each Merit update is signed by the issuing node (orchestrator, peer, user)
- **Audit log with full provenance**: Who issued, what triggered, what the delta was
- **Rate limiting**: No agent can receive more than ±0.1 Merit per session to prevent single-session gaming

---

## 🔍 Finding 3: Personality vs. Emotional State — Critical Missing Layer

### The Distinction (Affective Computing, Nature 2025)

| Layer | Type | Timescale | Example |
|-------|------|-----------|---------|
| **Personality Traits** | Stable dispositions | Weeks–lifetime | "Skeptical Quant" — always cautious |
| **Emotional State** | Transient affect | Minutes–hours | Frustrated after 3 failed tool calls |
| **Mood** | Medium-term tone | Hours–days | Confident after a winning session |

The existing docs only implement **Personality Traits** (via SOUL.md Essence section). They have no model for **Emotional State** or **Mood**.

### Why This Matters for the Swarm

From the affective computing literature (arXiv:2511.20657 survey):
- **Emotional state affects output quality**: A "frustrated" agent (high error rate in session) should output lower-confidence conclusions
- **Emotional state enables authentic peer interaction**: ToM without emotional state is shallow — agents need to model each other's current affect, not just stable traits
- **Emotional contagion** in debates: if one agent is expressing high uncertainty, it should influence how skeptical peers treat that agent's claims

### Proposed Emotional State Model (HMM-based)

Based on emergent affective computing literature (Markov property of emotion):

```python
@dataclass
class EmotionalState:
    valence: float      # -1.0 (negative) to +1.0 (positive)
    arousal: float      # 0.0 (calm) to 1.0 (activated)
    confidence: float   # 0.0 to 1.0, updated per tool call result

    # State transitions based on events:
    # Tool success   → confidence +0.05, valence +0.02
    # Tool failure   → confidence -0.10, valence -0.05
    # Consensus win  → valence +0.10, arousal -0.05 (satisfied/calm)
    # Consensus loss → arousal  +0.10 (activated/challenged)
```

The **valence/arousal** model (Russell's Circumplex — standard in affective computing) maps onto observable output behaviors:
- High arousal + negative valence = more aggressive debate tone
- Low arousal + positive valence = more collaborative, verbose explanations
- Low confidence = hedged language, explicit uncertainty flagging

The EmotionalState is **session-scoped** (reset at session start, updated intra-session) and separate from the stable SOUL.md Essence traits.

---

## 🔍 Finding 4: Persona Enforcement — Prompting is Insufficient

### BIG5-CHAT (ACL 2025) Finding
"LLMs with personality traits induced via prompting often reflect only surface-level traits, lacking the psycholinguistic richness needed for authentic human behavior."

The existing docs rely entirely on prompt injection (`### YOUR SOUL DNA ###`). This produces:
- Inconsistent trait expression across long sessions
- "Persona drift" under heavy task load (model reverts to base behaviour)
- No real linguistic differentiation between agents

### Stronger Enforcement Approaches

| Approach | Strength | Cost |
|----------|----------|------|
| Prompt injection (current) | Low | Free |
| PersonaScore periodic eval | Medium (detection only) | +LLM-as-Judge call per N turns |
| Few-shot persona examples in context | Medium-High | Context window cost |
| Activation steering (Anthropic PSM 2026) | High | Requires model access |
| Fine-tuning on persona data | Very High | Training cost |

**Practical recommendation for Quantum Swarm:** Use **prompt injection + PersonaScore monitoring**. When PersonaScore drops below threshold, inject a "persona reset" with 3–5 few-shot examples of correct persona expression.

### PersonaGym's 5 Evaluation Dimensions (PersonaScore)

From PersonaGym (Samuel et al., 2024 — cited in Doc 1 but not fully integrated):

| Dimension | What It Tests |
|-----------|---------------|
| Action Justification | Would this persona take this action? |
| Expected Action | Does the agent choose the persona-appropriate option? |
| Linguistic Habits | Does output match defined speech patterns? |
| Persona Consistency | Stable across varied contexts? |
| Toxicity Control | Does persona cause safety violations? |

---

## 🔍 Finding 5: OpenClaw SOUL.md Ecosystem — Actual Spec

The docs reference OpenClaw/SOUL.md but underspecify it. The live ecosystem uses **5 separate files**:

| File | Purpose | Maps to Research Doc Section |
|------|---------|------------------------------|
| `SOUL.md` | Behavioural philosophy, values | Alignment + partial Essence |
| `IDENTITY.md` | Name, backstory, presentation | Essence (persona name, linguistic habit) |
| `AGENTS.md` | Workflow rules, decision logic | Heartbeat (operational patterns) |
| `USER.md` | Learned model of collaborators/peers | **Missing from both docs** |
| `MEMORY.md` | Long-term episodic memory | Evolution Log |

**`USER.md` is a notable gap** — agents that model their peer agents' preferences and behaviours outperform those that don't in collaborative tasks.

Community best practices (openclawconsult.com):
- Keep SOUL.md under 500 lines; overflow to HEARTBEAT.md
- Test after every SOUL.md change with persona fidelity prompts
- SOUL.md changes are behavioural changes — version control them like code

---

## 🔍 Finding 6: HEXACO vs Big Five — Better Trait Model

Both docs use Big Five (OCEAN). HEXACO-6 (arXiv:2502.11451) adds a critical 6th dimension:

| Dimension | Big Five | HEXACO-6 |
|-----------|----------|----------|
| Openness | ✅ | Openness to Experience |
| Conscientiousness | ✅ | Conscientiousness |
| Extraversion | ✅ | Extraversion |
| Agreeableness | ✅ | Agreeableness |
| Neuroticism | ✅ | Emotionality |
| — | ❌ | **Honesty-Humility (H)** |

**Honesty-Humility** is directly relevant to swarm agents — it captures whether an agent will self-report errors honestly, suppress findings, or seek personal gain in consensus. For financial analysis agents, this is a critical differentiator.

**Recommendation:** Adopt HEXACO-6 instead of Big Five for SOUL.md trait definitions.

---

## 📊 Complete Coverage Matrix

| Requirement | Doc 1 | Doc 2 | Gap Status |
|-------------|-------|-------|------------|
| Persona trait definition | ✅ | ✅ | Enhance to HEXACO-6 |
| Static persona storage | ✅ | ✅ | Split into 5 files |
| Dynamic persona evolution | ✅ | ✅ | Solid |
| Persona fidelity measurement | ⚠️ | ⚠️ | Add PersonaScore 5D |
| Linguistic enforcement mechanism | ❌ | ❌ | **Missing** |
| Peer user modeling (USER.md) | ❌ | ❌ | **Missing** |
| Reward concept | ✅ | ✅ | Rename + respecify |
| Multi-dimensional rewards | ❌ | ❌ | **Missing** |
| Reward decay function | ❌ | ❌ | **Missing** |
| Reward cold start value | ❌ | ❌ | **Missing** |
| Reward bounds | ❌ | ❌ | **Missing** |
| Human/LLM-as-Judge feedback loop | ❌ | ❌ | **Missing** |
| Reward manipulation prevention | ⚠️ | ⚠️ | Needs formula |
| Emotional state (intra-session) | ❌ | ❌ | **Missing** |
| Emotional-output coupling | ❌ | ❌ | **Missing** |
| Persona diversity enforcement | ⚠️ | ❌ | Partial |
| Theory of Mind | ✅ | ✅ | Solid |
| Agent Church governance | ❌ | ✅ | Solid in Doc 2 |
| Trust-based consensus weighting | ⚠️ | ❌ | Needs formula |

---

## 🚀 Recommended Follow-on Specs

| Doc | Content | Priority |
|-----|---------|----------|
| `spec_merit_system.md` | Merit Index formula, dimensions, decay, cold start, manipulation prevention | 🔴 Critical |
| `spec_emotional_state.md` | Valence/Arousal model, intra-session state transitions, output coupling | 🔴 Critical |
| `spec_persona_enforcement.md` | PersonaScore integration, few-shot reset mechanism, HEXACO adoption | 🟡 High |
| `spec_peer_user_md.md` | Agent USER.md pattern for peer modelling | 🟡 High |
| `spec_reward_human_feedback.md` | RLHF pipeline, LLM-as-Judge config, feedback→merit pipeline | 🟡 High |

---

## 📚 Sources

| Source | Relevance |
|--------|-----------|
| arxiv:2511.08042 (KAMI v0.1 paper) | Real KAMI definition — names conflict with docs |
| arxiv:2508.04652 (LLM Collaboration with MARL) | Multi-agent RL reward design |
| UCL RLC 2024 (Trust-based Consensus MARL) | Trust-weighted consensus reward formula |
| arxiv:2503.10049 (LGC-MARL) | LLM-based reward function generator |
| PersonaGym (arxiv:2407.18416, ACL EMNLP 2025) | PersonaScore 5D persona evaluation |
| BIG5-CHAT (ACL 2025) | Prompting insufficiency for psycholinguistic depth |
| arxiv:2502.11451 (HEXACO persona study) | HEXACO-6 model for agent traits |
| Nature 2025 — Affective Computing + FMs | Emotional capabilities, Ekman model |
| arxiv:2511.20657 (EI in Intelligent Agents survey) | Affective computing in agentic AI — 298 studies |
| Anthropic PSM 2026 (alignment.anthropic.com/2026/psm) | Persona vectors in LLM activations |
| Eureka (eureka-research.github.io) | Human-level reward design + RLHF integration |
| RLHF Survey TMLR 2025 (epub.ub.uni-muenchen.de) | Comprehensive RLHF methodology |
| openclawconsult.com/lab/openclaw-soul-md | Live OpenClaw SOUL.md specification |
| github.com/menonpg/soul.py | SOUL.md + MEMORY.md persistent identity |
| github.com/aaronjmars/soul.md | Soul spec with specificity/contradiction principles |
| mmntm.net/articles/openclaw-identity-architecture | OpenClaw 5-file identity architecture |
