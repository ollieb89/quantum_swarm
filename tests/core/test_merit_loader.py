"""Merit loader node tests — stubs for Plan 02 implementation."""
import pytest


@pytest.mark.skip(reason="Implemented in Plan 02")
def test_merit_loader_cold_start():
    """merit_loader populates state from DB; cold-start defaults to 0.5 for unknown agents."""
    pass


@pytest.mark.skip(reason="Implemented in Plan 02")
def test_merit_scores_field_no_accumulation():
    """merit_scores field in SwarmState survives LangGraph cycle without accumulation."""
    pass


@pytest.mark.skip(reason="Implemented in Plan 02")
def test_merit_loader_idempotent():
    """merit_loader skips DB load if merit_scores already populated (idempotency guard)."""
    pass
