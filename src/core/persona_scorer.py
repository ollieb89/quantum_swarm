"""
src.core.persona_scorer — PersonaScore 5D LLM-as-Judge evaluation.

Evaluates each L2 agent's output against their soul definition across
5 dimensions: Consistency, Tone, Logic, Depth, Bias. Produces a composite
score (simple average) used by KAMI for fidelity-weighted merit updates.

Phase 29: PersonaScore 5D + KAMI Fidelity Wiring.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from pydantic import BaseModel, Field

from src.core.circuit_breaker import CircuitBreaker
from src.core.db import ensure_pool_open
from src.core.soul_loader import AgentSoul, load_soul

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class PersonaScoreResult(BaseModel):
    """5-dimension persona fidelity score returned by LLM-as-Judge."""

    consistency: float = Field(ge=0.0, le=1.0)
    tone: float = Field(ge=0.0, le=1.0)
    logic: float = Field(ge=0.0, le=1.0)
    depth: float = Field(ge=0.0, le=1.0)
    bias: float = Field(ge=0.0, le=1.0)
    rationale: str

    @property
    def composite(self) -> float:
        """Simple average of the 5 dimension scores, rounded to 4 dp."""
        return round(
            (self.consistency + self.tone + self.logic + self.depth + self.bias) / 5,
            4,
        )


class PersonaScoreEntry(BaseModel):
    """Entry for a single agent in the cycle's persona score map."""

    soul_handle: str
    consistency: float
    tone: float
    logic: float
    depth: float
    bias: float
    composite: float
    rationale: str
    fallback: bool = False


# ---------------------------------------------------------------------------
# Handle mappings (duplicated from memory_writer -- Import Layer Law)
# ---------------------------------------------------------------------------

HANDLE_TO_AGENT_ID: dict[str, str] = {
    "AXIOM": "macro_analyst",
    "MOMENTUM": "bullish_researcher",
    "CASSANDRA": "bearish_researcher",
    "SIGMA": "quant_modeler",
}

HANDLE_TO_OUTPUT_FIELD: dict[str, str] = {
    "AXIOM": "macro_report",
    "MOMENTUM": "bullish_thesis",
    "CASSANDRA": "bearish_thesis",
    "SIGMA": "quant_proposal",
}

# ---------------------------------------------------------------------------
# Lazy LLM init (Gemini validates API key at instantiation)
# ---------------------------------------------------------------------------

_judge_llm = None


def _get_judge_llm():
    """Lazy-init the LLM-as-Judge with structured output."""
    global _judge_llm
    if _judge_llm is None:
        from langchain_google_genai import ChatGoogleGenerativeAI

        base = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)
        _judge_llm = base.with_structured_output(PersonaScoreResult)
    return _judge_llm


# ---------------------------------------------------------------------------
# Circuit breaker (separate instance from graph breaker)
# ---------------------------------------------------------------------------

_scorer_breaker = CircuitBreaker(threshold=3, cooldown_s=30)

# ---------------------------------------------------------------------------
# Judge prompt builder
# ---------------------------------------------------------------------------


def _build_judge_prompt(soul: AgentSoul, agent_output: dict, soul_handle: str) -> str:
    """Construct the LLM-as-Judge evaluation prompt.

    Includes full soul files and the agent's output, plus a rubric
    explaining each of the 5 scoring dimensions.
    """
    output_str = json.dumps(agent_output, indent=2, default=str)

    return f"""You are a persona fidelity evaluator. Your task is to score how well
an AI agent's output aligns with its defined persona (soul).

## Agent Identity (IDENTITY.md)
{soul.identity}

## Agent Soul (SOUL.md)
{soul.soul}

## Agent Context (AGENTS.md)
{soul.agents}

## Agent Output to Evaluate
Soul Handle: {soul_handle}
```json
{output_str}
```

## Scoring Rubric (0.0 = poor, 1.0 = excellent)

Score the agent's output on these 5 dimensions:

1. **Consistency** (0.0-1.0): How well does the output align with the agent's stated
   core beliefs, worldview, and analytical framework? Does it stay true to its
   defined perspective?

2. **Tone** (0.0-1.0): Does the writing voice match the agent's defined personality?
   Consider formality, confidence level, and communication style as specified in the
   soul definition.

3. **Logic** (0.0-1.0): How rigorous is the reasoning? Are conclusions well-supported
   by evidence? Does the analytical approach match what the agent's soul prescribes?

4. **Depth** (0.0-1.0): How thorough is the analysis? Does it cover the breadth and
   detail expected from this agent's role and expertise level?

5. **Bias** (0.0-1.0): Is the agent appropriately directional per its role? A bullish
   researcher should show bullish bias; a bearish researcher should show bearish bias.
   1.0 = well-calibrated directional stance matching the role definition.

Provide a brief rationale explaining your scores.
"""


