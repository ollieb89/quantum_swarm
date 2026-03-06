# Phase 1: Foundation & Orchestration (L1) - Context

**Gathered:** March 6, 2026
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the skeletal hierarchical framework and inter-agent communication layer (L1 Orchestrator). This includes the core message routing, task delegation, and security guardrails necessary for the swarm to operate autonomously and safely.

</domain>

<decisions>
## Implementation Decisions

### L1 Strategic Orchestrator (ORCH-01)
- **Model:** Frontier-tier (e.g., Claude 3.5/3.7/4 or similar).
- **Execution Mode:** Suspension model. The L1 agent issues objectives, delegates, and suspends its active state to save context and costs. It only wakes for aggregation, consensus, or escalations.

### Inter-Agent Communication (ORCH-02)
- **Mechanism:** "Blackboard" pattern on the filesystem.
- **Format:** Markdown-based shared coordination state in a dedicated `data/inter_agent_comms/` (or similar) directory.
- **Locking:** Filesystem mutexes and atomic commits to prevent race conditions during concurrent agent access.

### Procedural Efficiency (ORCH-03, ORCH-04)
- **Deterministic Bypass:** Use `command-dispatch:` tool directive to execute procedural scripts (L3 tasks) directly without LLM invocation when appropriate.
- **Skill Discovery:** Progressive disclosure using YAML frontmatter in skill files located in the project's skill registry. L1 only loads specific skill definitions when semantically triggered.

### Security & Budgeting (SEC-01, SEC-02)
- **Sandboxing:** Implement "ClawGuard" verifiable guardrails to restrict agent shell access to authorized directories and tools.
- **Budgeting:** Programmatic budget ceilings enforced at the routing layer. Total token spend is tracked across the swarm, triggering a safety shutdown if thresholds are reached.

### Claude's Discretion
- Specific file naming conventions for the blackboard entries.
- Internal schema for the YAML skill metadata.
- Selection of the exact Docker/Sandbox image for ClawGuard.

</decisions>

<specifics>
## Specific Ideas
- The Orchestrator should scan metadata from `AGENTS.md` and `SOUL.md` to map swarm capabilities.
- Delegation from L1 to L2 should use the `sessions_send` command or an equivalent OpenClaw-native routing mechanism.
- The suspension model must include a robust state serialization/deserialization to ensure continuity when the L1 agent wakes.

</specifics>

<deferred>
## Deferred Ideas
- Level 2 specialized analysis (Macro/Quant) — Phase 2.
- Level 3 execution (Order Routing/Live API) — Phase 3.
- Adversarial Debate (Bull vs. Bear) — Phase 2.

</deferred>

---

*Phase: 01-foundation-orchestration-l1*
*Context gathered: March 6, 2026*