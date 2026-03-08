import pytest
from src.core.soul_loader import load_soul


@pytest.fixture(autouse=True)
def clear_soul_caches():
    """Clear lru_cache on load_soul before and after every test.

    Scoped to tests/core/ only — does not affect the 244 existing tests.
    Extended explicitly by future phases when new lru_cached soul functions exist.
    """
    load_soul.cache_clear()
    yield
    load_soul.cache_clear()
