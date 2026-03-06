"""
src.tools.dexter_bridge — Async subprocess wrapper for the Dexter CLI agent.

Provides:
    invoke_dexter(query) -> str       — raises EnvironmentError / TimeoutError / RuntimeError
    invoke_dexter_safe(query, symbol) -> FundamentalsData — never raises; degrades to mock

Dexter is a TypeScript/Bun agent at src/agents/dexter/ that accepts a --query flag
and writes Markdown fundamental research to STDOUT.

Pattern: Pattern 3 from Phase 3 RESEARCH.md — asyncio.create_subprocess_exec with
asyncio.wait_for timeout, never subprocess.run (would block LangGraph event loop).
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Dexter lives two levels up from this file: src/tools/ -> src/ -> project root,
# then down to agents/dexter/
DEXTER_DIR = Path(__file__).parent.parent / "agents" / "dexter"

DEXTER_TIMEOUT = 90  # seconds — per Phase 3 RESEARCH.md and CONTEXT.md decision

# Env vars required by the Dexter TypeScript agent (checked in its own .env)
_REQUIRED_ENV_VARS = (
    "FINANCIAL_DATASETS_API_KEY",
    "EXASEARCH_API_KEY",
    "ANTHROPIC_API_KEY",
)


# ---------------------------------------------------------------------------
# Environment validation
# ---------------------------------------------------------------------------


def _check_dexter_env() -> list[str]:
    """Return a list of missing required Dexter environment variable names.

    Checks os.environ first, then falls back to reading the Dexter .env file
    using python-dotenv so that variables set only in that file are detected.
    """
    # Try to load Dexter's own .env file without modifying the main process env
    dexter_env_path = DEXTER_DIR / ".env"
    env_snapshot: dict[str, str] = dict(os.environ)

    if dexter_env_path.exists():
        try:
            from dotenv import dotenv_values  # type: ignore[import-untyped]

            dotenv_vars = dotenv_values(dexter_env_path)
            env_snapshot.update({k: v for k, v in dotenv_vars.items() if v})
        except ImportError:
            # python-dotenv not installed — fall back to os.environ only
            pass

    return [var for var in _REQUIRED_ENV_VARS if not env_snapshot.get(var)]


# ---------------------------------------------------------------------------
# Core async bridge
# ---------------------------------------------------------------------------


async def invoke_dexter(query: str) -> str:
    """Invoke Dexter CLI asynchronously and return Markdown STDOUT.

    Args:
        query: Natural-language research query passed to Dexter via --query flag.

    Returns:
        Decoded STDOUT string (Markdown format).

    Raises:
        EnvironmentError: One or more required env vars are missing.
        TimeoutError: Dexter process exceeded DEXTER_TIMEOUT seconds.
        RuntimeError: Dexter process exited with a non-zero return code.
    """
    missing = _check_dexter_env()
    if missing:
        raise EnvironmentError(
            f"Dexter env vars missing: {', '.join(missing)}. "
            f"Set them in {DEXTER_DIR / '.env'} or export them before running."
        )

    logger.info("Invoking Dexter for query: %s", query[:80])

    proc = await asyncio.create_subprocess_exec(
        "bun",
        "run",
        "src/index.tsx",
        "--query",
        query,
        cwd=str(DEXTER_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=DEXTER_TIMEOUT
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise TimeoutError(
            f"Dexter exceeded {DEXTER_TIMEOUT}s timeout for query: {query[:80]}"
        )

    if proc.returncode != 0:
        error_detail = stderr.decode(errors="replace") if stderr else "no stderr"
        raise RuntimeError(
            f"Dexter failed (exit {proc.returncode}): {error_detail}"
        )

    return stdout.decode(errors="replace")


# ---------------------------------------------------------------------------
# Safe wrapper with graceful fallback
# ---------------------------------------------------------------------------


async def invoke_dexter_safe(query: str, symbol: str) -> "FundamentalsData":
    """Invoke Dexter and return FundamentalsData; never raises.

    Catches EnvironmentError, TimeoutError, and RuntimeError, returning a
    FundamentalsData with raw_markdown describing the failure reason.

    Args:
        query: Research query string.
        symbol: Ticker symbol (used to populate FundamentalsData.symbol).

    Returns:
        FundamentalsData — either real Dexter output or a graceful fallback.
    """
    from src.models.data_models import FundamentalsData

    now = datetime.now(tz=timezone.utc)

    try:
        markdown = await invoke_dexter(query)
        return FundamentalsData(
            symbol=symbol,
            raw_markdown=markdown,
            summary=None,
            timestamp=now,
            source="dexter",
        )
    except EnvironmentError as exc:
        reason = f"missing env vars: {exc}"
        logger.warning("Dexter unavailable — %s", reason)
    except TimeoutError as exc:
        reason = f"timeout after {DEXTER_TIMEOUT}s"
        logger.warning("Dexter timeout — %s", exc)
    except RuntimeError as exc:
        reason = f"process error: {exc}"
        logger.warning("Dexter runtime error — %s", exc)
    except Exception as exc:  # noqa: BLE001
        reason = f"unexpected error: {exc}"
        logger.warning("Dexter unexpected error — %s", exc)

    return FundamentalsData(
        symbol=symbol,
        raw_markdown=f"Dexter unavailable: {reason}",
        summary=None,
        timestamp=now,
        source="dexter",
    )