# ---------------------------------------------------------------------------
# Single-agent evaluation
# ---------------------------------------------------------------------------


async def evaluate_agent(
    soul_handle: str,
    agent_output: dict | None,
    cycle_id: int,
) -> PersonaScoreResult | None:
    """Evaluate a single agent's output against its soul definition.

    Returns None if:
    - agent_output is None (degraded cycle skip)
    - Circuit breaker is open
    - LLM call fails (logs warning, does not raise)
    """
    if agent_output is None:
        logger.info("persona_scorer: skipping %s — agent output is None (degraded)", soul_handle)
        return None

    if not _scorer_breaker.check():
        logger.warning("persona_scorer: skipping %s — circuit breaker open", soul_handle)
        return None

    try:
        agent_id = HANDLE_TO_AGENT_ID[soul_handle]
        soul = load_soul(agent_id)
        prompt = _build_judge_prompt(soul, agent_output, soul_handle)
        result = await _get_judge_llm().ainvoke(prompt)
        _scorer_breaker.record_success()
        return result
    except Exception as exc:
        _scorer_breaker.record_failure()
        logger.warning(
            "persona_scorer: evaluation failed for %s in cycle %d: %s",
            soul_handle,
            cycle_id,
            exc,
        )
        return None


# ---------------------------------------------------------------------------
# Parallel evaluation of all agents
# ---------------------------------------------------------------------------


async def evaluate_all_agents(
    agent_outputs: dict[str, dict | None],
    cycle_id: int,
) -> dict[str, PersonaScoreEntry]:
    """Run persona evaluation for all 4 LLM agents in parallel.

    Uses asyncio.gather with return_exceptions=True. Failed evaluations
    fall back to the previous cycle's composite score (or 0.5 if none).
    """
    handles = list(HANDLE_TO_AGENT_ID.keys())
    tasks = [
        evaluate_agent(handle, agent_outputs.get(handle), cycle_id)
        for handle in handles
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    entries: dict[str, PersonaScoreEntry] = {}
    for handle, raw in zip(handles, raw_results):
        if isinstance(raw, PersonaScoreResult):
            entries[handle] = PersonaScoreEntry(
                soul_handle=handle,
                consistency=raw.consistency,
                tone=raw.tone,
                logic=raw.logic,
                depth=raw.depth,
                bias=raw.bias,
                composite=raw.composite,
                rationale=raw.rationale,
                fallback=False,
            )
        else:
            # Failure or None -- use fallback
            if isinstance(raw, Exception):
                logger.warning(
                    "persona_scorer: exception for %s in gather: %s", handle, raw
                )
            prev = await get_latest_persona_composite(handle)
            fallback_val = prev if prev is not None else 0.5
            entries[handle] = PersonaScoreEntry(
                soul_handle=handle,
                consistency=fallback_val,
                tone=fallback_val,
                logic=fallback_val,
                depth=fallback_val,
                bias=fallback_val,
                composite=fallback_val,
                rationale=f"Fallback from previous cycle (composite={fallback_val})",
                fallback=True,
            )

    return entries


# ---------------------------------------------------------------------------
# DB persistence
# ---------------------------------------------------------------------------


async def persist_persona_scores(
    cycle_id: int,
    scores: dict[str, PersonaScoreEntry],
) -> None:
    """Write persona scores to the persona_scores PostgreSQL table.

    Logs errors but does not raise -- evaluation persistence must not
    block cycle completion.
    """
    pool = await ensure_pool_open()
    if pool is None:
        logger.info("persona_scorer: DB unavailable, skipping persist")
        return

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                for entry in scores.values():
                    await cur.execute(
                        """
                        INSERT INTO persona_scores
                            (cycle_id, soul_handle, consistency, tone, logic,
                             depth, bias, composite, rationale)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            cycle_id,
                            entry.soul_handle,
                            entry.consistency,
                            entry.tone,
                            entry.logic,
                            entry.depth,
                            entry.bias,
                            entry.composite,
                            entry.rationale,
                        ),
                    )
    except Exception as exc:
        logger.error("persona_scorer: failed to persist scores for cycle %d: %s", cycle_id, exc)


async def get_latest_persona_composite(soul_handle: str) -> Optional[float]:
    """Return the most recent composite score for a soul_handle, or None."""
    pool = await ensure_pool_open()
    if pool is None:
        return None

    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT composite FROM persona_scores WHERE soul_handle = %s "
                    "ORDER BY scored_at DESC LIMIT 1",
                    (soul_handle,),
                )
                row = await cur.fetchone()
                return float(row[0]) if row else None
    except Exception as exc:
        logger.error("persona_scorer: failed to query composite for %s: %s", soul_handle, exc)
        return None
