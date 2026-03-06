"""
LangChain Tool wrappers for injecting MemoryService into L2 ReAct agents.

Agent factory functions are also here to keep tool-binding logic in one place.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from langchain_core.tools import Tool

from src.memory.config import DEFAULT_SEARCH_K, MAX_HIT_CONTENT_CHARS

if TYPE_CHECKING:
    from src.memory.service import MemoryHit, MemoryService, MemorySource


def _format_hits(hits: list["MemoryHit"]) -> str:
    """Format MemoryHit list as structured text for agent tool output."""
    if not hits:
        return "No relevant memory found."

    lines: list[str] = []
    for i, hit in enumerate(hits, 1):
        meta = hit.metadata or {}
        lines.append(f"Memory result {i}")
        lines.append(
            f"Source: {hit.source.value} | "
            f"Timestamp: {meta.get('timestamp', 'unknown')} | "
            f"Document: {hit.document_id}"
        )
        if meta.get("symbol"):
            lines.append(f"Symbol: {meta['symbol']}")
        lines.append(f"Relevance: {hit.score:.2f}")
        content = hit.content[:MAX_HIT_CONTENT_CHARS]
        lines.append(f"Content: {content}")
        lines.append("")

    return "\n".join(lines).strip()


def make_memory_search_tool(
    memory: "MemoryService",
    source_filter: "MemorySource | None" = None,
    k: int = DEFAULT_SEARCH_K,
    name: str = "memory_search",
    description: str = "Search past trades, research, and market data stored in memory.",
) -> Tool:
    """
    Return a LangChain Tool wrapping MemoryService.search().

    Results are formatted as structured text for consistent model consumption.
    Results are deduplicated by document_id inside MemoryService.search().
    """

    def _search(query: str) -> str:
        hits = memory.search(query=query, source_filter=source_filter, k=k)
        return _format_hits(hits)

    return Tool(name=name, func=_search, description=description)


def make_trade_memory_search_tool(memory: "MemoryService", k: int = 3) -> Tool:
    """Opinionated wrapper that searches only trade memory."""
    from src.memory.service import MemorySource

    return make_memory_search_tool(
        memory,
        source_filter=MemorySource.TRADE,
        k=k,
        name="search_trade_memory",
        description="Search historical trade records and outcomes for similar setups.",
    )


def make_research_memory_search_tool(memory: "MemoryService", k: int = 3) -> Tool:
    """Opinionated wrapper that searches only research memory."""
    from src.memory.service import MemorySource

    return make_memory_search_tool(
        memory,
        source_filter=MemorySource.RESEARCH,
        k=k,
        name="search_research_memory",
        description="Search past research notes, analyst reports, and debate summaries.",
    )


def filter_hits_by_recency(
    hits: list["MemoryHit"],
    days: int = 30,
) -> list["MemoryHit"]:
    """
    Filter MemoryHits to only those with timestamp within the last `days` days.

    Used by L1 routing enrichment to enforce recency on retrieved context.
    Hits without a parseable timestamp are excluded.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = []
    for hit in hits:
        ts_str = (hit.metadata or {}).get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts >= cutoff:
                result.append(hit)
        except (ValueError, AttributeError):
            pass
    return result


def format_hits_for_l1_prompt(hits: list["MemoryHit"], max_hits: int = 3) -> str:
    """
    Format a small set of memory hits as compact context for the L1 routing prompt.

    Trims excerpts and caps at max_hits to avoid dominating the classifier.
    """
    if not hits:
        return ""

    lines = ["Recent similar setups from memory:"]
    for hit in hits[:max_hits]:
        meta = hit.metadata or {}
        excerpt = hit.content[:300].replace("\n", " ")
        lines.append(
            f"- [{meta.get('source', '?')}] {meta.get('symbol', '?')} @ "
            f"{meta.get('timestamp', '?')}: {excerpt}..."
        )
    return "\n".join(lines)
