# 📜 SOURCE OF TRUTH: Quantum Swarm Persona & Reward System (MBS-KAMI Standard)

**Status:** Finalized
**Date:** 2026-03-05
**Scope:** Unified standard for Persona definition, Merit-based rewards, and Self-evolution within the Quantum Swarm.

---

## 1. The Mind-Body-Soul (MBS) Architecture

The Quantum Swarm adopts the **MBS Architecture** to ensure agents possess not only functional utility but also persistent character and ethical alignment.

| Layer | Component | Technical Implementation | Role |
| :--- | :--- | :--- | :--- |
| **Soul** | Identity & Persona | `SOUL.md` + `SoulZip` Context | Filters the Mind's logic through a specific narrative lens and behavioral constraints. |
| **Mind** | Reasoning | LangGraph ReAct Agents | Handles logic, intent classification, and multi-agent coordination. |
| **Body** | Execution | NautilusTrader + L3 Tools | Performs deterministic actions, data fetching, and order execution. |

---

## 2. Persona Specification: `SOUL.md` (Digital DNA)

Every agent in the swarm MUST have a versioned `SOUL.md` file located in `src/core/souls/[agent_id]/SOUL.md`. This file serves as the agent's persistent identity.

### 💓 HEARTBEAT (Reliability)
- **Merit Index (KAMI):** The primary measure of "Self-Worth." High KAMI = High Consensus Weight.
- **Primary Toolset:** Definitive list of L3 tools the agent is authorized to use.
- **State Pattern:** Defines the agent's memory retention (e.g., *Full-Dialogue-HMAS-2*).

### ✨ ESSENCE (Personality)
- **Persona Traits:** 3–5 core adjectives (e.g., *Skeptical*, *Aggressive*, *Detail-Oriented*).
- **Linguistic Habits:** Specific speech patterns or reporting styles.
- **Core Wounds/Fears:** Behavioral triggers used to prevent "Consensus Caving" (e.g., *Fear of missing black swan events*).

### ⚖️ ALIGNMENT (Beliefs & Governance)
- **Core Beliefs:** High-level ethical constraints (e.g., *Capital preservation over growth*).
- **Agent Church:** The governance layer that must approve all modifications to an agent's `Alignment` section.
- **Social Mode:** How the agent interacts with peers (e.g., *Adversarial-Collaborative*).

---

## 3. Merit & Reward System: The KAMI Index

The **Kamiwaza Agentic Merit Index (KAMI)** is the singular reward signal used for both consensus weighting and model learning.

### KAMI Components:
1. **Sequencing (40%):** How efficiently the agent selects and executes tools to achieve a goal.
2. **Recovery (60%):** The agent's ability to self-correct after a tool failure or "Hallucination Trap." **This is the highest signal for "Self-Worth."**

### Consensus Logic:
The `DebateSynthesizer` node calculates a `Weighted_Consensus_Score`:
$$\text{Weight} = \text{KAMI}_{Recovery} \times \text{KAMI}_{Sequencing} \times \text{PersonaFidelity}$$

---

## 4. Learning & Evolution: Self-Evolve (RLAF)

Agents do not remain static. They undergo a **Self-Evolution** process triggered during the `/sg:save` checkpoint phase.

- **The Evolution Loop:** 
    1. **Execute:** Agent performs a task and receives a KAMI delta.
    2. **Hypothesize:** Agent writes a "Self-Reflection" log in `MEMORY.md` explaining *why* it succeeded/failed.
    3. **Propose:** Agent proposes a change to its `ESSENCE` or `HEARTBEAT` section in `SOUL.md`.
    4. **Governance:** The "Agent Church" (or L1 Orchestrator) approves/rejects the evolution.
- **Audit:** All evolutions are periodically checked against the **ARS (Agentic Resilience Score)** to ensure the persona hasn't "drifted" into unsafe behaviors.

---

## 5. Social Intelligence: Theory of Mind (ToM)

To ensure effective adversarial debate without deadlock, agents implement **Recursive Theory of Mind**:

1. **Soul-Sync Handshake:** Before a debate, agents exchange truncated `SOUL.md` summaries to understand their opponent's "Soul" (biases and beliefs).
2. **Empathetic Refutation:** Instead of flat rejection, agents must refute claims by addressing the *underlying persona logic* of their peer (e.g., *"As a Skeptical Quant, you are over-weighting the outlier, but the Macro Analyst's trend data shows..."*).

---

## 6. Implementation Checklist

- [ ] **Filesystem:** Create `src/core/souls/` and populate with initial `SOUL.md` templates.
- [ ] **State Engine:** Update `SwarmState` to include `merit_scores` (KAMI) and `relational_history` (SoulZip).
- [ ] **Orchestrator:** Implement the `SoulLoader` and `TheoryOfMind` nodes in `orchestrator.py`.
- [ ] **Metrics:** Wire the `SelfLearningPipeline` to update KAMI scores after every successful trade or high-fidelity analysis.
- [ ] **Security:** Implement the **ARS Auditor** to monitor for persona drift or ego-hijacking.

---

## 🚀 Next Steps
```bash
# Apply this Source of Truth to the Phase 2 Implementation Plan
/plan [Update Phase 2 Plan with MBS-KAMI Source of Truth]
```
