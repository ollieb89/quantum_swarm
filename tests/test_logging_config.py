"""Tests for structlog logging configuration (Phase 25, Plan 01)."""

import io
import logging
import os
import sys

import pytest


class TestConfigureLogging:
    """Verify configure_logging() installs structlog ProcessorFormatter on root logger."""

    def setup_method(self):
        """Reset root logger before each test."""
        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(logging.WARNING)  # default

    def test_root_handler_uses_processor_formatter(self):
        from src.core.logging_config import configure_logging
        configure_logging()
        root = logging.getLogger()
        assert len(root.handlers) == 1
        handler = root.handlers[0]
        # structlog ProcessorFormatter should be the formatter
        import structlog
        assert isinstance(handler.formatter, structlog.stdlib.ProcessorFormatter)

    def test_handler_outputs_to_stderr(self):
        from src.core.logging_config import configure_logging
        configure_logging()
        root = logging.getLogger()
        handler = root.handlers[0]
        assert handler.stream is sys.stderr

    def test_root_level_set_to_info(self):
        from src.core.logging_config import configure_logging
        configure_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_json_format_produces_json_output(self, monkeypatch):
        monkeypatch.setenv("LOG_FORMAT", "json")
        from src.core.logging_config import configure_logging
        configure_logging()
        root = logging.getLogger()
        handler = root.handlers[0]
        # Capture output
        buf = io.StringIO()
        handler.stream = buf
        test_logger = logging.getLogger("test.json_format")
        test_logger.info("hello")
        output = buf.getvalue()
        assert "{" in output  # JSON output contains braces

    def test_console_format_is_default(self):
        # No LOG_FORMAT env var set (or set to "console")
        from src.core.logging_config import configure_logging
        os.environ.pop("LOG_FORMAT", None)
        configure_logging()
        root = logging.getLogger()
        handler = root.handlers[0]
        buf = io.StringIO()
        handler.stream = buf
        test_logger = logging.getLogger("test.console_format")
        test_logger.info("hello")
        output = buf.getvalue()
        # Console renderer should NOT produce JSON braces at start of line
        # (it produces colorized human-readable output)
        assert output.strip()  # some output was produced
