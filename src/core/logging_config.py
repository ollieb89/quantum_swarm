"""
src.core.logging_config -- Structured logging configuration via structlog.

Provides:
    configure_logging() — Replaces root logger handlers with structlog ProcessorFormatter.

Logs go to stderr so stdout remains clean for CycleSnapshot JSON output.

Environment variables:
    LOG_FORMAT: "json" for JSONRenderer, anything else (default "console") for ConsoleRenderer.
"""

import logging
import os
import sys

import structlog


def configure_logging() -> None:
    """Configure stdlib logging to emit structured output via structlog ProcessorFormatter.

    Replaces all existing root logger handlers with a single StreamHandler(stderr)
    formatted by structlog's ProcessorFormatter.

    JSON mode (LOG_FORMAT=json) is intended for production log aggregation.
    Console mode (default) provides colorized human-readable output for development.
    """
    log_format = os.environ.get("LOG_FORMAT", "console").lower()

    shared_processors: list[structlog.types.Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ExtraAdder(),
    ]

    if log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
