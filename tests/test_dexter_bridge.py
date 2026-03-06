"""Dexter bridge unit tests — stubs."""
import pytest


@pytest.mark.xfail(reason="stub — 03-01 implements Dexter bridge")
def test_dexter_success():
    """Mocked subprocess returns Markdown string."""
    from src.tools.dexter_bridge import invoke_dexter
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="stub — 03-01 implements Dexter bridge")
def test_dexter_timeout():
    """asyncio.wait_for raises TimeoutError after 90s (mocked)."""
    from src.tools.dexter_bridge import invoke_dexter
    pytest.fail("not implemented")


@pytest.mark.xfail(reason="stub — 03-01 implements Dexter bridge")
def test_dexter_missing_env_vars():
    """Returns graceful FundamentalsData with unavailable message when env vars missing."""
    from src.tools.dexter_bridge import invoke_dexter
    pytest.fail("not implemented")
